# Implementation Plan: Add /goodbye Endpoint

## Issue
Add a `/goodbye` endpoint that returns `{"message": "Goodbye, World!"}`

**Iteration:** Add a parameter to customize the goodbye message

## Analysis
This is a Python FastAPI-based GitHub bot (AIDW). All HTTP endpoints are defined in `/home/user/repo/src/aidw/server/app.py`. Currently, there are three endpoints:
- `GET /` - Health check
- `GET /health` - Health check
- `POST /webhook` - GitHub webhook handler

Tests exist in `/home/user/repo/tests/test_app.py` using FastAPI TestClient.

## Implementation Approach

### 1. Add the /goodbye Endpoint with Optional Parameter
**File:** `/home/user/repo/src/aidw/server/app.py`

Add a new GET endpoint with an optional query parameter for customization:
```python
@app.get("/goodbye")
async def goodbye(name: str | None = None):
    """Goodbye endpoint with optional name parameter."""
    if name:
        return {"message": f"Goodbye, {name}!"}
    return {"message": "Goodbye, World!"}
```

**Location:** After the `/health` endpoint (around line 66)

**Rationale:**
- Follows existing code style and conventions
- Uses FastAPI's automatic query parameter handling
- Optional parameter maintains backward compatibility
- Default behavior returns "Goodbye, World!" when no parameter provided
- When `name` parameter is provided, returns personalized message

### 2. Update Test Suite
**File:** `/home/user/repo/tests/test_app.py`

Update pytest tests for the `/goodbye` endpoint to cover both cases:
- Test default behavior: `/goodbye` returns `{"message": "Goodbye, World!"}`
- Test with parameter: `/goodbye?name=Alice` returns `{"message": "Goodbye, Alice!"}`
- Test URL encoding: `/goodbye?name=John%20Doe` works correctly

**Rationale:**
- Tests ensure both default and parameterized behavior work
- Comprehensive coverage of the new feature
- Backward compatibility is validated

### 3. Update Documentation
**File:** `/home/user/repo/README.md`

Update the API endpoints section to document the optional parameter:
- Change description from `Returns {"message": "Goodbye, World!"}` to include parameter info
- Add example usage with parameter

**Rationale:**
- Keeps documentation in sync with code
- Helps users discover the parameter functionality

## Files to Modify
1. `/home/user/repo/PLAN.md` - Update with iteration details
2. `/home/user/repo/src/aidw/server/app.py` - Add optional parameter
3. `/home/user/repo/tests/test_app.py` - Update tests for parameterized behavior
4. `/home/user/repo/README.md` - Update documentation

## Testing Plan
- Run pytest to verify all tests pass
- Test default behavior: `GET /goodbye`
- Test with parameter: `GET /goodbye?name=Alice`

## Risks/Considerations
- Backward compatible - existing behavior preserved when no parameter provided
- No security implications - simple string formatting
- No breaking changes
