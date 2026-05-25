# Codex Setup

This directory contains public-safe Codex instructions and a MCP config template.

## Install

`install.sh` symlinks:

- `codex/AGENTS.md` -> `~/.codex/AGENTS.md`
- `codex/RTK.md` -> `~/.codex/RTK.md`

It intentionally does not overwrite `~/.codex/config.toml`, because that file usually contains live MCP credentials.

## MCP Config

Use `codex/config.toml.template` as a source for `~/.codex/config.toml`.

Replace placeholders locally:

- `<YOUR_CONTEXT7_API_KEY>`
- `<YOUR_SKYVERN_API_KEY>`
- `<YOUR_DATADOG_API_KEY>`
- `<YOUR_DATADOG_APP_KEY>`
- `<YOUR_EXA_API_KEY>`

Never commit the rendered config.
