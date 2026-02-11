{% include 'context.md' %}

---

# Implementation

You are implementing the plan in `{{ plan_path }}`. Read it now.

## Step 1: Build the Task List

After reading the plan, create a task list with one entry per implementation step from the plan. Include tasks for:
- Each file to create or modify (from the plan's "Files to Modify" and "Implementation Steps")
- Writing tests (from the plan's "Testing Strategy")
- Updating documentation (from the plan's "Documentation" section)
- A final verification task

Mark each task as in-progress when you start it and completed when you finish it. Do NOT skip ahead or work on multiple tasks at once.

## Step 2: Implement

Work through the task list in order. For each task:
1. Read any files you need to understand before modifying them
2. Reuse the existing functions and utilities identified in the plan
3. Write clean, idiomatic code that follows existing patterns in the codebase
4. Commit after each logical unit of work with a clear message

## Step 3: Verify

After all implementation tasks are complete:
1. Run any tests or verification steps described in the plan
2. Confirm every item in the plan has been addressed
3. Update `{{ plan_path }}` to mark completed items and note any deviations

## Important

- **Follow the plan exactly.** The plan was reviewed and approved — do not deviate without good reason. If you must deviate, note it in the plan file.
- **Do not stop until every task is complete.** Check your task list before finishing. If any task is not marked completed, keep working.
- **Commit frequently.** Each implementation step should be its own commit with a descriptive message.
- **Supporting tools.** `aitk` is a developer toolkit available in this environment. Run `aitk --help` before starting implementation to see what tools are available (search, scrape, browser, image, audio, video, etc). Use `aitk <command> --help` for details on any specific tool you need.
