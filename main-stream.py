from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import shutil
from pathlib import Path
from datetime import datetime

from langchain_core.messages import HumanMessage
from utils.document_process import document_upload_vector
from utils.aichat import collection_name #, RAG_agent
from utils.aistream import graph


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins (use specific URL in production)
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# docs = "Incident-Management-SOP.md"
# docs = "IT-Security-Policy.md"

UPLOAD_DIRECTORY = Path("uploaded_files")
UPLOAD_DIRECTORY.mkdir(exist_ok=True)

print(collection_name)

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

        x = document_upload_vector(
            doc_location=file_location,
            doc_name = file.filename,
            collection_name=collection_name
        )
        if type(x) == str:
            return JSONResponse(content={
                "status": "failed",
                "message": x,
                "filename": file.filename,
                "size": file.size 
            })

    except Exception as e:
        await file.close() 
        print(f"Error saving file: {e}")
        raise HTTPException(status_code=500, detail=f"Could not save file{e}")

    finally:
        pass

    print(datetime.now() - st)

    return JSONResponse(content={
        "status": "success",
        "message": "Upload successful",
        "filename": file.filename,
        "size": file.size 
    })


@app.get("/")
def read_root():
    return {"Hello": "FastAPI File Uploader is running! Go to */uploadfile/* for file upload."}

# @app.post("/chat/")
# async def ai_chat_endpoint(user_query: str, thread_id: str ):
#     # try:
        
#         ai_respons = RAG_agent(user_message=user_query, thread_id=thread_id)
#         return JSONResponse(content={
#             "status": "success",
#             "user_query": user_query,
#             "response": ai_respons
#         })
    
#     # except Exception as e:
#     #     print("An unexpected error occurred:", e)
#     #     return JSONResponse(content={
#     #         "status": "Error",
#     #         "user_query": user_query,
#     #         "response": "error on processing"
#     #     })


@app.get("/chat/stream")
async def chat_stream(query: str, thread_id: str, user_id: str = "1"):

    async def event_stream():
        config = {
            "configurable": {
                "thread_id": thread_id,
                "user_id": user_id
            }
        }

        final_output = ""  # collect full response

        # --- STREAMING START ---
        for chunk in graph.stream(
            {"messages": [HumanMessage(content=query)]},
            config,
            stream_mode="values"
        ):
            msg = chunk["messages"][-1].content
            final_output += msg  # append to final message

            # send chunk to client
            yield f"data: {msg}\n\n"

        # --- AFTER STREAM FINISHES ---
        print("\n" + "=" * 60)
        print("🟦 FULL AI RESPONSE (DEV LOG):")
        print("=" * 60)
        print(final_output)
        print("=" * 60 + "\n")

        # notify SSE end
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

# uvicorn main-stream:app --reload