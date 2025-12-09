from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware # Import CORS Middleware
import shutil
from pathlib import Path
from datetime import datetime

from utils.document_process import document_upload_vector
from utils.aichat_edited import RAG_agent, collection_name


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace "*" with your specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (POST, GET, etc.)
    allow_headers=["*"],  # Allows all headers
)
# --------------------------------

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
            doc_name = file.filename,
            collection_name=collection_name
        )
        
        # Check for failure string from document_process
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
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")

    finally:
        pass

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
async def ai_chat_endpoint(user_query: str, thread_id: str):
    # try:
        # Call the RAG Agent
        ai_respons = RAG_agent(user_message=user_query, thread_id=thread_id)
        
        return JSONResponse(content={
            "status": "success",
            "user_query": user_query,
            "response": ai_respons
        })
    
    # except Exception as e:
    #     print("An unexpected error occurred:", e)
    #     return JSONResponse(content={
    #         "status": "Error",
    #         "user_query": user_query,
    #         "response": "error on processing"
    #     }, status_code=500)


# uvicorn maintemp:app --reload
