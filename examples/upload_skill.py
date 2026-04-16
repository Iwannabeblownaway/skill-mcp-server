#!/usr/bin/env python3
"""
SKILL 上传示例脚本

演示通过 API 上传 SKILL 的多种方式。
"""

import requests
import sys
import zipfile
import io
from pathlib import Path

# ==================== 配置 ====================
BASE_URL = "http://localhost:8000"
API_KEY = "your_admin_api_key_here"  # 替换为你的 admin API key

HEADERS = {"X-API-Key": API_KEY}

# 示例 Skill 路径（OpenCode 内置的 skill-auditor）
EXAMPLE_SKILL_PATH = Path(r"C:\Users\Administrator\.config\opencode\skills\skill-auditor")


def upload_single_file(filepath: str, skill_name: str = None):
    """方式1: 上传单个文件（自动封装到文件夹）

    Args:
        filepath: 文件路径
        skill_name: 可选，指定 skill 名称（默认从文件名提取）
    """
    if skill_name is None:
        skill_name = Path(filepath).stem

    print(f"\n[方式1] 上传单个文件: {filepath}")
    print("-" * 50)

    with open(filepath, "rb") as f:
        filename = Path(filepath).name
        files = {"file": (filename, f, "text/markdown")}
        response = requests.post(
            f"{BASE_URL}/api/v1/skills",
            files=files,
            headers=HEADERS,
        )

    if response.status_code == 201:
        data = response.json()
        print(f"✅ 创建成功!")
        print(f"   Skill: {data['name']}")
        print(f"   Path: skills/{data['path']}/")
        return data
    else:
        print(f"❌ 失败: {response.status_code} - {response.text}")
        return None


def upload_archive(filepath: str):
    """方式2: 上传压缩包（.zip/.tar.gz/.skill）

    Args:
        filepath: 压缩包路径
    """
    filename = Path(filepath).name
    print(f"\n[方式2] 上传压缩包: {filepath}")
    print("-" * 50)

    with open(filepath, "rb") as f:
        files = {"file": (filename, f, "application/zip")}
        response = requests.post(
            f"{BASE_URL}/api/v1/skills",
            files=files,
            headers=HEADERS,
        )

    if response.status_code == 201:
        data = response.json()
        print(f"✅ 创建成功!")
        print(f"   Skill: {data['name']}")
        print(f"   Files: {response.json().get('extracted_files', [])}")
        return data
    else:
        print(f"❌ 失败: {response.status_code} - {response.text}")
        return None


def update_skill_content(skill_name: str, filepath: str):
    """方式3: 更新已存在的 skill 内容

    Args:
        skill_name: skill 名称
        filepath: 文件路径
    """
    print(f"\n[方式3] 更新 skill 内容: {skill_name}")
    print("-" * 50)

    with open(filepath, "rb") as f:
        files = {"file": (Path(filepath).name, f, "text/markdown")}
        response = requests.put(
            f"{BASE_URL}/api/v1/skills/{skill_name}/upload",
            files=files,
            headers=HEADERS,
        )

    if response.status_code == 201:
        data = response.json()
        print(f"✅ 更新成功!")
        print(f"   文件: {data['extracted_files']}")
        return data
    else:
        print(f"❌ 失败: {response.status_code} - {response.text}")
        return None


def grant_skill(skill_name: str, user_id: int):
    """授权 skill 给用户

    Args:
        skill_name: skill 名称
        user_id: 用户 ID
    """
    print(f"\n[授权] {skill_name} -> user_id:{user_id}")
    print("-" * 50)

    response = requests.post(
        f"{BASE_URL}/api/v1/user_skills?user_id={user_id}&skill_name={skill_name}",
        headers=HEADERS,
    )

    if response.status_code == 201:
        print(f"✅ 授权成功!")
        return True
    else:
        print(f"❌ 失败: {response.status_code} - {response.text}")
        return False


def upload_text_content(skill_name: str, content: str):
    """方式4: 直接通过 JSON 上传文本内容

    Args:
        skill_name: skill 名称
        content: SKILL.md 内容
    """
    print(f"\n[方式4] 直接上传文本内容: {skill_name}")
    print("-" * 50)

    response = requests.put(
        f"{BASE_URL}/api/v1/skills/{skill_name}/content",
        json={"content": content},
        headers=HEADERS,
    )

    if response.status_code == 200:
        data = response.json()
        print(f"✅ 上传成功!")
        print(f"   大小: {data['content_length']} bytes")
        return data
    else:
        print(f"❌ 失败: {response.status_code} - {response.text}")
        return None


def list_skills():
    """列出所有 skills"""
    print("\n" + "=" * 60)
    print("当前所有 Skills:")
    print("-" * 50)
    response = requests.get(f"{BASE_URL}/api/v1/skills", headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        for skill in data.get("skills", []):
            print(f"  - {skill['name']}: {skill['description']}")
    return response.json() if response.status_code == 200 else None


def main():
    """主函数 - 演示各种上传方式"""
    print("=" * 60)
    print("SKILL 上传示例")
    print("=" * 60)

    # 检查示例文件是否存在
    skill_md_file = EXAMPLE_SKILL_PATH / "SKILL.md"
    if not skill_md_file.exists():
        print(f"❌ 示例文件不存在: {skill_md_file}")
        print(f"   请确认 OpenCode skill-auditor 路径正确")
        return

    # 方式1: 上传单个 SKILL.md（推荐）
    print(f"\n使用示例文件: {skill_md_file}")
    result = upload_single_file(str(skill_md_file))

    if result:
        # 授权给用户
        grant_skill(result["name"], user_id=1)

    # 列出所有 skills
    list_skills()

    print("\n" + "=" * 60)
    print("上传测试完成!")
    print("\n提示:")
    print("  1. 方式1: POST /api/v1/skills (单文件自动封装)")
    print("  2. 方式2: POST /api/v1/skills (压缩包自动解压)")
    print("  3. 方式3: PUT /api/v1/skills/{name}/upload (更新已有)")
    print("  4. 方式4: PUT /api/v1/skills/{name}/content (JSON上传)")


if __name__ == "__main__":
    main()
