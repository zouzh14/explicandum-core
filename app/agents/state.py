import operator
from typing import TypedDict, List, Optional, Annotated
from app.schema.models import VectorChunk


class AgentState(TypedDict):
    # Inputs
    message: str
    personal_context: List[str]
    retrieved_chunks: List[VectorChunk]

    # Intermediate outputs
    logic_analysis: str
    philosophy_analysis: str

    # Final output
    final_response: str
