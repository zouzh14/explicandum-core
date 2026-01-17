#!/usr/bin/env python3
"""
测试管理员登录和用户管理API
"""

import requests
import json

API_BASE_URL = "http://localhost:8000"


def test_admin_login_and_user_management():
    print("测试管理员登录和用户管理API")
    print("=" * 60)

    # 1. 管理员登录
    print("1. 管理员登录...")
    login_data = {"username": "admin", "password": "admin123"}

    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login", json=login_data, timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            user = data.get("user")
            print(f"   登录成功!")
            print(f"   用户: {user.get('username')} (角色: {user.get('role')})")
            print(f"   Token: {token[:20]}...")
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
            print(f"     Token统计: {stats.get('token_stats')}")
        else:
            print(f"   用户统计API失败: {response.status_code}")
            print(f"   响应: {response.text}")
    except Exception as e:
        print(f"   用户统计API请求失败: {e}")

    # 3. 测试用户列表API
    print("\n3. 测试用户列表API...")

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
                print(f"     用户列表:")
                for i, user in enumerate(users[:3]):  # 只显示前3个
                    print(
                        f"       {i + 1}. {user.get('username')} (角色: {user.get('role')}, 临时: {user.get('is_temp')})"
                    )
                if len(users) > 3:
                    print(f"       ... 还有 {len(users) - 3} 个用户")
            else:
                print(f"     ⚠️ 用户列表为空！")
        else:
            print(f"   用户列表API失败: {response.status_code}")
            print(f"   响应: {response.text}")
    except Exception as e:
        print(f"   用户列表API请求失败: {e}")

    # 4. 测试权限验证
    print("\n4. 测试权限验证...")

    try:
        response = requests.get(
            f"{API_BASE_URL}/auth/validate", headers=headers, timeout=10
        )

        if response.status_code == 200:
            validate_data = response.json()
            print(f"   权限验证成功:")
            print(f"     用户: {validate_data.get('user', {}).get('username')}")
            print(f"     角色: {validate_data.get('user', {}).get('role')}")
        else:
            print(f"   权限验证失败: {response.status_code}")
    except Exception as e:
        print(f"   权限验证请求失败: {e}")

    print("\n" + "=" * 60)
    print("测试完成")


if __name__ == "__main__":
    test_admin_login_and_user_management()
