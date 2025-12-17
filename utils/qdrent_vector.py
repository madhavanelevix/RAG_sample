import os
import uuid
import pandas as pd
from typing import List
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct


# =========================================================
# CONFIG
# =========================================================
QDRANT_URL = "http://localhost:6333"   # change if needed
QDRANT_API_KEY = None                 # set if using cloud
EMBEDDING_DIMENSION = 768              # MUST match your embedding model
DEFAULT_COLLECTION = "excel_vectors"


# =========================================================
# QDRANT CLIENT
# =========================================================
def vectordb(collection: str = DEFAULT_COLLECTION) -> QdrantClient:
    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY
    )

    collections = client.get_collections().collections
    existing = [c.name for c in collections]

    if collection not in existing:
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(
                size=EMBEDDING_DIMENSION,
                distance=Distance.COSINE
            )
        )
        print(f"✅ Qdrant collection created: {collection}")

    return client


# =========================================================
# EMBEDDING (USE YOUR EXISTING MODEL HERE)
# =========================================================
def data_embedding(text: str) -> List[float]:
    """
    Replace this body with your real embedding logic.
    MUST return List[float] of size EMBEDDING_DIMENSION
    """
    raise NotImplementedError("Plug your embedding model here")


# =========================================================
# EXCEL HELPERS
# =========================================================
def detect_title_and_header(df: pd.DataFrame):
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


def sheet_to_text(df: pd.DataFrame, title: str | None, header_row: int | None):
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


def chunk_text(text: str, size: int = 600, overlap: int = 100):
    chunks = []
    start = 0
    length = len(text)

    while start < length:
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap

    return chunks


# =========================================================
# EXCEL UPLOAD → QDRANT
# =========================================================
def excel_upload(
    excel_path: str,
    collection_name: str,
    document_link: str,
    chunk_size: int = 600,
    chunk_overlap: int = 100
):
    """
    Excel → Qdrant upload

    Metadata format:
    {"document_link": "<document_link>"}
    """

    excel_path = os.path.abspath(os.path.expanduser(excel_path))
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel not found: {excel_path}")

    client = vectordb(collection=collection_name)
    xls = pd.ExcelFile(excel_path, engine="openpyxl")

    points: List[PointStruct] = []

    print(f"📄 Excel sheets detected: {xls.sheet_names}")

    for page_index, sheet_name in enumerate(xls.sheet_names):
        df = xls.parse(sheet_name, header=None)

        title, header_row = detect_title_and_header(df)
        sheet_text = sheet_to_text(df, title, header_row)

        if not sheet_text.strip():
            continue

        chunks = chunk_text(sheet_text, chunk_size, chunk_overlap)

        for chunk_index, chunk in enumerate(chunks):
            embedding = data_embedding(chunk)
            if embedding is None:
                continue

            payload = {
                "document_link": document_link,
                "sheet_name": sheet_name,
                "page": page_index,
                "chunk": chunk_index,
                "title": title
            }

            points.append(
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload=payload
                )
            )

    if points:
        client.upsert(
            collection_name=collection_name,
            points=points
        )

    print(f"✅ Excel upload completed → {len(points)} vectors stored")
    return {"status": "success", "vectors": len(points)}


# =========================================================
# SIMILARITY SEARCH
# =========================================================
def similarity_search(
    query: str,
    collection_name: str,
    top_k: int = 5
):
    client = vectordb(collection=collection_name)
    query_vector = data_embedding(query)

    results = client.search(
        collection_name=collection_name,
        query_vector=query_vector,
        limit=top_k
    )

    return [
        {
            "score": hit.score,
            "metadata": hit.payload
        }
        for hit in results
    ]
