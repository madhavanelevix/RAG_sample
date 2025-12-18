from pydantic import BaseModel
from sqlalchemy import create_engine, desc, asc
from sqlalchemy.orm import sessionmaker, Session

from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

from custom_utils.aichat_edited import DB_URL

load_dotenv()


if not DB_URL:
    raise ValueError("PG_VECTOR environment variable is not set.")

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class SessionListResponse(BaseModel):
    id: str
    session_name: Optional[str] = None
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChatMessageResponse(BaseModel):
    id: str
    message_number: int
    type: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
