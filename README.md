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

创建 `.env` 文件，配置数据库和 Redis：

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=skill_mcp

REDIS_HOST=localhost
REDIS_PORT=6379

SECRET_KEY=change-me-in-production
DEBUG=true
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
| GET | `/api/v1/users` | 用户列表（分页） | admin |

### 技能管理

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | `/api/v1/skills` | 从文件创建技能 | admin |
| POST | `/api/v1/skills/json` | 从 JSON 创建技能 | admin |
| GET | `/api/v1/skills` | 技能列表 | admin |
| PUT | `/api/v1/skills/{name}` | 更新技能元数据 | admin |
| PUT | `/api/v1/skills/{name}/content` | 更新技能内容 | admin |
| PUT | `/api/v1/skills/{name}/upload` | 上传技能文件 | admin |
| POST | `/api/v1/skills/{name}/sync` | 同步文件系统到数据库 | admin |
| DELETE | `/api/v1/skills/{name}` | 删除技能 | admin |
| GET | `/api/v1/skills/{name}/content` | 获取技能内容 | admin |
| GET | `/api/v1/skills/{name}/files` | 列出技能文件 | admin |
| GET | `/api/v1/skills/{name}/files/{filename}` | 下载技能文件 | user |

### 授权管理

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| POST | `/api/v1/user_skills` | 授权技能 | admin |
| DELETE | `/api/v1/user_skills` | 撤销授权 | admin |

### 调用日志

| 方法 | 路径 | 描述 | 权限 |
|------|------|------|------|
| GET | `/api/v1/logs` | 调用日志列表 | admin |

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

### get_skill_index

获取技能的文件索引（文件名和大小，不含内容）。

**输入**:
```json
{
  "arguments": {
    "skill_name": "code-review"
  }
}
```

**输出**: JSON 格式的文件索引

### get_skill_file

读取技能指定文件的内容。

**输入**:
```json
{
  "arguments": {
    "skill_name": "code-review",
    "file_path": "SKILL.md"
  }
}
```

**输出**: 文件内容

## 测试

```bash
# 单元测试（需要服务运行）
python -m pytest tests/ -v
```

> 注：集成测试已移除。请使用 MCP 客户端直接测试。

## 项目结构

```
skill-mcp-server/
├── app/
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py             # 配置管理
│   ├── api/v1/              # REST API
│   │   ├── users.py         # 用户管理
│   │   ├── skills.py         # 技能管理
│   │   ├── auth.py           # 授权管理
│   │   └── logs.py           # 日志查询
│   ├── mcp/
│   │   ├── server.py         # MCP 服务端实现
│   │   ├── handlers.py        # MCP 工具处理
│   │   └── session.py         # 会话管理
│   ├── services/             # 业务逻辑
│   │   ├── skill_service.py
│   │   └── user_service.py
│   ├── db/
│   │   ├── session.py        # 数据库连接池
│   │   └── crud/            # CRUD 操作
│   │       ├── user.py
│   │       ├── skill.py
│   │       ├── user_skill.py
│   │       └── call_log.py
│   └── models/              # Pydantic 模型
│       ├── user.py
│       └── skill.py
├── tests/                   # 单元测试
├── scripts/                 # 辅助脚本
│   └── seed_data.py         # 初始化数据
├── skills/                  # 技能内容目录
│   ├── code-review/
│   ├── data-analysis/
│   └── ...
├── examples/                # 示例脚本
└── docs/                    # 文档
```

## 技术栈

- **Web 框架**: FastAPI
- **MCP 协议**: mcp Python SDK
- **数据库**: MySQL (aiomysql)
- **缓存**: Redis
- **认证**: API Key (X-API-Key header 或 ?key= query param)

## License

MIT
