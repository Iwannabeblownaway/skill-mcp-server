# Unit Tests for skill-mcp-server

This directory contains comprehensive unit tests for the skill-mcp-server project.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Fixtures and configuration
├── README.md                # This file
├── test_api/                # API endpoint tests
│   ├── __init__.py
│   ├── test_auth.py         # User-skill authorization tests
│   ├── test_skills.py       # Skill management tests
│   └── test_users.py        # User management tests
├── test_mcp/                # MCP server tests
│   ├── __init__.py
│   └── test_server.py       # MCP tools and dependencies
├── test_admin/              # Admin panel tests
│   ├── __init__.py
│   └── test_router.py       # Admin router helpers
└── test_services/           # Service layer tests
    ├── __init__.py
    ├── test_skill_service.py # Skill service tests
    └── test_user_service.py  # User service tests
```

## Running Tests

### Run all tests
```bash
python -m pytest tests/
```

### Run with verbose output
```bash
python -m pytest tests/ -v
```

### Run specific test file
```bash
python -m pytest tests/test_services/test_skill_service.py -v
```

### Run specific test class
```bash
python -m pytest tests/test_api/test_skills.py::TestCreateSkill -v
```

### Run specific test method
```bash
python -m pytest tests/test_services/test_user_service.py::TestVerifyApiKey::test_verify_api_key_success -v
```

### Run with coverage
```bash
python -m pytest tests/ --cov=app --cov-report=html
```

## Test Coverage

### API Endpoints (`test_api/`)

#### `test_users.py`
- `POST /api/v1/users` - Create users (admin only)
  - Success with user role
  - Success with admin role
  - Default role
  - Unauthorized (non-admin)
  - No authentication
  - Invalid data
- `GET /api/v1/users` - List users with pagination (admin only)
  - Success
  - Pagination
  - Empty list
  - Unauthorized (non-admin)
  - Invalid page number
  - Invalid page size

#### `test_skills.py`
- `POST /api/v1/skills/json` - Create skills (admin only)
- `GET /api/v1/skills` - List skills (admin only)
- `GET /api/v1/skills/{name}/dependencies` - Get skill dependencies (admin only)
- `GET /api/v1/skills/{name}/files` - List skill files (admin only)
- `GET /api/v1/skills/{name}/content` - Get skill content (admin only)
- `PUT /api/v1/skills/{name}` - Update skills (admin only)
- `PUT /api/v1/skills/{name}/content` - Update skill content (admin only)
- `POST /api/v1/skills/{name}/sync` - Sync skill from filesystem (admin only)
- `DELETE /api/v1/skills/{name}` - Delete skills (admin only)

#### `test_logs.py`
- `GET /api/v1/logs` - List call logs (admin only)
  - Success
  - Filter by user
  - Filter by skill
  - Filter by time range
  - Pagination
  - Empty list
  - Unauthorized (non-admin)
  - Invalid page/page_size

#### `test_auth.py`
- `POST /api/v1/user_skills` - Grant skills to users (admin only)
- `DELETE /api/v1/user_skills` - Revoke skills from users (admin only)
- Authentication dependencies (`get_current_user`, `verify_admin_api_key`)

### MCP Server (`test_mcp/`)

#### `test_server.py`
- `MCP_CONFIG_PATTERNS` - AI client config path validation
- `_append_deps_warning` - MCP dependency warning injection
- `list_tools` - Tool listing with permission filtering
- `call_tool` - Tool invocation (get_skill_index, get_skill_file, legacy tools)

### Admin Panel (`test_admin/`)

#### `test_router.py`
- `_flatten_single_top_level_dir` - ZIP common prefix detection
- `_parse_dependencies` - Dependency parsing (comma, JSON array, MCP config)
- `redirect_with_message` - XSS protection in flash messages

### Services (`test_services/`)

#### `test_skill_service.py`
- `get_user_skills()` - Retrieve user-authorized skills
- `check_permission()` - Verify user skill access
- `get_skill_content()` - Get skill content with permission check
- `log_call()` - Log skill invocations (success, failure, denied)

#### `test_user_service.py`
- `verify_api_key()` - Validate API keys
- `create_user()` - Create new users
- `get_user_by_id()` - Retrieve users by ID

## Fixtures (`conftest.py`)

### Database Fixtures
- `mock_db_connection` - Mock database connection and cursor
- `mock_db_pool` - Mock database connection pool
- `mock_get_db` - Mocked get_db context manager
- `sqlite_in_memory_db` - SQLite in-memory database for testing

### Redis Fixtures
- `mock_redis_client` - Mock Redis client
- `mock_redis_patch` - Globally patched Redis

### Sample Data Fixtures
- `sample_user` - Regular user sample data
- `sample_admin` - Admin user sample data
- `sample_skill` - Skill sample data
- `sample_skills_list` - Multiple skills sample data
- `sample_call_log` - Call log sample data

### Authentication Fixtures
- `user_auth_headers` - Headers for regular user authentication
- `admin_auth_headers` - Headers for admin authentication

### CRUD Mock Fixtures
- `mock_user_crud` - Mocked user CRUD operations
- `mock_skill_crud` - Mocked skill CRUD operations
- `mock_user_skill_crud` - Mocked user_skill CRUD operations
- `mock_call_log_crud` - Mocked call_log CRUD operations
- `mock_crud_operations` - All CRUD mocks combined

### Application Fixtures
- `app` - FastAPI application with mocked dependencies
- `client` - TestClient for making HTTP requests

## Key Testing Principles

1. **No Real Database/Redis**: All external dependencies are mocked
2. **SQLite In-Memory**: Available for integration-style tests if needed
3. **Async Support**: Uses `pytest-asyncio` for async test functions
4. **Comprehensive Coverage**: Tests cover success cases, failures, and edge cases
5. **Authentication Testing**: Both user and admin role testing
6. **Error Cases**: 401, 403, 404, 422 error scenarios covered

## Known Gaps (Areas for Improvement)

### Low Priority
- **Skills file upload** - POST /api/v1/skills (file upload with multi-part form) - requires actual file mocking
- **Admin skill management** - Status (draft/active), download package, rebuild package
- **MCP auth middleware** - Authentication middleware tests
- **Logs API admin panel** - Admin log viewer integration tests

## Configuration

Test configuration is in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

## Dependencies

Test dependencies are included in `requirements.txt`:
```bash
pip install -r requirements.txt
```