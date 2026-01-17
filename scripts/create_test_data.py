#!/usr/bin/env python3
"""
创建测试用户数据的脚本
"""

import sys
import os
from datetime import datetime, timedelta
import uuid

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database.base import engine, SessionLocal
from app.database.models import (
    User,
    InvitationCode,
)
from app.core.auth import get_password_hash

# 确保数据库路径正确
import os

print(f"数据库引擎URL: {engine.url}")


def create_test_users():
    """创建测试用户"""
    db = SessionLocal()

    try:
        # 检查是否已有用户
        existing_users = db.query(User).count()
        if existing_users > 0:
            print(f"数据库中已有 {existing_users} 个用户，跳过创建")
            return

        print("开始创建测试用户...")

        # 创建管理员用户
        admin_user = User(
            id="usr_admin001",
            username="admin",
            email="admin@explicandum.ai",
            hashed_password=get_password_hash("admin123"),
            role="admin",
            is_temp=False,
            token_quota=1000000,
            tokens_used=0,
            request_count=0,
            registration_ip="127.0.0.1",
            created_at=datetime.utcnow(),
            last_request_at=datetime.utcnow(),
        )
        db.add(admin_user)

        # 创建学术用户（学术邮箱自动获得researcher身份）
        academic_user = User(
            id="usr_academic001",
            username="researcher_zhang",
            email="zhang@university.edu.cn",
            hashed_password=get_password_hash("academic123"),
            role="researcher",
            is_temp=False,
            token_quota=500000,
            tokens_used=25000,
            request_count=45,
            registration_ip="192.168.1.100",
            created_at=datetime.utcnow() - timedelta(days=30),
            last_request_at=datetime.utcnow() - timedelta(hours=2),
        )
        db.add(academic_user)

        # 创建普通用户（非学术邮箱）
        regular_user = User(
            id="usr_regular001",
            username="student_wang",
            email="wang@student.com",
            hashed_password=get_password_hash("student123"),
            role="user",
            is_temp=False,
            token_quota=100000,
            tokens_used=15000,
            request_count=23,
            registration_ip="192.168.1.101",
            created_at=datetime.utcnow() - timedelta(days=15),
            last_request_at=datetime.utcnow() - timedelta(hours=6),
        )
        db.add(regular_user)

        # 创建临时用户
        temp_user = User(
            id="usr_temp001",
            username="Guest_abc123",
            email=None,
            hashed_password=None,
            role="temp",
            is_temp=True,
            expires_at=datetime.utcnow() + timedelta(days=30),
            upgrade_token="upgrade_token_abc123",
            token_quota=20000,
            tokens_used=5000,
            request_count=8,
            registration_ip="192.168.1.102",
            created_at=datetime.utcnow() - timedelta(days=5),
            last_request_at=datetime.utcnow() - timedelta(hours=1),
        )
        db.add(temp_user)

        # 创建更多测试用户
        test_users = [
            {
                "id": "usr_researcher002",
                "username": "prof_li",
                "email": "li@institute.ac.cn",  # 学术邮箱
                "role": "researcher",
                "token_quota": 500000,
                "tokens_used": 45000,
                "request_count": 67,
                "ip": "192.168.1.103",
                "days_ago": 45,
            },
            {
                "id": "usr_student002",
                "username": "student_chen",
                "email": "chen@campus.com",  # 非学术邮箱
                "role": "user",
                "token_quota": 100000,
                "tokens_used": 8000,
                "request_count": 12,
                "ip": "192.168.1.104",
                "days_ago": 7,
            },
            {
                "id": "usr_researcher003",
                "username": "dr_liu",
                "email": "liu@hospital.edu.cn",  # 学术邮箱
                "role": "researcher",
                "token_quota": 500000,
                "tokens_used": 120000,
                "request_count": 156,
                "ip": "192.168.1.105",
                "days_ago": 60,
            },
        ]

        for user_data in test_users:
            user = User(
                id=user_data["id"],
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=get_password_hash("test123"),
                role=user_data["role"],
                is_temp=False,
                token_quota=user_data["token_quota"],
                tokens_used=user_data["tokens_used"],
                request_count=user_data["request_count"],
                registration_ip=user_data["ip"],
                created_at=datetime.utcnow() - timedelta(days=user_data["days_ago"]),
                last_request_at=datetime.utcnow()
                - timedelta(hours=user_data["days_ago"] % 24),
            )
            db.add(user)

        db.commit()
        print(f"成功创建了 {len(test_users) + 4} 个测试用户")

    except Exception as e:
        print(f"创建用户时出错: {e}")
        db.rollback()
    finally:
        db.close()


def create_test_invitations():
    """创建测试邀请码"""
    db = SessionLocal()

    try:
        # 检查是否已有邀请码
        existing_invites = db.query(InvitationCode).count()
        if existing_invites > 0:
            print(f"数据库中已有 {existing_invites} 个邀请码，跳过创建")
            return

        print("开始创建测试邀请码...")

        # 创建测试邀请码
        invitations = [
            {
                "id": "inv_001",
                "code": "ACADEMIC2024",
                "created_by": "usr_admin001",
                "max_uses": 10,
                "used_count": 3,
                "is_used": False,
                "allows_guest": False,
                "requires_verification": True,
                "expires_at": datetime.utcnow() + timedelta(days=90),
            },
            {
                "id": "inv_002",
                "code": "RESEARCHER2024",
                "created_by": "usr_admin001",
                "max_uses": 5,
                "used_count": 1,
                "is_used": False,
                "allows_guest": True,
                "requires_verification": False,
                "expires_at": datetime.utcnow() + timedelta(days=60),
            },
            {
                "id": "inv_003",
                "code": "GUEST2024",
                "created_by": "usr_admin001",
                "max_uses": 50,
                "used_count": 15,
                "is_used": False,
                "allows_guest": True,
                "requires_verification": True,
                "expires_at": datetime.utcnow() + timedelta(days=30),
            },
        ]

        for inv_data in invitations:
            invitation = InvitationCode(
                id=inv_data["id"],
                code=inv_data["code"],
                created_by=inv_data["created_by"],
                used_by=None,
                is_used=inv_data["is_used"],
                max_uses=inv_data["max_uses"],
                used_count=inv_data["used_count"],
                expires_at=inv_data["expires_at"],
                allows_guest=inv_data["allows_guest"],
                requires_verification=inv_data["requires_verification"],
                created_at=datetime.utcnow() - timedelta(days=7),
            )
            db.add(invitation)

        db.commit()
        print(f"成功创建了 {len(invitations)} 个测试邀请码")

    except Exception as e:
        print(f"创建邀请码时出错: {e}")
        db.rollback()
    finally:
        db.close()


def verify_data():
    """验证创建的数据"""
    db = SessionLocal()

    try:
        print("\n=== 数据验证 ===")

        # 统计用户
        user_count = db.query(User).count()
        admin_count = db.query(User).filter(User.role == "admin").count()
        researcher_count = db.query(User).filter(User.role == "researcher").count()
        user_regular_count = db.query(User).filter(User.role == "user").count()
        temp_count = db.query(User).filter(User.is_temp == True).count()

        print(f"用户总数: {user_count}")
        print(f"  - 管理员: {admin_count}")
        print(f"  - 研究员: {researcher_count}")
        print(f"  - 普通用户: {user_regular_count}")
        print(f"  - 临时用户: {temp_count}")

        # 统计邀请码
        inv_count = db.query(InvitationCode).count()
        active_count = (
            db.query(InvitationCode).filter(InvitationCode.is_used == False).count()
        )

        print(f"\n邀请码总数: {inv_count}")
        print(f"  - 可用: {active_count}")

        # 显示用户列表
        print(f"\n=== 用户列表 ===")
        users = db.query(User).all()
        for user in users:
            status = "临时" if user.is_temp else "正式"
            print(f"{user.username} ({user.email or 'N/A'}) - {user.role} - {status}")

    except Exception as e:
        print(f"验证数据时出错: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    print("开始创建测试数据...")

    # 创建表（如果不存在）
    from app.database.models import Base

    Base.metadata.create_all(bind=engine)

    # 创建测试数据
    create_test_users()
    create_test_invitations()

    # 验证数据
    verify_data()

    print("\n测试数据创建完成！")
    print("\n=== 测试账号信息 ===")
    print("管理员: admin / admin123")
    print("学术用户: researcher_zhang / academic123")
    print("普通用户: student_wang / student123")
    print("临时用户: Guest_abc123 (无密码)")
    print("\n=== 系统逻辑说明 ===")
    print("1. 学术邮箱用户自动获得researcher身份")
    print("2. 非学术邮箱用户获得user身份")
    print("3. 中国地域用户使用非学术邮箱注册失败")
    print("4. 系统只有用户注册一层，无学术申请流程")
