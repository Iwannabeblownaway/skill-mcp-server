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
API_KEY = "2rotINY-6BEbIOpHKMaQNrmVe324uJ56W0mBWTLYRFI"  # Admin API Key

HEADERS = {"X-API-Key": API_KEY}

# 示例 Skill 路径（OpenCode 内置的 skill-auditor）
EXAMPLE_SKILL_PATH = Path(
    r"C:\Users\Administrator\.config\opencode\skills\skill-auditor"
)


def upload_single_file(filepath: str, skill_name: str = None):
    """方式1: 上传单个文件（自动封装到文件夹）

    Args:
        filepath: 文件路径
        skill_name: 指定 skill 名称（必须）
    """
    if skill_name is None:
        # 从文件路径提取
        skill_name = Path(filepath).stem
        if skill_name.upper() == "SKILL":
            skill_name = Path(filepath).parent.name

    filename = Path(filepath).name

    print(f"\n[方式1] 上传单个文件: {filepath}")
    print(f"       Skill 名称: {skill_name}")
    print("-" * 50)

    # 先创建 skill 元数据
    response = requests.post(
        f"{BASE_URL}/api/v1/skills/json",
        json={
            "name": skill_name,
            "description": f"Skill from {filename}",
        },
        headers=HEADERS,
    )

    if response.status_code == 409:
        print(f"⚠️ Skill 已存在，跳过创建")
        skill = {"name": skill_name}
    elif response.status_code != 201:
        print(f"❌ 创建失败: {response.status_code} - {response.text}")
        return None
    else:
        skill = response.json()
        print(f"✅ 创建成功: {skill['name']}")

    # 上传内容
    with open(filepath, "rb") as f:
        content = f.read()

    content_response = requests.put(
        f"{BASE_URL}/api/v1/skills/{skill_name}/content",
        json={"content": content.decode("utf-8")},
        headers=HEADERS,
    )

    if content_response.status_code == 200:
        print(f"✅ 内容上传成功")
        return skill
    else:
        print(
            f"❌ 内容上传失败: {content_response.status_code} - {content_response.text}"
        )
        return skill


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

    # 先获取 skill_id
    resp = requests.get(f"{BASE_URL}/api/v1/skills", headers=HEADERS)
    if resp.status_code != 200:
        print(f"❌ 获取 skills 列表失败")
        return False

    skill_id = None
    for s in resp.json().get("skills", []):
        if s["name"] == skill_name:
            skill_id = s.get("id")
            break

    if not skill_id:
        print(f"❌ Skill '{skill_name}' not found")
        return False

    # 授权
    response = requests.post(
        f"{BASE_URL}/api/v1/user_skills",
        json={"user_id": user_id, "skill_id": skill_id},
        headers=HEADERS,
    )

    if response.status_code == 201:
        print(f"✅ 授权成功!")
        return True
    else:
        print(f"❌ 授权失败: {response.status_code} - {response.text}")
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

    # 方式1: 上传单个 SKILL.md（使用 skill_name 参数指定名称）
    print(f"\n使用示例文件: {skill_md_file}")
    result = upload_single_file(str(skill_md_file), skill_name="skill-auditor")

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
