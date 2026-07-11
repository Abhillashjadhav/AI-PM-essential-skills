# ChatGPT reconstruction adapter

## Capability boundary

In a bounded review on 2026-07-11, the cited public OpenAI documentation described ChatGPT Projects as a consumer workspace feature and referred maintainers to the Compliance API for some project information. That review did not verify a public API for creating consumer ChatGPT projects, chats, or historical messages. This is a dated negative search result, not a claim that such an API can never exist.

OpenAI API Platform projects are administrative resource and billing boundaries. They are not treated as equivalent to consumer ChatGPT Projects.

Sources:

- [Projects in ChatGPT](https://help.openai.com/en/articles/10169521-using-projects-in-chatgpt)
- [Managing projects in the API platform](https://help.openai.com/en/articles/9186755-managing-projects-in-the-api-platform)

## Public contract

`chatgpt-adapt` accepts a structurally valid, digest-bound reconstruction plan carrying an approval declaration and emits a deterministic adapter report. The digest proves integrity, not the identity of the approver. Every source operation is retained verbatim and classified `UNSUPPORTED` with reason `PUBLIC_CHATGPT_WRITE_API_NOT_VERIFIED`.

> **Private-data warning:** the adapter report embeds each source operation verbatim, including message content, and prints the report to standard output. Keep reports local, protect redirected files as private data, and never commit reports generated from real conversations.

The report distinguishes four facts:

- `VERIFIED`: the input satisfies the public plan structure, declares approval, and passes its integrity digest.
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
