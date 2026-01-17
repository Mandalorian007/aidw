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
- Include proper error handling for invalid requests

### Error Handling Strategy

The endpoint will handle invalid requests robustly:

1. **HTTP Method Validation**: FastAPI automatically returns 405 Method Not Allowed for non-GET requests
2. **Query Parameter Validation**: While no query parameters are required, any provided will be ignored gracefully
3. **Content Type**: No request body expected; if sent, FastAPI will ignore it for GET requests
4. **Response Validation**: Use Pydantic models to ensure consistent response structure

We'll add:
- A Pydantic response model to validate the output structure
- Explicit response model declaration in the endpoint decorator
- Tests to verify proper error responses for invalid requests

### Rationale

This approach:
- Maintains consistency with existing endpoint patterns (app.py:54-63)
- Requires minimal code changes (single function addition + response model)
- Follows FastAPI best practices for error handling and validation
- Leverages FastAPI's built-in HTTP method validation (no custom error handlers needed)
- Ensures type safety with Pydantic response models
- Requires no new dependencies
- Preserves existing functionality

## 2. Files

### Files to Modify

#### `/home/user/repo/src/aidw/server/app.py`
**Line location**: Between line 63 and line 66 (after `health()` endpoint, before `process_command()` function)

**Changes**:
1. Add Pydantic response model for type safety (after imports)
2. Add new GET endpoint `/hello` with response model validation

**Code to add**:

After the existing imports (around line 15):
```python
from pydantic import BaseModel

class HelloResponse(BaseModel):
    """Response model for hello endpoint."""
    message: str
```

Between line 63 and line 66 (after `health()` endpoint):
```python
@app.get("/hello", response_model=HelloResponse)
async def hello() -> HelloResponse:
    """Hello World endpoint for testing.

    Returns:
        HelloResponse: A greeting message
    """
    return HelloResponse(message="Hello, World!")
```

**Error Handling Notes**:
- FastAPI automatically returns 405 Method Not Allowed for POST, PUT, DELETE, etc.
- Response model ensures type safety and consistent response structure
- No additional error handling needed for this simple endpoint

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
- Test error handling for invalid requests

**Test cases**:
1. `test_hello_endpoint_success` - Verify endpoint returns correct response
2. `test_hello_endpoint_status_code` - Verify 200 OK status
3. `test_hello_response_structure` - Verify response has correct JSON structure with "message" key
4. `test_hello_response_content` - Verify message content is "Hello, World!"
5. `test_hello_endpoint_post_method_not_allowed` - Verify POST returns 405
6. `test_hello_endpoint_put_method_not_allowed` - Verify PUT returns 405
7. `test_hello_endpoint_delete_method_not_allowed` - Verify DELETE returns 405
8. `test_hello_with_query_params` - Verify endpoint handles unexpected query params gracefully
9. `test_hello_response_content_type` - Verify Content-Type is application/json

#### `/home/user/repo/tests/__init__.py`
**Purpose**: Make tests directory a Python package

**Contents**: Empty file (standard Python package marker)

## 3. Testing

### Testing Strategy

#### Unit Tests
- Create comprehensive unit tests using `pytest` and `pytest-asyncio` (already configured in pyproject.toml:52-54)
- Use FastAPI's `TestClient` for endpoint testing
- Test coverage should include:
  - **Success cases**:
    - Successful response (200 status code)
    - Correct JSON payload structure
    - Correct message content
    - Correct content-type header
  - **Error handling cases**:
    - POST request returns 405 Method Not Allowed
    - PUT request returns 405 Method Not Allowed
    - DELETE request returns 405 Method Not Allowed
    - PATCH request returns 405 Method Not Allowed
    - Unexpected query parameters are handled gracefully (ignored)
  - **Response validation**:
    - Response conforms to HelloResponse model
    - Response has "message" key
    - Message value is exactly "Hello, World!"

#### Manual Testing
After implementation, test manually using:
```bash
# Start the server
aidw server

# Test successful GET request (in another terminal)
curl http://localhost:8000/hello
# Expected output: {"message":"Hello, World!"}

# Test invalid POST request
curl -X POST http://localhost:8000/hello
# Expected output: {"detail":"Method Not Allowed"}
# Expected status: 405

# Test with query parameters (should be ignored)
curl http://localhost:8000/hello?foo=bar
# Expected output: {"message":"Hello, World!"}
# Expected status: 200

# Test with request body (should be ignored for GET)
curl -X GET http://localhost:8000/hello -H "Content-Type: application/json" -d '{"test":"data"}'
# Expected output: {"message":"Hello, World!"}
# Expected status: 200
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

1. **Add response model** (src/aidw/server/app.py)
   - Import `BaseModel` from pydantic (after line 15)
   - Create `HelloResponse` class with `message: str` field
   - Add docstring explaining the response model

2. **Add endpoint** (src/aidw/server/app.py:64-70)
   - Add `@app.get("/hello", response_model=HelloResponse)` decorator
   - Create `async def hello() -> HelloResponse` function
   - Return `HelloResponse(message="Hello, World!")`
   - Include comprehensive docstring

3. **Create test directory structure**
   - Create `/home/user/repo/tests/` directory
   - Create `/home/user/repo/tests/__init__.py`

4. **Write tests** (tests/test_app.py)
   - Import dependencies (pytest, TestClient, app)
   - Set up TestClient fixture
   - Write success test cases (GET, response validation)
   - Write error handling test cases (POST/PUT/DELETE return 405)
   - Write edge case tests (query params, content-type validation)

5. **Verify implementation**
   - Run pytest to ensure all tests pass (including error cases)
   - Start server and test manually with curl (success and error cases)
   - Check FastAPI docs at /docs to verify endpoint documentation
   - Verify error responses match FastAPI standards

## 6. Risk Assessment

### Risks: LOW
- Simple, isolated change
- No database interactions
- No external dependencies
- No authentication/authorization requirements
- No breaking changes to existing functionality
- Error handling leverages FastAPI's built-in mechanisms

### Potential Issues
1. **Port conflicts**: Server may not start if port 8000 is in use
   - Mitigation: Document port configuration options

2. **Test dependencies**: pytest/pytest-asyncio must be installed
   - Mitigation: Already configured in pyproject.toml dev dependencies

3. **Method Not Allowed responses**: Clients expecting different error format
   - Mitigation: FastAPI returns standard HTTP 405 responses with detail message
   - Impact: Very low - this is standard REST API behavior

4. **Pydantic model overhead**: Minimal performance impact for response validation
   - Mitigation: Negligible for this simple endpoint
   - Benefit: Type safety and consistent responses outweigh minimal overhead

## 7. Rollback Plan

If issues arise:
1. Remove the endpoint function from app.py (lines 64-68)
2. Remove test files (tests/test_app.py, tests/__init__.py)
3. Commit and push the revert

## 8. Acceptance Criteria

### Functionality
- [ ] `/hello` endpoint responds to GET requests
- [ ] Response is `{"message": "Hello, World!"}`
- [ ] Status code is 200 for GET requests
- [ ] Content-Type is application/json
- [ ] Response conforms to HelloResponse Pydantic model

### Error Handling
- [ ] POST requests return 405 Method Not Allowed
- [ ] PUT requests return 405 Method Not Allowed
- [ ] DELETE requests return 405 Method Not Allowed
- [ ] PATCH requests return 405 Method Not Allowed
- [ ] Unexpected query parameters are handled gracefully (ignored)
- [ ] Error responses follow FastAPI standard format

### Testing
- [ ] All tests pass (success and error cases)
- [ ] Test coverage includes method validation
- [ ] Test coverage includes response structure validation
- [ ] Manual testing confirms error responses

### Documentation & Quality
- [ ] Endpoint appears in FastAPI docs with correct schema
- [ ] Response model documented in OpenAPI schema
- [ ] No impact on existing endpoints
- [ ] Code follows project style (ruff linting passes)

## 9. Estimated Changes

- **Lines added**: ~70-80 total
  - ~12 in app.py (response model + endpoint)
  - ~60-70 in tests (9 test cases with comprehensive error handling tests)
- **Files modified**: 1 (src/aidw/server/app.py)
- **Files created**: 2 (tests/__init__.py, tests/test_app.py)
- **Complexity**: Very Low
- **Dependencies**: None (all required packages already present - pydantic, pytest, FastAPI)
