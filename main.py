from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
import os
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from sqlalchemy import desc, asc
from sqlalchemy.orm import Session

from custom_utils.schemas import ChatMessageResponse, SessionListResponse, get_db
from custom_utils.document_process import document_upload_vector
from custom_utils.aichat_edited import RAG_agent, collection_name
from custom_utils.pgsql_checkpointer import LanggraphCheckpoint, LanggraphMessage


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/sessions", response_model=List[SessionListResponse])
def get_session_list(
    user_id: Optional[str] = None,
    limit: int = 20,
    skip: int = 0,
    db: Session = Depends(get_db)
):
    """
    Fetch all chat sessions. Sorted by newest update first.
    """
    query = db.query(LanggraphCheckpoint)

    if user_id:
        query = query.filter(LanggraphCheckpoint.user_id == user_id)

    sessions = (
        query.order_by(desc(LanggraphCheckpoint.updated_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return sessions


@app.get("/sessions/{thread_id}/chats", response_model=List[ChatMessageResponse])
def get_chat_history(thread_id: str, db: Session = Depends(get_db)):
    """
    Fetch full chat history for a specific thread_id.
    """
    # Check if session exists
    session = db.query(LanggraphCheckpoint).filter(
        LanggraphCheckpoint.id == thread_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Fetch messages strictly ordered
    messages = (
        db.query(LanggraphMessage)
        .filter(LanggraphMessage.thread_id == thread_id)
        .order_by(asc(LanggraphMessage.message_number))
        .all()
    )
    return messages


@app.delete("/sessions/{thread_id}")
def delete_session(thread_id: str, db: Session = Depends(get_db)):
    """
    Delete a specific session. 
    Due to 'cascade="all, delete-orphan"' in the model, 
    this automatically removes all associated chat messages.
    """
    # 1. Find the session
    session = db.query(LanggraphCheckpoint).filter(
        LanggraphCheckpoint.id == thread_id).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2. Delete the session (SQLAlchemy handles the cascade to messages)
    try:
        db.delete(session)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error deleting session: {str(e)}")

    return {"status": "success", "message": f"Session {thread_id} deleted successfully"}


UPLOAD_DIRECTORY = Path("uploaded_files")
UPLOAD_DIRECTORY.mkdir(exist_ok=True)

print(f"Collection Name: {collection_name}")


@app.post("/uploadfile/")
async def upload_file(file: UploadFile = File(...)):
    """
    Handles file upload, saves the file locally, and returns a success response.
    """
    file_location = UPLOAD_DIRECTORY / file.filename
    st = datetime.now()

    try:
        with file_location.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Call the vector database logic
        x = document_upload_vector(
            doc_location=file_location,
            doc_name=file.filename,
            collection_name=collection_name
        )

        if isinstance(x, str) and "fail" in x.lower():
            return JSONResponse(content={
                "status": "failed",
                "message": x,
                "filename": file.filename,
                "size": file.size
            })

    except Exception as e:
        await file.close()
        print(f"Error saving file: {e}")
        raise HTTPException(
            status_code=500, detail=f"Could not save file: {e}")

    print(f"Processing time: {datetime.now() - st}")

    return JSONResponse(content={
        "status": "success",
        "message": "Upload successful",
        "filename": file.filename,
        "size": file.size
    })


@app.get("/")
def read_root():
    return {"Hello": "FastAPI File Uploader is running! Go to */uploadfile/* for file upload."}


@app.post("/chat/")
async def ai_chat_endpoint(user_query: str, thread_id: str, sources: str, model: str):
    print(f"user_query: '{type(user_query)}', '{user_query}'")
    print(f"thread_id: '{type(thread_id)}, '{thread_id}'")
    print(f"source: '{type(sources)}, '{sources}'")
    print(f"model: '{type(model)}, '{model}'")
    
    def trys(sources, model):
        sources = (sources == 'Document Source')
        model = 0 if model == 'Gemini' else 1 if model == 'Groq' else 2 if model == 'openai' else 3
        return sources, model

    try:
        sources, model = trys(sources, model)

        print("Outs:", sources, model)

        # Call the RAG Agent
        ai_respons = RAG_agent(
            user_message=user_query, 
            thread_id=thread_id,
            model = model,
            source = sources
        )
        print(type(ai_respons))
        # try:
        if isinstance(ai_respons, list):
            respons = ai_respons[0]["text"]
            print("list response", respons)

            return JSONResponse(content={
                "status": "success",
                "user_query": user_query,
                "response": respons
            })
        # except Exception as e:
        #     print("Error processing AI response:", e)
        #     ai_respons = str(ai_respons)
        else:
            return JSONResponse(content={
                "status": "success",
                "user_query": user_query,
                "response": ai_respons
            })

    except Exception as e:
        print("An unexpected error occurred:", e)
        return JSONResponse(content={
            "status": "Error",
            "user_query": user_query,
            "response": "error on processing"
        }, status_code=500)


# uvicorn main:app --reload
