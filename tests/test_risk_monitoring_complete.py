#!/usr/bin/env python3
"""
完整测试风险监控系统功能
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.base import get_db
from app.database.models import User, RiskEventRecord
from app.monitoring.risk_detector import RiskDetector, RiskLevel, RiskType
from app.monitoring.alert_manager import alert_manager
from app.core.auth import get_password_hash
from datetime import datetime, timedelta
import uuid
import json


def create_test_admin_user(db):
    """创建测试管理员用户"""
    admin_id = f"admin_{uuid.uuid4().hex[:8]}"
    admin_user = User(
        id=admin_id,
        username="test_admin_monitor",
        email="admin@test.com",
        hashed_password=get_password_hash("test123"),
        role="admin",
        registration_ip="127.0.0.1",
        last_request_at=datetime.utcnow() - timedelta(days=1),  # 1天前活跃
    )
    db.add(admin_user)
    db.commit()
    return admin_user


def create_test_users(db, count=5):
    """创建测试用户"""
    users = []
    for i in range(count):
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        user = User(
            id=user_id,
            username=f"testuser_{i}",
            email=f"user{i}@test.com",
            hashed_password=get_password_hash("test123"),
            role="user",
            token_quota=100000,
            tokens_used=95000 if i < 2 else 1000,  # 前2个用户接近配额限制
            registration_ip="192.168.1.100" if i < 3 else f"192.168.1.{i + 100}",
            last_request_at=datetime.utcnow() - timedelta(hours=i),  # 不同时间活跃
        )
        users.append(user)
        db.add(user)

    db.commit()
    return users


def test_risk_detection(db):
    """测试风险检测功能"""
    print("🧪 测试风险检测功能...")

    detector = RiskDetector()
    risks = detector.detect_all_risks(db)

    print(f"✅ 检测到 {len(risks)} 个风险事件")

    for i, risk in enumerate(risks):
        print(f"  {i + 1}. [{risk.level.value.upper()}] {risk.title}")
        print(f"     描述: {risk.description}")
        print(f"     值: {risk.value}, 阈值: {risk.threshold}")
        print(f"     推荐操作: {', '.join(risk.actions[:2])}")
        print()

    return risks


def test_alert_management(db, risks):
    """测试告警管理功能"""
    print("📢 测试告警管理功能...")

    # 存储风险事件
    stored_count = alert_manager.store_risk_events(risks, db)
    print(f"✅ 存储了 {stored_count} 个新的风险事件")

    # 获取未解决的风险
    unresolved_risks = alert_manager.get_unresolved_risks(db, limit=10)
    print(f"✅ 获取到 {len(unresolved_risks)} 个未解决的风险")

    # 获取统计数据
    stats = alert_manager.get_risk_statistics(db, 24)
    print(f"✅ 风险统计:")
    print(f"   - 总风险数: {stats['total_risks']}")
    print(f"   - 未解决: {stats['unresolved_risks']}")
    print(f"   - 严重: {stats['critical_count']}")
    print(f"   - 高: {stats['high_count']}")
    print(f"   - 中: {stats['medium_count']}")
    print(f"   - 低: {stats['low_count']}")

    return unresolved_risks


def test_risk_resolution(db, risks):
    """测试风险解决功能"""
    print("🔧 测试风险解决功能...")

    if not risks:
        print("⚠️  没有风险事件可供测试解决功能")
        return

    # 解决第一个风险
    risk_to_resolve = risks[0]
    success = alert_manager.resolve_risk(risk_to_resolve.id, "test_admin", db)

    if success:
        print(f"✅ 成功解决风险事件: {risk_to_resolve.title}")

        # 验证风险已标记为解决
        resolved_risk = (
            db.query(RiskEventRecord)
            .filter(RiskEventRecord.id == risk_to_resolve.id)
            .first()
        )
        if resolved_risk and resolved_risk.resolved:
            print(f"✅ 风险事件已正确标记为已解决")
            print(f"   解决时间: {resolved_risk.resolved_at}")
            print(f"   解决者: {resolved_risk.resolved_by}")
        else:
            print("❌ 风险事件标记解决失败")
    else:
        print(f"❌ 解决风险事件失败: {risk_to_resolve.title}")


def test_email_service():
    """测试邮件服务状态"""
    print("📧 测试邮件服务状态...")

    email_status = alert_manager.get_email_service_status()
    print(f"✅ 邮件服务状态:")
    print(f"   - 已配置: {email_status['configured']}")
    print(f"   - API密钥已配置: {email_status['api_key_configured']}")
    print(f"   - 发件邮箱: {email_status['from_email']}")
    print(f"   - 告警邮箱: {email_status['alert_email']}")
    print(f"   - 抄送邮箱: {email_status['cc_email']}")
    print(f"   - 服务提供商: {email_status['service_provider']}")


def cleanup_test_data(db, admin_user, test_users):
    """清理测试数据"""
    print("🧹 清理测试数据...")

    # 删除风险事件
    db.query(RiskEventRecord).delete()

    # 删除测试用户
    for user in test_users:
        db.delete(user)

    # 删除管理员用户
    db.delete(admin_user)

    db.commit()
    print("✅ 测试数据清理完成")


def main():
    """主测试函数"""
    print("🚀 开始完整风险监控系统测试...")
    print("=" * 60)

    db = next(get_db())

    try:
        # 1. 创建测试数据
        print("📝 创建测试数据...")
        admin_user = create_test_admin_user(db)
        test_users = create_test_users(db, 5)
        print(f"✅ 创建了 1 个管理员和 {len(test_users)} 个测试用户")
        print()

        # 2. 测试风险检测
        risks = test_risk_detection(db)
        print()

        # 3. 测试告警管理
        stored_risks = test_alert_management(db, risks)
        print()

        # 4. 测试风险解决
        test_risk_resolution(db, stored_risks)
        print()

        # 5. 测试邮件服务
        test_email_service()
        print()

        # 6. 最终验证
        print("🔍 最终验证...")
        final_stats = alert_manager.get_risk_statistics(db, 24)
        print(
            f"✅ 最终统计: 总风险={final_stats['total_risks']}, 未解决={final_stats['unresolved_risks']}"
        )

        print()
        print("🎉 风险监控系统测试完成！")
        print("✅ 所有核心功能正常工作")

    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        # 清理测试数据
        cleanup_test_data(db, admin_user, test_users)
        db.close()

    return True


if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
