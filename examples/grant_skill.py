#!/usr/bin/env python3
"""
SKILL 授权脚本 - 参数化可复用

使用命令示例:
    # 授权单个 skill 给单个用户
    python grant_skill.py -k API_KEY -s my-skill -u 1

    # 授权多个 skills 给单个用户
    python grant_skill.py -k API_KEY -s "skill1,skill2" -u 1,2

    # 授权单个 skill 给多个用户
    python grant_skill.py -k API_KEY -s my-skill -u "1,2,3"

    # 撤销授权
    python grant_skill.py -k API_KEY -s my-skill -u 1 --revoke

    # 列出当前所有 skills
    python grant_skill.py -k API_KEY -l
"""

import argparse
import sys
import requests


def parse_args():
    parser = argparse.ArgumentParser(
        description="管理 SKILL 授权",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s -k API_KEY -s my-skill -u 1
  %(prog)s -k API_KEY -s "skill1,skill2" -u 1,2
  %(prog)s -k API_KEY -s my-skill -u 1 --revoke
  %(prog)s -k API_KEY -l
        """,
    )
    parser.add_argument("-k", "--api-key", required=True, help="Admin API Key")
    parser.add_argument(
        "-b", "--base-url", default="http://localhost:8000", help="MCP 服务器 URL"
    )
    parser.add_argument("-s", "--skill", help="Skill 名称（多个用逗号分隔）")
    parser.add_argument("-u", "--user", help="用户 ID（多个用逗号分隔）")
    parser.add_argument("-l", "--list", action="store_true", help="列出所有 skills")
    parser.add_argument("--revoke", action="store_true", help="撤销授权（默认是授予）")

    return parser.parse_args()


def get_skills(base_url: str, headers: dict) -> list:
    """获取所有 skills"""
    response = requests.get(f"{base_url}/api/v1/skills", headers=headers)
    if response.status_code == 200:
        return response.json().get("skills", [])
    print(f"❌ 获取 skills 失败: {response.status_code}")
    return []


def grant_skill(base_url: str, headers: dict, skill_id: int, user_id: int) -> bool:
    """授予 skill 授权"""
    response = requests.post(
        f"{base_url}/api/v1/user_skills",
        json={"user_id": user_id, "skill_id": skill_id},
        headers=headers,
    )

    if response.status_code == 201:
        return True
    elif response.status_code == 409:
        print(f"⚠️ 已存在授权")
        return True
    else:
        print(f"❌ 授权失败: {response.status_code} - {response.text}")
        return False


def revoke_skill(base_url: str, headers: dict, skill_id: int, user_id: int) -> bool:
    """撤销 skill 授权"""
    response = requests.delete(
        f"{base_url}/api/v1/user_skills",
        json={"user_id": user_id, "skill_id": skill_id},
        headers=headers,
    )

    if response.status_code in (200, 204):
        return True
    else:
        print(f"❌ 撤销失败: {response.status_code} - {response.text}")
        return False


def main():
    args = parse_args()
    headers = {"X-API-Key": args.api_key}
    base_url = args.base_url

    # 列出所有 skills
    if args.list:
        skills = get_skills(base_url, headers)
        print(f"\n{'=' * 50}")
        print(f"当前所有 Skills ({len(skills)} 个):")
        print(f"{'=' * 50}")
        for s in skills:
            print(f"  - {s['name']}: {s.get('description', '')}")
        return

    # 参数校验
    if not args.skill or not args.user:
        print("❌ 需要指定 -s/--skill 和 -u/--user 参数")
        sys.exit(1)

    # 获取 skill ID
    skills = get_skills(base_url, headers)
    skill_map = {s["name"]: s["id"] for s in skills}

    skill_names = [s.strip() for s in args.skill.split(",")]
    user_ids = [int(u.strip()) for u in args.user.split(",")]

    # 执行授权/撤销
    action = "撤销" if args.revoke else "授权"
    success_count = 0
    fail_count = 0

    for skill_name in skill_names:
        if skill_name not in skill_map:
            print(f"❌ Skill '{skill_name}' 不存在")
            fail_count += 1
            continue

        skill_id = skill_map[skill_name]

        for user_id in user_ids:
            print(f"\n[{action}] {skill_name} -> user_id:{user_id}")

            if args.revoke:
                ok = revoke_skill(base_url, headers, skill_id, user_id)
            else:
                ok = grant_skill(base_url, headers, skill_id, user_id)

            if ok:
                print(f"✅ {action}成功")
                success_count += 1
            else:
                fail_count += 1

    print(f"\n{'=' * 50}")
    print(f"完成: 成功 {success_count}, 失败 {fail_count}")
    sys.exit(0 if fail_count == 0 else 1)


if __name__ == "__main__":
    main()
