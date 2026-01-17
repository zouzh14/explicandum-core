from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.schema.models import (
    ChatRequest,
    SendCodeRequest,
    VerifyRegisterRequest,
    LoginRequest,
    SessionCreate,
    StanceCreate,
    UserResponse,
    ChatSessionResponse,
    PhilosophicalStance,
    TempUserCreate,
)
from app.agents.graph_engine import (
    stream_explicandum_response,
    extract_philosophical_stance,
)
from app.database import models, base
from app.core import auth
from app.api.monitoring import router as monitoring_router
from app.services.email_service import email_service
import json
import random
import os
import uuid
from datetime import datetime, timedelta
from app.core.config import settings
import traceback

# Create database tables
models.Base.metadata.create_all(bind=base.engine)

app = FastAPI(title="Explicandum Brain API")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # Log the exception
    print(f"Unhandled exception: {exc}")
    traceback.print_exc()

    # Return a generic error response
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Internal server error. Please try again later.",
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    # Log the database error
    print(f"Database error: {exc}")

    # Return a generic error response
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Database error occurred. Please try again.",
        },
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    # Log the integrity error
    print(f"Integrity error: {exc}")

    # Try to extract more specific error message
    error_msg = str(exc.orig) if hasattr(exc, "orig") else "Database integrity error"

    # Check for common integrity errors
    if "UNIQUE constraint failed" in error_msg or "duplicate key" in error_msg:
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "Data conflict. The record may already exist.",
            },
        )

    return JSONResponse(
        status_code=400,
        content={
            "status": "error",
            "message": "Data validation error. Please check your input.",
        },
    )


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(base.get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = auth.decode_access_token(token)
    if payload is None:
        raise credentials_exception
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


# Initialize Resend (removed - now handled by unified email service)

# Database-backed verification codes


def is_academic(email: str) -> bool:
    academic_suffixes = [
        ".edu",
        ".edu.cn",
        ".ac.uk",
        ".org",
        ".org.cn",
        ".ac.cn",
        ".cas.cn",
        ".edu.au",
        ".edu.sg",
        ".edu.my",
        ".edu.hk",
        ".edu.mo",
        ".edu.tw",
        ".ac.jp",
        ".ac.kr",
        ".ac.in",
        ".res.in",
        ".edu.br",
        ".edu.tr",
        ".edu.za",
    ]
    return any(email.lower().endswith(s) for s in academic_suffixes)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include monitoring router
app.include_router(monitoring_router, tags=["monitoring"])


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    return StreamingResponse(
        stream_explicandum_response(
            request.message,
            request.personalContext,
            request.retrievedChunks,
            request.threadId,
        ),
        media_type="text/event-stream",
    )


@app.post("/extract-stance")
async def extract_stance_endpoint(payload: dict):
    message = payload.get("message", "")
    stance = await extract_philosophical_stance(message)
    return {"stance": stance}


@app.delete("/stances/{stance_id}")
async def delete_stance_endpoint(stance_id: str):
    # Currently, stances are primarily managed in the frontend's localStorage.
    # This endpoint provides a hook for future backend-side cleanup if a
    # persistent database for individual stances is implemented.
    return {"status": "success", "deleted_id": stance_id}


@app.delete("/sessions/{session_id}")
async def delete_session_endpoint(session_id: str):
    # This provides a hook to clean up session data in the future.
    # For LangGraph checkpoints, it would involve deleting records from
    # the sqlite database for the given thread_id.
    return {"status": "success", "deleted_id": session_id}


@app.get("/health")
async def health_check():
    return {"status": "active"}


@app.post("/auth/send-code")
async def send_code(request: SendCodeRequest, db: Session = Depends(base.get_db)):
    email = request.email
    code = f"{random.randint(100000, 999999)}"
    expires_at = datetime.now() + timedelta(minutes=5)

    # Clean up expired codes for this email
    db.query(models.VerificationCode).filter(
        models.VerificationCode.email == email,
        models.VerificationCode.expires_at < datetime.now(),
    ).delete(synchronize_session=False)

    # Create new verification code
    db_code = models.VerificationCode(
        email=email, code=code, expires_at=expires_at, is_used=False
    )
    db.add(db_code)
    db.commit()

    # Extract domain from email to use in sender (or use a fixed one if configured)
    # Recommended to use something like: verification@yourdomain.com
    sender_domain = settings.MAIL_DOMAIN

    # Check if we should skip actual email sending (for testing)
    if settings.SKIP_EMAIL_SENDING:
        # In test mode, log the code instead of sending email
        print(f"TEST MODE: Verification code for {email}: {code}")
        return {
            "status": "success",
            "message": "Code generated (test mode)",
            "test_code": code,  # Include code in response for testing
        }

    try:
        # Use unified email service
        result = await email_service.send_verification_code(email, code)

        if result["status"] == "error":
            # Rollback the database insertion if email sending fails
            db.rollback()
            return result

        return result
    except Exception as e:
        # Rollback the database insertion if email sending fails
        db.rollback()
        return {"status": "error", "message": f"Failed to send email: {str(e)}"}


@app.post("/auth/login")
async def login(request: LoginRequest, db: Session = Depends(base.get_db)):
    user = (
        db.query(models.User).filter(models.User.username == request.username).first()
    )
    if not user or not auth.verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token = auth.create_access_token(data={"sub": user.username})

    # 使用UserResponse类型，确保字段名一致
    user_response = UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        tokenQuota=user.token_quota,
        tokensUsed=user.tokens_used,
        requestCount=user.request_count,
        lastRequestAt=int(user.last_request_at.timestamp() * 1000)
        if user.last_request_at
        else None,
        createdAt=int(user.created_at.timestamp() * 1000),
        registrationIp=user.registration_ip or "unknown",
        isTemp=user.is_temp,
        expiresAt=int(user.expires_at.timestamp() * 1000) if user.expires_at else None,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_response.model_dump(),
    }


@app.post("/auth/verify-register")
async def verify_register(
    request: VerifyRegisterRequest, db: Session = Depends(base.get_db)
):
    email = request.email

    # Find the latest valid verification code for this email
    db_code = (
        db.query(models.VerificationCode)
        .filter(
            models.VerificationCode.email == email,
            models.VerificationCode.expires_at > datetime.now(),
            models.VerificationCode.is_used == False,
        )
        .order_by(models.VerificationCode.created_at.desc())
        .first()
    )

    if not db_code:
        return {"status": "error", "message": "No valid code found for this email"}

    if request.code != db_code.code:
        return {"status": "error", "message": "Invalid code"}

    # Check if username or email already exists
    existing_user = (
        db.query(models.User)
        .filter(
            (models.User.username == request.username) | (models.User.email == email)
        )
        .first()
    )

    if existing_user:
        if existing_user.username == request.username:
            return {"status": "error", "message": "Username already exists"}
        else:
            return {"status": "error", "message": "Email already registered"}

    # Assign quota based on academic status
    is_edu = is_academic(email)
    quota = 500000 if is_edu else 100000
    role = "researcher" if is_edu else "user"

    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    db_user = models.User(
        id=user_id,
        username=request.username,
        email=email,
        hashed_password=auth.get_password_hash(request.password),
        role=role,
        token_quota=quota,
        registration_ip="unknown",  # Could be improved by getting from request
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Mark verification code as used
    db_code.is_used = True
    db.commit()

    access_token = auth.create_access_token(data={"sub": db_user.username})

    # 使用UserResponse类型，确保字段名一致
    user_response = UserResponse(
        id=db_user.id,
        username=db_user.username,
        email=db_user.email,
        role=db_user.role,
        tokenQuota=db_user.token_quota,
        tokensUsed=db_user.tokens_used,
        requestCount=db_user.request_count,
        lastRequestAt=int(db_user.last_request_at.timestamp() * 1000)
        if db_user.last_request_at
        else None,
        createdAt=int(db_user.created_at.timestamp() * 1000),
        registrationIp=db_user.registration_ip or "unknown",
        isTemp=db_user.is_temp,
        expiresAt=int(db_user.expires_at.timestamp() * 1000)
        if db_user.expires_at
        else None,
    )

    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_response.model_dump(),
        "isVerified": True,
    }


@app.post("/test-email")
async def test_email_endpoint():
    """Test email endpoint for debugging"""
    try:
        result = await email_service.send_test_email("basic")
        return {
            "status": "success" if result else "error",
            "message": "Test email sent successfully"
            if result
            else "Failed to send test email",
            "email_config": email_service.get_email_status(),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error sending test email: {str(e)}",
            "email_config": email_service.get_email_status(),
        }


@app.post("/auth/create-temp")
async def create_temp_user(request: TempUserCreate, db: Session = Depends(base.get_db)):
    """创建临时用户"""
    # 生成唯一的临时用户名
    temp_id = f"temp_{uuid.uuid4().hex[:8]}"
    username = f"Guest_{temp_id[-4:]}"

    # 检查是否已存在相同IP的临时用户（可选限制）
    # 这里可以添加IP限制逻辑

    # 创建临时用户
    user_id = f"usr_{uuid.uuid4().hex[:8]}"
    db_user = models.User(
        id=user_id,
        username=username,
        email=None,  # 临时用户没有邮箱
        hashed_password=None,  # 临时用户没有密码
        role="temp",
        is_temp=True,
        expires_at=datetime.now() + timedelta(days=30),  # 30天后过期
        upgrade_token=uuid.uuid4().hex[:16],  # 生成升级token
        token_quota=20000,  # 临时用户配额20,000 tokens
        registration_ip=request.registration_ip or "unknown",
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    access_token = auth.create_access_token(data={"sub": db_user.username})

    # 使用UserResponse类型，确保字段名一致
    user_response = UserResponse(
        id=db_user.id,
        username=db_user.username,
        email=db_user.email or "",
        role=db_user.role,
        tokenQuota=db_user.token_quota,
        tokensUsed=db_user.tokens_used,
        requestCount=db_user.request_count,
        lastRequestAt=int(db_user.last_request_at.timestamp() * 1000)
        if db_user.last_request_at
        else None,
        createdAt=int(db_user.created_at.timestamp() * 1000),
        registrationIp=db_user.registration_ip or "unknown",
        isTemp=db_user.is_temp,
        expiresAt=int(db_user.expires_at.timestamp() * 1000)
        if db_user.expires_at
        else None,
    )

    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_response.model_dump(),
        "upgrade_token": db_user.upgrade_token,
    }


@app.get("/sessions")
async def get_sessions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(base.get_db),
):
    sessions = (
        db.query(models.ChatSession)
        .filter(models.ChatSession.user_id == current_user.id)
        .order_by(models.ChatSession.last_active.desc())
        .all()
    )

    session_responses = []
    for s in sessions:
        # 构建消息列表
        messages = []
        for m in s.messages:
            messages.append(
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "tokensConsumed": m.tokens_consumed,
                }
            )

        # 使用ChatSessionResponse类型
        session_response = ChatSessionResponse(
            id=s.id,
            title=s.title,
            createdAt=int(s.created_at.timestamp() * 1000),
            lastActive=int(s.last_active.timestamp() * 1000),
            personalLibraryEnabled=s.personal_library_enabled,
            activeFileIds=[],  # To be implemented with File models
            messages=messages,
        )
        session_responses.append(session_response.model_dump())

    return session_responses


@app.post("/sessions")
async def create_session(
    request: SessionCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(base.get_db),
):
    session_id = f"s_{uuid.uuid4().hex[:8]}"
    db_session = models.ChatSession(
        id=session_id, title=request.title, user_id=current_user.id
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return {"id": db_session.id, "title": db_session.title}


@app.get("/stances")
async def get_stances(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(base.get_db),
):
    stances = (
        db.query(models.PhilosophicalStance)
        .filter(models.PhilosophicalStance.user_id == current_user.id)
        .all()
    )

    stance_responses = []
    for s in stances:
        stance_response = PhilosophicalStance(
            id=s.id,
            view=s.view,
            sourceMessageId=s.source_message_id,
            timestamp=int(s.created_at.timestamp() * 1000),
        )
        stance_responses.append(stance_response.model_dump())

    return stance_responses


@app.post("/stances")
async def create_stance(
    request: StanceCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(base.get_db),
):
    stance_id = f"st_{uuid.uuid4().hex[:8]}"
    db_stance = models.PhilosophicalStance(
        id=stance_id,
        user_id=current_user.id,
        view=request.view,
        source_message_id=request.sourceMessageId,
    )
    db.add(db_stance)
    db.commit()
    return {"id": db_stance.id}
