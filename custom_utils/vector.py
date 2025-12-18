import os
import requests
from typing import Optional, List, Tuple, Any, Union
import pandas as pd
from uuid import uuid4
from datetime import datetime

# SQLAlchemy & PGVector Imports
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, BigInteger, ARRAY, func
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector

# OpenAI Imports
from langchain_openai import AzureOpenAIEmbeddings
from langchain_core.documents import Document as LCDocument

from dotenv import load_dotenv
load_dotenv()

# --- Database Setup ---

VECTOR_DB_URL = os.environ.get("CUSTOMV_DB")
print("custome vector db:", VECTOR_DB_URL[-20:])
if not VECTOR_DB_URL:
    raise ValueError("CUSTOMV_DB environment variable is not set.")

engine = create_engine(VECTOR_DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Models ---


class UploadedDocumentModel(Base):
    """
    Matches the 'uploaded_documents' table.
    Used for tracking file metadata.
    """
    __tablename__ = 'uploaded_documents'

    id = Column(Integer, primary_key=True)
    conversation_id = Column(String)
    file_name = Column(String)
    original_file_name = Column(String)
    file_size = Column(BigInteger)
    file_type = Column(String)
    blob_url = Column(Text)
    summary = Column(Text)
    key_points = Column(ARRAY(Text))
    upload_timestamp = Column(DateTime(timezone=True),
                              server_default=func.now())
    user_email = Column(String)


class DocumentModel(Base):
    """
    Matches the 'documents' table.
    Used for storing vector chunks.
    """
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True)
    document_id = Column(String)
    document_name = Column(String)
    chunk_index = Column(Integer)
    chunk_text = Column(Text)

    # OpenAI 'text-embedding-3-small' uses 1536 dimensions
    embedding = Column(Vector(1536))

    metadata_ = Column("metadata", JSONB)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(),
                        onupdate=func.now())

# Create tables if they don't exist
# Base.metadata.create_all(engine)

# --- Embedding Helper ---


def data_embedding(data: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
    """
    Generates text embeddings using Azure OpenAI 'text-embedding-3-small'.
    """
    try:
        # Initialize Azure OpenAI Embeddings
        # Make sure these ENV variables are set in your .env file
        embeddings_model = AzureOpenAIEmbeddings(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version="2024-02-15-preview",
            azure_deployment="text-embedding-ada-002",
        )

        # Handle both single string and list of strings
        if isinstance(data, list):
            return embeddings_model.embed_documents(data)
        else:
            embedding = embeddings_model.embed_query(data)
            # print("📝 Generated text embedding.")
            return embedding

    except Exception as e:
        print(f"⚠️ Failed to embed data: {e}")
        return None

# --- Upload Functions ---


def vector_upload(
    data: str,
    metadata: dict,
    collection_name: str,
    id: Optional[int] = None
):
    """
    Uploads a single text chunk to the 'documents' table.
    """
    session = SessionLocal()
    try:
        embedding = data_embedding(data)
        if embedding is None:
            return {"status": "failed", "reason": "Embedding generation failed"}

        doc_name = metadata.get("title", "Untitled")
        doc_id = metadata.get("document_id", str(uuid4()))
        chunk_idx = metadata.get("chunk", 0)

        new_doc = DocumentModel(
            document_id=doc_id,
            document_name=doc_name,
            chunk_index=chunk_idx,
            chunk_text=data,
            embedding=embedding,
            metadata_=metadata
        )

        session.add(new_doc)
        session.commit()
        # print("✅ upload completed to 'documents' table")

        return {"context": data, "collection_id": collection_name, "metadata": metadata}

    except Exception as e:
        session.rollback()
        print(f"❌ Upload failed: {e}")
        return {"status": "failed", "error": str(e)}
    finally:
        session.close()


def excel_upload(
    excel_path: str,
    collection_name: str,
    document_link: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 70
):
    """
    Reads Excel -> Chunks -> Inserts into 'documents' table.
    """
    excel_path = os.path.abspath(os.path.expanduser(excel_path))
    if not os.path.exists(excel_path):
        raise FileNotFoundError(f"Excel file not found: {excel_path}")

    xls = pd.ExcelFile(excel_path, engine="openpyxl")
    results = []

    session = SessionLocal()
    file_doc_id = str(uuid4())

    try:
        print(f"📄 Excel sheets detected: {xls.sheet_names}")

        for page_index, sheet_name in enumerate(xls.sheet_names):
            df = xls.parse(sheet_name, header=None)

            text_blocks = []
            for _, row in df.iterrows():
                row_text = " | ".join([str(v) for v in row if pd.notna(v)])
                if row_text.strip():
                    text_blocks.append(row_text)
            full_text = "\n".join(text_blocks)

            if not full_text.strip():
                continue

            start = 0
            length = len(full_text)
            chunk_idx = 0

            while start < length:
                end = start + chunk_size
                chunk_text = full_text[start:end]
                start = end - chunk_overlap

                embedding = data_embedding(chunk_text)
                if embedding:
                    metadata = {
                        "document_link": document_link,
                        "sheet_name": sheet_name,
                        "page": page_index,
                        "chunk": chunk_idx,
                        "original_file": os.path.basename(excel_path),
                        "document_id": file_doc_id
                    }

                    db_doc = DocumentModel(
                        document_id=file_doc_id,
                        document_name=os.path.basename(excel_path),
                        chunk_index=chunk_idx,
                        chunk_text=chunk_text,
                        embedding=embedding,
                        metadata_=metadata
                    )
                    session.add(db_doc)
                    results.append(
                        {"status": "success", "sheet": sheet_name, "chunk": chunk_idx})

                chunk_idx += 1

        session.commit()
        print(f"✅ Excel upload completed → {len(results)} chunks stored.")
        return results

    except Exception as e:
        session.rollback()
        print(f"❌ Excel upload failed: {e}")
        return [{"status": "failed", "error": str(e)}]
    finally:
        session.close()

# --- Retrieval Function ---


def retrive(
    user_query: str,
    k: int = 5
) -> List[Tuple[LCDocument, float]]:
    """
    Generates embedding for query and searches 'documents' table via Cosine Similarity.
    """
    session = SessionLocal()
    try:
        query_embedding = data_embedding(user_query)
        if query_embedding is None:
            return []

        # Cosine Distance (<=>)
        results = session.query(
            DocumentModel,
            DocumentModel.embedding.cosine_distance(
                query_embedding).label("distance")
        ).order_by(
            DocumentModel.embedding.cosine_distance(query_embedding)
        ).limit(k).all()

        formatted_results = []
        for doc_row, distance in results:
            lc_doc = LCDocument(
                page_content=doc_row.chunk_text,
                metadata=doc_row.metadata_ or {}
            )

            lc_doc.metadata["document_id"] = doc_row.document_id
            lc_doc.metadata["id"] = doc_row.id

            # Distance 0 = Exact match (Score 1.0)
            score = float(distance)

            formatted_results.append((lc_doc, score))

        return formatted_results

    except Exception as e:
        print(f"❌ Retrieval failed: {e}")
        return []
    finally:
        session.close()
