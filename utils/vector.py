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
    # return vector_store.similarity_search(
    #     query=user_query,
    #     k=k
    # )
    return vector_store.similarity_search_with_score(
        query=user_query,
        k=k
    )


def excel_upload(
    excel_path: str,
    collection_name: str,
    document_link: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 70
):
    """
    Excel → PGVector upload (DROP-IN REPLACEMENT)

    Uses:
    - vectordb()
    - data_embedding()
    - PGVector.add_embeddings()

    Metadata format:
    {"document_link": "<document_link>"}
    """

    import os
    import pandas as pd

    # -------------------------
    # Helpers (LOCAL)
    # -------------------------
    def detect_title_and_header(df):
        title = None
        header_row = None

        for i in range(min(5, len(df))):
            row = df.iloc[i].dropna().astype(str)

            if len(row) <= 2 and row.str.len().mean() > 20:
                title = " ".join(row.tolist())
                continue

            if len(row) >= 3 and row.str.len().mean() < 25:
                header_row = i
                break

        return title, header_row

    def sheet_to_text(df, title, header_row):
        blocks = []

        if title:
            blocks.append(f"TITLE: {title}")

        if header_row is not None:
            df.columns = df.iloc[header_row]
            df = df.iloc[header_row + 1:]

        for _, row in df.iterrows():
            row_text = " | ".join(
                [str(v) for v in row if pd.notna(v)]
            )
            if row_text.strip():
                blocks.append(row_text)

        return "\n".join(blocks)

    def chunk_text(text):
        chunks = []
        start = 0
        length = len(text)

        while start < length:
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - chunk_overlap

        return chunks

    # -------------------------
    # Validation
    # -------------------------
    excel_path = os.path.abspath(os.path.expanduser(excel_path))
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    vector_store = vectordb(collection=collection_name)
    xls = pd.ExcelFile(excel_path, engine="openpyxl")

    results = []

    print(f"📄 Excel sheets detected: {xls.sheet_names}")

    # -------------------------
    # Processing
    # -------------------------
    for page_index, sheet_name in enumerate(xls.sheet_names):
        df = xls.parse(sheet_name, header=None)

        title, header_row = detect_title_and_header(df)
        full_text = sheet_to_text(df, title, header_row)

        if not full_text.strip():
            continue

        chunks = chunk_text(full_text)

        for chunk_index, chunk in enumerate(chunks):
            embedding = data_embedding(chunk)
            if embedding is None:
                continue

            metadata = {
                "document_link": document_link,
                "sheet_name": sheet_name,
                "page": page_index,
                "chunk": chunk_index,
                "title": title
            }

            try:
                vector_store.add_embeddings(
                    texts=[chunk],
                    embeddings=[embedding],
                    metadatas=[metadata]
                )

                results.append({
                    "status": "success",
                    "sheet": sheet_name,
                    "chunk": chunk_index
                })

            except Exception as e:
                print(f"❌ Upload failed (sheet={sheet_name}, chunk={chunk_index}): {e}")
                results.append({
                    "status": "failed",
                    "sheet": sheet_name,
                    "chunk": chunk_index,
                    "error": str(e)
                })

    print(f"✅ Excel upload completed → {len(results)} chunks stored")
    return results
