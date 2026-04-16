import requests
import json

# Test MCP endpoint with JSON-RPC initialize request
url = "http://localhost:8000/mcp"

# JSON-RPC initialize request
payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "test-client", "version": "1.0.0"},
    },
}

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}

try:
    resp = requests.post(url, json=payload, headers=headers, timeout=5)
    print(f"Status: {resp.status_code}")
    print(f"Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
    print(f"Response: {resp.text[:1000]}")
except Exception as e:
    print(f"Error: {e}")
