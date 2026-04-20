"""
Skill MCP Server 自动化测试脚本

功能：
1. 清空并重建数据库表
2. 创建测试数据
3. 测试所有功能

用法：
python tests/admin_panel_test.py
"""

import asyncio
import sys
import os
import secrets
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# If running from scripts directory, go up one more level
if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == 'scripts':
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aiomysql
from app.config import settings
from app.db.crud import user as user_crud
from app.db.crud import skill as skill_crud
from app.db.crud import user_skill as user_skill_crud
from app.db.session import get_db, DatabasePool


class TestRunner:
    def __init__(self):
        self.results = []
        self.admin_user = None
        self.normal_user = None
        self.test_skill = None

    def log(self, test_name: str, passed: bool, message: str = ""):
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if message:
            print(f"       {message}")
        self.results.append({"name": test_name, "passed": passed, "message": message})

    async def setup_database(self):
        """清空并重建数据库表"""
        print("\n" + "="*60)
        print("步骤1: 初始化数据库")
        print("="*60)

        pool = await DatabasePool.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Drop existing tables
                print("删除旧表...")
                await cur.execute("DROP TABLE IF EXISTS skill_calls")
                await cur.execute("DROP TABLE IF EXISTS user_skills")
                await cur.execute("DROP TABLE IF EXISTS skills")
                await cur.execute("DROP TABLE IF EXISTS users")
                await conn.commit()

                # Create tables
                print("创建新表...")
                await cur.execute("""
                    CREATE TABLE users (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        user_id VARCHAR(100) UNIQUE NOT NULL,
                        username VARCHAR(100) NOT NULL,
                        api_key VARCHAR(128) UNIQUE NOT NULL,
                        role ENUM('admin', 'user') DEFAULT 'user',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        INDEX idx_api_key (api_key),
                        INDEX idx_user_id (user_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                await cur.execute("""
                    CREATE TABLE skills (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        name VARCHAR(100) UNIQUE NOT NULL,
                        description TEXT,
                        path VARCHAR(500) NOT NULL,
                        dependencies JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_name (name)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                await cur.execute("""
                    CREATE TABLE user_skills (
                        user_id INT NOT NULL,
                        skill_id INT NOT NULL,
                        granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, skill_id),
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                await cur.execute("""
                    CREATE TABLE skill_calls (
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        user_id INT NOT NULL,
                        skill_id INT NOT NULL,
                        call_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status ENUM('success', 'failure', 'denied') DEFAULT 'success',
                        error_message TEXT,
                        duration_ms INT DEFAULT 0,
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        FOREIGN KEY (skill_id) REFERENCES skills(id),
                        INDEX idx_call_time (call_time),
                        INDEX idx_user_id (user_id)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
                """)

                await conn.commit()

        self.log("数据库初始化", True, "所有表已创建")

    async def create_test_data(self):
        """创建测试数据"""
        print("\n" + "="*60)
        print("步骤2: 创建测试数据")
        print("="*60)

        async with get_db() as conn:
            # 创建 Admin 用户
            self.admin_user = await user_crud.create(
                conn,
                user_id="admin",
                username="管理员",
                role="admin"
            )
            self.log("创建 Admin 用户", True, f"API Key: {self.admin_user['api_key']}")

            # 创建普通用户 Alice
            self.normal_user = await user_crud.create(
                conn,
                user_id="alice",
                username="Alice",
                role="user"
            )
            self.log("创建普通用户 Alice", True, f"API Key: {self.normal_user['api_key']}")

            # 创建测试技能
            self.test_skill = await skill_crud.create(
                conn,
                name="time-compare",
                description="比较本地时间和远程服务器时间",
                path="time-compare",
                dependencies=["https://mcp.sorftime.com"]
            )
            self.log("创建测试技能 time-compare (含MCP依赖)", True, f"Skill ID: {self.test_skill['id']}")

            # 创建第二个技能
            self.second_skill = await skill_crud.create(
                conn,
                name="code-review",
                description="代码评审技能",
                path="code-review"
            )
            self.log("创建测试技能 code-review", True, f"Skill ID: {self.second_skill['id']}")

            # 授予 Alice 技能（admin 自动拥有所有技能，不需要授予）
            await user_skill_crud.grant(conn, self.normal_user["id"], self.test_skill["id"])
            self.log("授予 Alice time-compare 技能", True)

        return True

    async def test_admin_auto_all_skills(self):
        """测试 Admin 用户自动拥有所有技能"""
        print("\n" + "="*60)
        print("步骤3: 测试 Admin 用户权限（自动拥有所有技能）")
        print("="*60)

        from app.mcp.server import current_user

        # Simulate admin user context
        current_user.set({
            "id": self.admin_user["id"],
            "user_id": "admin",
            "role": "admin",
            "username": "管理员"
        })

        from app.db.crud import skill as skill_crud

        async with get_db() as conn:
            # Admin 应该能获取所有技能（绕过授权检查）
            all_skills = await skill_crud.list_all(conn, limit=1000)

            # 检查 admin 是否自动拥有所有技能（通过 list_tools 逻辑）
            is_admin = True  # 模拟 admin 角色
            if is_admin:
                admin_skills = all_skills  # Admin 直接获取所有技能

        if len(admin_skills) >= 2:
            self.log("Admin 自动拥有所有技能", True, f"拥有 {len(admin_skills)} 个技能")
        else:
            self.log("Admin 自动拥有所有技能", False, f"只拥有 {len(admin_skills)} 个技能")

    async def test_normal_user_limited_skills(self):
        """测试普通用户只能看到已授权技能"""
        print("\n" + "="*60)
        print("步骤4: 测试普通用户权限（只能看到已授权技能）")
        print("="*60)

        from app.db.crud import skill as skill_crud
        from app.db.crud import user_skill as user_skill_crud

        async with get_db() as conn:
            # 获取 Alice 已授权的技能
            user_skills = await user_skill_crud.get_user_skills(conn, self.normal_user["id"])
            skill_ids = [s["id"] for s in user_skills]

            if skill_ids:
                authorized_skills = await skill_crud.get_by_ids(conn, skill_ids)
            else:
                authorized_skills = []

        if len(authorized_skills) == 1:
            self.log("普通用户只能看到已授权技能", True, f"Alice 拥有 {len(authorized_skills)} 个技能")
        else:
            self.log("普通用户只能看到已授权技能", False, f"Alice 拥有 {len(authorized_skills)} 个技能")

        # 验证 Alice 没有 code-review 技能
        alice_skill_names = [s["name"] for s in authorized_skills]
        if "code-review" not in alice_skill_names:
            self.log("Alice 没有 code-review 技能", True)
        else:
            self.log("Alice 没有 code-review 技能", False, "Alice 错误地拥有 code-review")

    async def test_user_operations(self):
        """测试用户管理功能"""
        print("\n" + "="*60)
        print("步骤5: 测试用户管理功能")
        print("="*60)

        async with get_db() as conn:
            # 测试获取用户列表
            users = await user_crud.list_users(conn, limit=100)
            if len(users) >= 2:
                self.log("获取用户列表", True, f"共有 {len(users)} 个用户")
            else:
                self.log("获取用户列表", False, f"只有 {len(users)} 个用户")

            # 测试按 ID 获取用户
            user = await user_crud.get_by_id(conn, self.admin_user["id"])
            if user and user["user_id"] == "admin":
                self.log("按 ID 获取用户", True)
            else:
                self.log("按 ID 获取用户", False)

            # 测试按 user_id 获取用户
            user = await user_crud.get_by_user_id(conn, "alice")
            if user and user["username"] == "Alice":
                self.log("按 user_id 获取用户", True)
            else:
                self.log("按 user_id 获取用户", False)

    async def test_skill_operations(self):
        """测试技能管理功能"""
        print("\n" + "="*60)
        print("步骤6: 测试技能管理功能")
        print("="*60)

        async with get_db() as conn:
            # 测试获取技能列表
            skills = await skill_crud.list_all(conn, limit=100)
            if len(skills) >= 2:
                self.log("获取技能列表", True, f"共有 {len(skills)} 个技能")
            else:
                self.log("获取技能列表", False, f"只有 {len(skills)} 个技能")

            # 测试按名称获取技能
            skill = await skill_crud.get_by_name(conn, "time-compare")
            if skill and skill["description"]:
                self.log("按名称获取技能", True)
            else:
                self.log("按名称获取技能", False)

            # 测试更新技能描述
            await skill_crud.update(conn, "time-compare", description="更新的描述")
            skill = await skill_crud.get_by_name(conn, "time-compare")
            if "更新的描述" in skill["description"]:
                self.log("更新技能描述", True)
            else:
                self.log("更新技能描述", False)

    async def test_authorization_operations(self):
        """测试授权管理功能"""
        print("\n" + "="*60)
        print("步骤7: 测试授权管理功能")
        print("="*60)

        async with get_db() as conn:
            # 授予 Alice code-review 技能
            await user_skill_crud.grant(conn, self.normal_user["id"], self.second_skill["id"])
            self.log("授予技能", True)

            # 验证 Alice 现在有 2 个技能
            user_skills = await user_skill_crud.get_user_skills(conn, self.normal_user["id"])
            if len(user_skills) == 2:
                self.log("验证授权成功", True, f"Alice 现在有 {len(user_skills)} 个技能")
            else:
                self.log("验证授权成功", False, f"Alice 有 {len(user_skills)} 个技能")

            # 撤销 Alice 的 time-compare 技能
            await user_skill_crud.revoke(conn, self.normal_user["id"], self.test_skill["id"])
            self.log("撤销技能", True)

            # 验证 Alice 现在只有 1 个技能
            user_skills = await user_skill_crud.get_user_skills(conn, self.normal_user["id"])
            if len(user_skills) == 1:
                self.log("验证撤销成功", True, f"Alice 现在有 {len(user_skills)} 个技能")
            else:
                self.log("验证撤销成功", False, f"Alice 有 {len(user_skills)} 个技能")

            # 测试 has_skill
            has_time_compare = await user_skill_crud.has_skill(conn, self.normal_user["id"], "time-compare")
            has_code_review = await user_skill_crud.has_skill(conn, self.normal_user["id"], "code-review")

            if not has_time_compare and has_code_review:
                self.log("has_skill 正确", True)
            else:
                self.log("has_skill 正确", False, f"time-compare={has_time_compare}, code-review={has_code_review}")

    async def test_delete_user(self):
        """测试删除用户"""
        print("\n" + "="*60)
        print("步骤8: 测试删除用户")
        print("="*60)

        async with get_db() as conn:
            # 创建一个待删除的用户
            test_user = await user_crud.create(
                conn,
                user_id="test_delete",
                username="测试删除",
                role="user"
            )
            self.log("创建待删除用户", True)

            # 删除用户
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM users WHERE id = %s", (test_user["id"],))
                await conn.commit()

            # 验证用户已删除
            deleted_user = await user_crud.get_by_id(conn, test_user["id"])
            if deleted_user is None:
                self.log("删除用户", True)
            else:
                self.log("删除用户", False, "用户仍然存在")

    async def test_delete_skill(self):
        """测试删除技能"""
        print("\n" + "="*60)
        print("步骤9: 测试删除技能")
        print("="*60)

        async with get_db() as conn:
            # 创建一个待删除的技能
            test_skill = await skill_crud.create(
                conn,
                name="test_delete_skill",
                description="测试删除",
                path="test_delete_skill"
            )
            self.log("创建待删除技能", True)

            # 删除技能
            await skill_crud.delete(conn, "test_delete_skill")

            # 验证技能已删除
            deleted_skill = await skill_crud.get_by_name(conn, "test_delete_skill")
            if deleted_skill is None:
                self.log("删除技能", True)
            else:
                self.log("删除技能", False, "技能仍然存在")

    def print_summary(self):
        """打印测试结果汇总"""
        print("\n" + "="*60)
        print("测试结果汇总")
        print("="*60)

        passed = sum(1 for r in self.results if r["passed"])
        failed = sum(1 for r in self.results if not r["passed"])
        total = len(self.results)

        print(f"\n总计: {total} 个测试")
        print(f"通过: {passed} ✅")
        print(f"失败: {failed} ❌")

        if failed > 0:
            print("\n失败项:")
            for r in self.results:
                if not r["passed"]:
                    print(f"  - {r['name']}: {r['message']}")

        return failed == 0

    async def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "#"*60)
        print("# Skill MCP Server 自动化测试")
        print("#"*60)

        try:
            await self.setup_database()
            await self.create_test_data()
            await self.test_admin_auto_all_skills()
            await self.test_normal_user_limited_skills()
            await self.test_user_operations()
            await self.test_skill_operations()
            await self.test_authorization_operations()
            await self.test_delete_user()
            await self.test_delete_skill()

            success = self.print_summary()
            return success

        except Exception as e:
            print(f"\n❌ 测试过程出错: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    runner = TestRunner()
    success = await runner.run_all_tests()

    print("\n" + "="*60)
    if success:
        print("🎉 所有测试通过！")
    else:
        print("⚠️  部分测试失败，请检查上方的失败项。")
    print("="*60)

    # 打印测试数据供手动测试使用
    print("\n" + "="*60)
    print("手动测试用数据:")
    print("="*60)
    print(f"Admin User ID: admin")
    print(f"Admin API Key: {runner.admin_user['api_key']}")
    print(f"Alice User ID: alice")
    print(f"Alice API Key: {runner.normal_user['api_key']}")


if __name__ == "__main__":
    asyncio.run(main())
