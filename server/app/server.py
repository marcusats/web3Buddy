import os
import sys

# Get the current working directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add the main directory to the Python path
sys.path.append(os.path.dirname(current_dir))

# Add the utils package to the Python path
utils_dir = os.path.join(os.path.dirname(current_dir), 'utils')
sys.path.append(utils_dir)

from typing import Callable
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from typing import List, Any, Union, Dict
from utils.grader import GraderUtils
from utils.graph import GraphState
from utils.generate_chain import create_generate_chain
from utils.nodes import GraphNodes
from utils.edges import EdgeGraph
from utils.pinecone_store import PineconeRetriever
from utils.chatHistoryManager import ChatHistoryManager
from langgraph.graph import END, StateGraph
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated
from fastapi.responses import RedirectResponse
from langserve import add_routes
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from IPython.display import display, Image
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())  # important line if cannot load API key

## Getting the API keys from the .env file

# Initialize PineconeRetriever
pinecone_retriever = PineconeRetriever(
    pinecone_api_key=os.getenv("PINECONE_API_KEY"),
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    index_name="web3-api-index",
    namespace="infura-docs"
)

redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")

## LLM model
llm = ChatOpenAI(model="gpt-4o", temperature=0)

# Create the generate chain
generate_chain = create_generate_chain(llm)

## Get the grader instances
# Create an instance of the GraderUtils class
grader = GraderUtils(llm)

# Get the retrieval grader
retrieval_grader = grader.create_retrieval_grader()

# Get the hallucination grader
hallucination_grader = grader.create_hallucination_grader()

# Get the code evaluator
code_evaluator = grader.create_code_evaluator()

# Get the question rewriter
question_rewriter = grader.create_question_rewriter()

action_evaluator = grader.create_action_evaluator()

execute_evaluator = grader.create_execution_evaluator()

## Creating the Workflow
# Initiating the Graph
workflow = StateGraph(GraphState)

chat_history_manager = ChatHistoryManager(redis_url, redis_token)

memory = MemorySaver()

save_message = chat_history_manager.save_message
get_all_messages = chat_history_manager.get_all_messages
# Create an instance of the GraphNodes class with the new chat method
graph_nodes = GraphNodes(
    llm, pinecone_retriever, retrieval_grader, hallucination_grader, code_evaluator, question_rewriter,
    save_message, get_all_messages
)

# Create an instance of the EdgeGraph class
edge_graph = EdgeGraph(hallucination_grader, code_evaluator, action_evaluator, execute_evaluator)

workflow.add_node("retrieveInfura", graph_nodes.retrieveInfura)  # retrieve documents for Infura
workflow.add_node("retrieveSolidity", graph_nodes.retrieveSolidity)  # retrieve documents for Solidity
workflow.add_node("grade_documents", graph_nodes.grade_documents)  # grade documents
workflow.add_node("generate", graph_nodes.generate)  # generate answers
workflow.add_node("transform_query", graph_nodes.transform_query)
workflow.add_node("evaluator", graph_nodes.rewrite_question)
workflow.add_node("chat", graph_nodes.chat)  # Chat interaction
workflow.add_node("transform_execution", graph_nodes.transform_execution)  # Transform to cURL command
workflow.add_node("execution", graph_nodes.execution)  # Execute cURL command
workflow.add_node("path_to_execution", graph_nodes.path_to_execution)  # Guide to execution
workflow.add_node("command_interpreter", graph_nodes.execution_interpreter)  # Interpret the command
workflow.add_node("ending", graph_nodes.ending)  # End the conversation

workflow.set_entry_point("evaluator")

workflow.add_conditional_edges(
    "evaluator",
    edge_graph.action_first,  # Check if the tool used is the LLM
    {
        "infura": "retrieveInfura",  # Continue with the Infura tool
        "solidity": "retrieveSolidity",  # Continue with the Solidity tool
        "chat": "chat",  # End the conversation
    },
)

workflow.add_edge("ending", END)
workflow.add_edge("chat", "ending")


workflow.add_edge("retrieveInfura", "grade_documents")
workflow.add_edge("retrieveSolidity", "grade_documents")
workflow.add_conditional_edges(
    "grade_documents",
    edge_graph.decide_to_generate,
    {
        "transform_query": "transform_query",
        "generate": "generate",
    },
)

workflow.add_conditional_edges(
    "transform_query",
    edge_graph.tool_direction,
    {
        "infura": "retrieveInfura",
        "solidity": "retrieveSolidity",
    },
)
workflow.add_conditional_edges(
    "generate",
    edge_graph.grade_generation_v_documents_and_question,
    {
        "not supported": "generate",
        "useful": "path_to_execution",
        "not useful": "transform_query",
    },
)

workflow.add_conditional_edges(
    "path_to_execution",
    edge_graph.decide_to_execute,
    {
        "execute": "transform_execution",
        "no-execute": "ending",
    },
)

workflow.add_edge("transform_execution", "execution")
workflow.add_edge("execution", "command_interpreter")
workflow.add_edge("command_interpreter", "ending")

# Compile the workflow
chain = workflow.compile()

output_folder = os.path.join(current_dir, 'output')
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Define the image file name and full path
image_file = os.path.join(output_folder, 'workflow_image.png')

# Generate the image and save it to the specified path
workflow_image = chain.get_graph().draw_mermaid_png()

# Save the image to the file
with open(image_file, 'wb') as f:
    f.write(workflow_image)

print(f"Workflow image saved at {image_file}")

async def check_authentication(userId: str):
    if not userId or userId not in app.state.sessions or not app.state.sessions[userId].get("is_authenticated"):
        raise HTTPException(status_code=403, detail="User not authenticated")
    return userId

app = FastAPI(
    title="Web3Buddy",
    version="1.0",
    description="An API server that answers questions regarding Web3 technology and assists in navigating Web3 and its technology"
)

# Enable CORS for handling cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to allow specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.sessions = {}

class User(BaseModel):
    userId: str

# Input and Output for the chat route
class Input(BaseModel):
    input: str

class Output(BaseModel):
    output: dict

class ConversationKeysResponse(BaseModel):
    conversation_keys: List[str]

# Define a response model for the messages
class ConversationMessagesResponse(BaseModel):
    messages: List[dict]

@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")

@app.middleware("http")
async def extract_user_id_middleware(request: Request, call_next: Callable):
    # Skip authentication check for OPTIONS requests (commonly used for CORS preflight)
    if request.method == "OPTIONS":
        return await call_next(request)

    # Expect the userId header in the request
    user_id = request.headers.get("user_id")
    conv_id = request.headers.get("conv_id")
    print("---------Header Response----------")
    print(f"User ID: {user_id}")
    print(f"Conversation ID: {conv_id}")
    if not user_id:
        raise HTTPException(status_code=403, detail="User ID header missing")

    # Save user_id in request.state so it can be accessed in route handlers
    request.state.user_id = user_id


    graph_nodes.saveChatInfo(user_id, conv_id)

    # Proceed with the request
    return await call_next(request)

@app.get("/conversations/{user_id}", response_model=ConversationKeysResponse)
async def retrieve_conversation_keys_route(user_id: str):
    """
    Retrieve all conversation keys for a specific user.
    
    Args:
        user_id (str): The ID of the user.

    Returns:
        ConversationKeysResponse: A list of conversation keys for the user.
    """
    conversation_keys = chat_history_manager.retrieve_conversation_keys(user_id)
    if not conversation_keys:
        raise HTTPException(status_code=404, detail="No conversation keys found for the user.")
    
    return {"conversation_keys": conversation_keys}


@app.get("/conversations/{user_id}/{conversation_id}", response_model=ConversationMessagesResponse)
async def get_all_messages_route(user_id: str, conversation_id: str):
    """
    Retrieve all messages from a specific conversation for a user.

    Args:
        user_id (str): The ID of the user.
        conversation_id (str): The ID of the conversation.

    Returns:
        ConversationMessagesResponse: A list of all messages for the specified conversation.
    """
    messages = chat_history_manager.get_all_messages(user_id, conversation_id)
    if not messages:
        raise HTTPException(status_code=404, detail="No messages found for this conversation.")
    
    return {"messages": messages}


# Add workflow routes to FastAPI using the chain
add_routes(
    app,
    chain.with_types(input_type=Input, output_type=Output),
    path="/web3buddy_chat"
)


# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
