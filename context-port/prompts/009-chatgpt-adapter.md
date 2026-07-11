# Phase 9 prompt: ChatGPT reconstruction adapter

## Date

2026-07-11

## Branch

`context-port/009-chatgpt-adapter`

## Public task record

Build a public, standalone ChatGPT reconstruction adapter without inventing a destination API. Verify the public capability boundary from official OpenAI documentation. Translate an approved assistant-neutral reconstruction plan into a deterministic offline adapter report, preserve every operation, classify unsupported ChatGPT writes explicitly, and perform no network calls, browser automation, account access, or ChatGPT writes. Include a public schema, synthetic tests, documentation, and evaluation evidence.

## Status

Complete. Implemented as an offline, fail-closed capability adapter because the required consumer ChatGPT write surface is not established in public documentation.
