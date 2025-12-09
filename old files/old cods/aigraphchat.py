from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AnyMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from typing_extensions import Annotated, TypedDict
import operator

from langchain.agents import create_agent
from langchain.tools import tool

from utils.vector import retrive

from dotenv import load_dotenv
load_dotenv()

collection_name = "uploaded_documents"


@tool
def data_retriever(user_request: str):
    """
    Retrieves existing content from vector DB based on user request.

    Args:
        user_request: The search query.

    Returns:
        str: Retrieved content or error message.
    """
    print("data_retriever\n"*5)
    print("user_request:\n", user_request)
    print()
    try:
        existing_content = retrive(user_request, collection_name=collection_name)
        return existing_content
    
    except:
        return "❌ Error retrieving content"
    
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a {role} that answers about {topic}."),
    ("human", "{question}")
])

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

# Initialize LLM (set your API key)
model = ChatGoogleGenerativeAI(model="gemini-2.5-flash").bind_tools([data_retriever])



def agent(state: State):
    """Single agent node calls LLM with conversation history"""
    # Pass system prompt + all messages
    response = model.invoke(state["messages"])
    return {"messages": [response]}

# Build graph
workflow = StateGraph(State)
workflow.add_node("agent", agent)

# Add edges: START -> agent -> END (single pass, or loop with tools)
workflow.add_edge(START, "agent")
workflow.add_edge("agent", END)

# Compile graph
app = workflow.compile()

# Chat with the agent
config = {"configurable": {"thread_id": "1"}}  # Optional: persist across calls
input_message = HumanMessage(content="Hello! What's 15 * 3?")

result = app.invoke({"messages": [input_message]}, config)
print(result["messages"][-1].content)  # Prints: "45"