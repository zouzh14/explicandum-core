from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.schema.models import ChatRequest, SendCodeRequest, VerifyRegisterRequest
from app.agents.graph_engine import (
    stream_explicandum_response,
    extract_philosophical_stance,
)
import json
import random
import resend
import os
from datetime import datetime, timedelta
from app.core.config import settings

app = FastAPI(title="Explicandum Brain API")

# Initialize Resend
resend.api_key = settings.RESEND_API_KEY

# Temporary in-memory store for verification codes (Use Redis in production)
# Structure: { email: {"code": "123456", "expires": datetime} }
verification_store = {}


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
async def send_code(request: SendCodeRequest):
    email = request.email
    code = f"{random.randint(100000, 999999)}"
    expires = datetime.now() + timedelta(minutes=5)
    verification_store[email] = {"code": code, "expires": expires}

    # Extract domain from email to use in sender (or use a fixed one if configured)
    # Recommended to use something like: verification@yourdomain.com
    sender_domain = settings.MAIL_DOMAIN

    try:
        resend.Emails.send(
            {
                "from": f"Explicandum System <verification@{sender_domain}>",
                "to": email,
                "subject": f"{code} is your Explicandum verification code",
                "html": f"""
                <div style="font-family: sans-serif; padding: 20px; color: #18181b;">
                    <h2 style="color: #18181b;">Verification Code</h2>
                    <p>Your verification code for Explicandum is:</p>
                    <div style="background: #f4f4f5; padding: 15px; font-size: 24px; font-weight: bold; letter-spacing: 5px; text-align: center; border-radius: 10px;">
                        {code}
                    </div>
                    <p style="font-size: 12px; color: #71717a; margin-top: 20px;">This code will expire in 5 minutes.</p>
                </div>
            """,
            }
        )
        return {"status": "success", "message": "Code sent"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/auth/verify-register")
async def verify_register(request: VerifyRegisterRequest):
    email = request.email
    stored = verification_store.get(email)

    if not stored:
        return {"status": "error", "message": "No code found for this email"}

    if datetime.now() > stored["expires"]:
        return {"status": "error", "message": "Code expired"}

    if request.code != stored["code"]:
        return {"status": "error", "message": "Invalid code"}

    # Assign quota based on academic status
    is_edu = is_academic(email)
    quota = 500000 if is_edu else 100000
    role = "researcher" if is_edu else "user"

    # In a real app, you'd save this to a DB.
    # For now, we return the calculated user data so the frontend can save it.
    new_user_data = {
        "id": f"usr_{int(datetime.now().timestamp())}",
        "username": request.username,
        "role": role,
        "email": email,
        "tokenQuota": quota,
        "isVerified": True,
    }

    # Clean up
    del verification_store[email]

    return {"status": "success", "user": new_user_data}
