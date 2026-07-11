# ChatGPT reconstruction adapter

## Capability boundary

As verified on 2026-07-11, public OpenAI documentation describes ChatGPT Projects as a consumer workspace feature and exposes some project information through the Compliance API. It does not establish a public API for creating consumer ChatGPT projects, chats, or historical messages.

OpenAI API Platform projects are administrative resource and billing boundaries. They are not treated as equivalent to consumer ChatGPT Projects.

Sources:

- [Projects in ChatGPT](https://help.openai.com/en/articles/10169521-using-projects-in-chatgpt)
- [Managing projects in the API platform](https://help.openai.com/en/articles/9186755-managing-projects-in-the-api-platform)

## Public contract

`chatgpt-adapt` accepts an approved, digest-valid reconstruction plan and emits a deterministic adapter report. Every source operation is retained verbatim and classified `UNSUPPORTED` with reason `PUBLIC_CHATGPT_WRITE_API_NOT_VERIFIED`.

The report distinguishes four facts:

- `VERIFIED`: the input is an approved, integrity-checked dry-run plan.
- `VERIFIED`: no network call, browser automation, or destination write is performed.
- `UNSUPPORTED`: public consumer ChatGPT reconstruction writes were not verified.
- `UNKNOWN`: whether OpenAI will add such a public API in the future.

This is intentionally fail-closed. Compliance API visibility, an API key, and API Platform projects do not authorize or imply consumer ChatGPT writes.

## Run locally

```sh
python3 context-port/contextport.py chatgpt-adapt \
  context-port/fixtures/reconstruction-plan-synthetic.json
```

Exit status `7` means the input was assessed successfully but reconstruction is blocked because the public destination capability is unsupported. Exit status `2` means the input itself was invalid.
