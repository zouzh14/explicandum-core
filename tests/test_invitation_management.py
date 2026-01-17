#!/usr/bin/env python3
"""
测试邀请码管理功能
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.base import get_db
from app.database.models import InvitationCode, User
from app.schema.models import InvitationCodeCreate
from app.core.auth import get_password_hash
from sqlalchemy.orm import Session
import uuid


def test_invitation_management():
    """测试邀请码管理功能"""
    print("🧪 开始测试邀请码管理功能...")

    # 获取数据库会话
    db = next(get_db())

    try:
        # 1. 创建测试管理员用户
        admin_id = f"admin_{uuid.uuid4().hex[:8]}"
        admin_user = User(
            id=admin_id,
            username="test_admin",
            email="admin@test.com",
            hashed_password=get_password_hash("test123"),
            role="admin",
            registration_ip="127.0.0.1",
        )
        db.add(admin_user)
        db.commit()
        print(f"✅ 创建测试管理员用户: {admin_user.username}")

        # 2. 测试创建邀请码
        invitation_data = InvitationCodeCreate(
            code="TEST123",
            max_uses=5,
            allows_guest=True,
            requires_verification=False,
            expires_at=None,
        )

        invitation_id = f"inv_{uuid.uuid4().hex[:8]}"
        invitation = InvitationCode(
            id=invitation_id,
            code=invitation_data.code,
            created_by=admin_user.id,
            max_uses=invitation_data.max_uses,
            allows_guest=invitation_data.allows_guest,
            requires_verification=invitation_data.requires_verification,
            expires_at=invitation_data.expires_at,
        )

        db.add(invitation)
        db.commit()
        print(f"✅ 创建邀请码: {invitation.code}")

        # 3. 测试查询邀请码
        invitations = db.query(InvitationCode).all()
        print(f"✅ 查询到 {len(invitations)} 个邀请码")

        # 4. 测试更新邀请码使用状态
        test_user_id = f"user_{uuid.uuid4().hex[:8]}"
        invitation.used_count += 1
        invitation.used_by = test_user_id
        db.commit()
        print(f"✅ 更新邀请码使用状态: {invitation.used_count}/{invitation.max_uses}")

        # 5. 测试删除邀请码
        db.delete(invitation)
        db.commit()
        print(f"✅ 删除邀请码: {invitation.code}")

        # 6. 清理测试数据
        db.delete(admin_user)
        db.commit()
        print("✅ 清理测试数据")

        print("🎉 所有测试通过！邀请码管理功能正常工作。")

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    test_invitation_management()
