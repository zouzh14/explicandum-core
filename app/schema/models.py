from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Union, Dict
from enum import Enum
from datetime import datetime


class AgentType(str, Enum):
    SYSTEM = "SYSTEM"
    LOGIC_ANALYST = "LOGIC_ANALYST"
    PHILOSOPHY_EXPERT = "PHILOSOPHY_EXPERT"
    USER = "USER"


class ThinkingStep(BaseModel):
    agent: AgentType
    content: str
    timestamp: int


class PhilosophicalStance(BaseModel):
    id: str
    view: str
    sourceMessageId: str
    timestamp: int

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # 允许使用字段别名
    )


class VectorChunk(BaseModel):
    id: str
    fileId: str
    fileName: str
    content: str
    index: int


class Message(BaseModel):
    id: str
    role: str  # 'user' or 'assistant'
    content: str
    thinkingSteps: Optional[List[ThinkingStep]] = None
    ragSources: Optional[List[str]] = None
    attachedFileIds: Optional[List[str]] = None
    retrievedChunkIds: Optional[List[str]] = None
    isStreaming: Optional[bool] = False
    tokensConsumed: Optional[int] = 0


# 用户相关类型
class UserBase(BaseModel):
    username: str
    email: str
    role: str = "user"


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class TempUserCreate(BaseModel):
    registration_ip: str


class UserResponse(UserBase):
    id: str
    tokenQuota: int
    tokensUsed: int
    requestCount: int
    lastRequestAt: Optional[int] = None
    createdAt: int
    registrationIp: str
    isTemp: bool = False  # 替换isAnonymous为isTemp
    expiresAt: Optional[int] = None  # 临时用户过期时间

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# 会话相关类型
class ChatSessionBase(BaseModel):
    title: str
    personalLibraryEnabled: bool = True


class ChatSessionCreate(ChatSessionBase):
    pass


class ChatSessionResponse(ChatSessionBase):
    id: str
    createdAt: int
    lastActive: int
    activeFileIds: List[str] = []
    messages: List[Message] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# API请求/响应类型
class ChatRequest(BaseModel):
    message: str
    threadId: Optional[str] = "default"
    personalContext: List[str] = []
    retrievedChunks: List[VectorChunk] = []
    sessionHistory: List[Message] = []


class SendCodeRequest(BaseModel):
    email: str


class VerifyRegisterRequest(BaseModel):
    email: str
    code: str
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class SessionCreate(BaseModel):
    title: str


class StanceCreate(BaseModel):
    view: str
    sourceMessageId: str


# 使用统计
class UsageRecord(BaseModel):
    userId: str
    tokens: int
    timestamp: Optional[int] = None


# 文件相关
class FileUploadResponse(BaseModel):
    fileId: str
    name: str
    chunks: List[str]
    indexed: bool


class VectorSearchRequest(BaseModel):
    query: str
    fileIds: List[str]
    limit: int = 3


# 配额检查
class QuotaCheckResponse(BaseModel):
    allowed: bool
    reason: Optional[str] = None
