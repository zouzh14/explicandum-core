import json
from typing import List, AsyncGenerator
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from app.core.config import settings
from app.agents.state import AgentState
from app.agents.prompts import SYSTEM_PROMPT


# Helper to extract text from LangChain message content
def extract_text_from_content(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict) and "text" in part:
                text_parts.append(part["text"])
        return "".join(text_parts)
    return str(content)


# Models
# Use DeepSeek (via OpenAI compatible API) for Logic if key is available, else fallback to Gemini
if settings.DEEPSEEK_API_KEY:
    logic_model = ChatOpenAI(
        model="deepseek-chat",
        api_key=settings.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
    )
    philosophy_model = ChatOpenAI(
        model="deepseek-chat",
        api_key=settings.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
    )
    stance_model = ChatOpenAI(
        model="deepseek-chat",
        api_key=settings.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
    )
else:
    logic_model = ChatGoogleGenerativeAI(
        model="gemini-3-flash-preview", google_api_key=settings.GEMINI_API_KEY
    )
    philosophy_model = ChatGoogleGenerativeAI(
        model="gemini-3-flash-preview", google_api_key=settings.GEMINI_API_KEY
    )
    stance_model = ChatGoogleGenerativeAI(
        model="gemini-3-flash-preview", google_api_key=settings.GEMINI_API_KEY
    )


# Nodes
async def logic_analyst_node(state: AgentState):
    context = ""
    if state["retrieved_chunks"]:
        context = "\n".join(
            [
                f"SOURCE: {c.fileName}\nCONTENT: {c.content}"
                for c in state["retrieved_chunks"]
            ]
        )

    prompt = f"""You are the Logic Analyst (LOGIC_ANALYST). 
Decompose the logical structure of the following message, identifying premises, conclusions, and any fallacies.
Use the provided context if relevant.

CONTEXT:
{context}

USER MESSAGE:
{state["message"]}
"""
    response = await logic_model.ainvoke([HumanMessage(content=prompt)])
    return {"logic_analysis": extract_text_from_content(response.content)}


async def philosophy_expert_node(state: AgentState):
    personal_philosophy = "\n".join(state["personal_context"])
    prompt = f"""You are the Philosophy Expert (PHILOSOPHY_EXPERT).
Link the following topic to epistemology, ontology, or the philosophy of science.
Check for alignment with the user's personal philosophy library.

PERSONAL PHILOSOPHY:
{personal_philosophy}

USER MESSAGE:
{state["message"]}
"""
    response = await philosophy_model.ainvoke([HumanMessage(content=prompt)])
    return {"philosophy_analysis": extract_text_from_content(response.content)}


async def consolidator_node(state: AgentState):
    prompt = f"""You are the Explicandum Backend. Consolidate the analysis from the Logic Analyst and the Philosophy Expert into a final response.
Maintain the required format:
<logic_thinking>{state["logic_analysis"]}</logic_thinking>
<philosophy_thinking>{state["philosophy_analysis"]}</philosophy_thinking>
Final Answer: [Your consolidated response]

USER MESSAGE:
{state["message"]}
"""
    response = await philosophy_model.ainvoke([HumanMessage(content=prompt)])
    return {"final_response": extract_text_from_content(response.content)}


# Workflow Construction
workflow = StateGraph(AgentState)

workflow.add_node("logic_analyst", logic_analyst_node)
workflow.add_node("philosophy_expert", philosophy_expert_node)
workflow.add_node("consolidator", consolidator_node)

workflow.set_entry_point("logic_analyst")
workflow.add_edge("logic_analyst", "philosophy_expert")
workflow.add_edge("philosophy_expert", "consolidator")
workflow.add_edge("consolidator", END)


async def stream_explicandum_response(
    message: str,
    personal_context: List[str],
    retrieved_chunks: List[any],
    thread_id: str = "default",
) -> AsyncGenerator[str, None]:
    # We use a context manager for the SQLite checkpointer to ensure it's closed properly
    # In a production app, you might want to manage this connection more globally
    async with AsyncSqliteSaver.from_conn_string(
        "explicandum_sessions.db"
    ) as checkpointer:
        app_graph = workflow.compile(checkpointer=checkpointer)

        inputs = {
            "message": message,
            "personal_context": personal_context,
            "retrieved_chunks": retrieved_chunks,
        }

        config = {"configurable": {"thread_id": thread_id}}

        # Invoke the graph with the thread_id config for persistence
        result = await app_graph.ainvoke(inputs, config=config)
    final_text = result["final_response"]

    # Simulate streaming for the frontend
    chunk_size = 20
    for i in range(0, len(final_text), chunk_size):
        yield final_text[i : i + chunk_size]


async def extract_philosophical_stance(message: str) -> str:
    prompt = f"""Identify if the following user message expresses a core philosophical stance, belief, or value. If so, summarize it as a single concise first-person statement. If no philosophical stance is expressed, return ONLY the word "NONE".
      
      Message: "{message}" """

    response = await stance_model.ainvoke([HumanMessage(content=prompt)])
    text = extract_text_from_content(response.content).strip()
    return None if text == "NONE" else text
