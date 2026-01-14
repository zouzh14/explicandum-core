from pydantic import BaseModel, Field
from typing import List, Optional, Union, Dict
from enum import Enum


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


class ChatRequest(BaseModel):
    message: str
    threadId: Optional[str] = "default"
    personalContext: List[str] = []
    retrievedChunks: List[VectorChunk] = []
    sessionHistory: List[Message] = []
