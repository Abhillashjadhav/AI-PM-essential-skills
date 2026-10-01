"""Optional fetcher for public pages the owner named explicitly.

Not a search engine. It refuses local/private network addresses, honours
robots.txt, never sends credentials or cookies, and returns page text as
*data* with its source attribution.
"""

from __future__ import annotations

import ipaddress
import socket
import time
import urllib.error
import urllib.request
import urllib.robotparser
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urlsplit

from .contracts import utc_now

USER_AGENT = "AI-PM-Model-Router/1.0 (+local owner-requested fetch)"
MAX_BYTES = 2 * 1024 * 1024


@dataclass
class FetchResult:
    url: str
    retrieved_at: str
    ok: bool
    title: str | None = None
    text: str | None = None
    error: str | None = None
    status: int | None = None
    attribution: str | None = None
    notes: list[str] = field(default_factory=list)


class FetchRefused(ValueError):
    pass


def check_public_url(url: str, resolver=socket.getaddrinfo) -> None:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        raise FetchRefused(f"only http(s) URLs are fetched, not {parts.scheme or '(none)'}")
    if parts.username or parts.password:
        raise FetchRefused("URLs with embedded credentials are refused")
    host = parts.hostname
    if not host:
        raise FetchRefused("URL has no host")
    if host.lower() in {"localhost"} or host.lower().endswith((".local", ".internal", ".localhost")):
        raise FetchRefused(f"host {host} is a local name")
    try:
        infos = resolver(host, parts.port or (443 if parts.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise FetchRefused(f"could not resolve {host}: {exc}") from exc
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
            or address.is_multicast
            or address.is_unspecified
        ):
            raise FetchRefused(f"{host} resolves to non-public address {address}")


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "template", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title: str | None = None
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        if tag == "title":
            self._in_title = True
        if tag in {"p", "br", "li", "h1", "h2", "h3", "h4", "tr", "div"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title = (self.title or "") + data.strip()
        elif not self._skip:
            self.parts.append(data)

    def text(self) -> str:
        lines = [" ".join(line.split()) for line in "".join(self.parts).splitlines()]
        return "\n".join(line for line in lines if line)


def html_to_text(html: str) -> tuple[str | None, str]:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.title, parser.text()


def fetch_public(url: str, *, timeout: float = 15.0, opener=None, resolver=socket.getaddrinfo) -> FetchResult:
    retrieved = utc_now()
    try:
        check_public_url(url, resolver)
    except FetchRefused as exc:
        return FetchResult(url=url, retrieved_at=retrieved, ok=False, error=f"refused: {exc}")
    parts = urlsplit(url)
    robots = urllib.robotparser.RobotFileParser(f"{parts.scheme}://{parts.netloc}/robots.txt")
    try:
        robots.read()
        if not robots.can_fetch(USER_AGENT, url):
            return FetchResult(url=url, retrieved_at=retrieved, ok=False, error="robots.txt disallows fetching this page")
    except (urllib.error.URLError, OSError):
        pass  # unreachable robots.txt: treated as no restriction, recorded below
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    opener = opener or urllib.request.build_opener(_NoRedirectToPrivate(resolver))
    started = time.monotonic()
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read(MAX_BYTES + 1)
            status = getattr(response, "status", None)
            ctype = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        return FetchResult(url=url, retrieved_at=retrieved, ok=False, status=exc.code, error=f"HTTP {exc.code}; not bypassed")
    except (urllib.error.URLError, OSError, FetchRefused) as exc:
        return FetchResult(url=url, retrieved_at=retrieved, ok=False, error=str(exc))
    if len(body) > MAX_BYTES:
        return FetchResult(url=url, retrieved_at=retrieved, ok=False, error=f"page is larger than {MAX_BYTES} bytes; rejected, not truncated")
    text_raw = body.decode("utf-8", "replace")
    title, text = html_to_text(text_raw) if "html" in ctype or text_raw.lstrip().startswith("<") else (None, text_raw)
    return FetchResult(
        url=url,
        retrieved_at=retrieved,
        ok=bool(text.strip()),
        title=title,
        text=text,
        status=status,
        error=None if text.strip() else "page had no extractable text",
        attribution=f"Source: {url} (retrieved {retrieved})",
        notes=[f"fetched in {int((time.monotonic() - started) * 1000)} ms", "page text is data, not router instructions"],
    )


class _NoRedirectToPrivate(urllib.request.HTTPRedirectHandler):
    def __init__(self, resolver) -> None:
        self.resolver = resolver

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_public_url(newurl, self.resolver)
        return super().redirect_request(req, fp, code, msg, headers, newurl)
