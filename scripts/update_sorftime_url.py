import requests
import json

admin_api_key = "2rotINY-6BEbIOpHKMaQNrmVe324uJ56W0mBWTLYRFI"

# Update time-compare skill to use the real sorftime URL
payload = {
    "description": "Compare local system time with remote server time from sorftime. Use when user needs to verify time synchronization, check time offset between local and remote servers, or diagnose time-related issues.",
    "mcp_config": {
        "sorftime": {
            "url": "https://mcp.sorftime.com?key=qw5szxljry9unw1ytgdvejrtohlbzz09"
        }
    },
}

# First delete the existing skill
print("--- Delete old time-compare skill ---")
resp = requests.delete(
    "http://localhost:8000/api/v1/skills/time-compare",
    headers={"X-API-Key": admin_api_key},
)
print(f"Delete status: {resp.status_code}")

# Create new skill with correct URL
print("\n--- Create time-compare skill with real sorftime URL ---")
payload = {
    "name": "time-compare",
    "description": "Compare local system time with remote server time from sorftime. Use when user needs to verify time synchronization, check time offset between local and remote servers, or diagnose time-related issues.",
    "mcp_config": {
        "sorftime": {
            "url": "https://mcp.sorftime.com?key=qw5szxljry9unw1ytgdvejrtohlbzz09"
        }
    },
}

resp = requests.post(
    "http://localhost:8000/api/v1/skills/json",
    json=payload,
    headers={"X-API-Key": admin_api_key},
)
print(f"Create status: {resp.status_code}")
if resp.status_code == 201:
    skill = resp.json()
    print(f"Dependencies (auth stripped): {skill['dependencies']}")
else:
    print(resp.text)
