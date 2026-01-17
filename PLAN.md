# Implementation Plan: Add /goodbye Endpoint

## Issue
Add a `/goodbye` endpoint that returns `{"message": "Goodbye, World!"}`

## Analysis
This is a Python FastAPI-based GitHub bot (AIDW). All HTTP endpoints are defined in `/home/user/repo/src/aidw/server/app.py`. Currently, there are three endpoints:
- `GET /` - Health check
- `GET /health` - Health check
- `POST /webhook` - GitHub webhook handler

The project currently has no test suite (pytest is configured but no tests exist).

## Implementation Approach

### 1. Add the /goodbye Endpoint
**File:** `/home/user/repo/src/aidw/server/app.py`

Add a new GET endpoint following the existing pattern:
```python
@app.get("/goodbye")
async def goodbye():
    """Goodbye endpoint."""
    return {"message": "Goodbye, World!"}
```

**Location:** After the `/health` endpoint (around line 64)

**Rationale:**
- Follows existing code style and conventions
- Uses FastAPI's automatic JSON conversion
- Simple async function with docstring
- Consistent with other simple endpoints in the file

### 2. Create Test Infrastructure and Tests
**New Directory:** `/home/user/repo/tests/`
**New File:** `/home/user/repo/tests/test_app.py`

Create pytest tests for the `/goodbye` endpoint (and optionally other endpoints for completeness):
- Test that `/goodbye` returns 200 status code
- Test that response JSON matches `{"message": "Goodbye, World!"}`
- Use `httpx.AsyncClient` with FastAPI's TestClient pattern

**Rationale:**
- Pytest is already configured in `pyproject.toml`
- `pytest-asyncio` is available for async testing
- Tests ensure the endpoint works as expected

### 3. Update Documentation
**File:** `/home/user/repo/README.md`

Update the API endpoints section (if it exists) to include the new `/goodbye` endpoint.

**Rationale:**
- Keeps documentation in sync with code
- Helps users discover the endpoint

### 4. Commit Strategy
- Single commit with all changes: "Add /goodbye endpoint with tests"
- Or separate commits if changes are substantial

## Files to Modify
1. `/home/user/repo/src/aidw/server/app.py` - Add endpoint
2. `/home/user/repo/tests/test_app.py` - Create tests (new file)
3. `/home/user/repo/README.md` - Update documentation (if applicable)

## Testing Plan
- Run pytest to verify tests pass
- Optionally start the server and test manually with curl/httpx

## Risks/Considerations
- None - this is a simple, non-breaking additive change
- No dependencies on other systems
- No security implications
