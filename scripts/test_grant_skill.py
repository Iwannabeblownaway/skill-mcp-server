import requests
import json

admin_api_key = "2rotINY-6BEbIOpHKMaQNrmVe324uJ56W0mBWTLYRFI"

# Grant time-compare skill to admin
resp = requests.post(
    "http://localhost:8000/api/v1/user_skills",
    json={"skill_name": "time-compare", "user_id": 1},
    headers={"X-API-Key": admin_api_key},
)
print("Grant skill status:", resp.status_code)
print(
    "Response:",
    json.dumps(
        resp.json() if resp.status_code in (200, 201) else resp.text,
        indent=2,
        ensure_ascii=False,
    ),
)

# Now test the MCP tools/list endpoint
print("\n--- Testing MCP tools/list ---")
# MCP list_tools uses session-based auth, we need to get session first
# But we can verify by listing skills which shows the dependencies
resp = requests.get(
    "http://localhost:8000/api/v1/skills/time-compare",
    headers={"X-API-Key": admin_api_key},
)
print("Get skill status:", resp.status_code)
if resp.status_code == 200:
    skill = resp.json()
    print(f"Skill: {skill['name']}")
    print(f"Dependencies: {skill['dependencies']}")
    print(f"Description: {skill['description'][:100]}...")
