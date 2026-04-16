#!/usr/bin/env python3
"""Database seeding script for skill-mcp-server.

Creates an admin user with a generated API key and optionally adds sample skills.
Usage:
    python scripts/seed_data.py [--with-samples]

Environment variables:
    DB_HOST: Database host (default: localhost)
    DB_PORT: Database port (default: 3306)
    DB_USER: Database user (default: root)
    DB_PASSWORD: Database password (default: empty)
    DB_NAME: Database name (default: skill_mcp)
    ADMIN_EXTERNAL_ID: Admin external ID (default: admin)
    ADMIN_USERNAME: Admin display name (default: Admin)
    API_KEY_LENGTH: Length of generated API key (default: 32)
"""

import os
import sys
import argparse
import secrets
import pymysql
from datetime import datetime


def generate_api_key(length: int = 32) -> str:
    """Generate a secure random API key."""
    return secrets.token_urlsafe(length)


def get_db_connection():
    """Create a database connection using environment variables."""
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "skill_mcp"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def create_admin_user(conn, api_key_length: int = 32) -> dict:
    """Create an admin user with a generated API key."""
    external_id = os.getenv("ADMIN_EXTERNAL_ID", "admin")
    username = os.getenv("ADMIN_USERNAME", "Admin")
    api_key = generate_api_key(api_key_length)

    with conn.cursor() as cursor:
        # Check if admin already exists
        cursor.execute(
            "SELECT id, external_id, username, api_key, role FROM users WHERE external_id = %s",
            (external_id,),
        )
        existing = cursor.fetchone()

        if existing:
            print(f"Admin user already exists: {existing['external_id']}")
            print(f"Existing API Key: {existing['api_key']}")
            return existing

        # Create new admin user
        cursor.execute(
            """
            INSERT INTO users (external_id, username, api_key, role, created_at)
            VALUES (%s, %s, %s, 'admin', %s)
            """,
            (external_id, username, api_key, datetime.now()),
        )
        conn.commit()

        # Get the created user
        cursor.execute(
            "SELECT id, external_id, username, api_key, role FROM users WHERE external_id = %s",
            (external_id,),
        )
        user = cursor.fetchone()

        print(f"Created admin user: {user['external_id']} ({user['username']})")
        print(f"API Key: {user['api_key']}")
        print("\nIMPORTANT: Save this API key - it will not be shown again!")

        return user


def create_sample_skills(conn, admin_user_id: int) -> list:
    """Create sample skills for demonstration (metadata only).

    Note: Skill content is stored in filesystem (skills/ folder).
    This function only creates database records.
    """
    from pathlib import Path

    # Skills that exist in filesystem
    sample_skills = [
        {
            "name": "code-review",
            "description": "Perform comprehensive code review including style, logic, and best practices.",
            "path": "code-review",
        },
        {
            "name": "data-analysis",
            "description": "Analyze datasets and generate summary statistics and visualizations.",
            "path": "data-analysis",
        },
        {
            "name": "api-design",
            "description": "Design RESTful APIs with proper HTTP methods, status codes, and documentation.",
            "path": "api-design",
        },
        {
            "name": "hello",
            "description": "A simple test skill for development and verification.",
            "path": "hello",
        },
    ]

    created_skills = []

    with conn.cursor() as cursor:
        for skill in sample_skills:
            # Check if skill already exists
            cursor.execute("SELECT id FROM skills WHERE name = %s", (skill["name"],))
            if cursor.fetchone():
                print(f"Skill '{skill['name']}' already exists, skipping...")
                continue

            # Create skill metadata record
            cursor.execute(
                """
                INSERT INTO skills (name, description, path, version, created_at, updated_at)
                VALUES (%s, %s, %s, '1.0', %s, %s)
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

            # Grant admin user access to this skill
            cursor.execute(
                """
                INSERT INTO user_skills (user_id, skill_id, granted_at)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE granted_at = granted_at
                """,
                (admin_user_id, skill_id, datetime.now()),
            )
            conn.commit()

            created_skills.append(skill["name"])
            print(f"Created skill record: {skill['name']} -> {skill['path']}/")

    return created_skills


def main():
    parser = argparse.ArgumentParser(
        description="Seed the skill-mcp-server database with initial data."
    )
    parser.add_argument(
        "--with-samples",
        action="store_true",
        help="Also create sample skills (optional)",
    )
    args = parser.parse_args()

    api_key_length = int(os.getenv("API_KEY_LENGTH", "32"))

    try:
        print("Connecting to database...")
        conn = get_db_connection()
        print("Connected successfully!\n")

        print("=" * 50)
        print("Creating admin user...")
        print("=" * 50)
        admin = create_admin_user(conn, api_key_length)

        if args.with_samples:
            print("\n" + "=" * 50)
            print("Creating sample skills...")
            print("=" * 50)
            created = create_sample_skills(conn, admin["id"])
            if created:
                print(
                    f"\nCreated {len(created)} sample skill(s) and granted access to admin."
                )
            else:
                print("\nNo new skills created (all already exist).")

        print("\n" + "=" * 50)
        print("Seeding complete!")
        print("=" * 50)

    except pymysql.MySQLError as e:
        print(f"Database error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if "conn" in locals():
            conn.close()


if __name__ == "__main__":
    main()
