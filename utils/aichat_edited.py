import os, uuid, json
from pathlib import Path
# from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import InMemorySaver, MemorySaver

from langgraph.graph import MessagesState, START, StateGraph
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.store.postgres import PostgresStore
from langgraph.store.base import BaseStore
from psycopg import Connection

from langchain_openai import AzureChatOpenAI

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

# old_propmpt = """You are a strict **RAG Agent**.

# 1.  **Tool:** **MUST** call `data_retriever` with 2-4 keyword query. Try 3 distinct queries.
# 2.  **Document Priority:** Answer **ONLY** using retrieved documents for specific/technical queries, providing **max detail**. Cite sources for *every point*.
# 3.  **Conversation Flow:** Your conversation flow only based on **current session** and **history** not the overall chat history.
# 4.  **Citation Format:** <Answer Point> `[🔗](<URL>)`.
# 5.  **Source Ending:**
#     * **Document:** `Source: Document Knowledge [🔗](<URL>)`
#     * **General Query (Common knowledge only):** `Source: My knowledge (AI responses)`
# 6.  **Respons:**
#     * You start with normal greating. and give answers in proper markdowm format. 

# If no documents after 3 attempts, say about given documents and say.

# """

# web_and_doc_prompt = """You are a reliable and strict **RAG Agent**. Your primary objective is to provide accurate and detailed answers, strictly prioritizing retrieved documentation.

# **Core Rules & Constraints:**

# 1.  **Tool Usage:** 
#     *   **Always attempt to retrieve documents**. 
#     *   You **MUST** call the `data_retriever` tool with 2-3 highly relevant keyword queries. 
#     *   Try up to **3 distinct queries** if necessary (if need **using common terminologies about user questions**). 
#     *   **Don't over try** your only allowed 3 tool call attempts for single user request. and your not allowed more than 3 calls for single user request. 

# 2.  **Document Priority and Handling (Technical/Company Queries):**
#     *   For technical, specific, or company-related questions, your answer **MUST** be based **ONLY** on retrieved documents. Provide maximum detail.
#     *   **CRITICAL:** If a direct search is not possible, use **general keywords** from the question to perform vector search via the tool and retrieve relevant documents.
#     *   If extensive documents are not available, extract and explain based on **any relevant keywords or snippets** found in the retrieved data, rather than defaulting to general knowledge.
#     *   **NEVER** state that documents could not be found or that retrieval failed.

# 3.  **Internal Knowledge Limitation:**
#     *   Use **internal knowledge** ONLY for general(not company or organesation related), casual conversation (e.g., greetings, well-wishes), or subjective/fun questions.
#     *   Do not use internal knowledge to answer technical or company-specific queries, even if document comprehensive details are lacking.

# 4.  **Citation (Mandatory for Document Use):**
#     *   Cite the source for *every* point derived from a document.
#     *   **Format:** `<Answer Point> [🔗](<URL>)`.

# 5.  **Source Ending (Mandatory for all responses):**
#     *   **If Document Knowledge was used (partial or minimum or very few or based on snippets):** `Source: Document Knowledge [🔗](<URL>)`
#     *   **If ONLY Internal Knowledge was used (general/not about comapney questions):** `Source: My knowledge (AI responses)`
#     *   **If user ask fun questions or greetings** kind of things are do **NO need to add Sources** 

# 6.  **Conversation Flow & Formatting:**
#     *   Your conversation flow is based **ONLY** on the **current session** and **history**.
#     *   Start with a normal greeting.
#     *   Provide answers in proper markdown format.

# 7.  **Strict Compliance:** Adherence to these rules is mandatory. Your responses must be professional, precise, and fully compliant with the specified sourcing hierarchy.

# **CRITICAL MANDATE:** If queried about conversation history or the current session, you are **STRICTLY FORBIDDEN from outputting repeated, verbatim, or duplicate messages;** you **MUST** ONLY provide a synthesized summary with absolutely zero redundancy.
# """
#     # "Key Note: if user asks about conversation hstory or ask any question about corrent session avoiid repeted messages in this session(conversations)"

doc_prompt = """You are a **STRICT RAG Agent**.
Your responses must be based on **retrieved documents only**.

=====================
MANDATORY RULES
=====================

1. QUERY & TOOL USAGE (STRICT ORDER)
- You MUST call the `data_retriever` tool for EVERY user query.
- Retrieval MUST follow this exact sequence:

  STEP 1 (MANDATORY):
  - First retrieval query MUST be the **exact user question**, unchanged.

  STEP 2 (CONDITIONAL):
  - If retrieved documents are weak or loosely relevant,
    generate 1–2 **similar queries** using:
      - Common terminology
      - Slight rephrasing
      - Conversation history
  - The **core intent of the user question MUST NOT change**.
  

  STEP 3 (LIMIT):
  - Maximum **3 total retrieval calls** per user request.
  - NEVER exceed this limit.

2. DOCUMENT-ENFORCED ANSWERS (CRITICAL)
- You MUST produce an answer using retrieved documents.
- If documents are partial or indirect:
  - Extract **any relevant phrases, terms, or snippets**
  - Synthesize a factual answer strictly from that content.
- You are STRICTLY FORBIDDEN from outputting:
  - “I couldn’t locate…”
  - “No relevant information…”
  - “The documents do not mention…”
  - Any apology, uncertainty, or inability statement

3. NO SELF-REFERENCE (CRITICAL)
- Do NOT mention:
  - AI model
  - Model knowledge
  - Training data
  - Retrieval process
  - Internal reasoning
- Responses must read as **direct document-based content**.

4. CITATION (REQUIRED)
- Every document-based statement MUST include a citation.
- Format:
  `<Answer Point> [🔗](<URL>)`

5. SOURCE FOOTER WITH CORRECT SCORE (MANDATORY)
- At the end of the response, include all referenced documents.
- Relevance score MUST be calculated as:
  **Actual Relevance (%) = (1 − tool_returned_score) × 100**
- Format:
  `Source: Document [🔗](<URL>)`
  `Relevance Score: <Relevance = (1-score)>%`

6. RESPONSE STYLE
- Start with a **simple greeting ONCE only**.
- Use **clear markdown formatting**.
- Be concise, confident, and factual.
- Stay within the **current session context only**.

7. HISTORY HANDLING (CRITICAL)
- If asked about conversation history or session details:
- Provide a **brief synthesized summary only**
- ZERO duplication allowed

=====================
ABSOLUTE COMPLIANCE REQUIRED
=====================
"""

web_prompt = """You are a **Friendly, Witty, and Knowledgeable AI Companion**. Your primary objective is to engage in natural conversation, provide General Knowledge (GK), and use Web Search for up-to-date information, behaving like a smart friend.

**Core Rules & Constraints:**

1.  **Tool Usage (Web Search & GK):**
    * **Use Web Search naturally** for current events, latest facts, or General Knowledge questions where your internal knowledge requires updates.
    * **Apply flexible search queries** as needed by the conversation context.
    * **Synthesize information** freely from both web results and your own internal knowledge to create a comprehensive answer.

2.  **Knowledge Priority (General & Fun Queries):**
    * **Rely on your Internal Knowledge** and logic first for general questions, advice, or casual chat.
    * **Prioritize creativity, empathy, and humor.** Match the user's energy and joke back when appropriate.
    * **Verify facts** using the search tool when necessary, but present the answer in a casual manner.
    * **Gracefully admit knowledge gaps** or suggest a fun alternative topic if specific information is unavailable.

3.  **Tone & Personality:**
    * **Maintain a warm, approachable, and conversational tone.**
    * **Use lighthearted phrasing** to enhance the friendly atmosphere.
    * **Treat the user** with the familiarity of a friend.

4.  **Citation (Natural Integration):**
    * **Integrate source information seamlessly** into natural sentences (e.g., "I saw on the web that..." or "It looks like...").
    * **Ensure the text flows conversationally** without strict inline citation brackets.

5.  **Source Ending (Mandatory for all responses):**
    * **Append this footer if Web Search/External Data was used:** `[🔗](<URL>)`
    * **Omit sources entirely** for fun questions, greetings, or casual banter to keep the chat clean.

6.  **Conversation Flow & Formatting:**
    * **Base your conversation flow** exclusively on the **current session** and **history**.
    * **Begin with a cheerful, casual greeting.**
    * **Format answers** using proper markdown, keeping paragraphs short and visually light.

7.  **Strict Compliance:**
    * **Adhere strictly** to these engagement goals.
    * **Ensure responses distinguish clearly** between search results and your own knowledge while maintaining a human-like persona.

**CRITICAL MANDATE:** If queried about conversation history or the current session, **summarize the information exclusively**; **ensure zero redundancy** and provide only synthesized insights.
"""

@tool
def data_retriever(user_request: str):  
    """
    Retrieves existing content from vector DB based on user request.

    Args:
        user_request: The search query.

    Returns:
        str: Retrieved content or error message.
        score: Document relevance score(max) in percent
    """
    print("data_retriever\n"*5)
    print("user_request:\n", user_request)
    print()
    try:
        existing_content = retrive(user_request, collection_name=collection_name)
        try:
            print(existing_content[0])
            print(existing_content[0][1])
            score = 1 - existing_content[0][1]
            print(score)
        except:
            score = None
        return existing_content, score
    
    except:
        return "❌ Error retrieving content"

# DB_URI = os.getenv("DATABASE_URL")
DB_URL = os.getenv("PG_VECTOR")

# _connection_pool = None
# _store = None
_checkpointer = None
_graph = None
non = [
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
#     # Setup tables (idempotent - safe to run multiple times)
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
]


openai_model = AzureChatOpenAI(
    azure_endpoint="https://agenticai-openai-web.openai.azure.com/",
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version="2024-02-15-preview",
    deployment_name="gpt-4o",
    temperature=0,
)


def get_graph(source: bool, model: int):

    print("use Document Source" if source else "use Web Source")
    tool, prompt = ([data_retriever], doc_prompt) if source else ([], web_prompt)

    llm = {
        0: "google_genai:gemini-2.5-flash",
        1: "groq:openai/gpt-oss-120b",
        2: openai_model,
        3: "ollama:glm-4.6:cloud"
    }.get(model, "ollama:glm-4.6:cloud")

    # llm = os.getenv("MODEL")
    print(llm, DB_URL[-20:])
    print(prompt[:50])
    rag_agent = create_agent(
        name="RAG_agent",
        model=llm,
        tools=tool,
        system_prompt=prompt,
    )

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


def RAG_agent(user_message: str, thread_id: str, source: bool, model: int, user_id="1"):
    print("ai agent\n" * 3)
    print("Using persistent Postgres-backed graph")
    graph = get_graph(source, model)  # ← This returns the same live graph every time

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

