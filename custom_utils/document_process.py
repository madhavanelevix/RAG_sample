import os
from docx import Document
from datetime import datetime
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

# Updated imports to include your new DB models
from custom_utils.vector import vector_upload, excel_upload, SessionLocal, UploadedDocumentModel
# from custom_utils.seaweed import upload_file

def docx_to_txt(docx_path):
    base_path, _ = os.path.splitext(docx_path)
    txt_path = base_path + ".txt"
    doc = Document(docx_path)

    with open(txt_path, "w", encoding="utf-8") as f:
        for para in doc.paragraphs:
            f.write(para.text + "\n")

    print("📃 Word file Processing")
    return txt_path

def percentage(current, total):
    if total == 0:
        return 0
    percentage = (current / total) * 100
    return int(percentage)

def content_spliter(doc):
    with open(doc, encoding="utf-8") as f:  # Added encoding for safety
        state_of_the_union = f.read()
    
    print("book\n")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=70,
        length_function=len,
        is_separator_regex=False,
    )
    
    return text_splitter.create_documents([state_of_the_union])


def document_upload_vector(doc_location: str, doc_name: str, collection_name: str):
#   try:    
#     doc_path_obj = Path(doc_location)
#     doc_for_upload = str(doc_location).replace("\\", "/")
    
#     # 1. Upload to SeaweedFS (keep existing logic)
#     file_url = upload_file(doc_for_upload)
    
#     # 2. Identify File Type
#     ext = doc_for_upload.split('.')[-1].lower()
#     file_type_map = {"xlsx": "Excel", "xls": "Excel", "txt": "Text", "md": "Markdown", "docx": "Word"}
#     file_type = file_type_map.get(ext, "Unknown")
#     print(f"Detected type: {file_type}")

#     # 3. Create Metadata Record in 'uploaded_documents' (New Step)
#     session = SessionLocal()
#     try:
#         file_size = os.path.getsize(doc_location)
        
#         new_doc_record = UploadedDocumentModel(
#             file_name=doc_name,
#             original_file_name=doc_name,
#             file_size=file_size,
#             file_type=file_type,
#             blob_url=file_url,
#             upload_timestamp=datetime.now(),
#             user_email="system",  # Replace with actual user if available
#             key_points=[]
#         )
#         session.add(new_doc_record)
#         session.commit()
#         session.refresh(new_doc_record)
        
#         # Get the DB ID to link vectors later
#         db_document_id = str(new_doc_record.id) 
#         print(f"✅ Metadata saved with ID: {db_document_id}")

#     except Exception as e:
#         session.rollback()
#         print(f"❌ Failed to save metadata: {e}")
#         return f"Database error: {e}"
#     finally:
#         session.close()

#     # 4. Process File Content based on Type
#     if file_type == "Excel":
#         # Note: excel_upload in vector.py might generate its own UUID, 
#         # but the metadata record is now safe in uploaded_documents.
#         x = excel_upload(
#             excel_path=doc_location,
#             collection_name=collection_name,
#             document_link=file_url,
#         )
#         return 1

#     elif file_type in ["Text", "Markdown", "Word"]:
#         if file_type == "Word":
#             doc_location = docx_to_txt(doc_location)
            
#         texts = content_spliter(doc_location)
#         docs_len = len(texts)
#         print(f"Total chunks: {docs_len}")
        
#         for i in range(docs_len):
#             # Pass the DB ID so chunks link to the file metadata
#             metadata = {
#                 "document_link": file_url,
#                 "document_id": db_document_id, # Link to uploaded_documents table
#                 "chunk": i,
#                 "title": doc_name
#             }

#             vector_upload(
#                 data=texts[i].page_content,
#                 metadata=metadata,
#                 collection_name=collection_name
#             )
            
#             prog = percentage(i+1, docs_len)
#             print(f"completed {prog}%")
            
#         return 1
    
#     else: 
#         return "file not supported"
#   except:
    return "file not supported"

