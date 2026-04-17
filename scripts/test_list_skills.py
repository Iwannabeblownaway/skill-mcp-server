import requests
import json

# List skills
resp = requests.get(
    "http://localhost:8000/api/v1/skills",
    headers={"X-API-Key": "2rotINY-6BEbIOpHKMaQNrmVe324uJ56W0mBWTLYRFI"},
)
print("List skills status:", resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    for skill in data.get("skills", []):
        deps = skill.get("dependencies", [])
        print(f"  - {skill['name']}: deps={deps}")
else:
    print(resp.text)
