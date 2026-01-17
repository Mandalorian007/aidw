# Implementation Plan: Add /hello Endpoint

## 1. Approach

This is a straightforward feature addition that requires adding a new REST API endpoint to the existing FastAPI application. The endpoint will follow the established patterns in the codebase:

- **Framework**: FastAPI (already in use)
- **Location**: `/home/user/repo/src/aidw/server/app.py`
- **Pattern**: Simple GET endpoint using FastAPI decorator (similar to existing `/` and `/health` endpoints)
- **Response**: JSON object `{"message": "Hello, World!"}`

The implementation will be minimal and follow the existing code style:
- Add the endpoint between the existing health check endpoints and the webhook endpoint
- Use async function definition (consistent with other endpoints)
- Return a simple dictionary (FastAPI automatically serializes to JSON)
- Add appropriate docstring

### Rationale

This approach:
- Maintains consistency with existing endpoint patterns (app.py:54-63)
- Requires minimal code changes (single function addition)
- Follows FastAPI best practices
- Requires no new dependencies
- Preserves existing functionality

## 2. Files

### Files to Modify

#### `/home/user/repo/src/aidw/server/app.py`
**Line location**: Between line 63 and line 66 (after `health()` endpoint, before `process_command()` function)

**Changes**:
- Add new GET endpoint `/hello` that returns `{"message": "Hello, World!"}`
- Function signature: `async def hello()`
- Include docstring: `"""Hello World endpoint for testing."""`

**Code to add**:
```python
@app.get("/hello")
async def hello():
    """Hello World endpoint for testing."""
    return {"message": "Hello, World!"}
```

### Files to Create

#### `/home/user/repo/tests/test_app.py`
**Purpose**: Unit tests for the new `/hello` endpoint

**Contents**:
- Import necessary testing libraries (pytest, httpx, FastAPI TestClient)
- Create test client for the FastAPI app
- Test successful GET request to `/hello`
- Verify response status code (200)
- Verify response JSON structure and content
- Test response content-type header (application/json)

**Test cases**:
1. `test_hello_endpoint_success` - Verify endpoint returns correct response
2. `test_hello_endpoint_method` - Verify endpoint only accepts GET requests
3. `test_hello_response_structure` - Verify response has correct JSON structure

#### `/home/user/repo/tests/__init__.py`
**Purpose**: Make tests directory a Python package

**Contents**: Empty file (standard Python package marker)

## 3. Testing

### Testing Strategy

#### Unit Tests
- Create comprehensive unit tests using `pytest` and `pytest-asyncio` (already configured in pyproject.toml:52-54)
- Use FastAPI's `TestClient` for endpoint testing
- Test coverage should include:
  - Successful response (200 status code)
  - Correct JSON payload
  - Correct content-type header
  - HTTP method validation (GET only)

#### Manual Testing
After implementation, test manually using:
```bash
# Start the server
aidw server

# Test the endpoint (in another terminal)
curl http://localhost:8000/hello

# Expected output:
# {"message":"Hello, World!"}
```

#### Integration Testing
- Verify endpoint works alongside existing endpoints
- Ensure no interference with webhook functionality
- Test server startup/shutdown with new endpoint

### Test Execution
```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest -v tests/

# Run specific test file
pytest tests/test_app.py

# Run with coverage
pytest --cov=aidw.server tests/
```

## 4. Documentation

### Code Documentation
- **Docstring**: Add docstring to the `hello()` function explaining its purpose
- **Inline comments**: Not needed for this simple endpoint

### API Documentation
FastAPI automatically generates OpenAPI documentation. The new endpoint will appear at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

No manual documentation updates needed as FastAPI will auto-document:
- Endpoint path: `/hello`
- HTTP method: `GET`
- Response schema: `{"message": "string"}`
- Function docstring will appear as endpoint description

### User Documentation
No README.md updates required because:
- This is a test endpoint (per issue description)
- The main webhook endpoint (`/webhook`) remains the primary feature
- Users can discover the endpoint via FastAPI's auto-generated docs

### Optional Documentation (if desired)
If we want to document the endpoint in README.md:
- Add to API endpoints section (if exists)
- Include example curl command
- Mention it's a test endpoint

## 5. Implementation Steps

1. **Add endpoint** (src/aidw/server/app.py:64-68)
   - Add `@app.get("/hello")` decorator
   - Create `async def hello()` function
   - Return `{"message": "Hello, World!"}`

2. **Create test directory structure**
   - Create `/home/user/repo/tests/` directory
   - Create `/home/user/repo/tests/__init__.py`

3. **Write tests** (tests/test_app.py)
   - Import dependencies
   - Set up TestClient
   - Write test cases for /hello endpoint

4. **Verify implementation**
   - Run pytest to ensure tests pass
   - Start server and test manually with curl
   - Check FastAPI docs at /docs

## 6. Risk Assessment

### Risks: LOW
- Simple, isolated change
- No database interactions
- No external dependencies
- No authentication/authorization requirements
- No breaking changes to existing functionality

### Potential Issues
1. **Port conflicts**: Server may not start if port 8000 is in use
   - Mitigation: Document port configuration options

2. **Test dependencies**: pytest/pytest-asyncio must be installed
   - Mitigation: Already configured in pyproject.toml dev dependencies

## 7. Rollback Plan

If issues arise:
1. Remove the endpoint function from app.py (lines 64-68)
2. Remove test files (tests/test_app.py, tests/__init__.py)
3. Commit and push the revert

## 8. Acceptance Criteria

- [ ] `/hello` endpoint responds to GET requests
- [ ] Response is `{"message": "Hello, World!"}`
- [ ] Status code is 200
- [ ] Content-Type is application/json
- [ ] All tests pass
- [ ] Endpoint appears in FastAPI docs
- [ ] No impact on existing endpoints
- [ ] Code follows project style (ruff linting passes)

## 9. Estimated Changes

- **Lines added**: ~15 (4 in app.py, ~11 in tests)
- **Files modified**: 1 (src/aidw/server/app.py)
- **Files created**: 2 (tests/__init__.py, tests/test_app.py)
- **Complexity**: Very Low
- **Dependencies**: None (all required packages already present)
