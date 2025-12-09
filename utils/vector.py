from langchain.embeddings.base import Embeddings
from langchain_core.documents import Document
from langchain_postgres import PGVector

import os
import requests
from io import BytesIO
from PIL import Image
from sentence_transformers import SentenceTransformer

from uuid import uuid4
from typing import Optional
import pandas as pd

from dotenv import load_dotenv
load_dotenv()


class CLIPEmbeddings(Embeddings):
    def __init__(self, model_name="clip-ViT-B-32"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)

    def embed_documents(self, texts):
        return self.model.encode(texts, convert_to_tensor=False).tolist()

    def embed_query(self, text):
        return self.model.encode(text, convert_to_tensor=False).tolist()

def vectordb(collection: str):
    return PGVector(
        embeddings=CLIPEmbeddings(),
        collection_name=collection,
        connection=os.environ["PG_VECTOR"],
        use_jsonb=True,
    )

def data_embedding(data: str):
    
    model = SentenceTransformer('clip-ViT-B-32')
    try:
        if data.startswith("http://") or data.startswith("https://"):
            response = requests.get(data)
            image = Image.open(BytesIO(response.content))
            embedding = model.encode(image)
            print("🖼️ Generated image embedding from image URL.")

        elif os.path.exists(data):
            image = Image.open(data)
            embedding = model.encode(image)
            print("🖼️ Generated image embedding from local image.")

        else:
            embedding = model.encode(data)
            print("📝 Generated text embedding from text.")

    except Exception as e:
        print(f"⚠️ Failed to embed data: {e}")
        embedding = None
        return None
    return embedding

def vector_upload(
    data: str,
    metadata: dict,
    collection_name: str,
    id: Optional[int] = None
):
    """
    data: text or image_path or image url.
    metadata: adisenal das about document 
    id: project id 
    collection_name: User unique ID 
    """
    vector_store = vectordb(collection=collection_name)
    metadata = metadata
    # metadata = {"content_id": f"{uuid4().hex}" or id, "title": title, "discription": discription}
    embeddings = data_embedding(data)

    try:
        vector_store.add_embeddings(
            texts=[data],
            embeddings=[embeddings],
            metadatas=[metadata]
        )
        print("✅ upload completed")

        return {"context": data, "collection_id": collection_name, "metadata": metadata}

    except Exception as e:
        print("An unexpected error occurred:", e,
              "you receive metadata you given. correct that and Re-try.")
        return {"context": data, "collection_id": collection_name, "metadata": metadata}


def retrive(
    user_query: str,
    collection_name: str,
    k: Optional[int] = 10
):
    """
    retruve data 
    """
    vector_store = vectordb(collection=collection_name)
    data = vector_store.similarity_search(
        query=user_query,
        k=k
    )

    return data

def excel_upload(
    excel_path: str,
    collection_name: str,
    metadata_columns: list,
    text_columns: list = None,
    image_column: str = None,
    sheet_name: str = None  # You can specify sheet name or index
):
    """
    Fixed version: Properly handles file paths and ensures df is always a DataFrame
    """
    # --- Fix Windows path issues ---
    excel_path = os.path.expanduser(excel_path)  # Handles ~ if any
    excel_path = os.path.abspath(excel_path)     # Converts to absolute path
 
    print(f"Attempting to load Excel file from: {excel_path}")
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel file not found at: {excel_path}")
 
    # --- Load Excel safely as DataFrame ---
    try:
        # Always force loading a single sheet to get a DataFrame, not dict
        df = pd.read_excel(excel_path, sheet_name=sheet_name, engine='openpyxl')
        # If user didn't specify sheet_name and file has multiple sheets,
        # pd.read_excel returns dict only when sheet_name=None → we avoid that
        if isinstance(df, dict):
            # Take the first sheet if multiple
            sheet_names = list(df.keys())
            print(f"Multiple sheets found: {sheet_names}. Using the first one: '{sheet_names[0]}'")
            df = df[sheet_names[0]]
 
        print(f"Successfully loaded Excel: {len(df)} rows × {len(df.columns)} columns")
        print(f"Columns: {list(df.columns)}")
 
    except Exception as e:
        raise ValueError(f"Failed to read Excel file: {e}")
 
    # --- Determine columns for text, metadata, image ---
    all_columns = df.columns.tolist()
 
    if metadata_columns is None:
        metadata_columns = []
 
    if text_columns is None:
        excluded = metadata_columns + ([image_column] if image_column else [])
        text_columns = [col for col in all_columns if col not in excluded]
 
    # --- Reuse your existing vectordb and data_embedding logic ---
    vector_store = vectordb(collection=collection_name)
    results = []
 
    for idx, row in df.iterrows():
        row_dict = row.to_dict()
 
        # Build text content
        text_parts = []
        for col in text_columns:
            val = row_dict.get(col)
            if pd.notna(val):
                text_parts.append(str(val).strip())
        text_content = " | ".join(text_parts) if text_parts else ""
 
        # Metadata
        metadata = metadata_columns
        # metadata = {col: row_dict.get(col) for col in metadata_columns}
        if metadata_columns is None:
            metadata.update({
                "row_index": idx,
                "source": excel_path,
                "content_id": uuid4().hex
            })
    
        # Decide what to embed
        data_to_embed = None
        embed_type = "text"
 
        if image_column and pd.notna(row_dict.get(image_column)):
            img_path = str(row_dict[image_column]).strip()
            data_to_embed = img_path
            embed_type = "image"
        elif text_content:
            data_to_embed = text_content
        else:
            print(f"Row {idx}: Skipping — no text or image found")
            results.append({"status": "skipped", "row": idx})
            continue
 
        print(f"Row {idx}: Embedding {embed_type} → {data_to_embed[:80]}{'...' if len(data_to_embed)>80 else ''}")
 
        # Generate embedding using your existing function
        embedding = data_embedding(data_to_embed)
 
        if embedding is None:
            results.append({"status": "failed", "row": idx, "reason": "embedding_failed"})
            continue
 
        # Upload
        try:
            vector_store.add_embeddings(
                texts=[data_to_embed],
                embeddings=[embedding],
                metadatas=[metadata]
            )
            results.append({"status": "success", "row": idx, "metadata": metadata})
        except Exception as e:
            print(f"Row {idx}: Upload failed → {e}")
            results.append({"status": "failed", "row": idx, "error": str(e)})
 
    success_count = len([r for r in results if r["status"] == "success"])
    print(f"\nExcel upload completed! {success_count}/{len(df)} rows successfully uploaded.")
    return results
 
