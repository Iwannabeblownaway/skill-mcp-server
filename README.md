# Skill MCP Server

基于 MCP (Model Context Protocol) 协议的技能管理服务端。支持 AI Agent（如 Claude Code、OpenCode）通过 MCP 协议动态获取授权的 Skills。

## 特性

- **MCP 协议支持**: 通过 HTTP Streamable 传输层暴露 MCP 接口
- **用户认证**: API Key 认证，每个用户独立的 Key
- **权限控制**: 基于用户的 Skill 授权，实时生效
- **REST API**: 完整的管理接口（用户、技能、授权）
- **调用审计**: 记录所有 Skill 调用日志
- **权限过滤**: `tools/list` 仅返回用户授权的 Skills

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，修改数据库和 Redis 配置：

```bash
cp .env.example .env
```

### 3. 初始化数据库

```bash
python scripts/seed_data.py --with-samples
```

### 4. 启动服务

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

服务启动后：
- REST API: `http://localhost:8000`
- MCP 端点: `http://localhost:8000/mcp`
- 健康检查: `http://localhost:8000/health`
- API 文档: `http://localhost:8000/docs`

## OpenCode 配置

在 OpenCode 的 `config.json` 中添加：

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

> 获取 API Key: 登录后访问 `http://localhost:8000/docs` 查看用户 API

## API 接口

### 用户管理

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | `/api/v1/users` | 创建用户 | admin |
| GET | `/api/v1/users` | 用户列表 | admin |
| GET | `/api/v1/users/{id}` | 用户详情 | admin |

### 技能管理

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | `/api/v1/skills` | 创建技能 | admin |
| GET | `/api/v1/skills` | 技能列表 | admin |
| PUT | `/api/v1/skills/{id}` | 更新技能 | admin |
| DELETE | `/api/v1/skills/{id}` | 删除技能 | admin |

### 授权管理

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | `/api/v1/user_skills` | 授权技能 | admin |
| DELETE | `/api/v1/user_skills` | 撤销授权 | admin |

## MCP 工具

### tools/list

返回当前用户授权的所有技能。

**输入**: 无

**输出**: Skill 列表（含 name, description, inputSchema）

### tools/call

调用指定技能获取内容。

**输入**:
```json
{
  "name": "use_skill_code-review",
  "arguments": {
    "skill_name": "code-review"
  }
}
```

**输出**: Skill 内容 (Markdown 格式)

## 测试

```bash
# 单元测试（需要服务运行）
python -m pytest tests/ -v

# MCP 集成测试（需要服务运行）
python scripts/test_mcp_integration.py
python scripts/test_opencode_mcp.py
```

> 注：集成测试依赖服务在 localhost:8000 运行。先启动服务再运行集成测试。

## 项目结构

```
skill-mcp-server/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── api/v1/              # REST API
│   │   ├── users.py         # 用户管理
│   │   ├── skills.py        # 技能管理
│   │   └── auth.py          # 授权管理
│   ├── mcp/
│   │   └── server.py        # MCP 服务端实现
│   ├── services/            # 业务逻辑
│   │   ├── skill_service.py
│   │   └── user_service.py
│   └── db/
│       ├── session.py        # 数据库连接
│       └── crud/             # CRUD 操作
├── tests/                   # 单元测试
├── scripts/                 # 辅助脚本
│   └── seed_data.py         # 初始化数据
└── docs/                   # 文档
```

## 技术栈

- **Web 框架**: FastAPI
- **MCP 协议**: mcp Python SDK
- **数据库**: MySQL (aiomysql)
- **缓存**: Redis
- **认证**: API Key

## License

MIT
