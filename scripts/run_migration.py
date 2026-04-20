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
    # Add status column if it doesn't exist
    cursor.execute("""
        SELECT COUNT(*) as cnt
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = 'skills' AND column_name = 'status'
    """, (os.getenv("DB_NAME", "skill_mcp"),))
    result = cursor.fetchone()
    if result['cnt'] == 0:
        cursor.execute("ALTER TABLE skills ADD COLUMN status ENUM('draft', 'active') DEFAULT 'draft' AFTER dependencies")
        cursor.execute("UPDATE skills SET status = 'active' WHERE status IS NULL")
        print("Added 'status' column to skills table")
    else:
        print("'status' column already exists, skipping")

    conn.commit()
    print("Migration complete!")

conn.close()