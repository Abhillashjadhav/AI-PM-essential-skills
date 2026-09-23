# Focused verification

Cloud preparation, 23 September 2026. No real exports or model calls.

- ContextPort capabilities output, stderr and exit status matched the original
  repository version byte for byte with the optional adapter active.
- PM Verifier's actual module CLI displayed help and returned zero with the adapter.
- Changed Python sources compiled.
- The adapter's independent checks cover missing collector, unwritable outbox,
  original stdout/stderr and exit-code preservation, SIGTERM, local-only receipt,
  loopback-only HTTP, rejected redirects and OTLP partial-success handling.

The first two checks plus Dreamjob's synthetic boundary check and compilation took
under one second together. Static review is additional work; this is not a claim
that overall QA was precisely 5%. Optional broad testing was omitted to respect
the requested budget. Actual Mac capture and installed-console behavior remain
part of the terminal handoff. This document does not certify model reliability.
