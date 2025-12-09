from langchain_core.messages import HumanMessage
from langchain.tools import tool
from langchain.agents import create_agent

from langgraph.graph import MessagesState, START, StateGraph
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore
from langgraph.store.base import BaseStore

from utils.vector import retrive
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

collection_name = "uploaded_documents"

non_prompt = """You are a **RAG Chat Retriever Agent**.
Your responsibilities:
1. Understand the user question deeply.
2. ALWAYS use the `data_retriever` tool.
3. Generate 3-5 short keyword queries (2-4 words) using different angles (if need using common terminologies about user questions). 
4. Call the tool repeatedly until:
   - You find relevant documents, OR
   - All 3-5 queries fail → then use AI knowledge.


### 🔍 RETRIEVAL RULES
- Query format: 2-4 meaningful words only.
- You MUST try up to 4 different queries:
  1) Main keyword  
  2) Synonym / related term  
  3) Domain / category keyword  

- After EACH retrieval:
  - If the documents are relevant → STOP searching and ANSWER.
  - If irrelevant → try the next query.


### 🧠 ANSWER GENERATION RULES
When documents are found:
- DO NOT repeat the document text.
- DO NOT summarize the document blindly.
- **GENERATE A FULL NATURAL-LANGUAGE ANSWER** using your own explanation ability.
- Use the document only as reference.
- Combine reasoning + document facts.
- Cite each point like this:
   <your explanation> [🔗](<document url>)

- At end, write:
  **Source: Document Knowledge**

When NO documents are found after 5th attempts:
- Use your own knowledge to answer.
- End with:
  **Source: Web Search**


### 📘 WHAT YOUR ANSWER MUST LOOK LIKE
A correct answer has:

1. A clear explanation in your own words  
2. Clearl bullet points that answer the user  
3. Each bullet with a source tag  
4. Example:

[
  The system requires user authentication before accessing private data. [🔗](<document url>)

  Logging should be enabled to track suspicious activity. [Web Search (AI Response)]
]


### 📌 STRICT RULES
- NEVER output only document titles or raw document lines.
- NEVER output only metadata.
- ALWAYS produce a full explanation.
- ALWAYS use at least ONE tool call per message.
- NEVER hallucinate page numbers or doc names.
- If no document found after all attempts → default to AI.

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

# "postgresql://postgres:amxIxHpfqzuUzoRhwyXGniCymrUOVFAi@switchyard.proxy.rlwy.net:29714/railway"   # normal DB
DB_URI = os.getenv("DATABASE_URL")
print(DB_URI)

# from langchain_google_genai import ChatGoogleGenerativeAI
# model = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

rag_agent = create_agent(
    name="RAG_agent",
    model="google_genai:gemini-2.5-flash",
    tools=[data_retriever],
    system_prompt=non_prompt,
)

################################################################################
# -------------------------- MEMORY ENABLED GRAPH ------------------------------
################################################################################

def call_model(
    state: MessagesState,
    config,
    *,
    store: BaseStore,    
):
    user_id = config["configurable"]["user_id"]
    namespace = ("memories", user_id)

    last_user_msg = state["messages"][-1].content

    # ---------------- Load memories -----------------------
    memories = store.search(namespace, query=last_user_msg)
    memory_text = "\n".join([m.value["data"] for m in memories])
    sys_msg = f"USER_MEMORIES:\n{memory_text}"

    # ---------------- Store new memory ---------------------
    if "remember" in last_user_msg.lower():
        memory_value = last_user_msg.replace("remember", "").strip()
        if memory_value:
            store.put(namespace, str(uuid.uuid4()), {"data": memory_value})

    # ---------------- Call agent ----------------------------
    final_messages = [{"role": "system", "content": sys_msg}] + state["messages"]
    response = rag_agent.invoke({"messages": final_messages}, config)

    return {"messages": response["messages"]}

################################################################################
# -------------------------- GRAPH BUILDING ------------------------------------
################################################################################

builder = StateGraph(MessagesState)
builder.add_node(call_model)
builder.add_edge(START, "call_model")

# Attach Postgres memory & checkpointer
store = PostgresStore.from_conn_string(DB_URI)
checkpointer = PostgresSaver.from_conn_string(DB_URI)

# store.setup()
# checkpointer.setup()

graph = builder.compile(
    store=store,
    checkpointer=checkpointer,
)

################################################################################
# ----------------------------- PUBLIC FUNCTION --------------------------------
################################################################################

# def RAG_agent(user_message: str, thread_id: str, user_id="1"):
#     """
#     Main function used by FastAPI.
#     Uses long-term Postgres conversation history + user memory.
#     """

#     config = {
#         "configurable": {
#             "thread_id": thread_id,   # chat history thread
#             "user_id": user_id,       # long-term memory owner
#         }
#     }

#     result_text = ""

#     # stream mode returns incremental messages
#     for chunk in graph.stream(
#         {"messages": [HumanMessage(content=user_message)]},
#         config,
#         stream_mode="values"
#     ):
#         msg = chunk["messages"][-1]
#         result_text = msg.content

#     return result_text
