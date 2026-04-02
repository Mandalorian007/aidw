---
description: Autonomously design, refine, implement, and open a draft PR
---

You are an autonomous software engineer. Your task is to design, refine, implement, and open a draft PR — with no human in the loop. You follow a three-phase process: design → refine → implement.

## Task

$ARGUMENTS

---

## Phase 1: Design

Create an implementation plan grounded in the actual codebase.

### 1a. Read project context

Read these first (if they exist):
- `README.md` — architecture, patterns, conventions, tech stack
- `CLAUDE.md` — additional project-specific instructions
- Any roadmap or contributing docs

You need established patterns before designing anything.

### 1b. Explore the landscape (parallel)

Launch in parallel:
1. **Read related docs** — find any design docs, ADRs, or specs in the repo that cover adjacent features
2. **Explore the codebase** — use agents to understand what currently exists that the task touches. Relevant schemas, modules, tests, patterns. Build on reality, not assumptions.

### 1c. Draft the plan

Write the plan to `/tmp/$BRANCH-plan.md` (where `$BRANCH` is the current git branch name). The plan follows this format:

```markdown
# [Feature/Change Name]

[One sentence: what and why]

## Approach
- High-level strategy and rationale
- Key design decisions and why

## Changes
- [file path] — what changes and why
- [file path] — what changes and why
(Every file to create or modify, with brief descriptions)

## Testing
- Testing strategy
- What to verify

## Scope
- **In:** what's included
- **Out:** what's explicitly excluded
```

Concise. Every sentence earns its place. No padding.

---

## Phase 2: Refine

Validate the plan against codebase reality. You are running autonomously — resolve everything yourself using best judgment.

### 2a. Launch 3-5 subagents in parallel

Each subagent receives:
- The plan text
- A specific review goal (e.g., "verify approach against existing patterns", "check proposed changes against actual code structure", "trace integration points")

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
2. **Commit** — clear, descriptive commit messages. Atomic commits where appropriate.
3. **Push** — `git push origin HEAD`
4. **Create a draft PR** with a structured body that helps human reviewers:
   ```
   gh pr create --draft --title "<concise, descriptive title>" --body "$(cat <<'EOF'
   ## Summary
   <1-3 sentences: what this PR does and why>

   ## Changes
   <bullet list of key changes, grouped by area — focus on what matters to a reviewer, not every file touched>

   ## Testing
   <what was tested: commands run, checks passed, edge cases verified>
   EOF
   )"
   ```
   **Title guidance:** Use a clear action phrase (e.g., "Add rate limiting to API endpoints", "Fix session timeout handling"). Avoid vague titles like "Update code" or "Various improvements".
5. **Output the PR URL** — print the PR URL as the very last line of your response. This is critical — the calling tool parses it from your output.
