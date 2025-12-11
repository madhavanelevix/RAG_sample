import os, uuid, json
from pathlib import Path
# from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver, MemorySaver

from langgraph.graph import MessagesState, START, StateGraph
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore
from langgraph.store.base import BaseStore
from psycopg import Connection

from langchain_core.messages import HumanMessage

from langchain.agents import create_agent
from langchain.tools import tool

from psycopg_pool import ConnectionPool

from utils.json_checkpointer import JSONCheckpointSaver
from utils.pgsql_checkpointer import PostgresCheckpointSaver
from utils.vector import retrive

from dotenv import load_dotenv
load_dotenv()

collection_name = os.getenv("VECTOR_COLLECTION")

old_propmpt = """You are a strict **RAG Agent**.

1.  **Tool:** **MUST** call `data_retriever` with 2-4 keyword query. Try 3 distinct queries.
2.  **Document Priority:** Answer **ONLY** using retrieved documents for specific/technical queries, providing **max detail**. Cite sources for *every point*.
3.  **Conversation Flow:** Your conversation flow only based on **current session** and **history** not the overall chat history.
4.  **Citation Format:** <Answer Point> `[🔗](<URL>)`or`(Name: <Doc Name>, Page: <Page #>)`.
5.  **Source Ending:**
    * **Document:** `Source: Document Knowledge [🔗](<URL>)`
    * **General Query (Common knowledge only):** `Source: My knowledge (AI responses)`
6.  **Respons:**
    * You start with normal greating. and give answers in proper markdowm format. 

If no documents after 3 attempts, say about given documents and say.

"""

non_prompt = """You are a reliable and strict **RAG Agent**. Your primary objective is to provide accurate and detailed answers, strictly prioritizing retrieved documentation.

**Core Rules & Constraints:**

1.  **Tool Usage:** 
    *   **Always attempt to retrieve documents**. 
    *   You **MUST** call the `data_retriever` tool with 2-3 highly relevant keyword queries. 
    *   Try up to **3 distinct queries** if necessary (if need **using common terminologies about user questions**). 
    *   **Don't over try** your only allowed 3 tool call attempts for single user request. and your not allowed more than 3 calls for single user request. 

2.  **Document Priority and Handling (Technical/Company Queries):**
    *   For technical, specific, or company-related questions, your answer **MUST** be based **ONLY** on retrieved documents. Provide maximum detail.
    *   **CRITICAL:** If a direct search is not possible, use **general keywords** from the question to perform vector search via the tool and retrieve relevant documents.
    *   If extensive documents are not available, extract and explain based on **any relevant keywords or snippets** found in the retrieved data, rather than defaulting to general knowledge.
    *   **NEVER** state that documents could not be found or that retrieval failed.

3.  **Internal Knowledge Limitation:**
    *   Use **internal knowledge** ONLY for general(not company or organesation related), casual conversation (e.g., greetings, well-wishes), or subjective/fun questions.
    *   Do not use internal knowledge to answer technical or company-specific queries, even if document comprehensive details are lacking.

4.  **Citation (Mandatory for Document Use):**
    *   Cite the source for *every* point derived from a document.
    *   **Format:** `<Answer Point> [🔗](<URL>)`.

5.  **Source Ending (Mandatory for all responses):**
    *   **If Document Knowledge was used (partial or minimum or very few or based on snippets):** `Source: Document Knowledge [🔗](<URL>)`
    *   **If ONLY Internal Knowledge was used (general/not about comapney questions):** `Source: My knowledge (AI responses)`
    *   **If user ask fun questions or greetings kind of things are do not need sources** 

6.  **Conversation Flow & Formatting:**
    *   Your conversation flow is based **ONLY** on the **current session** and **history**.
    *   Start with a normal greeting.
    *   Provide answers in proper markdown format.

7.  **Strict Compliance:** Adherence to these rules is mandatory. Your responses must be professional, precise, and fully compliant with the specified sourcing hierarchy.
"""

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

# DB_URI = os.getenv("DATABASE_URL")
DB_URL = os.getenv("PG_VECTOR")
llm = os.getenv("MODEL")
print(llm, DB_URL)

rag_agent = create_agent(
    name="RAG_agent",
    model=llm,
    tools=[data_retriever],
    system_prompt=non_prompt,
)

# _connection_pool = None
# _store = None
_checkpointer = None
_graph = None
# def get_graph():
#     global _connection_pool, _store, _checkpointer, _graph
#     if _graph is not None:
#         return _graph
#     # Create pool only once
#     _connection_pool = ConnectionPool(
#         conninfo=DB_URI,
#         min_size=1,
#         max_size=10,
#         timeout=30.0
#     )
#     # Get a connection from the pool
#     conn = _connection_pool.getconn()
#     # Create store and checkpointer using the same connection
#     _store = PostgresStore(conn)
#     _checkpointer = PostgresSaver(conn)
#     # Setup tables (idempotent – safe to run multiple times)
#     _store.setup()
#     _checkpointer.setup()
#     _connection_pool.putconn(conn)
#     # Reusable call_model that uses the global store
#     def call_model(state: MessagesState, config, *, store: BaseStore = _store):
#         user_id = config["configurable"]["user_id"]
#         namespace = ("memories", user_id)
#         last_user_msg = state["messages"][-1].content
#         # Load memories
#         memories = store.search(namespace, query=last_user_msg)
#         memory_text = "\n".join([m.value["data"] for m in memories]) if memories else ""
#         sys_msg = f"USER_MEMORIES:\n{memory_text}"
#         # Store new memory if requested
#         if "remember" in last_user_msg.lower():
#             memory_value = last_user_msg.lower().replace("remember", "").strip()
#             if memory_value:
#                 store.put(namespace, str(uuid.uuid4()), {"data": memory_value})
        
#         # FIXED: Use ALL messages from state (includes history from checkpointer)
#         # Only prepend system message if not already present
#         messages = state["messages"]
#         if not messages or messages[0].type != "system":
#             messages = [{"role": "system", "content": sys_msg}] + messages
        
#         # Call the agent with full conversation history
#         response = rag_agent.invoke({"messages": messages}, config)
#         return {"messages": response["messages"]}
#     # Build graph once
#     builder = StateGraph(MessagesState)
#     builder.add_node("call_model", call_model)
#     builder.add_edge(START, "call_model")
#     _graph = builder.compile(
#         store=_store,
#         checkpointer=_checkpointer,
#     )
#     return _graph

# # Lines 79-139 - REPLACE entire get_graph function
# def get_graph():
#     global _checkpointer, _graph
#     if _graph is not None:
#         return _graph
    
#     # Use JSON file-based checkpointer
#     _checkpointer = JSONCheckpointSaver(sessions_folder="sessions")
    
#     # Simple in-memory store for memories (or you can make this JSON-based too)
#     from langgraph.store.memory import InMemoryStore
#     _store = InMemoryStore()
    
#     # Reusable call_model
#     def call_model(state: MessagesState, config, *, store: BaseStore = _store):
#         user_id = config["configurable"]["user_id"]
#         namespace = ("memories", user_id)
        
#         # Get all messages from state (includes history)
#         messages = state.get("messages", [])
        
#         if not messages:
#             return {"messages": []}
        
#         last_user_msg = messages[-1].content if messages else ""
        
#         # Load memories
#         memories = store.search(namespace, query=last_user_msg)
#         memory_text = "\n".join([m.value["data"] for m in memories]) if memories else ""
#         sys_msg = f"USER_MEMORIES:\n{memory_text}"
#         # Store new memory if requested
#         if "remember" in last_user_msg.lower():
#             memory_value = last_user_msg.lower().replace("remember", "").strip()
#             if memory_value:
#                 store.put(namespace, str(uuid.uuid4()), {"data": memory_value})
        
#         # Prepend system message if needed
#         if not messages or not hasattr(messages[0], 'type') or messages[0].type != "system":
#             final_messages = [{"role": "system", "content": sys_msg}] + messages
#         else:
#             final_messages = messages
        
#         # Call the agent with full conversation history
#         response = rag_agent.invoke({"messages": final_messages}, config)
#         return {"messages": response["messages"]}
    
#     # Build graph
#     builder = StateGraph(MessagesState)
#     builder.add_node("call_model", call_model)
#     builder.add_edge(START, "call_model")
    
#     _graph = builder.compile(
#         store=_store,
#         checkpointer=_checkpointer,
#     )
    
#     return _graph


def get_graph():
    global _checkpointer, _graph
    if _graph is not None:
        return _graph
    
    # Use JSON file-based checkpointer
    
    _checkpointer = PostgresCheckpointSaver(postgres_url=DB_URL)
    # _checkpointer = JSONCheckpointSaver(sessions_folder="sessions")
    
    # Build graph with direct RAG agent call
    def call_rag_agent(state: MessagesState):
        """Call RAG agent directly without nesting."""
        messages = state.get("messages", [])
        
        if not messages:
            return {"messages": []}
        
        # Call the RAG agent directly
        response = rag_agent.invoke({"messages": messages})
        return {"messages": response["messages"]}
    
    # Build graph
    builder = StateGraph(MessagesState)
    builder.add_node("call_rag_agent", call_rag_agent)
    builder.add_edge(START, "call_rag_agent")
    
    _graph = builder.compile(checkpointer=_checkpointer)
    
    return _graph


def RAG_agent(user_message: str, thread_id: str, user_id="1"):
    print("ai agent\n" * 3)
    print("Using persistent Postgres-backed graph")
    graph = get_graph()  # ← This returns the same live graph every time

    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
        }
    }
    print("config:", config)
    result_text = ""
    for chunk in graph.stream(
        {"messages": [HumanMessage(content=user_message)]},
        config,
        stream_mode="values"
    ):
        msg = chunk["messages"][-1]
        print("msge out\n", msg)
        result_text = msg.content
        
    return result_text

