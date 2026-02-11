# aidw

AI Dev Workflow — trigger AI workflows from GitHub issue/PR comments.

## How It Works

```
Issue → @aidw plan → PR with PLAN.md → @aidw build → Code + Tests + Docs
                                      → @aidw refine → Updated PLAN.md
                                      → @aidw iterate → Updated Code
                                      → @aidw codereview → Review Comment

Issue → @aidw oneshot → PR with Code + Tests + Docs (all-in-one)
```

Comment `@aidw plan` on any issue and the bot will:
1. Spin up an isolated E2B sandbox
2. Clone your repo
3. Run Claude Code to analyze the issue and create a plan
4. Push a branch and open a draft PR with `PLAN.md`

Then refine the plan, implement it, or iterate on the result — all from PR comments.

## Commands

| Command | Context | What it does |
|---------|---------|--------------|
| `@aidw plan` | Issue | Create branch + PR with implementation plan |
| `@aidw refine` | PR | Update plan based on feedback |
| `@aidw build` | PR | Implement the plan (code + tests + docs) |
| `@aidw iterate` | PR | Refine implementation based on feedback |
| `@aidw codereview` | PR | Analyze changes and post a review comment |
| `@aidw oneshot` | Issue | Full automation in one shot |

## Install

```bash
uv tool install git+https://github.com/Mandalorian007/aidw
```

## Update

```bash
uv tool upgrade aidw
```

## Configure

### Quick Setup

```bash
aidw config
```

Prompts for all credentials interactively. Press Enter to keep existing values.

### Set a Single Credential

```bash
aidw config --set KEY=VALUE
```

### Required Credentials

| Credential | Description | How to get |
|------------|-------------|------------|
| `AIDW_WEBHOOK_SECRET` | GitHub webhook signature secret | Generate any secret string |
| `E2B_API_KEY` | E2B sandbox API key | [e2b.dev/dashboard/keys](https://e2b.dev/dashboard/keys) |
| `GH_TOKEN` | GitHub PAT with `repo` scope | GitHub Settings > Developer settings > Personal access tokens |
| `CLAUDE_CODE_TOKEN` | Long-lived Claude Code auth token | Run `claude setup-token` |

Credentials are stored in `~/.config/aidw/credentials` with `600` permissions. Environment variables take precedence over the credentials file.

### Claude Code Token

Claude Code needs a long-lived token to run in the sandbox:

```bash
claude setup-token
aidw config --set CLAUDE_CODE_TOKEN=<paste-token-here>
```

## Run

### Webhook Server

```bash
aidw server           # Start webhook server
aidw server --dev     # With auto-reload
```

### Run as a Service (macOS)

To keep the server running across reboots, use `launchd`:

```bash
# Create the plist (adjust paths if your setup differs)
cat > ~/Library/LaunchAgents/com.aidw.server.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.aidw.server</string>
    <key>ProgramArguments</key>
    <array>
        <string>$HOME/.local/bin/aidw</string>
        <string>server</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/.config/aidw/server.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/.config/aidw/server.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF

# Replace $HOME with your actual home directory
sed -i '' "s|\$HOME|$HOME|g" ~/Library/LaunchAgents/com.aidw.server.plist

# Load (starts immediately and on every reboot)
launchctl load ~/Library/LaunchAgents/com.aidw.server.plist

# Check status
launchctl list | grep aidw

# View logs
tail -f ~/.config/aidw/server.log

# Stop the service
launchctl unload ~/Library/LaunchAgents/com.aidw.server.plist
```

The service auto-restarts if the process crashes (`KeepAlive: true`).

### Webhook Management

Manage GitHub webhooks directly from the CLI:

```bash
aidw webhook add --repo owner/repo       # Create webhook on a repo
aidw webhook status --repo owner/repo    # Show config + recent deliveries
aidw webhook remove --repo owner/repo    # Remove webhook from a repo
```

The webhook URL is built from `server.domain` in `~/.config/aidw/config.yml`. Set it during `aidw config` or manually:

```yaml
server:
  domain: https://your-server.example.com
  port: 8787
  workers: 3
```

If no domain is configured, it falls back to `http://localhost:{port}/webhook`.

You can also expose the server with [Tailscale Funnel](https://tailscale.com/kb/1223/funnel) or ngrok.

### Manual Triggers

Run workflows directly from the CLI for testing or CI:

```bash
aidw run plan --repo owner/repo --issue 123
aidw run build --repo owner/repo --pr 124
aidw run refine --repo owner/repo --pr 124 --instruction "simplify the approach"
aidw run iterate --repo owner/repo --pr 124 --instruction "fix the failing test"
aidw run codereview --repo owner/repo --pr 124 --instruction "focus on error handling"
aidw run oneshot --repo owner/repo --issue 123
```

## Architecture

```
GitHub Webhook
       |
  FastAPI Server --> SQLite (sessions)
       |
  E2B Sandbox
       |
  Claude Code --> git push --> GitHub PR
              \-> AIDW_REVIEW.md --> GitHub Comment (codereview only)
```

Each workflow runs in an isolated [E2B](https://e2b.dev) sandbox with full repo context. Changes are committed and pushed directly from the sandbox. The `codereview` command is read-only — it posts a review comment instead of pushing code.

## Requirements

- Python 3.11+
- [E2B](https://e2b.dev) account for sandbox execution
- GitHub PAT with `repo` scope
- Claude Code token (run `claude setup-token`)

## License

MIT
