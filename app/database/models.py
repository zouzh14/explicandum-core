from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    Text,
    Float,
    DateTime,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


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
