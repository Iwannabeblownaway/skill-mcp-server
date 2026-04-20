#!/usr/bin/env python3
"""
SKILL 上传脚本 - 参数化可复用

用法:
    python upload_skill.py -k <API_KEY> -s <skill_path> [-n <skill_name>] [-d <description>]
    python upload_skill.py -k <API_KEY> -z <zip_file> [-d <description>]
    python upload_skill.py -k <API_KEY> -f <file> --update <skill_name>

使用命令示例:
    # 上传单个 SKILL.md 文件
    python upload_skill.py -k YOUR_API_KEY -s ./my-skill/SKILL.md -n my-skill

    # 上传整个 skill 文件夹（自动打包为 zip）
    python upload_skill.py -k YOUR_API_KEY -s ./my-skill/ -n my-skill -d "我的 skill 描述"

    # 上传已有 zip 压缩包
    python upload_skill.py -k YOUR_API_KEY -z my-skill.zip

    # 更新已存在的 skill
    python upload_skill.py -k YOUR_API_KEY -f ./new-SKILL.md --update my-skill
"""

import argparse
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Optional
import requests


def parse_args():
    parser = argparse.ArgumentParser(
        description="上传 SKILL 到 MCP 服务器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s -k API_KEY -s ./skill/SKILL.md -n my-skill
  %(prog)s -k API_KEY -s ./my-skill/ -n my-skill -d "我的 skill 描述"
  %(prog)s -k API_KEY -z skill.zip
  %(prog)s -k API_KEY -f ./new.md --update existing-skill
        """,
    )
    parser.add_argument("-k", "--api-key", required=True, help="Admin API Key")
    parser.add_argument(
        "-u", "--url", default="http://localhost:8000", help="MCP 服务器 URL"
    )
    parser.add_argument("-s", "--source", help="Skill 源路径（文件或文件夹）")
    parser.add_argument("-n", "--name", help="Skill 名称（可选，从路径推断）")
    parser.add_argument("-d", "--description", default="", help="Skill 描述")
    parser.add_argument("-z", "--zip", help="直接上传 zip 压缩包")
    parser.add_argument("-f", "--file", help="上传单个文件")
    parser.add_argument("--update", help="更新已存在的 skill 名称")

    return parser.parse_args()


def get_skill_name(path: Path, name: Optional[str] = None) -> str:
    """从路径推断 skill 名称"""
    if name:
        return name
    if path.is_file():
        stem = path.stem
        if stem.upper() == "SKILL":
            return path.parent.name
        return stem
    return path.name


def create_zip_from_folder(folder_path: Path) -> str:
    """将文件夹打包为 zip 文件"""
    zip_path = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    zip_path.close()

    with zipfile.ZipFile(zip_path.name, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in folder_path.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(folder_path)
                zf.write(file_path, arcname)

    return zip_path.name


def upload_single_file(
    base_url: str, headers: dict, filepath: str, skill_name: str, description: str = ""
):
    """上传单个文件"""
    print(f"\n[上传] 单文件: {filepath}")
    print(f"       Skill 名称: {skill_name}")

    # 创建 skill 元数据
    response = requests.post(
        f"{base_url}/api/v1/skills/json",
        json={"name": skill_name, "description": description},
        headers=headers,
    )

    if response.status_code == 409:
        print(f"⚠️ Skill 已存在，跳过创建")
    elif response.status_code not in (200, 201):
        print(f"❌ 创建失败: {response.status_code} - {response.text}")
        return None
    else:
        print(f"✅ 创建成功: {skill_name}")

    # 上传内容
    with open(filepath, "rb") as f:
        content = f.read()

    content_response = requests.put(
        f"{base_url}/api/v1/skills/{skill_name}/content",
        json={"content": content.decode("utf-8")},
        headers=headers,
    )

    if content_response.status_code == 200:
        print(f"✅ 内容上传成功")
        return {"name": skill_name}
    else:
        print(
            f"❌ 内容上传失败: {content_response.status_code} - {content_response.text}"
        )
        return None


def upload_archive(base_url: str, headers: dict, filepath: str):
    """上传压缩包"""
    filename = Path(filepath).name
    print(f"\n[上传] 压缩包: {filepath}")

    with open(filepath, "rb") as f:
        files = {"file": (filename, f, "application/zip")}
        response = requests.post(
            f"{base_url}/api/v1/skills",
            files=files,
            headers=headers,
        )

    if response.status_code == 201:
        data = response.json()
        print(f"✅ 上传成功!")
        print(f"   Skill: {data['name']}")
        print(f"   文件: {data.get('extracted_files', [])}")
        return data
    elif response.status_code == 409:
        print(f"⚠️ Skill 已存在，请使用 --update 更新")
        return None
    else:
        print(f"❌ 失败: {response.status_code} - {response.text}")
        return None


def update_skill(base_url: str, headers: dict, skill_name: str, filepath: str):
    """更新已存在的 skill"""
    print(f"\n[更新] {skill_name} <- {filepath}")

    with open(filepath, "rb") as f:
        files = {"file": (Path(filepath).name, f, "text/markdown")}
        response = requests.put(
            f"{base_url}/api/v1/skills/{skill_name}/upload",
            files=files,
            headers=headers,
        )

    if response.status_code in (200, 201):
        data = response.json()
        print(f"✅ 更新成功!")
        print(f"   文件: {data.get('extracted_files', [])}")
        return data
    else:
        print(f"❌ 失败: {response.status_code} - {response.text}")
        return None


def main():
    args = parse_args()

    headers = {"X-API-Key": args.api_key}

    # 优先处理更新
    if args.update:
        if not args.file:
            print("❌ 更新模式需要指定 -f/--file 参数")
            sys.exit(1)
        result = update_skill(args.url, headers, args.update, args.file)
        sys.exit(0 if result else 1)

    # 处理 zip 上传
    if args.zip:
        result = upload_archive(args.url, headers, args.zip)
        sys.exit(0 if result else 1)

    # 处理文件/文件夹上传
    if args.source:
        source_path = Path(args.source)

        if not source_path.exists():
            print(f"❌ 路径不存在: {source_path}")
            sys.exit(1)

        skill_name = get_skill_name(source_path, args.name)

        if source_path.is_file():
            # 单文件上传
            result = upload_single_file(
                args.url, headers, str(source_path), skill_name, args.description
            )
        else:
            # 文件夹上传 -> 打包为 zip
            print(f"\n[打包] 将文件夹打包为 zip: {source_path}")
            zip_path = create_zip_from_folder(source_path)
            result = upload_archive(args.url, headers, zip_path)
            os.unlink(zip_path)  # 清理临时 zip

        sys.exit(0 if result else 1)

    # 处理单文件上传（非更新模式）
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ 文件不存在: {file_path}")
            sys.exit(1)

        skill_name = get_skill_name(file_path, args.name)
        result = upload_single_file(
            args.url, headers, str(file_path), skill_name, args.description
        )
        sys.exit(0 if result else 1)

    print("❌ 请指定 -s/--source, -z/--zip, 或 -f/--file 参数")
    sys.exit(1)


if __name__ == "__main__":
    main()
