import asyncio
from app.db.session import get_db
from app.db.crud import user as user_crud


async def get_first_user_api_key():
    async with get_db() as conn:
        users = await user_crud.list_users(conn, limit=1)
        if users:
            print(f"User: {users[0]['username']}, API Key: {users[0]['api_key']}")
            return users[0]["api_key"]
        else:
            print("No users found")
            return None


key = asyncio.run(get_first_user_api_key())
print(f"\nUse this key in OpenCode config:")
print(f"X-API-Key: {key}")
