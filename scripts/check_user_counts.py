#!/usr/bin/env python3
"""
检查用户管理页面上的数目是否和数据库中一致
"""

import sys
import os
import sqlite3
import requests
import json
from datetime import datetime

# 数据库路径 - 注意：数据库文件已移动到 data/ 目录
DB_PATH = "data/explicandum.db"
API_BASE_URL = "http://localhost:8000"


def get_db_user_counts():
    """从数据库直接查询用户统计"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 获取总用户数
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    # 按角色统计
    cursor.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
    role_counts = cursor.fetchall()

    # 按临时状态统计
    cursor.execute("SELECT is_temp, COUNT(*) FROM users GROUP BY is_temp")
    temp_counts = cursor.fetchall()

    # 转换为字典
    role_dict = {role: count for role, count in role_counts}
    temp_dict = {is_temp: count for is_temp, count in temp_counts}

    # 计算研究员数量（role='researcher'）
    researcher_count = role_dict.get("researcher", 0)

    # 计算普通用户数量（role='user'）
    user_count = role_dict.get("user", 0)

    # 计算管理员数量（role='admin'）
    admin_count = role_dict.get("admin", 0)

    # 计算临时用户数量（is_temp=1）
    temp_user_count = temp_dict.get(1, 0)

    conn.close()

    return {
        "total_users": total_users,
        "admin_count": admin_count,
        "researcher_count": researcher_count,
        "user_count": user_count,
        "temp_count": temp_user_count,
        "role_distribution": role_dict,
        "temp_distribution": temp_dict,
    }


def get_admin_token():
    """获取管理员token"""
    # 尝试使用admin用户登录
    login_data = {"username": "admin", "password": "admin123"}

    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/login", json=login_data, timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            print(f"登录失败: {response.status_code}")
            print(f"响应: {response.text}")
            return None
    except Exception as e:
        print(f"登录请求失败: {e}")
        return None


def get_api_user_stats(token):
    """通过API获取用户统计"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        response = requests.get(
            f"{API_BASE_URL}/admin/users/stats", headers=headers, timeout=10
        )

        if response.status_code == 200:
            return response.json()
        else:
            print(f"API请求失败: {response.status_code}")
            print(f"响应: {response.text}")
            return None
    except Exception as e:
        print(f"API请求异常: {e}")
        return None


def compare_counts(db_counts, api_stats):
    """比较数据库和API的统计"""
    print("\n" + "=" * 60)
    print("用户数量一致性检查")
    print("=" * 60)

    # 提取API统计
    api_total = api_stats.get("total_users", 0)
    api_role_dist = api_stats.get("role_distribution", {})
    api_admin = api_role_dist.get("admin", 0)
    api_researcher = api_role_dist.get("researcher", 0)
    api_user = api_role_dist.get("user", 0)
    api_temp = api_role_dist.get("temp", 0)

    # 数据库统计
    db_total = db_counts["total_users"]
    db_admin = db_counts["admin_count"]
    db_researcher = db_counts["researcher_count"]
    db_user = db_counts["user_count"]
    db_temp = db_counts["temp_count"]

    # 比较结果
    comparisons = [
        ("总用户数", db_total, api_total),
        ("管理员数", db_admin, api_admin),
        ("研究员数", db_researcher, api_researcher),
        ("普通用户数", db_user, api_user),
        ("临时用户数", db_temp, api_temp),
    ]

    all_match = True

    print(f"{'项目':<15} {'数据库':<10} {'API':<10} {'状态':<10}")
    print("-" * 45)

    for name, db_val, api_val in comparisons:
        match = db_val == api_val
        status = "✓ 一致" if match else "✗ 不一致"
        if not match:
            all_match = False
        print(f"{name:<15} {db_val:<10} {api_val:<10} {status:<10}")

    print("\n" + "=" * 60)

    if all_match:
        print("✅ 所有用户数量一致！")
    else:
        print("❌ 发现不一致的用户数量！")

        # 详细分析差异
        print("\n详细分析:")
        if db_total != api_total:
            print(f"  - 总用户数差异: 数据库({db_total}) vs API({api_total})")
            print(f"    差异: {abs(db_total - api_total)} 个用户")

        # 检查角色分布总和
        db_role_sum = db_admin + db_researcher + db_user + db_temp
        api_role_sum = api_admin + api_researcher + api_user + api_temp

        if db_role_sum != db_total:
            print(f"  - 数据库角色分布总和({db_role_sum})不等于总用户数({db_total})")

        if api_role_sum != api_total:
            print(f"  - API角色分布总和({api_role_sum})不等于总用户数({api_total})")

    return all_match


def main():
    print("开始检查用户数量一致性...")
    print(f"数据库路径: {DB_PATH}")
    print(f"API地址: {API_BASE_URL}")

    # 1. 获取数据库统计
    print("\n1. 从数据库查询用户统计...")
    db_counts = get_db_user_counts()
    print(f"   数据库总用户数: {db_counts['total_users']}")
    print(f"   角色分布: {db_counts['role_distribution']}")
    print(f"   临时用户分布: {db_counts['temp_distribution']}")

    # 2. 获取管理员token
    print("\n2. 获取管理员token...")
    token = get_admin_token()
    if not token:
        print("   无法获取管理员token，尝试使用现有token...")
        # 尝试从环境变量获取token
        token = os.environ.get("ADMIN_TOKEN")
        if not token:
            print("   错误: 无法获取管理员token，无法继续检查API")
            return False

    print("   Token获取成功")

    # 3. 获取API统计
    print("\n3. 从API获取用户统计...")
    api_stats = get_api_user_stats(token)
    if not api_stats:
        print("   错误: 无法从API获取用户统计")
        return False

    print(f"   API总用户数: {api_stats.get('total_users', 'N/A')}")
    print(f"   API角色分布: {api_stats.get('role_distribution', {})}")

    # 4. 比较结果
    print("\n4. 比较数据库和API数据...")
    result = compare_counts(db_counts, api_stats)

    # 5. 额外检查：分页用户列表
    print("\n5. 检查分页用户列表...")
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = requests.get(
            f"{API_BASE_URL}/admin/users/?page=1&size=100", headers=headers, timeout=10
        )
        if response.status_code == 200:
            user_list_data = response.json()
            api_user_list_count = len(user_list_data.get("users", []))
            api_pagination_total = user_list_data.get("pagination", {}).get("total", 0)

            print(f"   分页API返回用户数: {api_user_list_count}")
            print(f"   分页API总用户数: {api_pagination_total}")

            if api_pagination_total != db_counts["total_users"]:
                print(
                    f"   ⚠️  分页API总用户数({api_pagination_total})与数据库({db_counts['total_users']})不一致"
                )
            else:
                print(f"   ✅ 分页API总用户数与数据库一致")
        else:
            print(f"   分页API请求失败: {response.status_code}")
    except Exception as e:
        print(f"   分页API检查异常: {e}")

    return result


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
