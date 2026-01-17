#!/usr/bin/env python3
"""
诊断前端显示"Total 0 users"的问题
"""

import requests
import json

API_BASE_URL = "http://localhost:8000"


def test_frontend_flow():
    print("诊断前端用户显示问题")
    print("=" * 60)

    # 1. 获取管理员token
    print("1. 获取管理员token...")
    login_data = {"username": "admin", "password": "admin123"}

    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login", json=login_data, timeout=10
        )

        if response.status_code == 200:
            token = response.json().get("access_token")
            print(f"   Token获取成功: {token[:20]}...")
        else:
            print(f"   登录失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return
    except Exception as e:
        print(f"   登录请求失败: {e}")
        return

    # 2. 测试用户统计API
    print("\n2. 测试用户统计API...")
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(
            f"{API_BASE_URL}/admin/users/stats", headers=headers, timeout=10
        )

        if response.status_code == 200:
            stats = response.json()
            print(f"   用户统计API成功:")
            print(f"     总用户数: {stats.get('total_users')}")
            print(f"     角色分布: {stats.get('role_distribution')}")
        else:
            print(f"   用户统计API失败: {response.status_code}")
            print(f"   响应: {response.text}")
    except Exception as e:
        print(f"   用户统计API请求失败: {e}")

    # 3. 测试用户列表API（分页）
    print("\n3. 测试用户列表API（分页）...")

    try:
        response = requests.get(
            f"{API_BASE_URL}/admin/users/?page=1&size=10", headers=headers, timeout=10
        )

        if response.status_code == 200:
            user_list = response.json()
            users = user_list.get("users", [])
            pagination = user_list.get("pagination", {})

            print(f"   用户列表API成功:")
            print(f"     返回用户数: {len(users)}")
            print(f"     分页信息: {pagination}")

            if len(users) > 0:
                print(
                    f"     第一个用户: {users[0].get('username')} ({users[0].get('role')})"
                )
            else:
                print(f"     ⚠️ 用户列表为空！")

            # 检查分页总数
            if pagination.get("total", 0) == 0:
                print(f"     ⚠️ 分页显示总用户数为0！")
            else:
                print(f"     分页显示总用户数: {pagination.get('total')}")
        else:
            print(f"   用户列表API失败: {response.status_code}")
            print(f"   响应: {response.text}")
    except Exception as e:
        print(f"   用户列表API请求失败: {e}")

    # 4. 检查可能的权限问题
    print("\n4. 检查用户权限...")

    # 获取当前用户信息
    try:
        # 首先解码token获取用户名
        import jwt

        decoded = jwt.decode(token, options={"verify_signature": False})
        username = decoded.get("sub")
        print(f"   Token中的用户名: {username}")

        # 检查用户是否是admin
        print(f"   Token payload: {decoded}")
    except Exception as e:
        print(f"   Token解码失败: {e}")

    # 5. 检查数据库连接
    print("\n5. 检查数据库连接...")
    import sqlite3

    try:
        conn = sqlite3.connect("data/explicandum.db")
        cursor = conn.cursor()

        # 检查users表
        cursor.execute("SELECT COUNT(*) FROM users")
        db_count = cursor.fetchone()[0]
        print(f"   数据库中的用户总数: {db_count}")

        # 检查用户详情
        cursor.execute("SELECT id, username, role, is_temp FROM users LIMIT 5")
        users = cursor.fetchall()
        print(f"   前5个用户:")
        for user in users:
            print(f"     - {user[1]} (ID: {user[0]}, 角色: {user[2]}, 临时: {user[3]})")

        conn.close()
    except Exception as e:
        print(f"   数据库检查失败: {e}")

    print("\n" + "=" * 60)
    print("诊断完成")


if __name__ == "__main__":
    test_frontend_flow()
