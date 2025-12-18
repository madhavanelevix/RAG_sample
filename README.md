# Project Setup Guide

## Environment Details

- **Python version**: 3.12
- **Framework**: LangChain, LangGraph
- **Chat Models**:
  - OpenAI (Azure-OpenAI)
  - Gemini ("gemini-2.5-flash" in Free Tier)
  - Groq ("gpt-oss-120b" in Free Tier)
  - Ollama (Locally hosted Model)
- **Embedding Model**: SentenceTransformer (clip-ViT-B-32, Open-source, Locally hosted)
- **File Store (document format)**: Seaweed
- **Vector DB**: PGVector
- **Session & Chat**: PostGreSQL

### Dependencies Management

- Dependencies are managed by **UV environment**.

---

## Setup Steps

### Step 1: Verify Python Version

1. Ensure that Python 3.12 is installed on your PC.

### Step 2: Install UV Environment

1. Install UV by running the following command:

   ```bash
   pip install uv
   ```

### Step 3: Clone the Repository & Install Dependencies

1. Clone the repository.
2. Install all dependencies using this command:

   ```bash
   uv sync
   ```

### Step 4: Activate Virtual Environment

1. Activate the virtual environment with this command:

   ```bash
   .venv\Scripts\activate
   ```

### Step 5: Run Backend Server

1. Run the backend server with the following command:

   ```bash
   uvicorn main:app --reload
   ```

---

### Final Step: Open Chat Interface

1. Open the "static/dbchat.html" file in your browser.
2. Start chatting.

---

> **Note:** If you encounter any issues with the setup, refer to the UV documentation or open an issue on the repo.


uvicorn main:app --reload

![Link Icon](https://img.shields.io/badge/-%20-111111?style=flat&logo=link&logoColor=white&labelColor=111111)

