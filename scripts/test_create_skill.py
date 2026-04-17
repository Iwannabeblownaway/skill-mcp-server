import requests
import json

# Create time-compare skill with mcp_config
payload = {
    "name": "time-compare",
    "description": "Compare local system time with remote server time from sorftime. Use when user needs to verify time synchronization, check time offset between local and remote servers, or diagnose time-related issues.",
    "mcp_config": {
        "sorftime": {"url": "http://localhost:5173/sorftime?api_key=dev-key-12345"}
    },
}

resp = requests.post(
    "http://localhost:8000/api/v1/skills/json",
    json=payload,
    headers={"X-API-Key": "2rotINY-6BEbIOpHKMaQNrmVe324uJ56W0mBWTLYRFI"},
)
print("Create skill status:", resp.status_code)
print(
    "Response:",
    json.dumps(
        resp.json() if resp.status_code == 201 else resp.text,
        indent=2,
        ensure_ascii=False,
    ),
)
