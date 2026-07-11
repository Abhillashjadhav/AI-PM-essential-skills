# Phase 12 prompt: installer

## Date

2026-07-11

## Branch

`context-port/012-installer`

## Public task record

Add a standalone local installer for ContextPort. It must be dry-run by default, require an explicit install flag, refuse any existing target, build and install only the local verified wheel with no index or dependencies, verify the installed CLI observably, emit a structured report, and never overwrite, delete, uninstall, or publish anything. Include synthetic temporary-directory tests, documentation, and evaluation.

## Status

Complete. The installer is dry-run first, refuses existing targets, installs only the local wheel offline, and verifies the installed CLI.
