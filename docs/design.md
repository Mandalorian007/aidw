# AIDW (AI Dev Workflow) - Implementation Plan

## Overview

Create `aidw`, an outer loop AI system that triggers AI workflows from GitHub issue/PR comments. Designed as a companion to `aitk` (AI Toolkit) with the same modular CLI patterns.

**Core Concept:** Issue = Unit of Work → Branch → PR. All context flows automatically.

## The 5 Commands

| Command | Purpose | When to use | Output |
|---------|---------|-------------|--------|
| `@aidw plan` | Create initial plan | Starting work on an issue | Branch + PR with `docs/plans/{slug}.md` |
| `@aidw refine` | Iterate on plan | Feedback on the plan before building | Updated plan file |
| `@aidw build` | Implement from plan | Plan approved, ready to code | Code + tests + docs added to PR |
| `@aidw oneshot` | Full automation | Straightforward issues | Branch + PR with everything |
| `@aidw iterate` | Iterate on implementation | Feedback on code/tests/docs | Updated code + plan + tests + docs |

## State Machine

```
ISSUE (no PR)
    │
    ├── @aidw plan ────────► PR with docs/plans/{slug}.md (draft)
    │                              │
    │                              ├── @aidw refine ──► Updated plan
    │                              │       │
    │                              │       └── (loop) @aidw refine
    │                              │
    │                              └── @aidw build ───► PR with code + tests + docs
    │                                                       │
    │                                                       └── @aidw iterate ► Refine impl
    │                                                               │
    │                                                               └── (loop) @aidw iterate
    │
    └── @aidw oneshot ─────► PR with code + plan + tests + docs
                                   │
                                   └── @aidw iterate ► Refine impl
```

## Architecture

```
GitHub Webhook → FastAPI Server → Command Router → E2B Sandbox → GitHub API
                     ↓                                  ↓
                SQLite DB                        Claude Code
                (sessions)                    (runs in sandbox)
```

**E2B Integration:**
- Each workflow gets its own isolated E2B sandbox
- Repo is cloned into sandbox, agent runs there
- Changes pushed directly from sandbox to GitHub
- Parallel execution without conflicts
- Sandbox auto-terminates after completion

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Project | **Separate repo** (`~/IdeaProjects/aidw`) | Server vs CLI tool |
| Framework | **FastAPI** | Async, Pydantic, battle-tested |
| Execution | **E2B Sandboxes** | Isolated, parallel, scalable |
| Prompts | **Separate files** in `prompts/` | Editable, versionable, reusable |
| Agent | **Claude Code only** | Keep it simple, no backend abstraction |
| Auth | **GitHub username whitelist** | Simple, effective for personal use |
| Persistence | **SQLite** | No infra needed, local-first |

## Directory Structure

```
aidw/
├── src/aidw/
│   ├── __init__.py           # CLI entry (Click)
│   ├── cli.py                # Commands: server, run, status
│   ├── env.py                # Config loading (aitk pattern)
│   │
│   ├── server/
│   │   ├── app.py            # FastAPI + routes
│   │   ├── webhook.py        # Event handling
│   │   └── security.py       # Signature verification
│   │
│   ├── commands/             # The 5 entry points
│   │   ├── plan.py           # @aidw plan
│   │   ├── refine.py         # @aidw refine
│   │   ├── build.py          # @aidw build
│   │   ├── oneshot.py        # @aidw oneshot
│   │   └── iterate.py        # @aidw iterate
│   │
│   ├── sandbox/              # E2B sandbox management
│   │   ├── __init__.py
│   │   ├── manager.py        # Create, connect, kill sandboxes
│   │   ├── executor.py       # Run Claude Code in sandbox
│   │   ├── files.py          # Upload/download files
│   │   ├── git.py            # Clone, push, PR from sandbox
│   │   └── auth.py           # Sync ~/.claude auth to sandbox
│   │
│   ├── github/
│   │   ├── client.py         # gh CLI + httpx (on server)
│   │   ├── context.py        # Build full context (issue + PR + comments)
│   │   └── progress.py       # Progress comment formatting
│   │
│   └── database/
│       ├── models.py         # Session/run models
│       └── db.py             # SQLite operations
│
├── prompts/                   # Prompt templates
│   ├── context.md            # Uniform context injection
│   ├── plan.md               # Create initial plan
│   ├── refine.md             # Iterate on plan
│   ├── build.md              # Implement from plan
│   ├── oneshot.md            # Full automation
│   └── iterate.md            # Iterate on implementation
│
└── pyproject.toml
```

## E2B Sandbox Workflow

Each command follows this lifecycle:

```
1. INIT SANDBOX
   └── Create E2B sandbox (standard template with Claude Code pre-installed)
   └── Store sandbox_id in session

2. SYNC CLAUDE AUTH
   └── Copy ~/.claude config from host to /home/user/.claude in sandbox
   └── Enables Claude Code subscription auth to work in sandbox

3. CLONE REPO
   └── git clone https://github.com/owner/repo.git /home/user/repo
   └── Checkout branch (aidw/issue-123 or existing PR branch)

4. INJECT CONTEXT
   └── Write assembled context to /home/user/context.md
   └── Write prompt to /home/user/prompt.md

5. RUN AGENT
   └── claude -p "$(cat /home/user/prompt.md)" --output-format json
   └── Stream progress updates to GitHub comment

6. EXTRACT RESULTS
   └── Read git log, diff, modified files
   └── Update session state

7. PUSH TO GITHUB
   └── git push from sandbox (using injected GH_TOKEN)
   └── Create/update PR via GitHub API

8. CLEANUP
   └── E2B auto-terminates sandbox after ~1-2 hours
   └── Long workflows: checkpoint state, reboot sandbox if needed
```

**Standard Sandbox:** Single template with Claude Code, Node.js, Python, gh CLI pre-installed.

## Context Assembly

When any command runs, full context is assembled automatically:

```markdown
# Context

## Issue #{{issue.number}}: {{issue.title}}
{{issue.body}}

## Issue Comments
{% for c in issue.comments %}
@{{c.author}} ({{c.date}}): {{c.body}}
{% endfor %}

{% if pr %}
## PR #{{pr.number}}
{{pr.description}}

### PR Comments
{% for c in pr.comments %}
@{{c.author}} ({{c.date}}): {{c.body}}
{% endfor %}

### Current Branch: {{pr.branch}}
{{git_log}}
{% endif %}

## Trigger
@{{trigger.author}}: {{trigger.body}}
```

The agent sees EVERYTHING relevant - issue, all comments, PR, all PR comments, git state.

## Prompt Architecture

All prompts follow the same structure: **context injection + command-specific instructions**.

### Context Template (`prompts/context.md`)
This is injected into EVERY prompt - clean, uniform metadata:

```markdown
# Context

## Issue #{{issue.number}}: {{issue.title}}
{{issue.body}}

## Issue Comments
{% for c in issue.comments %}
**@{{c.author}}** ({{c.date}}):
{{c.body}}
{% endfor %}

{% if pr %}
## Pull Request #{{pr.number}}: {{pr.title}}
Branch: `{{pr.branch}}`

{{pr.body}}

### PR Comments
{% for c in pr.comments %}
**@{{c.author}}** ({{c.date}}):
{{c.body}}
{% endfor %}

### Git State
```
{{git_log}}
```

### Files Changed
{{git_diff_stat}}
{% endif %}

## Trigger
**@{{trigger.author}}**: {{trigger.body}}
```

### Command-Specific Prompts

**`prompts/plan.md`:**
```markdown
{{> context.md}}

---

Create a detailed implementation plan for this issue.

Create the docs/plans/ directory if it doesn't exist, then output the plan to {{ plan_path }} with:
1. **Approach** - High-level strategy and rationale
2. **Files** - List files to create/modify with brief descriptions
3. **Testing** - Testing strategy
4. **Documentation** - What needs to be documented

Be specific and actionable. This plan will be reviewed before implementation.
```

**`prompts/refine.md`:**
```markdown
{{> context.md}}

---

Refine the existing {{ plan_path }} based on the feedback above.

Update the plan to address the feedback while maintaining:
- Clear approach and rationale
- Specific file list
- Testing strategy
- Documentation plan

Do NOT implement yet - only update the plan.
```

**`prompts/build.md`:**
```markdown
{{> context.md}}

---

Implement the plan in {{ plan_path }}.

1. Read and follow the plan exactly
2. Write clean, idiomatic code
3. Add tests that verify the implementation
4. Update documentation as specified

Commit with clear messages. The PR description will be updated with implementation details.
```

**`prompts/iterate.md`:**
```markdown
{{> context.md}}

---

Iterate on the implementation based on the feedback above.

Update the implementation AND ensure all artifacts stay aligned:
- Update code to address feedback
- Update {{ plan_path }} if approach changed
- Update tests to cover new behavior
- Update docs if needed

Keep everything consistent.
```

## Config (`~/.aidw/config.yml`)

```yaml
server:
  port: 8787
  workers: 3

github:
  bot_name: aidw

auth:
  allowed_users:
    - "Mandalorian007"
```

**Credentials (aitk pattern: env → config → .env chain):**
| Key | Purpose | Get from |
|-----|---------|----------|
| `AIDW_WEBHOOK_SECRET` | GitHub webhook signature | GitHub App settings |
| `E2B_API_KEY` | Sandbox management | e2b.dev/dashboard/keys |
| `GH_TOKEN` | GitHub operations | GitHub PAT with repo scope |

**Claude Code Auth:** Uses subscription auth from `~/.claude` (synced to sandbox on startup). No API key needed.

**E2B Auto-Cleanup:** Sandboxes auto-terminate after 1-2 hours. Long workflows checkpoint state and reboot sandbox if needed.

## PR Artifacts

After `@aidw oneshot` or `@aidw build`, the PR contains:

```
PR #124 (branch: aidw/issue-123)
├── docs/plans/{slug}.md # The plan (updated on iterate)
├── src/...              # Implementation
├── tests/...            # Tests
└── PR Description       # Summary linking to issue
```

## Progress Updates

```markdown
🤖 **oneshot** running

- [x] Analyze issue (8s)
- [x] Create plan (15s)
- [ ] Implement ← running
- [ ] Test
- [ ] Document
- [ ] Create PR

_Session: abc123_
```

## Implementation Phases

### Phase 1: Foundation
- Project scaffolding at `~/IdeaProjects/aidw`
- Click CLI: `aidw server`, `aidw --version`
- FastAPI webhook with signature verification
- GitHub username whitelist auth
- Context assembly system (the uniform `context.md` template)
- `@aidw plan` command (create plan)

### Phase 2: Full Command Set
- `@aidw refine` - iterate on plan
- `@aidw build` - implement from plan
- `@aidw oneshot` - full automation
- `@aidw iterate` - iterate on implementation
- SQLite session tracking
- Progress comments on GitHub

### Phase 3: Polish
- `aidw status`, `aidw logs` commands
- Manual trigger: `aidw run plan --repo owner/repo --issue 123`
- Structured logging
- Documentation

## CLI Commands

```bash
# Server
aidw server                    # Start webhook server
aidw server --dev              # With auto-reload

# Manual triggers (for testing or CI)
aidw run plan --repo o/r --issue 123
aidw run refine --repo o/r --pr 124
aidw run build --repo o/r --pr 124
aidw run oneshot --repo o/r --issue 123
aidw run iterate --repo o/r --pr 124 --instruction "make it blue"

# Operations
aidw status abc123             # Check session status
aidw logs                      # Tail logs
```

## Tech Stack

- Python 3.12+
- FastAPI + uvicorn
- Click (CLI)
- httpx (HTTP client)
- SQLite (sessions)
- Jinja2 (prompt templates)
- **e2b** (sandbox management)
- gh CLI (GitHub operations, runs in sandbox)

## Setup

1. Create project: `mkdir ~/IdeaProjects/aidw && cd ~/IdeaProjects/aidw`
2. Initialize git: `git init`
3. **Copy this plan to docs/design.md**: `cp ~/.claude/plans/calm-pondering-chipmunk.md docs/design.md`

## Verification

1. Start server: `aidw server --dev`
2. Expose via Tailscale Funnel
3. Configure GitHub repo webhook
4. Create test issue

**Test each command:**
5. `@aidw plan` → verify PR with plan file in `docs/plans/` created
6. `@aidw refine add error handling` → verify plan file updated
7. `@aidw build` → verify code + tests + docs added to PR
8. `@aidw iterate make the tests more thorough` → verify all artifacts updated
9. Test `@aidw oneshot` on fresh issue → verify full flow in one command
