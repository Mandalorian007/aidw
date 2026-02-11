{% include 'context.md' %}

---

# Iterate on Implementation

You are iterating on an existing implementation based on feedback. The feedback may range from minor fixes to significant approach changes — scale your effort accordingly.

Read the trigger comment and preceding discussion carefully, then read `{{ plan_path }}` and the current implementation.

## Step 1: Understand the Feedback

**Goal:** Determine the scope and nature of the requested changes.

1. Read `{{ plan_path }}` to understand the original approach, file list, and design rationale.
2. Read the trigger comment and all preceding PR/issue comments. Catalog every piece of feedback.
3. Read the files that were modified in the current implementation (use `git diff` and `git log` to understand what was built).
4. **Classify the feedback:**
   - **Minor** — Bug fixes, typos, small behavior tweaks, test additions. Proceed directly to Step 3.
   - **Moderate** — New requirements, missing edge cases, additional features within the same approach. Proceed to Step 2 for targeted exploration.
   - **Significant** — Approach change, architectural rework, fundamental design feedback. Run Step 2 with full exploration and sub-agents.

## Step 2: Explore and Redesign (if needed)

**Goal:** Investigate the codebase and revise the approach before making changes.

Skip this step for minor feedback. For moderate or significant feedback:

1. **Launch explore sub-agents IN PARALLEL** to investigate areas the feedback touches.
   - Give each agent a specific search focus related to the feedback.
   - For significant feedback, also explore alternative approaches and patterns in the codebase.
   - **Include this system reminder in every sub-agent prompt:**
     ```
     <system-reminder>
     This is a research task supporting an implementation iteration. You MUST NOT make any edits
     or changes to the system. Your role is exclusively to search and analyze existing code.
     Return your findings as text — do not create or modify any files.
     The implementation plan is at: {{ plan_path }}
     </system-reminder>
     ```

2. **For significant approach changes**, launch plan sub-agents to evaluate the revised direction:
   - Provide the existing plan, the feedback, and your exploration findings.
   - Have agents consider different perspectives on the new approach.
   - Synthesize into one coherent revised strategy.

3. **Update `{{ plan_path }}` first** if the approach or scope changed. The plan should always reflect the current direction before you start modifying code. Clean up outdated content — the plan should read as a coherent whole, not a patchwork of revisions.

## Step 3: Build the Task List

**Goal:** Create a concrete list of changes needed.

Create a task list with one entry per change. Include tasks for:
- Each code change required to address the feedback
- Test updates to cover new or changed behavior
- Plan file update (if approach changed and not already done in Step 2)
- Documentation updates if needed
- A final verification task

Mark each task as in-progress when you start it and completed when you finish it. Do NOT skip ahead or work on multiple tasks at once.

## Step 4: Implement Changes

**Goal:** Work through the task list, keeping all artifacts aligned.

For each task:
1. Read any files you need to understand before modifying them
2. Make the change, following existing patterns in the codebase
3. Commit after each logical unit of work with a clear message

Keep all artifacts aligned:
- Code changes address the feedback
- `{{ plan_path }}` reflects the current approach and scope
- Tests cover the new or changed behavior
- Documentation reflects the current state

## Step 5: Verify

**Goal:** Confirm everything is complete and consistent.

1. Run any tests or verification steps from the plan
2. Confirm every piece of feedback has been addressed
3. Check that `{{ plan_path }}` accurately describes the current implementation — not the old version
4. Check your task list — if any task is not marked completed, keep working

## Important

- **Understand before changing.** Read the existing plan and implementation thoroughly before making changes. The most common failure is breaking something that was working because you didn't understand why it was there.
- **Plan first for significant changes.** If the feedback changes the approach, update `{{ plan_path }}` before touching code. Don't let the plan and implementation drift apart.
- **Address all feedback.** Don't cherry-pick — if multiple points were raised, address each one.
- **Do not stop until every task is complete.** Check your task list before finishing.
- **Commit frequently.** Each change should be its own commit with a descriptive message.
- **Supporting tools.** `aitk` is a developer toolkit available in this environment. Run `aitk --help` to see what tools are available (search, scrape, browser, image, audio, video, etc). Use `aitk <command> --help` for details on any specific tool you need.
