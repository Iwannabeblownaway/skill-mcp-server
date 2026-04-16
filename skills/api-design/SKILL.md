# API Design Skill

Design RESTful APIs with proper HTTP methods, status codes, and documentation.

## Principles

### REST Constraints
1. **Client-Server**: Separation of concerns
2. **Stateless**: Each request contains all info
3. **Cacheable**: Responses can be cached
4. **Uniform Interface**: Consistent resource identification

### URL Design

```
# Good
GET    /users              # List users
GET    /users/{id}         # Get user
POST   /users              # Create user
PUT    /users/{id}         # Update user
DELETE /users/{id}         # Delete user

# Bad
GET    /getUsers
POST   /createUser
POST   /deleteUser?id=123
```

### HTTP Methods

| Method | Purpose | Idempotent | Safe |
|--------|---------|------------|------|
| GET | Read resource | Yes | Yes |
| POST | Create resource | No | No |
| PUT | Replace resource | Yes | No |
| PATCH | Partial update | No | No |
| DELETE | Remove resource | Yes | No |

### Status Codes

| Code | Meaning | When to Use |
|------|---------|-------------|
| 200 | OK | Successful GET/PUT/PATCH |
| 201 | Created | Successful POST creating resource |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Missing auth |
| 403 | Forbidden | Auth but no permission |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Duplicate resource |
| 500 | Server Error | Unexpected error |

## Documentation

### OpenAPI/Swagger

```yaml
openapi: 3.0.0
info:
  title: My API
  version: 1.0.0
paths:
  /users:
    get:
      summary: List users
      responses:
        '200':
          description: Success
```

## Best Practices

1. Use nouns for resources, not verbs
2. Use plural forms: `/users` not `/user`
3. Nest sub-resources max 2 levels
4. Use query params for filtering/pagination
5. Version your API: `/v1/users`
6. Return consistent error format
7. Include pagination metadata
