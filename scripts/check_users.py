import asyncio
import aiomysql

async def check_users():
    pool = await aiomysql.create_pool(host='localhost', port=3306, user='root', password='', db='skill_mcp', charset='utf8mb4')
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            print("=== All skills with status ===")
            await cur.execute("SELECT id, name, status FROM skills")
            skills = await cur.fetchall()
            for s in skills:
                print(f"- ID: {s['id']}, name: {s['name']}, status: {s['status']}")

            print("\n=== Alice's skills with status ===")
            await cur.execute("""
                SELECT s.id, s.name, s.description, s.status
                FROM skills s
                JOIN user_skills us ON s.id = us.skill_id
                WHERE us.user_id = 2
            """)
            skills = await cur.fetchall()
            print(f"Found {len(skills)} skills")
            for s in skills:
                print(f"- ID: {s['id']}, name: {s['name']}, status: {s['status']}, description: {s['description']}")

    pool.close()
    await pool.wait_closed()

asyncio.run(check_users())
