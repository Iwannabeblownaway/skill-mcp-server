import requests
import json

admin_api_key = "2rotINY-6BEbIOpHKMaQNrmVe324uJ56W0mBWTLYRFI"

# Check the skill details to verify dependencies are stored
print("--- Get time-compare skill ---")
resp = requests.get(
    "http://localhost:8000/api/v1/skills/time-compare",
    headers={"X-API-Key": admin_api_key},
)
print("Get skill status:", resp.status_code)
if resp.status_code == 200:
    skill = resp.json()
    print(f"Skill: {skill['name']}")
    print(f"Dependencies: {skill['dependencies']}")

# Also check the skill file was created
import os

skill_file = "D:/Project/skill-mcp-server/skills/time-compare/SKILL.md"
if os.path.exists(skill_file):
    print(f"\nSKILL.md exists at: {skill_file}")
    with open(skill_file, "r", encoding="utf-8") as f:
        content = f.read()
        print(f"Content preview:\n{content[:300]}...")
