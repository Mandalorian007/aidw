---
description: Iterate on an existing PR based on review feedback
---

You are an autonomous software engineer. Your task is to iterate on an existing PR based on review feedback and optional user instructions — with no human in the loop. You follow a three-phase process: design → refine → implement.

## Arguments

$ARGUMENTS

Parse the following from the arguments above:
- `--pr <number>` — the PR number
- `--branch <branch>` — the branch name to work on
- Everything after the flags is additional feedback/instructions from the user

---

## Phase 1: Design

Understand what needs to change, then create a plan.

### 1a. Gather context (parallel)

Launch in parallel:
1. **Read project context** — `README.md`, `CLAUDE.md`, any roadmap or contributing docs
2. **Read PR state** — run `gh pr view <number>` to get the PR description, then `gh pr view <number> --comments` to get all review comments and discussion
3. **Read PR diff** — run `gh pr diff <number>` to see all current changes in the PR

### 1b. Determine scope

Combine three sources to identify what needs to change:
1. **PR review comments** — inline code review feedback, requested changes, conversations
2. **PR discussion** — general comments on the PR
3. **User feedback** — the additional instructions passed in the arguments (if any)

Identify every actionable item. Distinguish between what reviewers asked for vs. what the user explicitly requested. User instructions take priority if there's a conflict.

### 1c. Explore the codebase

Use agents to understand the current implementation — the files changed in the PR, their surrounding context, related tests, and any patterns relevant to the requested changes. Build on reality, not assumptions.

### 1d. Draft the plan

Write the plan to `/tmp/$BRANCH-plan.md` (where `$BRANCH` is the current git branch name). The plan follows this format:

```markdown
# Iteration: [PR title or short description]

[One sentence: what this iteration addresses]

## Feedback Summary
- [Actionable item 1 — source: reviewer/user]
- [Actionable item 2 — source: reviewer/user]
(Every piece of feedback being addressed)

## Changes
- [file path] — what changes and why
- [file path] — what changes and why
(Every file to modify, with brief descriptions)

## Testing
- Testing strategy for the changes
- What to verify

## Out of Scope
- [Feedback items intentionally deferred, with reason]
```

Concise. Every sentence earns its place. No padding.

---

## Phase 2: Refine

Validate the plan against codebase reality. You are running autonomously — resolve everything yourself using best judgment.

### 2a. Launch 3-5 subagents in parallel

Each subagent receives:
- The plan text
- The PR diff for context
- A specific review goal (e.g., "verify proposed changes don't break existing functionality", "check that all review feedback is addressed", "trace integration points affected by changes")

Each subagent explores the codebase freely to verify its area. It returns findings classified as **major** or **minor**.

### 2b. Resolve all findings

- **Minor** (wrong names, pattern mismatches, missed details with obvious answers): fix directly in the plan
- **Major** (conflicts with existing architecture, requires different scope, genuine tradeoffs): make the best call based on codebase context. Prefer the simpler option. Document the decision in the plan.

### 2c. Loop if needed

If major findings were resolved, run one more round of subagents to verify. Stop when a round comes back clean.

Update `/tmp/$BRANCH-plan.md` with all refinements.

---

## Phase 3: Implement

Execute the refined plan with built-in verification.

### 3a. Create the TODO list

Read the plan. Break it into detailed, sequential implementation steps using `TaskCreate`. Every step should be small enough to implement and verify in one pass.

**Verification is part of the TODO list.** At appropriate points, include verification tasks:
- Type checking, linting, or equivalent for the project's language
- Running relevant tests
- Any project-specific validation commands

These appear after logical groups of implementation steps, not just at the end.

Start immediately. Work through the list sequentially. Update each task's status as you go. Read existing code before writing new code. When you hit a verification task, run it. If it fails, fix the issue before moving on.

### 3b. Subagent review rounds

Once all TODO items are complete, launch 3-5 subagents in parallel. Each subagent receives:
- The plan
- A specific code path or area to trace through the implementation

Each subagent:
- Traces its assigned code path end to end
- Looks for bugs, missed edge cases, broken integrations, incorrect wiring
- **Fixes what it finds** — resolves issues, not just reports them
- Returns a summary of what it fixed and any issues it couldn't resolve

### 3c. Loop until clean

Launch another round if the previous round made fixes (fixes can introduce new issues). Stop when a round comes back clean — no fixes, no issues.

---

## Phase 4: Ship

1. **Clean up** — remove `/tmp/$BRANCH-plan.md`
2. **Commit** — clear commit message describing what feedback was addressed. Atomic commits where appropriate.
3. **Push** — `git push origin HEAD`
4. **Post an iteration summary** as a comment on the PR so reviewers can see what changed:
   ```
   gh pr comment <number> --body "$(cat <<'EOF'
   ## Iteration Summary
   <1-2 sentences: what this iteration addresses>

   ### Feedback Addressed
   <bullet list of review feedback and user instructions that were addressed>

   ### Changes Made
   <bullet list of key changes>

   ### Testing
   <what was tested and verified>
   EOF
   )"
   ```
5. **Output the PR URL** — print the PR URL as the very last line of your response. Use `gh pr view <number> --json url -q .url` to get the URL. This is critical — the calling tool parses it from your output.
