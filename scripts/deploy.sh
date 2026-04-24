#!/bin/bash
# 部署脚本 - 适用于阿里云轻量应用服务器 (Alibaba Cloud Linux 3)
# 无需 Docker，直接运行 Python

set -e

echo "=== Skill MCP Server 部署脚本 ==="

# 检测操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_ID=$ID
else
    echo "无法检测操作系统"
    exit 1
fi

echo "检测到操作系统: $OS_ID"

# 安装 EPEL 源 (Alibaba Cloud Linux 基于 RHEL)
sudo yum install -y epel-release

# 安装 Python 3.11
echo "=== 安装 Python 3.11 ==="
sudo yum module reset python39 -y
sudo yum module enable python39:3.11 -y
sudo yum install -y python311 python311-pip

# 创建虚拟环境
echo "=== 创建虚拟环境 ==="
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
echo "=== 安装 Python 依赖 ==="
pip install --upgrade pip
pip install -r requirements.txt

# 安装 MySQL (如果需要本地数据库)
echo "=== 安装 MySQL ==="
sudo yum install -y mysql mysql-server
sudo systemctl start mysqld
sudo systemctl enable mysqld

# 创建数据库
echo "=== 创建数据库 ==="
mysql -u root << 'EOSQL'
CREATE DATABASE IF NOT EXISTS skill_mcp CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'mcp_user'@'localhost' IDENTIFIED BY '你的密码';
GRANT ALL PRIVILEGES ON skill_mcp.* TO 'mcp_user'@'localhost';
FLUSH PRIVILEGES;
EOSQL

# 初始化表
mysql -u root skill_mcp < scripts/init_db.sql

# 安装 Redis
echo "=== 安装 Redis ==="
sudo yum install -y redis
sudo systemctl start redis
sudo systemctl enable redis

# 创建 .env 文件（如果不存在）
if [ ! -f .env ]; then
    echo "=== 创建 .env 文件 ==="
    cat > .env << 'EOF'
DB_HOST=localhost
DB_PORT=3306
DB_USER=mcp_user
DB_PASSWORD=你的密码
DB_NAME=skill_mcp

REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

SECRET_KEY=change-me-in-production
DEBUG=false
PORT=8000
LOG_LEVEL=INFO
EOF
    echo ".env 文件已创建，请编辑修改密码"
fi

# 初始化示例数据
echo "=== 初始化示例数据 ==="
python scripts/seed_data.py --with-samples

# 开放防火墙端口
echo "=== 开放防火墙端口 ==="
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload

echo ""
echo "=== 部署完成 ==="
echo "启动服务: source venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo "访问地址: http://服务器IP:8000/docs"
