#!/usr/bin/env python3
"""
创建风险监控相关的数据库表
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.base import engine, Base
from app.database.models import RiskEventRecord
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_risk_monitoring_tables():
    """创建风险监控相关的数据库表"""
    try:
        logger.info("开始创建风险监控数据库表...")

        # 创建所有表（包括新的RiskEventRecord表）
        Base.metadata.create_all(bind=engine)

        logger.info("✅ 风险监控数据库表创建成功！")

        # 验证表是否存在
        from sqlalchemy import inspect

        inspector = inspect(engine)
        tables = inspector.get_table_names()

        if "risk_events" in tables:
            logger.info("✅ risk_events 表已成功创建")

            # 检查表结构
            columns = inspector.get_columns("risk_events")
            logger.info("📋 risk_events 表结构:")
            for column in columns:
                logger.info(f"  - {column['name']}: {column['type']}")
        else:
            logger.error("❌ risk_events 表未找到")
            return False

        return True

    except Exception as e:
        logger.error(f"❌ 创建风险监控表失败: {e}")
        return False


if __name__ == "__main__":
    success = create_risk_monitoring_tables()
    if success:
        print("\n🎉 风险监控系统数据库初始化完成！")
        print("现在可以启动风险监控功能了。")
    else:
        print("\n❌ 风险监控系统数据库初始化失败！")
        print("请检查错误信息并重试。")
        sys.exit(1)
