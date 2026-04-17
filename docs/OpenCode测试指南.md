# OpenCode MCP 连接与测试指南

## 服务信息

- **服务地址**: `http://localhost:8000`
- **MCP 端点**: `http://localhost:8000/mcp`
- **API Key**: 获取方式见下方说明

## 获取 API Key

1. 启动服务后访问 `http://localhost:8000/docs`
2. 使用 admin API Key 登录
3. 调用 `POST /api/v1/users` 创建用户，或查看已有用户的 API Key

## OpenCode MCP 配置 (config.json)

```json
{
  "mcpServers": {
    "skill-server": {
      "url": "http://localhost:8000/mcp?key=YOUR_API_KEY",
      "transport": "streamable-http"
    }
  }
}
```

## 测试提示词

### 1. 连接验证
```
请连接到 skill-mcp-server，然后告诉我连接是否成功，以及返回了哪些可用的 skills。
```

### 2. 技能列表验证
```
调用 tools/list 方法，获取所有可用的 skills，告诉我一共有多少个，每个的名称和描述是什么。
```

### 3. 技能调用测试 - Code Review
```
请使用 code-review skill，帮我审查下面这段代码有没有问题：

def calculate_total(items):
    total = 0
    for item in items:
        total += item['price']
    return total
```

### 4. 技能调用测试 - Data Analysis
```
请使用 data-analysis skill，告诉我如何分析一个 CSV 文件中的销售数据。
```

### 5. 技能调用测试 - API Design
```
请使用 api-design skill，帮我设计一个用户管理系统的 RESTful API。
```

### 6. 批量测试所有技能
```
请依次测试所有技能，告诉我每个技能的返回内容是否正确。
```

## 预期返回格式

调用 `tools/list` 预期返回：
```json
{
  "result": [
    {
      "name": "use_skill_code-review",
      "description": "Perform comprehensive code review...",
      "inputSchema": {...}
    },
    {
      "name": "use_skill_data-analysis",
      "description": "Analyze datasets and generate summary...",
      "inputSchema": {...}
    },
    {
      "name": "use_skill_api-design",
      "description": "Design RESTful APIs with proper HTTP...",
      "inputSchema": {...}
    }
  ]
}
```

调用 `tools/call` (skill=code-review) 预期返回：
```markdown
# Code Review Skill

When reviewing code, follow these steps:

1. **Style Check**: Verify code follows project conventions
2. **Logic Review**: Check for bugs, edge cases, and correctness
3. **Best Practices**: Ensure modern patterns and efficiency
4. **Documentation**: Check for appropriate comments and docstrings

Provide constructive feedback with specific suggestions.
```

## 可用 Skills

> 注：实际返回的 skills 取决于用户的授权情况。

| 名称 | 描述 |
|------|------|
| code-review | Perform comprehensive code review including style, logic, and best practices. |
| data-analysis | Analyze datasets and generate summary statistics and visualizations. |
| api-design | Design RESTful APIs with proper HTTP methods, status codes, and documentation. |

## 故障排查

### 401 Unauthorized
- 检查 API Key 是否正确配置
- 使用 Header 方式更安全：`X-API-Key: YOUR_API_KEY`
- 或使用 URL 方式：`?key=YOUR_API_KEY`
- 检查 key 是否过期或被禁用

### 连接超时
- 确认服务正在运行：`curl http://localhost:8000/health`
- 确认端口 8000 未被占用

### 返回空的 tools list
- 确认用户已被授权相应技能
- 使用 admin API Key 调用 `POST /api/v1/user_skills` 为用户授权

### 500 Internal Server Error
- 检查服务日志
- 确认 MySQL 和 Redis 服务正常运行
- 确认 skills 目录存在且有权限
