from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.schema.models import ChatRequest
from app.agents.graph_engine import (
    stream_explicandum_response,
    extract_philosophical_stance,
)
import json

app = FastAPI(title="Explicandum Brain API")

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
