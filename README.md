# Skill MCP Server

基于 MCP (Model Context Protocol) 协议的技能管理服务端。支持 AI Agent（如 Claude Code、OpenCode）通过 MCP 协议动态获取授权的 Skills。

## 特性

- **MCP 协议支持**: 通过 HTTP Streamable 传输层暴露 MCP 接口
- **用户认证**: API Key 认证，每个用户独立的 Key
- **权限控制**: 基于用户的 Skill 授权，实时生效
- **REST API**: 完整的管理接口（用户、技能、授权）
- **调用审计**: 记录所有 Skill 调用日志
- **权限过滤**: `tools/list` 仅返回用户授权的 Skills
- **安全防护**: 支持压缩包炸弹检测、路径遍历防护
- **MCP 依赖**: 支持声明技能所需的外部 MCP 服务依赖

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
REDIS_DB=0
REDIS_PASSWORD=

SECRET_KEY=change-me-in-production
DEBUG=true
PORT=8000
LOG_LEVEL=INFO
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
| GET | `/api/v1/skills/{name}/files/{filename}` | 下载技能文件 | admin |
| GET | `/api/v1/skills/{name}/dependencies` | 获取 MCP 依赖 | admin |

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

返回当前用户授权的所有技能（含全局工具和技能专用工具）。

**全局工具**:
- `get_skill_index` - 获取技能的文件索引
- `get_skill_file` - 读取技能指定文件的内容

**技能工具**:
- `get_skill_{name}` - 获��指定技能完整内容（向后兼容）

### get_skill_index

获取技能的文件索引（文件名和大小，不含内容）。

**输入**:
```json
{
  "skill_name": "code-review"
}
```

**输出**: JSON 格式的文件索引

### get_skill_file

读取技能指定文件的内容。

**输入**:
```json
{
  "skill_name": "code-review",
  "file_path": "SKILL.md"
}
```

**输出**: 文件内容

### get_skill_{name}

获取指定技能完整内容（向后兼容）。

**输入**:
```json
{
  "skill_name": "code-review"
}
```

**输出**: Skill 内容 (JSON 格式)

## MCP 依赖配置

技能可以声明所需的外部 MCP 服务依赖。在创建技能时，通过 `mcp_config` 参数传入：

```json
{
  "mcpServers": {
    "sorftime": {
      "url": "https://mcp.sorftime.com",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      }
    }
  }
}
```

系统会自动提取 URL 并存储，调用技能时会返回详细的 MCP 配置检查指南。

## 安全特性

- **API Key 认证**: 通过 `X-API-Key` header 或 `?key=` query param
- **路径遍历防护**: 防止 `..` 攻击
- **压缩包炸弹检测**: 检测恶意压缩比（>100:1）
- **文件大小限制**: 单文件最大 100MB，总提取最大 100MB
- **文件数量限制**: 最多 1000 个文件

## 测试

```bash
# 单元测试（需要服务运行）
python -m pytest tests/ -v
```

## 技术栈

- **Web 框架**: FastAPI
- **MCP 协议**: mcp Python SDK
- **数据库**: MySQL (aiomysql)
- **缓存**: Redis
- **认证**: API Key (X-API-Key header 或 ?key= query param)

## License

MIT