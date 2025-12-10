import os, uuid
# from langchain_google_genai import ChatGoogleGenerativeAI
# from langgraph.checkpoint.memory import InMemorySaver, MemorySaver

from langgraph.graph import MessagesState, START, StateGraph
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore
from langgraph.store.base import BaseStore
from psycopg import Connection

from langchain_core.messages import HumanMessage

from langchain.agents import create_agent
from langchain.tools import tool

from psycopg_pool import ConnectionPool

from utils.vector import retrive

from dotenv import load_dotenv
load_dotenv()

collection_name = os.getenv("VECTOR_COLLECTION")

non_prompt = """You are a strict **RAG Agent**.

1.  **Tool:** **MUST** call `data_retriever` with 2-4 keyword query. Try 3 distinct queries.
2.  **Document Priority:** Answer **ONLY** using retrieved documents for specific/technical queries, providing **max detail**. Cite sources for *every point*.
3.  **Citation Format:** <Answer Point> `[🔗](<URL>)`or`(Name: <Doc Name>, Page: <Page #>)`.
4.  **Source Ending:**
    * **Document:** `Source: Document Knowledge [🔗](<URL>)`
    * **General Query (Common knowledge only):** `Source: [My knowledge (AI responses)] for (Gemini) knowledge based`
5.  **Respons:**
    * You start with normal greating. and give answers in proper markdowm format. 

If no documents after 3 attempts, say 'No relevant documents found'.
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

DB_URI = os.getenv("DATABASE_URL")
llm = os.getenv("MODEL")
print(llm, DB_URI)

rag_agent = create_agent(
    name="RAG_agent",
    model=llm,
    tools=[data_retriever],
    system_prompt=non_prompt,
)

_connection_pool = None
_store = None
_checkpointer = None
_graph = None
def get_graph():
    global _connection_pool, _store, _checkpointer, _graph
    if _graph is not None:
        return _graph
    # Create pool only once
    _connection_pool = ConnectionPool(
        conninfo=DB_URI,
        min_size=1,
        max_size=10,
        timeout=30.0
    )
    # Get a connection from the pool
    conn = _connection_pool.getconn()
    # Create store and checkpointer using the same connection
    _store = PostgresStore(conn)
    _checkpointer = PostgresSaver(conn)
    # Setup tables (idempotent – safe to run multiple times)
    _store.setup()
    _checkpointer.setup()
    # Reusable call_model that uses the global store
    def call_model(state: MessagesState, config, *, store: BaseStore = _store):
        user_id = config["configurable"]["user_id"]
        namespace = ("memories", user_id)
        last_user_msg = state["messages"][-1].content
        # Load memories
        memories = store.search(namespace, query=last_user_msg)
        memory_text = "\n".join([m.value["data"] for m in memories]) if memories else ""
        sys_msg = f"USER_MEMORIES:\n{memory_text}"
        # Store new memory if requested
        if "remember" in last_user_msg.lower():
            memory_value = last_user_msg.lower().replace("remember", "").strip()
            if memory_value:
                store.put(namespace, str(uuid.uuid4()), {"data": memory_value})
        # Call the agent
        final_messages = [{"role": "system", "content": sys_msg}] + state["messages"]
        response = rag_agent.invoke({"messages": final_messages}, config)
        return {"messages": response["messages"]}
    # Build graph once
    builder = StateGraph(MessagesState)
    builder.add_node("call_model", call_model)
    builder.add_edge(START, "call_model")
    _graph = builder.compile(
        store=_store,
        checkpointer=_checkpointer,
    )
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

