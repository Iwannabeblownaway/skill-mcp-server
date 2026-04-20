#!/usr/bin/env python3
"""Register colleague and leader skills to database."""

import sys
import pymysql
from datetime import datetime

conn = pymysql.connect(
    host="localhost",
    port=3306,
    user="Dorothy",
    password="<redacted>",
    database="skill_mcp",
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
)

new_skills = [
    {
        "name": "colleague",
        "description": "将普通说话方式转换为互联网黑话风格。赋能、闭环、拉齐、打透、抓手、链路...",
        "path": "colleague",
    },
    {
        "name": "leader",
        "description": "将普通说话方式转换为领导讲话风格。战略、格局、方向、资源倾斜、重点突破...",
        "path": "leader",
    },
]

with conn.cursor() as cursor:
    # Get admin user id
    cursor.execute("SELECT id FROM users WHERE role = 'admin' LIMIT 1")
    admin = cursor.fetchone()
    if not admin:
        print("Error: No admin user found. Please run seed_data.py first.")
        sys.exit(1)
    admin_id = admin["id"]

    for skill in new_skills:
        # Check if exists
        cursor.execute("SELECT id FROM skills WHERE name = %s", (skill["name"],))
        if cursor.fetchone():
            print(f"Skill '{skill['name']}' already exists, skipping...")
            continue

        # Insert skill
        cursor.execute(
            """
            INSERT INTO skills (name, description, path, status, created_at, updated_at)
            VALUES (%s, %s, %s, 'active', %s, %s)
        """,
            (
                skill["name"],
                skill["description"],
                skill["path"],
                datetime.now(),
                datetime.now(),
            ),
        )
        conn.commit()

        skill_id = cursor.lastrowid

        # Grant admin access
        cursor.execute(
            """
            INSERT INTO user_skills (user_id, skill_id, granted_at)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE granted_at = granted_at
        """,
            (admin_id, skill_id, datetime.now()),
        )
        conn.commit()

        print(f"Created skill: {skill['name']} -> {skill['path']}/")

conn.close()
print("Done!")
