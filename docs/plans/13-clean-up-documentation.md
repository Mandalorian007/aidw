# Plan: Clean Up Documentation

## Problem

After recent changes (especially the move from `PLAN.md` to `docs/plans/{number}-{slug}.md` in issue #12), the project's documentation has accumulated inconsistencies and gaps:

1. **README.md** may reference outdated paths, commands, or workflows
2. **docs/design.md** describes the original architecture but doesn't mention newer features (`codereview`, `scope` commands)
3. **Code docstrings** have significant coverage gaps across the codebase (150+ missing docstrings)
4. **Prompt templates** need consistency checks to ensure they all use proper variable syntax

This cleanup ensures documentation is accurate, cohesive, and helpful for contributors and users.

## Approach

### Phase 1: Documentation Accuracy Review
1. **README.md**: Verify all commands, paths, and workflow diagrams reflect current implementation
2. **docs/design.md**: Update to include missing commands and verify architecture matches current state
3. **Identify stale references**: Look for any mentions of old `PLAN.md` path or deprecated patterns

### Phase 2: Code Docstring Improvements
Based on the docstring audit, prioritize documentation for:
1. **Critical public API** - Core classes like `BaseCommand`, `SandboxManager`, `GitHubClient`, `Database`
2. **Complex workflows** - `run_workflow()` methods, context building, sandbox lifecycle
3. **Public methods** - All public methods should have at minimum a one-line docstring
4. **Dataclasses** - All dataclasses need class-level docstrings explaining their purpose

Focus on highest-impact areas rather than achieving 100% coverage.

### Phase 3: Prompt Template Consistency
1. Verify all prompts use `{{ plan_path }}` variable (not hardcoded paths)
2. Ensure consistent formatting and structure across all templates
3. Check that inline comments/instructions are clear and consistent

### Phase 4: Overall Cohesion
1. Ensure terminology is consistent across all documentation
2. Verify cross-references between docs are accurate
3. Add any missing context that would help new contributors

## Files to Create/Modify

### Files to Modify

#### 1. `README.md`
- **Purpose**: Verify accuracy, update any stale references
- **Changes**:
  - Confirm workflow diagram shows correct path (`docs/plans/{number}-{slug}.md`)
  - Verify all commands listed are current and complete (check for missing `codereview`, `scope`)
  - Check installation/update instructions are accurate
  - Verify configuration instructions match current `env.py` implementation
  - Ensure webhook management section is current

#### 2. `docs/design.md`
- **Purpose**: Update to reflect current architecture and all implemented features
- **Changes**:
  - Add `codereview` and `scope` commands to command tables and state machine
  - Update "The 5 Commands" section (now 7+ commands)
  - Verify directory structure matches actual implementation
  - Add documentation for `AIDW_REVIEW.md` output (codereview workflow)
  - Update prompt architecture section to include all current prompts
  - Ensure E2B sandbox workflow accurately describes current implementation
  - Remove any outdated or incorrect information

#### 3. `src/aidw/commands/base.py`
- **Purpose**: Add comprehensive docstrings to core base class
- **Priority**: HIGHEST - This is the foundational class
- **Changes**:
  - Add `__init__()` docstring
  - Expand `execute()` docstring to explain lifecycle, error handling, progress tracking
  - Add `execute_manual()` docstring
  - Add detailed docstring to `_get_plan_path()` with examples (as suggested in issue #12 plan)
  - Add docstring to `_get_branch_name()` explaining logic
  - Add docstring to `_render_prompt()`
  - Add docstring to `_update_step()`
  - Add examples to `_slugify_title()` docstring

#### 4. `src/aidw/sandbox/manager.py`
- **Purpose**: Document sandbox lifecycle and complex initialization
- **Priority**: HIGH - Critical infrastructure component
- **Changes**:
  - Add class docstrings to `SandboxConfig` and `SandboxInstance`
  - Add `__init__()` docstring
  - Add docstrings to all private methods (`_install_tools`, `_sync_aitk_config`, `_sync_claude_auth`, `_clone_repo`, `_checkout_branch`)
  - Add docstrings to public methods (`write_context`, `write_prompt`, `get_git_state`, `push_changes`, `read_file`, `kill_sandbox`, `reconnect`)
  - Document `SANDBOX_TIMEOUT` constant

#### 5. `src/aidw/sandbox/executor.py`
- **Purpose**: Document Claude Code execution flow
- **Priority**: HIGH - Core execution logic
- **Changes**:
  - Add class docstring to `ExecutionResult`
  - Add `__init__()` docstring
  - Add docstring to `_ensure_claude_installed()`
  - Expand `run_claude_with_context()` docstring to explain context/prompt file usage
  - Expand `commit_changes()` docstring to explain complex commit logic
  - Add docstrings to helper methods (`get_changed_files`, `file_exists`, `read_repo_file`, `write_repo_file`)
  - Document `CLAUDE_TIMEOUT` constant

#### 6. `src/aidw/github/client.py`
- **Purpose**: Document GitHub API interface
- **Priority**: HIGH - External API boundary
- **Changes**:
  - Add class docstrings to all dataclasses (`Comment`, `Issue`, `PullRequest`, `Webhook`, `WebhookDelivery`)
  - Add `__init__()`, `__aenter__()`, `__aexit__()` docstrings
  - Add docstring to `client` property
  - Expand `get_issue()` docstring to mention comment fetching
  - Add docstring to `_get_issue_comments()`
  - Expand `get_pull_request()` docstring to mention both comment types
  - Add docstrings to `_get_review_comments()` and `_parse_linked_issue()`
  - Document `API_BASE` constant

#### 7. `src/aidw/database/db.py`
- **Purpose**: Document data persistence layer
- **Priority**: HIGH - Data integrity
- **Changes**:
  - Add `__init__()` docstring
  - Expand `connect()` docstring to mention schema initialization
  - Add `close()` and `conn` property docstrings
  - Expand `create_session()` docstring to document UUID generation
  - Add docstrings to `get_session()`, `list_sessions()`, `get_active_session_for_issue()`, `get_latest_session_for_pr()`, `cleanup_old_sessions()`
  - Expand `update_session()` docstring to explain complex update logic
  - Document `SCHEMA` constant

#### 8. Command classes (`src/aidw/commands/*.py`)
- **Purpose**: Document command-specific workflows
- **Priority**: MEDIUM - User-facing functionality
- **Files**: `plan.py`, `refine.py`, `build.py`, `oneshot.py`, `iterate.py`, `codereview.py`, `scope.py`
- **Changes** (apply to all):
  - Add `get_progress_steps()` docstrings
  - Expand `run_workflow()` docstrings to explain the specific workflow steps
  - Add `execute_manual()` docstrings
  - For `scope.py`: Add docstrings to helper methods (`_load_prompt`, `_install_tools`, `_sync_aitk_config`, `_sync_claude_auth`, `_setup_github_auth`)
  - For `codereview.py`: Document `REVIEW_FILE` constant

#### 9. `src/aidw/github/context.py`
- **Purpose**: Document context assembly system
- **Priority**: MEDIUM - Core workflow component
- **Changes**:
  - Add class docstrings to `TriggerInfo`, `GitState`, `WorkflowContext`
  - Add docstring to `WorkflowContext.to_dict()`
  - Add `__init__()` docstrings to `ContextBuilder` and `PromptRenderer`
  - Expand `build_context()` docstring to explain complex context assembly
  - Add docstrings to `render()` and `render_context()`

#### 10. `src/aidw/github/progress.py`
- **Purpose**: Document progress tracking system
- **Priority**: MEDIUM - User experience
- **Changes**:
  - Add class docstrings to `StepStatus`, `ProgressStep`, `ProgressTracker`
  - Add docstrings to all `ProgressTracker` methods (`format`, `format_completed`, `format_failed`)
  - Add `__init__()` docstrings to `ProgressReporter`
  - Add docstrings to `start`, `update`, `complete`, `fail` methods

#### 11. `src/aidw/env.py`
- **Purpose**: Document configuration system
- **Priority**: MEDIUM - Setup and configuration
- **Changes**:
  - Add class docstrings to `ServerConfig`, `GitHubConfig`, `AuthConfig`, `Settings`
  - Add docstring to `webhook_url` property
  - Add docstrings to `load_config_file()` and `load_credentials_file()`
  - Document module-level constants

#### 12. `src/aidw/cli.py`
- **Purpose**: Document CLI interface
- **Priority**: LOW-MEDIUM - Already has decent coverage
- **Changes**:
  - Expand `_find_aidw_webhook()` docstring to document parameters and return value
  - Add docstrings to nested helper functions (`_status`, `_add`, `_remove`)

#### 13. `src/aidw/server/*.py`
- **Purpose**: Document webhook server
- **Priority**: LOW-MEDIUM
- **Files**: `app.py`, `webhook.py`, `security.py`
- **Changes**:
  - `app.py`: Add docstrings to `db` variable, `lifespan()`, route handlers
  - `webhook.py`: Add class docstrings to `ParsedCommand`, `WebhookContext`; expand validation docstrings; document `COMMAND_PATTERN`
  - `security.py`: Expand `is_user_allowed()` docstring to document empty list behavior

#### 14. Other lower-priority files
- **Purpose**: Round out documentation coverage
- **Priority**: LOW
- **Files**: `sandbox/files.py`, `sandbox/git.py`, `sandbox/auth.py`, `database/models.py`
- **Changes**:
  - Add parameter and return value documentation to functions
  - Add class docstrings where missing
  - Document constants

### Files to Review (No Changes Expected)

#### Prompt Templates
All prompt templates already use correct `{{ plan_path }}` syntax and follow consistent structure:
- `src/aidw/prompts/context.md` ✓
- `src/aidw/prompts/plan.md` ✓
- `src/aidw/prompts/refine.md` ✓
- `src/aidw/prompts/build.md` ✓
- `src/aidw/prompts/oneshot.md` ✓
- `src/aidw/prompts/iterate.md` ✓
- `src/aidw/prompts/codereview.md` ✓
- `src/aidw/prompts/scope.md` ✓

Only modify if inconsistencies are found during implementation.

## Testing Strategy

### Manual Verification

#### README.md Accuracy
- [ ] Follow installation instructions on a fresh machine/environment
- [ ] Verify all commands listed actually exist and work as described
- [ ] Check that configuration steps match actual implementation
- [ ] Verify webhook setup instructions are complete and accurate

#### docs/design.md Accuracy
- [ ] Cross-reference architecture diagram with actual code structure
- [ ] Verify all commands are documented
- [ ] Check that state machine matches actual workflow logic
- [ ] Confirm directory structure matches reality

#### Docstring Quality
- [ ] Use an IDE or tool to check docstring coverage improvement
- [ ] Verify docstrings render correctly in IDE tooltips
- [ ] Check that parameter names match function signatures
- [ ] Ensure return types are documented

#### Prompt Template Consistency
- [ ] Grep for any hardcoded "PLAN.md" references
- [ ] Verify all templates use `{{ plan_path }}` variable
- [ ] Check that all templates include context properly
- [ ] Ensure formatting is consistent

### Automated Checks

#### Docstring Coverage
Could add a future CI check using tools like:
- `interrogate` (Python docstring coverage)
- `pydocstyle` (docstring style checker)

For now, manual review is sufficient.

#### Link Checking
- [ ] Check that any cross-references between docs are valid
- [ ] Verify external links (E2B, GitHub, etc.) are current

### Regression Prevention
- [ ] No functional code changes, only documentation
- [ ] Changes should not affect runtime behavior
- [ ] Existing commands should continue to work identically

## Documentation Updates

This issue IS the documentation update. After implementation:

1. **README.md** will be accurate and complete
2. **docs/design.md** will reflect current architecture
3. **Code docstrings** will provide helpful context for developers
4. **Prompt templates** will be verified for consistency

The plan file itself (`docs/plans/13-clean-up-documentation.md`) serves as documentation of the cleanup process.

## Implementation Notes

### Docstring Style Guide

Use this format for consistency:

```python
def method_name(self, param1: Type1, param2: Type2) -> ReturnType:
    """Brief one-line summary.

    More detailed explanation if needed. Describe behavior,
    side effects, and any important context.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ExceptionType: When this exception is raised
    """
```

For simple, obvious methods, a one-line docstring is sufficient:
```python
def close(self) -> None:
    """Close the database connection."""
```

### Prioritization Strategy

Given the volume of docstring gaps (150+ missing), focus on:

1. **Public API first** - Classes and methods users/contributors interact with
2. **Complex logic second** - Non-obvious code that needs explanation
3. **Private helpers last** - Internal methods (can be brief)

Aim for "good enough" rather than perfection. The goal is helpful documentation, not 100% coverage.

### README.md Updates

Current README.md looks good but needs verification for:
- Command completeness (are `codereview` and `scope` mentioned?)
- Path accuracy (uses `docs/plans/{number}-{slug}.md` format)
- Workflow diagram accuracy
- Recent changes like webhook CLI commands

### docs/design.md Updates

Key areas needing updates:
- "The 5 Commands" section title is outdated (now 7 commands)
- Missing `codereview` and `scope` command documentation
- State machine should show `codereview` workflow
- Prompt architecture should list all current prompts including `codereview.md` and `scope.md`

### Prompt Template Review

All templates already use `{{ plan_path }}` correctly. Main check is to ensure:
- No hardcoded paths remain
- Variable syntax is consistent
- Templates include context properly via `{% include 'context.md' %}`

## Breaking Changes

None. This is documentation-only.

## Rollout

1. Review and update README.md
2. Review and update docs/design.md
3. Add docstrings in priority order (base classes, then commands, then helpers)
4. Verify prompt templates
5. Final review for cohesion and consistency
6. Commit with message: "Clean up documentation across project"

## Success Criteria

- README.md accurately reflects current implementation
- docs/design.md documents all current commands and architecture
- Core classes (`BaseCommand`, `SandboxManager`, `GitHubClient`, `Database`) have comprehensive docstrings
- All public methods have at least one-line docstrings
- Command `run_workflow()` methods explain their workflow steps
- Prompt templates use consistent variable syntax
- No stale references to old `PLAN.md` path
- Documentation feels cohesive and helpful to new contributors
