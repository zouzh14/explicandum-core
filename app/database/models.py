from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    Text,
    Float,
    DateTime,
    Enum,
    JSON,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base
import enum


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)  # 允许为空
    hashed_password = Column(String, nullable=True)  # 允许为空（临时用户）
    role = Column(String, default="user")
    is_temp = Column(Boolean, default=False)  # 是否为临时用户
    expires_at = Column(DateTime, nullable=True)  # 临时用户过期时间
    upgrade_token = Column(String, nullable=True)  # 升级token
    registration_ip = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    token_quota = Column(Integer, default=100000)
    tokens_used = Column(Integer, default=0)
    request_count = Column(Integer, default=0)
    last_request_at = Column(DateTime)

    sessions = relationship("ChatSession", back_populates="owner")
    stances = relationship("PhilosophicalStance", back_populates="owner")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id = Column(String, primary_key=True, index=True)
    title = Column(String)
    user_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    personal_library_enabled = Column(Boolean, default=True)

    owner = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session")


class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"))
    role = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    tokens_consumed = Column(Integer, default=0)

    session = relationship("ChatSession", back_populates="messages")


class PhilosophicalStance(Base):
    __tablename__ = "philosophical_stances"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"))
    view = Column(Text)
    source_message_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="stances")


class VerificationCode(Base):
    __tablename__ = "verification_codes"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    code = Column(String)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_used = Column(Boolean, default=False)


class InvitationCode(Base):
    """邀请码管理"""

    __tablename__ = "invitation_codes"

    id = Column(String, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)  # 创建者
    used_by = Column(String, ForeignKey("users.id"), nullable=True)  # 使用者
    is_used = Column(Boolean, default=False)
    max_uses = Column(Integer, default=1)  # 最大使用次数
    used_count = Column(Integer, default=0)  # 已使用次数
    expires_at = Column(DateTime, nullable=True)  # 过期时间

    # 权限设置
    allows_guest = Column(Boolean, default=False)  # 是否允许guest用户
    requires_verification = Column(Boolean, default=True)  # 是否需要验证

    created_at = Column(DateTime, default=datetime.utcnow)
    used_at = Column(DateTime, nullable=True)  # 使用时间

    # 关联
    creator = relationship(
        "User", foreign_keys=[created_by], backref="created_invitations"
    )
    user = relationship("User", foreign_keys=[used_by], backref="used_invitation")


class UserRegion(Base):
    """用户地区记录"""

    __tablename__ = "user_regions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    ip_address = Column(String, nullable=False)
    region = Column(String, nullable=False)  # 地区
    country_code = Column(String, nullable=True)  # 国家代码
    is_china_region = Column(Boolean, nullable=False)  # 是否为中国地区
    detected_at = Column(DateTime, default=datetime.utcnow)

    # 关联
    user = relationship("User", backref="region_history")


class AccessLog(Base):
    """访问日志"""

    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # 可能未登录
    ip_address = Column(String, nullable=False)
    region = Column(String, nullable=False)
    action = Column(
        String, nullable=False
    )  # login_attempt, register_attempt, access_denied, etc.
    user_agent = Column(Text, nullable=True)
    success = Column(Boolean, default=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关联
    user = relationship("User", backref="access_logs")


class RiskEventRecord(Base):
    """风险事件记录"""

    __tablename__ = "risk_events"

    id = Column(String, primary_key=True, index=True)
    type = Column(String, nullable=False)  # security, performance, usage, system
    level = Column(String, nullable=False)  # critical, high, medium, low
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    value = Column(Float, nullable=False)
    threshold = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String, ForeignKey("users.id"), nullable=True)
    actions = Column(Text, nullable=True)  # JSON string
    event_metadata = Column(Text, nullable=True)  # JSON string
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime, nullable=True)

    # 关联
    resolver = relationship(
        "User", foreign_keys=[resolved_by], backref="resolved_risks"
    )
