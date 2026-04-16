## 任务目标
实现一个 MCP 协议的服务端（Python + FastAPI），用于管理团队 SKILL，并通过 MCP SSE 对外提供服务。

## 已有文档（请先阅读）
- 需求文档：`./docs/需求文档.md`
- 架构文档：`./docs/架构文档.md`
- 目录结构：按照 `./docs/目录结构.md` 中的设计

## 技术栈与版本
- Python 3.10+
- FastAPI 0.104+
- MCP SDK (Python) 0.1.0+ （`mcp` 包）
- aiomysql 0.2.0+
- redis 5.0+
- pydantic-settings 2.1+
- uvicorn 0.24+
- alembic (数据库迁移)

## 必须实现的核心功能

### 1. 配置模块 (`app/config.py`)
使用 `pydantic-settings.BaseSettings`，从 `.env` 读取：
- 数据库连接（host, port, user, password, database）
- Redis 连接（host, port, db）
- API Key 长度、JWT 密钥（如需要）
- 服务端口、环境（dev/prod）

### 2. 数据库连接池 (`app/db/session.py`)
- 使用 `aiomysql.create_pool`，全局单例
- 提供 `get_db()` 异步上下文管理器，自动归还连接

### 3. 数据访问层 (`app/db/crud/`)
为每张表实现异步 CRUD：
- `user.py`: `get_by_api_key`, `create`, `list`, `get_by_id`
- `skill.py`: `create`, `update`, `delete`, `get_by_name`, `list_all`
- `user_skill.py`: `grant`, `revoke`, `get_user_skills`
- `call_log.py`: `create_log`

### 4. 业务逻辑层 (`app/services/skill_service.py`)
- `async def get_user_skills(user_id: int) -> list[Skill]`：返回用户被授权的技能（name, description, content）
- `async def check_permission(user_id: int, skill_name: str) -> bool`
- `async def get_skill_content(user_id: int, skill_name: str) -> tuple[str, dict]`：返回 (content, error)，无权限或不存在时 error 非空
- `async def log_call(user_id: int, skill_name: str, status: str, error_msg: str, duration_ms: int)`

### 5. MCP 服务器 (`app/mcp/`)
- `server.py`：创建 `mcp.server.Server` 实例，并集成到 FastAPI（通过 SSE transport）
  - 具体方法：使用 `sse.SseServerTransport` 配合 FastAPI 路由 `@app.post("/mcp/sse")` 和 `@app.get("/mcp/messages")`
  - 参考 MCP Python SDK 文档中 “FastAPI + SSE” 的示例
- `handlers.py`：实现 `list_tools` 和 `call_tool` 处理器
  - `list_tools`：调用 `skill_service.get_user_skills`，返回 `[Tool(name=f"use_skill_{s.name}", description=s.description, inputSchema=...)]`
  - `call_tool`：处理 `use_skill_xxx` 工具，参数 `{"skill_name": "xxx"}`（或直接从 tool name 解析）。调用 `skill_service.get_skill_content`，返回技能内容或错误信息。同时记录调用日志（异步，不影响响应）。
- `auth.py`：在 MCP 连接建立时，从 HTTP 请求头获取 `X-API-Key`，验证后生成 session 存入 Redis，后续每个 MCP 消息都能通过 session 获取 user_id

### 6. 管理 REST API (`app/api/v1/`)
- 所有管理接口需验证 `X-API-Key`，且该用户 role='admin'
- `POST /users`：创建用户（生成随机 API Key）
- `GET /users`：用户列表
- `POST /skills`：创建技能
- `PUT /skills/{name}`：更新技能
- `DELETE /skills/{name}`：删除技能
- `POST /user_skills`：授权（user_id, skill_id）
- `DELETE /user_skills`：取消授权
- `GET /logs`：调用日志列表（支持过滤 user_id, skill_id, 时间范围）

### 7. 主入口 (`app/main.py`)
- 创建 FastAPI app
- 生命周期事件：启动时初始化数据库连接池、Redis 连接；关闭时清理
- 挂载路由：
  - `/mcp/sse`：MCP SSE 端点
  - `/api/v1`：管理 API
  - `/health`：健康检查
- 全局异常处理

## 额外要求
- 提供 `docker-compose.yml`：包含 MySQL, Redis, 以及本服务（使用 Dockerfile）
- 提供 `alembic` 迁移脚本：初始化表结构（`init_db.sql` 也可，但建议迁移）
- 提供 `requirements.txt` 和 `.env.example`
- 提供简单的单元测试（至少测试 `skill_service` 和 API 认证）

## 输出要求
请按照给定的目录结构，输出每个文件的完整代码。不要省略任何文件。代码必须可以直接复制、运行。
