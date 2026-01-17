# aidw

AI Dev Workflow — trigger AI workflows from GitHub issue/PR comments.

## How It Works

```
Issue → @aidw plan → PR with PLAN.md → @aidw build → Code + Tests + Docs
```

Comment on any issue with `@aidw plan` and the bot will:
1. Spin up an isolated E2B sandbox
2. Clone your repo
3. Run Claude Code to analyze the issue and create a plan
4. Push a branch and open a draft PR with `PLAN.md`

Then iterate with `@aidw refine` or implement with `@aidw build`.

## Commands

| Command | Context | What it does |
|---------|---------|--------------|
| `@aidw plan` | Issue | Create branch + PR with implementation plan |
| `@aidw refine` | PR | Update plan based on feedback |
| `@aidw build` | PR | Implement the plan (code + tests + docs) |
| `@aidw oneshot` | Issue | Full automation in one shot |
| `@aidw iterate` | PR | Refine implementation based on feedback |

## Install

```bash
uv tool install git+https://github.com/Mandalorian007/aidw
```

## Update

```bash
uv tool upgrade aidw
```

## Configure

### 1. Generate Claude Code Token

Claude Code needs a long-lived token for sandbox execution:

```bash
claude setup-token
```

Follow the prompts to authenticate and copy the generated token.

### 2. Run Configuration

```bash
aidw config
```

Prompts for credentials and allowed GitHub usernames. Saves to `~/.aidw/`.

**Required credentials:**
- `AIDW_WEBHOOK_SECRET` - GitHub webhook signature secret
- `E2B_API_KEY` - Get from [e2b.dev/dashboard/keys](https://e2b.dev/dashboard/keys)
- `GH_TOKEN` - GitHub PAT with `repo` scope
- `CLAUDE_CODE_TOKEN` - From `claude setup-token` above

## Run

```bash
aidw server           # Start webhook server
aidw server --dev     # With auto-reload
```

Expose with [Tailscale Funnel](https://tailscale.com/kb/1223/funnel) or ngrok, then configure your GitHub repo's webhook to point to `https://your-url/webhook`.

## Manual Triggers

For testing or CI:

```bash
aidw run plan --repo owner/repo --issue 123
aidw run build --repo owner/repo --pr 124
aidw run oneshot --repo owner/repo --issue 123
```

## Architecture

```
GitHub Webhook
       ↓
  FastAPI Server ──→ SQLite (sessions)
       ↓
  E2B Sandbox
       ↓
  Claude Code ──→ git push ──→ GitHub PR
```

Each workflow runs in an isolated [E2B](https://e2b.dev) sandbox with Claude Code. Changes are committed and pushed directly from the sandbox.

## Requirements

- Python 3.11+
- [E2B](https://e2b.dev) account for isolated sandbox execution
- GitHub PAT with `repo` scope for repo/PR operations
- Claude Code subscription with a setup token (run `claude setup-token`)

## License

MIT
