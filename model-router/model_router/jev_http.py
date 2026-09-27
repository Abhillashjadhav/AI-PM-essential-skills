"""One bounded TypeSafe request, in a disposable subprocess.

The parent enforces the total deadline, including DNS, TLS and slow responses.
Secrets arrive over stdin, never argv; errors never echo request or response bodies.
This file intentionally has no router imports, for isolated (-I) execution.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MAX_RESPONSE_BYTES = 65536


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # never forward a key or prompt to a redirect target


def main() -> None:
    result = {"error": "transport"}
    try:
        envelope = json.loads(sys.stdin.buffer.read(65537))
        body = json.dumps(envelope["request"], ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            ENDPOINT, data=body,
            headers={"Authorization": "Bearer " + envelope["key"], "Content-Type": "application/json"},
            method="POST",
        )
        # Ignore ambient proxy settings: this key is for the fixed TypeSafe origin.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(request, timeout=1.2) as response:
            payload = response.read(MAX_RESPONSE_BYTES + 1)
            if len(payload) <= MAX_RESPONSE_BYTES and response.status == 200:
                result = {"response": json.loads(payload)}
            else:
                result = {"error": "invalid_response"}
    except urllib.error.HTTPError as exc:
        result = {"error": "http", "status": exc.code}
    except Exception:
        pass
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
