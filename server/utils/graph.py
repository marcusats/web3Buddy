## Start the Graph
from typing_extensions import TypedDict
from typing import TypedDict, Annotated, Sequence, List
from langchain_core.messages import BaseMessage

class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        generation: LLM generation
        documents: list of documents
        chat_history: chat history
        api_call_count: count of API calls
    """

    input: str
    userId: str
    convId: str
    generation: str
    documents: List[str]  
    chat_history: List[BaseMessage]   
    vector_store_namespace: str