# Vendored gstack skills (subset)

This directory (`.claude/skills/gstack-*/` and this shared `gstack/bin/`) is a **manually trimmed, repo-local vendoring** of a subset of [gstack](https://github.com/garrytan/gstack) by Garry Tan, referenced from `temp/PROMPT.md` (a workflow doc from a different project) that this repo's own `docs/WORKFLOW.md` was adapted from.

## What's included

Only the 5 skills that `docs/WORKFLOW.md` actually uses, plus the shared `bin/` helper scripts they call:

| Skill folder | Upstream skill | Purpose |
|---|---|---|
| `gstack-review/` | `review` | Pre-landing PR review |
| `gstack-qa/` | `qa` | Systematic QA testing + bug fixing |
| `gstack-qa-only/` | `qa-only` | Report-only QA testing |
| `gstack-benchmark/` | `benchmark` | Performance regression detection |
| `gstack-health/` | `health` | Code quality dashboard |

`gstack/bin/` is the full upstream `bin/` directory (~800KB, mostly bash scripts) that these 5 skills call for config, telemetry, decision logging, etc.

## What's excluded, and why

The other 18+ upstream skills (`office-hours`, `plan-ceo-review`, `plan-eng-review`, `plan-design-review`, `design-*`, `ship`, `land-and-deploy`, `canary`, `cso`, `retro`, `autoplan`, `spec`, `document-*`, `make-pdf`, `diagram`, `pair-agent`, `careful`/`freeze`/`guard`/`unfreeze`, `setup-*`, `gstack-upgrade`) are **not** vendored — they aren't referenced by this project's workflow.

Most importantly, **`browse/` (the real-Chromium browser automation daemon) is excluded.** The official install (`./setup`, including the deprecated `--local` flag) unconditionally tries to download and launch Playwright Chromium via `bun`, which:
- requires a `bun`/Node.js runtime not otherwise needed by this project
- downloads a few hundred MB
- is not guaranteed to work in every environment (e.g. sandboxed/headless CI)

This project already uses `mcp__claude-in-chrome__*` tools for browser automation (see `docs/WORKFLOW.md` §5.2), so `/browse` was not needed.

**Consequence:** `gstack-qa`, `gstack-qa-only`, and `gstack-benchmark` each check for `.claude/skills/gstack/browse/dist/browse` and, if absent, ask the user before attempting to build/use it (they do not silently fail — this is upstream's own designed fallback, unmodified). Expect this prompt if you invoke those skills' browser-driven steps.

## What was changed from upstream

- Removed the `SKILL.md.tmpl` template source files (only the generated `SKILL.md` is needed at runtime).
- Renamed `name:` frontmatter and folder names with a `gstack-` prefix (matching upstream's own `--prefix` install option) to avoid any future collision with project-local skills of the same short name.
- Rewrote all hardcoded `~/.claude/skills/gstack/...` (global-install) paths to the repo-relative `.claude/skills/gstack/...` equivalent, since this is a **repo-local**, not global, install.
- No other content changes.

## Source

- Repo: https://github.com/garrytan/gstack
- Commit vendored from: `94993f74012782fd94416dd44b8314f6363a13a4` (2026-08-08)
- License: MIT (Copyright (c) 2026 Garry Tan) — see `LICENSE` in this directory.

## Known limitations of this manual install

- This did **not** go through the official `./setup` script, so:
  - `gstack-update-check` / auto-update will not find updates (there is no version-tracking state for a manual copy).
  - `gstack-team-init` / team-mode auto-update hooks were not configured.
- If you want the full upstream tool (all 23+ skills, `/browse`, auto-update), install it separately per the [upstream README](https://github.com/garrytan/gstack#install--30-seconds) — that is a global, machine-level install and is independent of this repo-local subset.
