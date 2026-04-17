import pymysql
import os

conn = pymysql.connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", 3306)),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "skill_mcp"),
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
)

with conn.cursor() as cursor:
    cursor.execute("ALTER TABLE skills ADD COLUMN dependencies JSON AFTER content_json")
    cursor.execute("UPDATE skills SET dependencies = '[]' WHERE dependencies IS NULL")
    conn.commit()
    print("Migration complete!")

conn.close()
