{% include 'context.md' %}

---

You are performing a **code review** of this pull request. This is a read-only review — do NOT modify any source code, tests, or documentation.

Analyze the code changes on the current branch compared to the base branch. Run `git diff main...HEAD` (or the appropriate base branch) to see all changes.

Consider:
- **Code quality**: Readability, maintainability, naming, structure
- **Bugs**: Logic errors, off-by-one, null/undefined handling, race conditions
- **Security**: Injection, auth issues, secrets exposure, input validation
- **Edge cases**: Missing error handling, boundary conditions, empty/null inputs
- **Patterns**: Consistency with existing codebase conventions and architecture
- **Performance**: Unnecessary allocations, N+1 queries, missing indexes

{% if trigger.instruction %}
**Reviewer's focus**: {{ trigger.instruction }}
{% endif %}

Write your complete review to a file called `AIDW_REVIEW.md` in the repository root. Use this structure:

```markdown
### Summary
One paragraph summarizing what this PR does and your overall assessment.

### Strengths
- What's done well

### Issues

#### Critical
- Bugs, security issues, or correctness problems that must be fixed

#### Important
- Significant concerns that should be addressed

#### Minor
- Style, naming, or small improvements

### Questions
- Anything unclear that the author should clarify

### Suggestions
- Optional improvements or alternative approaches
```

Reference specific files and line numbers (e.g., `src/foo.py:42`). If a category has no items, omit it.

Do NOT modify any files other than `AIDW_REVIEW.md`. Do NOT commit changes.
