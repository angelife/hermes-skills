---
name: hermes-provider-cleanup
description: >
  Safely prune Hermes provider/model/alias/credential state.
  Use when the user asks to remove failed providers, clean `/model`,
  delete stale entries, or inspect provider-related config/env/keys.
  Separates provider removal from catalog cleanup to avoid overreach.
tags:
  - hermes
  - provider
  - cleanup
---

# Hermes Provider Cleanup

## Goal
Keep Hermes model surface truthful:
- `/model` shows only tested-OK providers/models
- config.yaml retains only active provider entries
- `.env` only contains variables actually referenced
- stale credential artifacts outside `.env` are reported, not consumed

## Invariants
- **Treat secret-bearing files as obstacles, not inventory.** Plaintext key files
  found outside `.env`/Hermes secret stores are credential-hygiene issues.
  Do not enumerate, print, or pass them into test scripts.
- **Remove providers only when the user explicitly asks.** Do not bundle
  provider removal with `/model` list cleanup, alias trimming, or unrelated
  config rewrites unless explicitly requested.
- **Show first, write last.** Present deletions/diffs before touching
  config.yaml, custom_providers, aliases, or `.env`.
- **Respect Hermes config gating.** Direct rewrites may be blocked.
  Prefer the smallest possible change and one explicit confirmation.

## Step 1: Scope the cleanup
1. Confirm scope with the user:
   - providers to remove
   - whether to also clean `model_aliases:`, `custom_providers:`, `moa.presets`
   - whether to prune cache files like `provider_models_cache.json`
2. Lock scope before reading secrets.

## Step 2: Inspect current active set
Check:
- `config.yaml` provider entries under `providers:` and `custom_providers:`
- top-level `model.default` / `model.provider`
- `model_aliases:`
- referenced env vars vs actual `.env` contents

Do not touch `~/.hermes/shared/nous_auth.json`, `~/.hermes/auth.json`,
external provider token files, or built-in credential files.

## Step 3: Evidence-based retention
Keep a provider/alias only when there is explicit tested-OK evidence:
- recent healthcheck / `hermes doctor` result
- successful live chat call
- proven fallback behavior

If evidence is stale, mark pending or drop it.

## Step 4: Present diff for confirmation
Before writing:
- show exact deletions/renames/alias changes
- call out any touched blocks outside user-requested scope
- list any remaining stale credentials/material outside `.env`

Wait for explicit confirmation.

## Step 5: Apply minimal changes and verify
- Update `config.yaml` via smallest patch or `hermes config set`
- Update `model_aliases:` only if in scope
- Do not sweep `custom_providers:` or provider caches unless requested
- After change, verify with `hermes doctor` or focused connectivity checks

## Pitfalls
- **Hermes may block direct config writes.** Do not retry broad rewrites.
  Use terminal-based minimal edits or `hermes config set`.
- **Gateway restart is mandatory after config changes** and cannot be run
  from inside the gateway process.
- **Double surfaces:** some providers exist in both `providers:` and
  `custom_providers:`; remove both if the provider is being deleted.
- **`provider_models_cache.json` is cache, not source of truth.**
  Prune only as a housekeeping step, not as part of provider deletion.
- **External key files should not be treated as model catalog inputs.**
  They are secrets to secure, not inventory to iterate.

## Reference
See `references/provider-removal-checklist.md` for step-by-step confirmation
templates and `references/cleanup-notes.md` for session-specific findings.
