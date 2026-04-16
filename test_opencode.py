import requests

# Test exactly as OpenCode would
url = 'http://localhost:8000/mcp'
headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json, text/event-stream',
    'Authorization': 'Bearer 2rotINY-6BEbIOpHKMaQNrmVe324uJ56W0mBWTLYRFI'
}

payload = {
    'jsonrpc': '2.0',
    'id': 1,
    'method': 'initialize',
    'params': {
        'protocolVersion': '2024-11-05',
        'capabilities': {},
        'clientInfo': {'name': 'opencode', 'version': '1.0.0'}
    }
}

print("=== Test 1: With Accept header (both JSON and SSE) ===")
resp = requests.post(url, json=payload, headers=headers, timeout=5)
print(f'Status: {resp.status_code}')
print(f'Content-Type: {resp.headers.get("Content-Type")}')
print(f'Response: {resp.text[:300]}')
print()

print("=== Test 2: GET request (OpenCode might do this first) ===")
try:
    resp = requests.get(url, headers={'Accept': 'application/json, text/event-stream'}, timeout=5)
    print(f'GET Status: {resp.status_code}')
    print(f'GET Response: {resp.text[:300]}')
except Exception as e:
    print(f'GET Error: {e}')
