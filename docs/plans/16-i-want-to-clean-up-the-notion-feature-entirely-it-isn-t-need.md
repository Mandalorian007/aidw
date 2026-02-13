# Implementation Plan: Remove Notion Feature from AIDW

> **STATUS**: ✅ COMPLETED (2026-02-13)
>
> All scope command code and references have been successfully removed. The implementation followed the plan exactly with no deviations. All success criteria verified.
>
> **Commits**:
> - bcfd852: Remove scope CLI command entry point
> - c978229: Remove scope_command from module exports
> - 5a3c825: Delete scope command implementation files
> - 1f3a9bf: Update design.md to reflect removal of scope command
> - 1e08822: Add historical note to plan 13 about scope command removal

## Context

The `scope` command was designed as an internal/experimental workflow to discover unscoped Notion tasks, analyze relevant GitHub repositories, and post scoping comments back to Notion. This functionality is no longer needed with the current scoping approach used by the project.

The Notion integration was implemented through the external `aitk` (AI Toolkit) package, which provides CLI commands for Notion API access (`aitk notion dbs`, `aitk notion view`, `aitk notion comment`). The scope command orchestrates E2B sandboxes with Claude Code to execute this workflow autonomously.

**Why remove it**: The issue states that this feature "isn't needed with our scoping work" - indicating that the project has moved to a different scoping methodology that doesn't require Notion integration. Since the scope command was explicitly marked as "internal/experimental" and is not user-facing, removing it simplifies the codebase without impacting users.

**Key constraint**: While removing Notion-specific code, we must preserve the `aitk` installation infrastructure in `sandbox/manager.py` because it's critical for the env store functionality (encrypted .env file management) used by all 6 main commands.

## Approach

This is a **surgical deletion** approach: remove only Notion-specific code while preserving shared infrastructure. The strategy is to:

1. **Delete the scope command files** - Remove scope.py (234 lines) and scope.md (58 lines)
2. **Remove CLI integration** - Delete the scope command registration from cli.py
3. **Clean module exports** - Remove scope_command from commands/__init__.py
4. **Update documentation** - Remove references from design.md and mark historical plans
5. **Preserve aitk infrastructure** - Keep aitk installation in sandbox/manager.py for env store

The implementation follows a strict order to avoid Python import errors: remove CLI entry points first, then module exports, then delete files, then update documentation.

This approach was chosen because:
- The scope command is completely isolated - it doesn't share code with other commands
- The aitk toolkit serves dual purposes (Notion + env store), so we remove only Notion usage
- Clean deletion is preferable to commenting out or disabling code
- Git history preserves the implementation if needed in the future

## Files to Modify

### Files to Delete

- **src/aidw/commands/scope.py** (234 lines) — Complete file deletion: the entire scope command implementation including sandbox setup, aitk installation, and Notion workflow orchestration
- **src/aidw/prompts/scope.md** (58 lines) — Complete file deletion: the prompt template with instructions for Claude Code to interact with Notion via aitk commands

### Files to Edit

- **src/aidw/cli.py** — Remove the `scope()` command function (lines 301-318) that registers the CLI entry point for `@aidw scope`
- **src/aidw/commands/__init__.py** — Remove scope_command import (line 9) and remove "scope_command" from __all__ export list (line 18)
- **docs/design.md** — Remove 3 references to scope command:
  - Line 19: Remove scope row from commands table
  - Line 101: Remove scope.py from directory structure
  - Line 128: Remove scope.md from prompts list
- **docs/plans/13-clean-up-documentation.md** — Add deprecation note at the top indicating the scope command has been removed (issue #16) and this plan is preserved for historical context

### Files to Preserve (Critical)

- **src/aidw/sandbox/manager.py** — Keep all aitk installation code:
  - Lines 98-145: `_install_tools()` method installs aitk from GitHub
  - Lines 147-169: `_sync_aitk_config()` method syncs aitk configuration
  - Lines 245-266: `_pull_env_files()` method uses `aitk env pull` for encrypted .env file retrieval
  - **Reason**: All 6 main commands depend on env store functionality
- **src/aidw/prompts/{build,iterate,plan,refine}.md** — Keep aitk references as general toolkit documentation
- **src/aidw/env.py** — Keep aitk pattern references in comments (documentation of design decisions)

## Reusable Code

No reusable code from the scope command needs to be preserved. The scope command is fully self-contained and doesn't provide utilities used by other commands. All shared infrastructure (aitk installation, sandbox management, GitHub integration) already exists in other modules and will be preserved.

## Implementation Steps

Follow this exact order to avoid import errors and ensure safe deletion:

### Step 1: Remove CLI Entry Point

Edit `/home/user/repo/src/aidw/cli.py`:
- Delete lines 301-318 (entire `scope()` function including @cli.command() decorator)
- Verify no other imports of scope_command exist in cli.py

**Why first**: This prevents users from invoking the command before we delete the implementation.

### Step 2: Remove Module Exports

Edit `/home/user/repo/src/aidw/commands/__init__.py`:
- Delete line 9: `from aidw.commands.scope import scope_command`
- Delete line 18: `"scope_command",` from the `__all__` list

**Why second**: Breaks the import chain before deleting the actual file, preventing import errors.

### Step 3: Delete Implementation Files

Delete both files:
- `rm /home/user/repo/src/aidw/commands/scope.py`
- `rm /home/user/repo/src/aidw/prompts/scope.md`

**Why third**: Safe to delete after all imports are removed.

### Step 4: Update Design Documentation

Edit `/home/user/repo/docs/design.md`:

Line 9 update:
```diff
-## The 7 Commands
+## The 6 Commands
```

Line 19 deletion (remove entire row):
```diff
-| `@aidw scope` | Scope from Notion | Internal/experimental workflow | Not user-facing |
```

Line 101 deletion (remove from directory structure):
```diff
-│   │   └── scope.py          # @aidw scope (internal)
```

Line 128 deletion (remove from prompts list):
```diff
-│   └── scope.md              # Notion scoping (internal)
```

**Why fourth**: Documentation updates happen after code changes are complete.

### Step 5: Mark Historical Plan

Edit `/home/user/repo/docs/plans/13-clean-up-documentation.md`:

Add immediately after the title (line 1):
```markdown
> **HISTORICAL NOTE**: The scope command referenced in this plan has been removed in issue #16. This plan is preserved for historical context but no longer reflects current implementation.
```

**Why last**: Preserves historical context without confusing future readers.

## Testing Strategy

### Pre-Implementation Verification

Run these commands to establish baseline:
1. `python -c "from aidw.commands import scope_command; print('scope exists')"` — Should succeed
2. `aidw --help` — Should list scope command
3. `grep -c "scope_command" /home/user/repo/src/aidw/commands/__init__.py` — Should return 2

### Post-Implementation Validation

Run these commands to verify successful removal:

1. **Import test**: `python -c "from aidw.commands import *"` — Should succeed without scope_command
2. **CLI test**: `aidw --help` — Should NOT list scope command
3. **File deletion verification**:
   ```bash
   test ! -f /home/user/repo/src/aidw/commands/scope.py && echo "scope.py deleted"
   test ! -f /home/user/repo/src/aidw/prompts/scope.md && echo "scope.md deleted"
   ```
4. **Documentation cleanup**:
   ```bash
   grep -i "@aidw scope" /home/user/repo/docs/design.md  # Should return no results
   grep -c "## The 6 Commands" /home/user/repo/docs/design.md  # Should return 1
   ```
5. **Preserved functionality**:
   ```bash
   grep -q "_pull_env_files" /home/user/repo/src/aidw/sandbox/manager.py && echo "env store preserved"
   grep -q "aitk env pull" /home/user/repo/src/aidw/sandbox/manager.py && echo "aitk preserved"
   ```

### Critical Functionality Tests

After changes, verify that non-Notion features still work:
1. **aitk installation**: Check that sandbox/manager.py still contains `_install_tools()` and `_sync_aitk_config()`
2. **Env store access**: Verify `_pull_env_files()` method exists and references `aitk env pull`
3. **Module imports**: Ensure all 6 main commands import correctly: `python -c "from aidw.commands import plan_command, refine_command, build_command, oneshot_command, iterate_command, codereview_command"`

### Edge Cases to Verify

1. **No orphaned imports**: Search for any remaining scope references: `grep -r "scope_command" /home/user/repo/src/`
2. **Command count consistency**: Verify design.md consistently refers to "6 commands" not "7 commands"
3. **Historical preservation**: Check that git history still contains scope implementation: `git log -- src/aidw/commands/scope.py`

## Documentation

### Files Requiring Updates

1. **docs/design.md** — Update command count from 7 to 6, remove all scope references
2. **docs/plans/13-clean-up-documentation.md** — Add historical note about scope removal

### No README Updates Required

The README.md file does not mention the scope command (it was intentionally excluded as an internal feature). The only occurrence of "scope" in README is in the context of GitHub token permissions (`repo` scope), which is unrelated and should remain unchanged.

### Changelog/Release Notes

When this change is deployed, consider documenting in release notes:
- **Breaking change**: `@aidw scope` command has been removed
- **Impact**: Users who relied on the internal Notion scoping workflow should migrate to alternative scoping approaches
- **No impact**: All 6 public commands (plan, refine, build, oneshot, iterate, codereview) continue to work unchanged

## Success Criteria

Implementation is complete when ALL of the following are true:

1. ✅ scope.py file does not exist (234 lines removed)
2. ✅ scope.md file does not exist (58 lines removed)
3. ✅ CLI command removed from cli.py (lines 301-318 deleted)
4. ✅ Module exports removed from commands/__init__.py (2 lines removed)
5. ✅ Documentation updated in design.md (scope references removed, command count updated to 6)
6. ✅ Historical note added to docs/plans/13-clean-up-documentation.md
7. ✅ No Python import errors when importing aidw modules
8. ✅ `aidw --help` does not list scope command
9. ✅ aitk installation preserved in sandbox/manager.py (lines 98-169)
10. ✅ Env store functionality preserved (_pull_env_files method exists at lines 245-266)
11. ✅ General aitk toolkit references preserved in prompt templates
12. ✅ All 6 main commands import successfully without errors

## Risk Mitigation

### Risk 1: Breaking env store functionality

**Risk**: Accidentally removing aitk installation code could break encrypted .env file access for all workflows.

**Mitigation**:
- Explicitly preserve `_install_tools()`, `_sync_aitk_config()`, and `_pull_env_files()` in sandbox/manager.py
- Verify aitk installation code remains after changes
- Test that `aitk env pull` command is still available in sandboxes

**Validation**: `grep -q "aitk env pull" /home/user/repo/src/aidw/sandbox/manager.py`

### Risk 2: Import errors during cleanup

**Risk**: Deleting files before removing imports causes Python import failures.

**Mitigation**:
- Follow strict implementation order: CLI → module exports → file deletion → documentation
- Test imports after each step

**Validation**: `python -c "from aidw.commands import *"` succeeds after each step

### Risk 3: Missed scope references

**Risk**: Scope command referenced in unexpected locations not covered by the plan.

**Mitigation**:
- Comprehensive grep before and after: `grep -r "scope_command" /home/user/repo/`
- Search for "scope" in documentation: `grep -ri "@aidw scope" /home/user/repo/docs/`

**Validation**: No references to scope_command remain except in git history

### Risk 4: Documentation inconsistency

**Risk**: Command count or table entries become inconsistent after removal.

**Mitigation**:
- Update all command counts from 7 to 6
- Verify table alignment in design.md
- Check that examples only reference the 6 main commands

**Validation**: Read through design.md to ensure consistency (automated: `grep -c "The 6 Commands" /home/user/repo/docs/design.md`)

## Rollback Plan

If issues arise after implementation:

1. **Immediate rollback**: `git revert <commit-hash>`
2. **Selective file restoration**:
   ```bash
   git checkout HEAD~1 -- src/aidw/commands/scope.py
   git checkout HEAD~1 -- src/aidw/prompts/scope.md
   git checkout HEAD~1 -- src/aidw/cli.py
   git checkout HEAD~1 -- src/aidw/commands/__init__.py
   ```
3. **Verification**: `python -c "from aidw.commands import scope_command"` should succeed
4. **Investigation**: Determine root cause before attempting re-implementation
5. **Testing**: Run `aidw --help` to confirm scope command is restored

Git history permanently preserves the scope implementation, so it can be recovered if needed in the future.
