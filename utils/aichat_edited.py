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

DB_URL = os.getenv("DATABASE_URL")
# DB_URL = os.getenv("PG_VECTOR")

_checkpointer = PostgresCheckpointSaver(postgres_url=DB_URL)
# _checkpointer = JSONCheckpointSaver(sessions_folder="sessions")


openai_model = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"), 
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
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

    print(llm, DB_URL[-20:])

    # rag_agent = create_agent(
    #     name="agent",
    #     model=llm,
    #     tools=[data_retriever],
    #     system_prompt=doc_prompt,
    # )

    # web_agent = create_agent(
    #     name="agent",
    #     model=llm,
    #     system_prompt=web_prompt,
    # )

    agent = create_agent(
        name="agent",
        model=llm,
        tools=tool,
        system_prompt=prompt,
    )

    # Build graph with direct RAG agent call
    def call_rag_agent(state: MessagesState):
        """Call RAG agent directly without nesting."""
        messages = state.get("messages", [])
        
        if not messages:
            return {"messages": []}
        
        # if source:
        #     print("use Document Source")
        #     # Call the RAG agent directly
        #     response = rag_agent.invoke({"messages": messages})
        # else:
        #     print("use Web Source")
        #     # Call the Web agent directly
        #     response = web_agent.invoke({"messages": messages})

        response = agent.invoke({"messages": messages})

        return {"messages": response["messages"]}
    
    # Build graph
    builder = StateGraph(MessagesState)
    builder.add_node("call_rag_agent", call_rag_agent)
    builder.add_edge(START, "call_rag_agent")
    
    _graph = builder.compile(checkpointer=_checkpointer)
    
    return _graph


def RAG_agent(user_message: str, thread_id: str, source: bool, model: int, user_id="1"):
    print("ai agent\n" * 3)
    # print("Using persistent Postgres-backed graph")
    graph = get_graph(source, model)  # ← This returns the same live graph every time

    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
        }
    }
    print("config:\n", config)
    result_text = ""
    for chunk in graph.stream(
        {"messages": [HumanMessage(content=user_message)]},
        config,
        stream_mode="values"
    ):
        msg = chunk["messages"][-1]
        print("msge out\n"*3, f"{msg.content[:100]}...")
        result_text = msg.content
        
    return result_text

