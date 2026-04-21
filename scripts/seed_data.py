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

import argparse
import json
import os
import re
import secrets
from typing import Any
import sys
from datetime import datetime
from pathlib import Path

import pymysql


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


def generate_api_key(length: int = 32) -> str:
    """Generate a secure random API key."""
    return secrets.token_urlsafe(length)


def create_admin_user(conn, api_key_length: int = 32) -> dict:
    """Create an admin user with a generated API key."""
    user_id = os.getenv("ADMIN_USER_ID", "admin")
    username = os.getenv("ADMIN_USERNAME", "Admin")
    api_key = generate_api_key(api_key_length)

    with conn.cursor() as cursor:
        # Check if admin already exists
        cursor.execute(
            "SELECT id, user_id, username, api_key, role FROM users WHERE user_id = %s",
            (user_id,),
        )
        existing = cursor.fetchone()

        if existing:
            print(f"Admin user already exists: {existing['user_id']}")
            print(f"Existing API Key: {existing['api_key']}")
            return existing

        # Create new admin user
        cursor.execute(
            """
            INSERT INTO users (user_id, username, api_key, role, created_at)
            VALUES (%s, %s, %s, 'admin', %s)
            """,
            (user_id, username, api_key, datetime.now()),
        )
        conn.commit()

        # Get the created user
        cursor.execute(
            "SELECT id, user_id, username, api_key, role FROM users WHERE user_id = %s",
            (user_id,),
        )
        user = cursor.fetchone()

        print(f"Created admin user: {user['user_id']} ({user['username']})")
        print(f"API Key: {user['api_key']}")
        print("\nIMPORTANT: Save this API key - it will not be shown again!")

        return user


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Full file content with optional ---fenced frontmatter

    Returns:
        Tuple of (frontmatter_dict, body_content)
    """
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not fm_match:
        return {}, content

    fm_text = fm_match.group(1)
    body = content[fm_match.end():]
    result = {}

    # Parse simple key: value pairs at the top level
    for line in fm_text.split("\n"):
        line = line.rstrip()
        # Top-level key: value
        m = re.match(r"^(\w+):\s*(.*)$", line)
        if m:
            key, value = m.group(1), m.group(2).strip()
            if not value or value == "|":
                # Empty value - might be a nested block, init as dict
                result[key] = {}
            elif value.startswith('"') and value.endswith('"'):
                result[key] = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                result[key] = value[1:-1]
            elif value == "true":
                result[key] = True
            elif value == "false":
                result[key] = False
            elif re.match(r"^\d+$", value):
                result[key] = int(value)
            else:
                result[key] = value

    # Parse mcp_config nested structure if present
    if "mcp_config" in fm_text:
        mc = {}
        # Find mcp_config block
        mc_match = re.search(r"mcp_config:\s*\n", fm_text)
        if mc_match:
            mc_start = mc_match.end()
            # Extract lines belonging to mcp_config (by indentation)
            mc_lines = []
            for line in fm_text[mc_start:].split("\n"):
                if line.startswith("  ") or line.startswith("\t"):
                    mc_lines.append(line)
                elif line.strip() == "":
                    mc_lines.append(line)
                else:
                    break
            # Parse indented server entries
            current_server = None
            for mc_line in mc_lines:
                stripped = mc_line.strip()
                if not stripped:
                    continue
                # Server name at 2-space indent
                server_m = re.match(r"^(\w+):\s*$", stripped)
                if server_m and mc_line.startswith("  ") and not mc_line.startswith("    "):
                    current_server = server_m.group(1)
                    mc[current_server] = {}
                    continue
                # Key: value under server (4-space indent)
                if current_server and mc_line.startswith("    "):
                    kv_m = re.match(r"^(\w+):\s*(.*)$", stripped)
                    if kv_m:
                        mc[current_server][kv_m.group(1)] = kv_m.group(2).strip()
            if mc:
                result["mcp_config"] = mc

    return result, body


def extract_urls_from_mcp_config(mcp_config: dict) -> list[str]:
    """Extract base URLs from MCP config, removing all query parameters.

    Handles flexible formats:
    - Simple URL strings: {"server-name": "https://..."}
    - Object with url field: {"server-name": {"url": "https://..."}}
    - Nested mcpServers wrapper: {"mcpServers": {"server": {...}}}
    - Various url field names: url, baseUrl, remote_url, endpoint, server_url, uri
    """
    URL_FIELD_NAMES = ("url", "baseUrl", "remote_url", "endpoint", "server_url", "uri")

    def _extract_from_value(value: Any) -> None:
        if isinstance(value, str):
            _add_url(value)
        elif isinstance(value, dict):
            url = None
            for field in URL_FIELD_NAMES:
                if field in value:
                    url = value[field]
                    break
            if url and isinstance(url, str):
                _add_url(url)
            elif not url:
                for v in value.values():
                    _extract_from_value(v)
        elif isinstance(value, list):
            for item in value:
                _extract_from_value(item)

    def _add_url(url: str) -> None:
        if not url or not isinstance(url, str):
            return
        url = url.strip().rstrip("/")
        if not url.startswith(("http://", "https://", "//")):
            return
        if url.startswith("//"):
            url = "https:" + url
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if parsed.netloc:
                base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
                if base_url not in urls:
                    urls.append(base_url)
        except (ValueError, AttributeError):
            pass

    urls: list[str] = []

    if "mcpServers" in mcp_config:
        mcp_config = mcp_config["mcpServers"]

    for key, value in mcp_config.items():
        if key in ("mcpServers", "servers"):
            if isinstance(value, dict):
                for v in value.values():
                    _extract_from_value(v)
            elif isinstance(value, list):
                for item in value:
                    _extract_from_value(item)
        else:
            _extract_from_value(value)

    return urls


def load_skill_frontmatter(skill_path: str) -> dict:
    """Load and parse frontmatter from skill's SKILL.md.

    Args:
        skill_path: Relative path to skill folder (e.g., "time-compare")

    Returns:
        Dict with parsed frontmatter fields including optional mcp_config
    """
    # Skills directory is two levels up from this script
    skills_dir = Path(__file__).parent.parent / "skills"
    skill_md = skills_dir / skill_path / "SKILL.md"

    if not skill_md.exists():
        return {}

    content = skill_md.read_text(encoding="utf-8")
    fm, _ = parse_frontmatter(content)
    return fm


def create_sample_skills(conn, admin_user_id: int) -> list:
    """Create sample skills for demonstration.

    Reads skill metadata from filesystem SKILL.md frontmatter,
    extracts MCP dependencies, and creates database records.
    """
    # Skills that exist in filesystem (subdirectories under skills/)
    skills_dir = Path(__file__).parent.parent / "skills"
    skill_names = [d.name for d in skills_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

    created_skills = []

    with conn.cursor() as cursor:
        for skill_name in sorted(skill_names):
            # Check if skill already exists
            cursor.execute("SELECT id FROM skills WHERE name = %s", (skill_name,))
            if cursor.fetchone():
                print(f"Skill '{skill_name}' already exists, skipping...")
                continue

            # Load frontmatter from SKILL.md
            fm = load_skill_frontmatter(skill_name)
            description = fm.get("description", f"Skill: {skill_name}")

            # Extract MCP dependencies from mcp_config if present
            dependencies = None
            mcp_config = fm.get("mcp_config")
            if mcp_config:
                dependencies = extract_urls_from_mcp_config(mcp_config)
                if dependencies:
                    print(f"  → MCP dependencies: {dependencies}")

            # Create skill metadata record
            cursor.execute(
                """
                INSERT INTO skills (name, description, path, status, dependencies, created_at, updated_at)
                VALUES (%s, %s, %s, 'active', %s, %s, %s)
                """,
                (
                    skill_name,
                    description,
                    skill_name,
                    json.dumps(dependencies) if dependencies else None,
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

            created_skills.append(skill_name)
            dep_info = f" ({len(dependencies)} deps)" if dependencies else ""
            print(f"Created skill record: {skill_name}{dep_info} -> {skill_name}/")

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
    conn = None

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
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()
