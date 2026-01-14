from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.schema.models import ChatRequest
from app.agents.gemini_engine import (
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
            request.message, request.personalContext, request.retrievedChunks
        ),
        media_type="text/event-stream",
    )


@app.post("/extract-stance")
async def extract_stance_endpoint(payload: dict):
    message = payload.get("message", "")
    stance = await extract_philosophical_stance(message)
    return {"stance": stance}


@app.get("/health")
async def health_check():
    return {"status": "active"}
