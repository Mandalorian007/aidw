# Plan: Move plan files to docs/plans/{number}-{slug}.md

## Problem
When multiple issues are planned against the same repository, they all write to `PLAN.md` at the repository root, causing file overwrites and loss of plan data.

## Solution
Move plan files from `PLAN.md` to `docs/plans/{number}-{slug}.md` where:
- `{number}` is the issue number (guarantees uniqueness)
- `{slug}` is a slugified version of the issue title (improves readability)

## Approach

### Phase 1: Core Implementation (COMPLETED)
1. Add slugification logic to `BaseCommand`:
   - `_slugify_title()` - converts issue title to URL-friendly slug
   - `_get_plan_path()` - computes full path with issue number prefix
2. Centralize plan path computation in `BaseCommand.execute()` to avoid redundant calculations
3. Update all commands to use `context.plan_path` instead of hardcoded `PLAN.md`
4. Update all Jinja2 prompt templates to use `{{ plan_path }}` variable
5. Update documentation (README, design docs) to reflect new convention

### Phase 2: Refinements (Based on Code Review Feedback)

#### Important Issues to Address

**1. Ensure directory creation (Issue #1)**
- **File**: `src/aidw/commands/plan.py`
- **Change**: Add `await executor.execute_command("mkdir -p docs/plans")` before running Claude Code
- **Rationale**: Makes system robust; removes dependency on prompt compliance

- **File**: `src/aidw/commands/oneshot.py`
- **Change**: Add `await executor.execute_command("mkdir -p docs/plans")` before running Claude Code
- **Rationale**: Same as above

**2. Improve fallback slug (Issue #2)**
- **File**: `src/aidw/commands/base.py:224`
- **Change**: Update fallback from `"plan"` to `f"issue-{context.issue.number}"`
- **Rationale**: Makes filenames like `docs/plans/123-issue-123.md` clearer that title was non-slugifiable
- **Note**: Requires passing context to `_slugify_title()` or handling in `_get_plan_path()`

#### Documentation and Code Quality Improvements

**3. Add slugification logging (Issue #4)**
- **File**: `src/aidw/commands/base.py` (in `_get_plan_path()`)
- **Change**: Add `logger.debug(f"Slugified '{context.issue.title}' -> '{slug}'")`
- **Rationale**: Helps debugging; shows transformation from title to slug

**4. Document truncation rationale (Issue #5)**
- **File**: `src/aidw/commands/base.py:223`
- **Change**: Add comment: `# Truncate to 60 chars to keep paths readable and filesystem-friendly`
- **Rationale**: Explains magic number; improves maintainability

**5. Add docstring examples (Suggestion #3)**
- **File**: `src/aidw/commands/base.py` (in `_get_plan_path()`)
- **Change**: Add docstring with examples:
  ```python
  """Compute the plan file path from the issue number and title.

  Uses the issue number as a prefix for guaranteed uniqueness.

  Examples:
      Issue #123 "Add user authentication" -> "docs/plans/123-add-user-authentication.md"
      Issue #456 "Fix bug!!!" -> "docs/plans/456-fix-bug.md"
  """
  ```
- **Rationale**: Documents expected behavior; clarifies filename format

**6. Extract slug length constant (Suggestion #2)**
- **File**: `src/aidw/commands/base.py` (at class level)
- **Change**: Add `MAX_SLUG_LENGTH = 60  # Keep paths short for readability and filesystem compatibility`
- **Change**: Use constant in `_slugify_title()`: `slug = slug[:MAX_SLUG_LENGTH].rstrip("-")`
- **Rationale**: Makes limit adjustable; DRY principle

#### Optional/Future Considerations

**7. Hardcoded directory path (Issue #3)**
- **Decision**: Keep hardcoded for now
- **Rationale**: Making it configurable adds complexity without clear immediate benefit
- **Future**: Can make it a class attribute if testing or config needs arise

**8. Unit tests for edge cases (Suggestion #1)**
- **Decision**: Add in separate PR
- **Rationale**: Tests are valuable but not critical for this refactor; better as follow-up work
- **Coverage should include**:
  - Very long titles (>100 characters)
  - Titles with only special characters (`"!!!"`, `"???"`)
  - Unicode titles with emoji
  - Empty/whitespace-only titles
  - Titles that differ only in special characters

### Questions/Decisions

**Q1: Migration path for existing PRs?**
- **Decision**: Acceptable breaking change
- **Rationale**: This is a pre-release tool; old PRs can be manually migrated if needed
- **Future**: Could add fallback logic if this becomes a problem

**Q2: What if issue title changes after plan creation?**
- **Decision**: Accept current behavior (path recomputed from title)
- **Rationale**: Issue title changes are rare; persisting path in DB adds complexity
- **Future**: Could store plan_path in session record if needed

**Q3: Should PR links use specific commit blob URLs?**
- **Decision**: Keep current behavior (link to HEAD)
- **Rationale**: Users typically want to see current plan state, not historical snapshot
- **Note**: Users can navigate history via git if needed

## Files to Modify

### Phase 2 Changes
1. `src/aidw/commands/base.py`:
   - Add `MAX_SLUG_LENGTH` constant at class level
   - Update `_slugify_title()` to use constant and add truncation comment
   - Add docstring with examples to `_get_plan_path()`
   - Add debug logging for slugification
   - Improve fallback slug logic

2. `src/aidw/commands/plan.py`:
   - Add directory creation before running Claude Code

3. `src/aidw/commands/oneshot.py`:
   - Add directory creation before running Claude Code

## Testing Strategy

### Manual Testing
- [x] Verify plans land at `docs/plans/{number}-{slug}.md` (already verified in original implementation)
- [x] Verify PR body references correct path (already verified)
- [x] Verify `build` command finds plan at new path (already verified)
- [x] Verify no file collision when planning second issue (already verified)

### Additional Testing for Phase 2
- [ ] Test with issue title that has only special characters (e.g., "!!!")
  - Verify filename becomes `docs/plans/123-issue-123.md`
- [ ] Test with very long issue title (>100 chars)
  - Verify slug is truncated to 60 characters
- [ ] Test with non-existent `docs/plans/` directory
  - Verify directory is created automatically by plan/oneshot commands
- [ ] Check debug logs
  - Verify slugification transformation is logged

### Future Testing (Separate PR)
- Unit tests for `_slugify_title()` edge cases
- Unit tests for `_get_plan_path()` output format
- Integration tests for full workflow

## Documentation Updates

No additional documentation changes needed - all docs were already updated in Phase 1:
- README.md references `docs/plans/{number}-{slug}.md`
- docs/design.md references new path convention
- All prompt templates use `{{ plan_path }}`

## Implementation Notes

### Key Design Decisions
1. **Issue number prefix**: Guarantees uniqueness even for identical titles
2. **60-character slug limit**: Balances readability with filesystem compatibility
3. **Centralized computation**: Plan path computed once in `BaseCommand.execute()` to avoid redundancy
4. **Static methods**: `_slugify_title()` and `_get_plan_path()` are static for testability
5. **Explicit directory creation**: Moving from prompt-based to code-based to increase reliability

### Breaking Changes
- Old PRs with `PLAN.md` at root will not be found by new commands
- This is acceptable for a pre-release tool
- Manual migration: move `PLAN.md` to `docs/plans/{number}-{slug}.md` if needed

### Rollout
1. Phase 1 already complete and merged
2. Phase 2 refinements to be implemented based on code review
3. Future unit tests to be added in separate PR
