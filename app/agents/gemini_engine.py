import google.generativeai as genai
from app.core.config import settings
from app.agents.prompts import SYSTEM_PROMPT
from app.schema.models import VectorChunk
from typing import List, AsyncGenerator

genai.configure(api_key=settings.GEMINI_API_KEY)


async def stream_explicandum_response(
    message: str, personal_context: List[str], retrieved_chunks: List[VectorChunk]
) -> AsyncGenerator[str, None]:
    model = genai.GenerativeModel(
        model_name="gemini-1.5-pro",  # Using a stable version
        system_instruction=SYSTEM_PROMPT,
    )

    extended_context = ""
    if personal_context:
        extended_context += (
            f"\n\n[USER PERSONAL PHILOSOPHY LIBRARY]:\n{chr(10).join(personal_context)}"
        )

    if retrieved_chunks:
        fragments = [
            f"SOURCE: {c.fileName} (Part {c.index})\nCONTENT: {c.content}"
            for c in retrieved_chunks
        ]
        extended_context += (
            f"\n\n[RETRIEVED DOCUMENT FRAGMENTS (RAG)]:\n{chr(10).join(fragments)}"
        )

    response = await model.generate_content_async(
        message + extended_context, stream=True
    )

    async for chunk in response:
        if chunk.text:
            yield chunk.text


async def extract_philosophical_stance(message: str) -> str:
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = f"""Identify if the following user message expresses a core philosophical stance, belief, or value. If so, summarize it as a single concise first-person statement. If no philosophical stance is expressed, return ONLY the word "NONE".
      
      Message: "{message}" """

    response = await model.generate_content_async(prompt)
    text = response.text.strip()
    return None if text == "NONE" else text
