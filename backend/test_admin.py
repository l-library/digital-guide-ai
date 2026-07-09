"""管理员用户管理功能测试脚本

运行前请确保后端服务已启动:
    cd backend && conda activate DGA && uvicorn app.main:app

可通过环境变量修改后端地址:
    BASE_URL=http://127.0.0.1:8000 python test_admin.py
"""
import os
import sys
import requests

# ── 配置 ─────────────────────────────────────────────────────────────────

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
API_BASE = f"{BASE_URL}/api/v1"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# 测试用户信息（每次运行使用相同用户名，方便清理残留）
TEST_USERNAME = "test_admin_001"
TEST_PASSWORD = "test123456"
TEST_DISPLAY_NAME = "测试用户"

# ── 测试框架 ─────────────────────────────────────────────────────────────

passed = 0
failed = 0


def test(name: str, condition: bool, detail: str = "") -> None:
    """断言一个测试条件，打印 PASS/FAIL 并更新计数器。"""
    global passed, failed
    if condition:
        print(f"  \033[32mPASS\033[0m: {name}")
        passed += 1
    else:
        print(f"  \033[31mFAIL\033[0m: {name} {detail}")
        failed += 1


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── 清理残留 ─────────────────────────────────────────────────────────────

def cleanup_user_if_exists(admin_token: str) -> None:
    """如果上次测试的 test_admin_001 用户残留，先通过 API 删除它。"""
    # 先查列表找到该用户
    r = requests.get(
        f"{API_BASE}/admin/users",
        params={"search": TEST_USERNAME, "page_size": 5},
        headers=_auth_header(admin_token),
        timeout=10,
    )
    if r.status_code == 200:
        data = r.json().get("data", {})
        items = data.get("items", [])
        for u in items:
            if u.get("username") == TEST_USERNAME:
                user_id = u["id"]
                print(f"  清理残留用户: id={user_id}, username={TEST_USERNAME}")
                requests.delete(
                    f"{API_BASE}/admin/users/{user_id}",
                    headers=_auth_header(admin_token),
                    timeout=10,
                )
                return


# ── 主流程 ───────────────────────────────────────────────────────────────

def main() -> None:
    global passed, failed

    print("=" * 60)
    print("管理员用户管理功能测试")
    print(f"后端地址: {BASE_URL}")
    print("=" * 60)

    # ── 1. admin 登录获取 token ──────────────────────────────────────

    print("\n── 1. admin 登录获取 token ──")
    r = requests.post(
        f"{API_BASE}/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
        timeout=10,
    )
    test("admin 登录返回 200", r.status_code == 200, f"status={r.status_code}")
    admin_token = r.json().get("data", {}).get("token", "")
    test("admin token 不为空", bool(admin_token))
    if not admin_token:
        print("  ⚠ admin token 获取失败，终止测试")
        sys.exit(1)

    # 清理可能的残留用户
    cleanup_user_if_exists(admin_token)

    # ── 2. 创建测试用户 ──────────────────────────────────────────────

    print("\n── 2. 创建测试用户 ──")
    r = requests.post(
        f"{API_BASE}/admin/users",
        json={
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
            "display_name": TEST_DISPLAY_NAME,
        },
        headers=_auth_header(admin_token),
        timeout=10,
    )
    test("创建用户返回 201", r.status_code == 201, f"status={r.status_code} body={r.text[:200]}")
    user_data = r.json().get("data", {})
    created_user_id = user_data.get("user_id", 0) or user_data.get("id", 0)
    test("创建用户返回 user_id > 0", created_user_id > 0)
    if not created_user_id:
        print("  ⚠ 用户未成功创建，终止测试")
        sys.exit(1)
    print(f"  创建的用户 id={created_user_id}")

    # ── 3. 查询用户列表 ──────────────────────────────────────────────

    print("\n── 3. 查询用户列表 ──")
    r = requests.get(
        f"{API_BASE}/admin/users",
        params={"page": 1, "page_size": 10},
        headers=_auth_header(admin_token),
        timeout=10,
    )
    test("查询列表返回 200", r.status_code == 200, f"status={r.status_code}")
    data = r.json().get("data", {})
    items = data.get("items", [])
    found = any(u.get("id") == created_user_id for u in items)
    test("列表包含新创建的用户", found)

    # ── 4. 搜索用户 ──────────────────────────────────────────────────

    print("\n── 4. 搜索用户 ──")
    r = requests.get(
        f"{API_BASE}/admin/users",
        params={"search": "测试", "page_size": 10},
        headers=_auth_header(admin_token),
        timeout=10,
    )
    test("搜索返回 200", r.status_code == 200, f"status={r.status_code}")
    search_items = r.json().get("data", {}).get("items", [])
    found = any(u.get("id") == created_user_id for u in search_items)
    test("搜索结果包含目标用户", found)

    # ── 5. 获取用户详情 ──────────────────────────────────────────────

    print("\n── 5. 获取用户详情 ──")
    r = requests.get(
        f"{API_BASE}/admin/users/{created_user_id}",
        headers=_auth_header(admin_token),
        timeout=10,
    )
    test("获取详情返回 200", r.status_code == 200, f"status={r.status_code}")
    detail = r.json().get("data", {})
    test("详情包含 conversation_count", "conversation_count" in detail)

    # ── 6. 编辑用户信息 ──────────────────────────────────────────────

    print("\n── 6. 编辑用户信息 ──")
    r = requests.put(
        f"{API_BASE}/admin/users/{created_user_id}",
        json={"display_name": "更新昵称", "phone": "13800138000"},
        headers=_auth_header(admin_token),
        timeout=10,
    )
    test("编辑用户返回 200", r.status_code == 200, f"status={r.status_code}")
    updated = r.json().get("data", {})
    test("display_name 已更新", updated.get("display_name") == "更新昵称")
    test("phone 已更新", updated.get("phone") == "13800138000")

    # ── 7. 为被禁用用户登录获取 token（用于之后验证） ──────────────

    print("\n── 7. 为被禁用用户登录获取 token ──")
    r = requests.post(
        f"{API_BASE}/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        timeout=10,
    )
    test("被禁用前用户登录返回 200", r.status_code == 200, f"status={r.status_code}")
    disabled_user_token = r.json().get("data", {}).get("token", "")
    test("被禁用前获取到 token", bool(disabled_user_token))

    # ── 8. 禁用用户 ──────────────────────────────────────────────────

    print("\n── 8. 禁用用户 ──")
    r = requests.put(
        f"{API_BASE}/admin/users/{created_user_id}/status",
        json={"is_active": False},
        headers=_auth_header(admin_token),
        timeout=10,
    )
    test("禁用用户返回 200", r.status_code == 200, f"status={r.status_code}")
    status_data = r.json().get("data", {})
    test("is_active 为 False", status_data.get("is_active") is False)

    # ── 9. 验证禁用用户旧 token 失效 ────────────────────────────────

    print("\n── 9. 验证禁用用户旧 token 失效 ──")
    r = requests.get(
        f"{API_BASE}/auth/verify",
        headers=_auth_header(disabled_user_token),
        timeout=10,
    )
    test("禁用后旧 token 验证失败 (401/403)", r.status_code in (401, 403), f"status={r.status_code}, body={r.text[:100]}")

    # ── 10. 验证禁用用户无法登录 ─────────────────────────────────────

    print("\n── 10. 验证禁用用户无法登录 ──")
    r = requests.post(
        f"{API_BASE}/auth/login",
        json={"username": TEST_USERNAME, "password": TEST_PASSWORD},
        timeout=10,
    )
    test("禁用后登录返回 403", r.status_code == 403, f"status={r.status_code}")

    # ── 11. 启用用户 ─────────────────────────────────────────────────

    print("\n── 11. 启用用户 ──")
    r = requests.put(
        f"{API_BASE}/admin/users/{created_user_id}/status",
        json={"is_active": True},
        headers=_auth_header(admin_token),
        timeout=10,
    )
    test("启用用户返回 200", r.status_code == 200, f"status={r.status_code}")
    status_data = r.json().get("data", {})
    test("is_active 为 True", status_data.get("is_active") is True)

    # ── 12. 删除用户 ─────────────────────────────────────────────────

    print("\n── 12. 删除用户 ──")
    r = requests.delete(
        f"{API_BASE}/admin/users/{created_user_id}",
        headers=_auth_header(admin_token),
        timeout=10,
    )
    test("删除用户返回 200", r.status_code == 200, f"status={r.status_code}")

    # ── 13. 验证用户已删除 ──────────────────────────────────────────

    print("\n── 13. 验证用户已删除 ──")
    r = requests.get(
        f"{API_BASE}/admin/users/{created_user_id}",
        headers=_auth_header(admin_token),
        timeout=10,
    )
    test("查询已删除用户返回 404", r.status_code == 404, f"status={r.status_code}")

    # ── 14. visitor 越权测试 ────────────────────────────────────────

    print("\n── 14. visitor 越权测试 ──")
    # 注册一个 visitor 用户
    r = requests.post(
        f"{API_BASE}/auth/register",
        json={
            "username": "test_visitor_001",
            "password": "visitor123",
            "confirm_password": "visitor123",
            "display_name": "越权游客",
        },
        timeout=10,
    )
    visitor_token = r.json().get("data", {}).get("token", "")
    test("visitor 注册成功", r.status_code == 200 and bool(visitor_token))

    # 用 visitor token 尝试访问管理员接口
    r = requests.get(
        f"{API_BASE}/admin/users",
        params={"page": 1, "page_size": 5},
        headers=_auth_header(visitor_token) if visitor_token else {},
        timeout=10,
    )
    test("visitor 访问管理员接口返回 403", r.status_code == 403, f"status={r.status_code}")

    # 清理 visitor 用户
    if visitor_token:
        # 用 admin 查询 visitor 的 user_id 然后删除
        r = requests.get(
            f"{API_BASE}/admin/users",
            params={"search": "test_visitor_001", "page_size": 5},
            headers=_auth_header(admin_token),
            timeout=10,
        )
        if r.status_code == 200:
            for u in r.json().get("data", {}).get("items", []):
                if u.get("username") == "test_visitor_001":
                    requests.delete(
                        f"{API_BASE}/admin/users/{u['id']}",
                        headers=_auth_header(admin_token),
                        timeout=10,
                    )
                    break

    # ── 15. 保护超级管理员 - 删除 ───────────────────────────────────

    print("\n── 15. 保护超级管理员 - 删除 ──")
    r = requests.delete(
        f"{API_BASE}/admin/users/1",
        headers=_auth_header(admin_token),
        timeout=10,
    )
    test("删除超级管理员返回 403", r.status_code == 403, f"status={r.status_code}")

    # ── 16. 保护超级管理员 - 禁用 ───────────────────────────────────

    print("\n── 16. 保护超级管理员 - 禁用 ──")
    r = requests.put(
        f"{API_BASE}/admin/users/1/status",
        json={"is_active": False},
        headers=_auth_header(admin_token),
        timeout=10,
    )
    test("禁用超级管理员返回 403", r.status_code == 403, f"status={r.status_code}")

    # ── 总结 ─────────────────────────────────────────────────────────

    print(f"\n{'=' * 60}")
    total = passed + failed
    print(f"结果: {passed} passed, {failed} failed, {total} total")
    print("=" * 60)

    if failed > 0:
        print("⚠ 存在失败用例，请检查后端服务是否正确运行。")
        sys.exit(1)
    else:
        print("✓ 全部用例通过！")


if __name__ == "__main__":
    main()
