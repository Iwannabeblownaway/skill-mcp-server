"""
OpenCode MCP 测试脚本
通过 skill-server 连接 MCP 服务并测试核心功能
"""

import json

API_KEY = "2rotINY-6BEbIOpHKMaQNrmVe324uJ56W0mBWTLYRFI"
BASE_URL = "http://localhost:8000"


def test_initialize():
    """测试 1: MCP initialize"""
    print("\n" + "=" * 60)
    print("Test 1: MCP Initialize")
    print("=" * 60)

    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "opencode-test", "version": "1.0.0"},
        },
    }

    url = f"{BASE_URL}/mcp?key={API_KEY}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    import requests

    resp = requests.post(url, json=payload, headers=headers, timeout=10)

    print(f"Status: {resp.status_code}")
    data = resp.json()

    if "result" in data:
        print("✅ Initialize 成功!")
        print(f"   Server: {data['result']['serverInfo']['name']}")
        print(f"   Version: {data['result']['serverInfo']['version']}")
        print(f"   Protocol: {data['result']['protocolVersion']}")
    else:
        print(f"❌ Initialize 失败: {data}")
        return False

    return True


def test_list_tools():
    """测试 2: tools/list"""
    print("\n" + "=" * 60)
    print("Test 2: MCP Tools List")
    print("=" * 60)

    payload = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

    url = f"{BASE_URL}/mcp?key={API_KEY}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    import requests

    resp = requests.post(url, json=payload, headers=headers, timeout=10)

    print(f"Status: {resp.status_code}")
    data = resp.json()

    if "result" in data:
        tools = data["result"].get("tools", data["result"])
        print(f"✅ 找到 {len(tools)} 个工具:")
        for tool in tools:
            print(f"   - {tool['name']}")
            if "description" in tool:
                desc = (
                    tool["description"][:60] + "..."
                    if len(tool["description"]) > 60
                    else tool["description"]
                )
                print(f"     {desc}")
    else:
        print(f"❌ List tools 失败: {data}")
        return False

    return True


def test_call_tool():
    """测试 3: tools/call - 调用 skill"""
    print("\n" + "=" * 60)
    print("Test 3: MCP Call Tool (code-review skill)")
    print("=" * 60)

    payload = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "use_skill_code-review",
            "arguments": {"skill_name": "code-review"},
        },
    }

    url = f"{BASE_URL}/mcp?key={API_KEY}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    import requests

    resp = requests.post(url, json=payload, headers=headers, timeout=10)

    print(f"Status: {resp.status_code}")
    data = resp.json()

    if "result" in data:
        content = data["result"]["content"][0]["text"]
        print(f"✅ 调用成功!")
        print(f"   内容长度: {len(content)} 字符")
        print(f"   前200字符:\n{content[:200]}...")
    else:
        print(f"❌ Call tool 失败: {data}")
        return False

    return True


def test_health():
    """测试 0: Health Check"""
    print("\n" + "=" * 60)
    print("Test 0: Health Check")
    print("=" * 60)

    import requests

    resp = requests.get(f"{BASE_URL}/health", timeout=5)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}")

    if resp.status_code == 200 and resp.json().get("status") == "healthy":
        print("✅ Health check 成功!")
        return True
    else:
        print("❌ Health check 失败!")
        return False


def test_api_endpoints():
    """测试 4: REST API endpoints"""
    print("\n" + "=" * 60)
    print("Test 4: REST API Endpoints")
    print("=" * 60)

    import requests

    success = True

    # Test skills list
    url = f"{BASE_URL}/api/v1/skills"
    headers = {"X-API-Key": API_KEY}

    resp = requests.get(url, headers=headers, timeout=10)
    print(f"GET /api/v1/skills - Status: {resp.status_code}")

    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Skills API 成功! 找到 {data.get('total', 0)} 个 skills")
    else:
        print(f"❌ Skills API 失败: {resp.text[:100]}")
        success = False

    # Test users list
    url = f"{BASE_URL}/api/v1/users"
    resp = requests.get(url, headers=headers, timeout=10)
    print(f"GET /api/v1/users - Status: {resp.status_code}")

    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Users API 成功! 找到 {data.get('total', 0)} 个 users")
    else:
        print(f"❌ Users API 失败: {resp.text[:100]}")
        success = False

    return success


def test_auth_failure():
    """测试 5: Auth failure without API key"""
    print("\n" + "=" * 60)
    print("Test 5: Auth Failure (no API key)")
    print("=" * 60)

    import requests

    url = f"{BASE_URL}/mcp"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    resp = requests.post(
        url,
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        headers=headers,
        timeout=10,
    )
    print(f"Status: {resp.status_code}")

    if resp.status_code == 401:
        print("✅ 正确拒绝无 API key 请求!")
        print(f"   Error: {resp.json().get('error')}")
        return True
    else:
        print(f"❌ 应该返回 401，实际: {resp.status_code}")
        return False


def main():
    print("\n" + "#" * 60)
    print("#  OpenCode MCP Server 测试")
    print("#" * 60)

    results = []

    # 按顺序执行测试
    results.append(("Health Check", test_health()))
    results.append(("Initialize", test_initialize()))
    results.append(("List Tools", test_list_tools()))
    results.append(("Call Tool", test_call_tool()))
    results.append(("Auth Failure", test_auth_failure()))
    results.append(("REST API", test_api_endpoints()))

    # 汇总
    print("\n" + "#" * 60)
    print("#  测试结果汇总")
    print("#" * 60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {name}")

    print(f"\n总计: {passed}/{total} 通过")


if __name__ == "__main__":
    main()
