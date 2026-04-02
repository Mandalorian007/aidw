# AIDW — AI Dev Workflow

CLI that turns descriptions into draft PRs via Claude Code.

```
aidw one-shot "add rate limiting to the API" → draft PR
```

## Install

```bash
uv tool install aidw
aidw setup
```

`aidw setup` verifies dependencies (`git`, `gh`, `claude`) and installs Claude Code slash commands.

## Commands

### `aidw one-shot "description"`

Plan, implement, test, and open a draft PR — fully autonomous.

```bash
aidw one-shot "add rate limiting to the API"
# → https://github.com/you/repo/pull/42
```

### `aidw iterate <pr> ["feedback"]`

Iterate on an existing PR. Reads review comments and applies changes.

```bash
aidw iterate 42 "fix the error handling in the retry logic"
aidw iterate https://github.com/you/repo/pull/42
```

### `aidw cleanup`

Remove orphaned `aidw/*` worktrees left behind by interrupted runs.

```bash
aidw cleanup
```

### `aidw setup`

Install slash commands to `~/.claude/commands/aidw/` and verify dependencies.

### `aidw uninstall`

Remove slash commands and clean up worktrees.

## What to Expect

### Draft PRs

When `aidw one-shot` finishes, you get a draft PR with a structured body:

```
## Summary
Add rate limiting to API endpoints using a token bucket algorithm
to prevent abuse and ensure fair usage across tenants.

## Changes
- Add rate limiter middleware with per-tenant token bucket
- Wire middleware into API router for all authenticated endpoints
- Add configuration for rate limits in settings

## Testing
- Unit tests for token bucket logic pass
- Integration tests verify rate limiting triggers at threshold
- Existing API tests unaffected
```

### Iteration Comments

When `aidw iterate` finishes, it posts a comment on the PR summarizing what changed:

```
## Iteration Summary
Address reviewer feedback on error handling and test coverage.

### Feedback Addressed
- Reviewer: return 429 with Retry-After header instead of generic 400
- Reviewer: add test for concurrent request handling

### Changes Made
- Updated rate limiter to return 429 with Retry-After header
- Added concurrent request test using threading

### Testing
- All existing and new tests pass
```

### Timing

Runs typically take 5-15 minutes depending on task complexity and codebase size.

## Slash Commands

After `aidw setup`, these commands are available inside any Claude Code session:

- `/aidw:one-shot-pr <task>` — plan, implement, and open a draft PR
- `/aidw:iterate --pr <number> --branch <branch> [feedback]` — iterate on an existing PR

## Requirements

- **git** — version control
- **gh** — [GitHub CLI](https://cli.github.com/), authenticated (`gh auth login`)
- **claude** — [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)

## How It Works

1. You run `aidw one-shot "description"`
2. AIDW generates a slug and dispatches to Claude Code in an isolated git worktree
3. Claude Code explores the repo, implements changes, runs tests, and opens a draft PR
4. AIDW cleans up the worktree and prints the PR URL
