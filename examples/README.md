# Examples

本目录包含 SKILL 上传的示例脚本。

## 文件说明

| 文件 | 说明 |
|------|------|
| `upload_skill.py` | 上传 SKILL 的完整示例脚本 |

## 快速开始

### 1. 配置

修改 `upload_skill.py` 中的配置：
```python
BASE_URL = "http://localhost:8000"
API_KEY = "your_admin_api_key_here"  # 替换为你的 admin API key

# 示例 Skill 路径
EXAMPLE_SKILL_PATH = Path(r"C:\Users\Administrator\.config\opencode\skills\skill-auditor")
```

### 2. 运行

```bash
cd examples
python upload_skill.py
```

## 上传方式

### 方式1: 单文件上传（推荐）

```bash
# 上传单个 SKILL.md，自动创建 skills/{name}/SKILL.md
curl -X POST "http://localhost:8000/api/v1/skills" \
  -H "X-API-Key: YOUR_KEY" \
  -F "file=@skill.md"
```

### 方式2: 压缩包上传

```bash
# 上传 .zip/.tar.gz/.skill 等格式，自动解压
curl -X POST "http://localhost:8000/api/v1/skills" \
  -H "X-API-Key: YOUR_KEY" \
  -F "file=@skill.zip"
```

### 方式3: 更新已有 skill

```bash
curl -X PUT "http://localhost:8000/api/v1/skills/{name}/upload" \
  -H "X-API-Key: YOUR_KEY" \
  -F "file=@new-content.md"
```

### 方式4: JSON 上传文本

```bash
curl -X PUT "http://localhost:8000/api/v1/skills/{name}/content" \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"content": "# SKILL content..."}'
```

## 支持格式

| 格式 | 说明 |
|------|------|
| 单个文件 | 自动封装到 `skills/{name}/` |
| `.zip` | ZIP 压缩包 |
| `.tar`, `.tar.gz`, `.tgz` | TAR 压缩包 |
| `.tar.bz2`, `.tar.xz` | 其他 TAR 变体 |
| `.skill` | 等同于 .zip |
| `.gz`, `.bz2`, `.xz` | 单文件压缩 |
