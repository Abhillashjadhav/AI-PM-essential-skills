"""Local attachment extraction: TXT/MD, DOCX (standard-library ZIP/XML), and
text PDFs via an already-installed ``pdftotext``.

Nothing is truncated silently and nothing is uploaded anywhere. Failures are
explicit results, never an empty "success".
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_EXTRACTED_CHARS = 2_000_000
MAX_ZIP_ENTRIES = 2_000
MAX_ZIP_UNCOMPRESSED = 100 * 1024 * 1024
MAX_ZIP_RATIO = 100

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".text"}


@dataclass
class Extraction:
    path: str
    kind: str
    state: str  # "extracted" | "failed" | "blocked"
    text: str | None
    original_hash: str | None
    extracted_hash: str | None
    bytes: int | None
    duration_ms: float
    notes: list[str] = field(default_factory=list)
    error: str | None = None

    def manifest(self) -> dict:
        return {
            "path": self.path,
            "kind": self.kind,
            "state": self.state,
            "bytes": self.bytes,
            "original_sha256": self.original_hash,
            "extracted_sha256": self.extracted_hash,
            "notes": self.notes,
            "error": self.error,
        }


def extract(
    path: str | Path,
    *,
    max_bytes: int = MAX_FILE_BYTES,
    max_chars: int = MAX_EXTRACTED_CHARS,
    pdftotext: str | None = None,
) -> tuple[Extraction, bytes | None]:
    started = time.monotonic()
    source = Path(path).expanduser()
    suffix = source.suffix.lower()
    kind = {".docx": "docx", ".pdf": "pdf"}.get(suffix, "text" if suffix in TEXT_SUFFIXES else "unsupported")

    def result(state: str, *, text=None, raw=None, notes=None, error=None) -> tuple[Extraction, bytes | None]:
        return (
            Extraction(
                path=str(source),
                kind=kind,
                state=state,
                text=text,
                original_hash=hashlib.sha256(raw).hexdigest() if raw is not None else None,
                extracted_hash=hashlib.sha256(text.encode("utf-8")).hexdigest() if text is not None else None,
                bytes=len(raw) if raw is not None else None,
                duration_ms=(time.monotonic() - started) * 1000,
                notes=notes or [],
                error=error,
            ),
            raw,
        )

    if not source.is_file():
        return result("failed", error=f"file not found: {source}")
    size = source.stat().st_size
    if size > max_bytes:
        return result("failed", error=f"file is {size} bytes, above the {max_bytes}-byte limit; rejected, not truncated")
    raw = source.read_bytes()
    if kind == "unsupported":
        return result("failed", raw=raw, error=f"unsupported attachment type {suffix or '(none)'}; supported: txt, md, docx, text pdf")
    try:
        if kind == "text":
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError as exc:
                return result("failed", raw=raw, error=f"not valid UTF-8 text: {exc}")
            notes: list[str] = []
        elif kind == "docx":
            text, notes = _docx_text(source)
        else:
            tool = pdftotext if pdftotext is not None else shutil.which("pdftotext")
            if not tool:
                return result(
                    "blocked",
                    raw=raw,
                    error="PDF extraction is BLOCKED: no local 'pdftotext' (poppler-utils) was found. "
                    "Install it locally or paste the text; the file was not sent anywhere.",
                )
            text, notes = _pdf_text(source, tool)
    except AttachmentError as exc:
        return result("failed", raw=raw, error=str(exc))
    if not text.strip():
        return result("failed", raw=raw, error="no extractable text (scanned image, empty, or unsupported content); OCR is not part of V1")
    if len(text) > max_chars:
        return result(
            "failed",
            raw=raw,
            error=f"extracted text has {len(text)} characters, above the {max_chars}-character limit; rejected, not truncated",
        )
    return result("extracted", text=text, raw=raw, notes=notes)


class AttachmentError(RuntimeError):
    pass


def _docx_text(path: Path) -> tuple[str, list[str]]:
    notes = ["headers, footers, footnotes, comments, text boxes and embedded objects are not extracted"]
    try:
        archive = zipfile.ZipFile(path)
    except zipfile.BadZipFile as exc:
        raise AttachmentError(f"not a valid DOCX (zip) file: {exc}") from exc
    with archive:
        infos = archive.infolist()
        if len(infos) > MAX_ZIP_ENTRIES:
            raise AttachmentError(f"DOCX has {len(infos)} entries (limit {MAX_ZIP_ENTRIES})")
        total = sum(i.file_size for i in infos)
        if total > MAX_ZIP_UNCOMPRESSED:
            raise AttachmentError(f"DOCX expands to {total} bytes (limit {MAX_ZIP_UNCOMPRESSED})")
        for info in infos:
            if info.compress_size and info.file_size / max(info.compress_size, 1) > MAX_ZIP_RATIO:
                raise AttachmentError(f"DOCX entry {info.filename} has a suspicious compression ratio")
        names = {i.filename for i in infos}
        if "word/document.xml" not in names:
            if "EncryptedPackage" in names or any(n.startswith("EncryptionInfo") for n in names):
                raise AttachmentError("DOCX is password-protected or encrypted")
            raise AttachmentError("DOCX has no word/document.xml")
        if any(n.startswith("word/embeddings/") for n in names):
            notes.append("embedded objects present and not extracted")
        xml = archive.read("word/document.xml")
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise AttachmentError(f"DOCX XML could not be parsed: {exc}") from exc
    body = root.find(f"{W}body")
    if body is None:
        raise AttachmentError("DOCX has no document body")
    blocks: list[str] = []
    for child in body:
        if child.tag == f"{W}p":
            blocks.append(_paragraph(child))
        elif child.tag == f"{W}tbl":
            for row in child.iter(f"{W}tr"):
                cells = [" ".join(_paragraph(p) for p in cell.iter(f"{W}p")).strip() for cell in row.findall(f"{W}tc")]
                blocks.append(" | ".join(cells))
            blocks.append("")
    return "\n".join(blocks).strip() + "\n", notes


def _paragraph(node) -> str:
    parts: list[str] = []
    for element in node.iter():
        if element.tag == f"{W}t" and element.text:
            parts.append(element.text)
        elif element.tag == f"{W}tab":
            parts.append("\t")
        elif element.tag in (f"{W}br", f"{W}cr"):
            parts.append("\n")
    return "".join(parts)


def _pdf_text(path: Path, tool: str) -> tuple[str, list[str]]:
    try:
        completed = subprocess.run(
            [tool, "-enc", "UTF-8", "-layout", str(path), "-"], capture_output=True, timeout=60
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AttachmentError(f"pdftotext failed to run: {exc}") from exc
    stderr = completed.stderr.decode("utf-8", "replace").strip()
    if completed.returncode != 0:
        lowered = stderr.lower()
        if "password" in lowered or "encrypt" in lowered:
            raise AttachmentError("PDF is password-protected")
        raise AttachmentError(f"pdftotext exited {completed.returncode}: {stderr[:200]}")
    return completed.stdout.decode("utf-8", "replace"), ["extracted with local pdftotext -layout; images are not OCR'd"]
