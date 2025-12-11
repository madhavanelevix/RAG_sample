import json
import uuid
from typing import Optional, Dict, Any, Iterator, List, Set
from datetime import datetime

# SQLAlchemy Imports
from sqlalchemy import create_engine, Column, String, Text, Integer, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.sql import func

# LangChain/LangGraph Imports
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointTuple
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import (
    BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
)

# --- Database Setup ---

Base = declarative_base()

class LanggraphCheckpoint(Base):
    """
    Table: 'langgraph_checkpoints' (Acts as the Session table)
    Stores session metadata and the raw checkpoint blob (state without messages).
    """
    __tablename__ = 'langgraph_checkpoints'

    # id = session id or thread_id
    id = Column(String(255), primary_key=True) 
    user_id = Column(String(255), nullable=True)
    
    # Store minimal checkpoint data to resume state
    checkpoint_blob = Column(Text, nullable=False) 
    metadata_blob = Column(Text, default="{}")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationship to messages
    messages = relationship(
        "LanggraphMessage",
        order_by="LanggraphMessage.message_number", 
        back_populates="session",
        cascade="all, delete-orphan"
    )

class LanggraphMessage(Base):
    """
    Table: 'langgraph_messages'
    Stores individual chat messages strictly ordered by number.
    """
    __tablename__ = 'langgraph_messages'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Links to the session
    thread_id = Column(String(255), ForeignKey('langgraph_checkpoints.id'), index=True, nullable=False)
    user_id = Column(String(255), nullable=True)
    
    # Sequential number: 1, 2, 3...
    message_number = Column(Integer, nullable=False)
    
    # Author type: "human" or "ai"
    type = Column(String(50), nullable=False)
    
    # Content
    content = Column(Text, nullable=False)
    
    # Additional knowledge (JSON)
    additional_kwargs = Column(Text, default="{}")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    session = relationship("LanggraphCheckpoint", back_populates="messages")


# --- Custom Checkpoint Saver ---

class PostgresCheckpointSaver(BaseCheckpointSaver):
    """
    Saves conversation state to PostgreSQL.
    Features:
    1. Robust Deduplication: Prevents saving identical messages.
    2. Session/Message Split: Uses two tables as requested.
    """
    
    def __init__(self, postgres_url: str):
        self.engine = create_engine(postgres_url)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def _serialize_message(self, msg: Any) -> Optional[Dict]:
        """Convert message object to JSON-serializable dict."""
        try:
            if isinstance(msg, BaseMessage):
                return {
                    "type": msg.type,
                    "content": msg.content,
                    "additional_kwargs": getattr(msg, "additional_kwargs", {}),
                    "response_metadata": getattr(msg, "response_metadata", {})
                }
            elif isinstance(msg, dict):
                return {
                    "type": msg.get("type", "human"),
                    "content": msg.get("content", ""),
                    "additional_kwargs": msg.get("additional_kwargs", {}),
                    "response_metadata": msg.get("response_metadata", {})
                }
            return None
        except Exception:
            return None

    def _deserialize_message(self, msg_data: Dict) -> Optional[BaseMessage]:
        """Convert dict back to message object."""
        try:
            msg_type = msg_data.get("type", "human")
            content = msg_data.get("content", "")
            
            if msg_type == "human":
                return HumanMessage(content=content)
            elif msg_type == "ai":
                return AIMessage(
                    content=content,
                    additional_kwargs=msg_data.get("additional_kwargs", {}),
                    response_metadata=msg_data.get("response_metadata", {})
                )
            elif msg_type == "system":
                return SystemMessage(content=content)
            elif msg_type == "tool":
                return ToolMessage(
                    content=content,
                    tool_call_id=msg_data.get("tool_call_id", "")
                )
            else:
                return HumanMessage(content=content)
        except Exception:
            return None

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Load session and messages."""
        thread_id = config["configurable"]["thread_id"]
        session = self.Session()
        
        try:
            # 1. Fetch Session
            db_session = session.query(LanggraphCheckpoint).filter_by(id=thread_id).first()
            if not db_session:
                return None

            # 2. Parse State
            checkpoint = json.loads(db_session.checkpoint_blob)
            metadata = json.loads(db_session.metadata_blob)
            
            # 3. Fetch Messages
            db_messages = session.query(LanggraphMessage)\
                .filter_by(thread_id=thread_id)\
                .order_by(LanggraphMessage.message_number)\
                .all()

            messages = []
            for db_msg in db_messages:
                msg_data = {
                    "type": db_msg.type,
                    "content": db_msg.content,
                    "additional_kwargs": json.loads(db_msg.additional_kwargs)
                }
                msg_obj = self._deserialize_message(msg_data)
                if msg_obj:
                    messages.append(msg_obj)

            checkpoint["channel_values"]["messages"] = messages
            
            return CheckpointTuple(
                config=config,
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=None
            )
        except Exception as e:
            print(f"❌ Error loading: {e}")
            return None
        finally:
            session.close()

    def put(self, config: RunnableConfig, checkpoint: Checkpoint, metadata: dict, new_versions: dict) -> RunnableConfig:
        """Save session with strict deduplication."""
        thread_id = config["configurable"]["thread_id"]
        user_id = str(config["configurable"].get("user_id", ""))
        session = self.Session()
        
        try:
            # --- 1. PREPARE SESSION DATA ---
            current_messages = checkpoint.get("channel_values", {}).get("messages", [])
            
            # Save everything EXCEPT messages to the session blob
            checkpoint_data = checkpoint.copy()
            if "channel_values" in checkpoint_data:
                checkpoint_data["channel_values"] = checkpoint_data["channel_values"].copy()
                checkpoint_data["channel_values"]["messages"] = [] 

            # Update or Create Session
            db_session = session.query(LanggraphCheckpoint).filter_by(id=thread_id).first()
            if not db_session:
                db_session = LanggraphCheckpoint(
                    id=thread_id,
                    user_id=user_id,
                    checkpoint_blob=json.dumps(checkpoint_data, default=str),
                    metadata_blob=json.dumps(metadata, default=str)
                )
                session.add(db_session)
                session.flush()
            else:
                db_session.checkpoint_blob = json.dumps(checkpoint_data, default=str)
                db_session.metadata_blob = json.dumps(metadata, default=str)
                db_session.user_id = user_id

            # --- 2. ROBUST MESSAGE DEDUPLICATION ---
            
            # Step A: Get signatures of existing DB messages to prevent re-saving
            existing_msgs = session.query(LanggraphMessage.type, LanggraphMessage.content)\
                .filter_by(thread_id=thread_id).all()
            
            # Create a set of (type, content) tuples for O(1) lookups
            # content is hashed for memory efficiency if large, but here direct comparison is safer
            existing_signatures = set((m.type, m.content) for m in existing_msgs)
            
            # Step B: Filter incoming messages
            messages_to_save = []
            seen_in_batch = set() # To handle duplicates within the incoming batch itself

            for msg in current_messages:
                serialized = self._serialize_message(msg)
                if not serialized: continue
                
                m_type = serialized.get('type')
                m_content = serialized.get('content')

                # Filter 1: Empty Content
                if not m_content or not m_content.strip():
                    continue

                # Filter 2: Only Human/AI
                if m_type not in ['human', 'ai']:
                    continue

                signature = (m_type, m_content)

                # Filter 3: Already in DB?
                if signature in existing_signatures:
                    continue
                
                # Filter 4: Already seen in this current batch? (e.g. [A, B, A, B])
                if signature in seen_in_batch:
                    continue

                seen_in_batch.add(signature)
                messages_to_save.append(serialized)

            # --- 3. SAVE NEW MESSAGES ---
            
            if messages_to_save:
                # Get current highest message number
                max_num = session.query(func.max(LanggraphMessage.message_number))\
                    .filter_by(thread_id=thread_id).scalar() or 0
                
                for i, msg_data in enumerate(messages_to_save):
                    new_msg = LanggraphMessage(
                        thread_id=thread_id,
                        user_id=user_id,
                        message_number=max_num + 1 + i,
                        type=msg_data['type'],
                        content=msg_data['content'],
                        additional_kwargs=json.dumps(msg_data['additional_kwargs'])
                    )
                    session.add(new_msg)
                
                # print(f"✅ Saved {len(messages_to_save)} new unique messages.")

            session.commit()
            
        except Exception as e:
            session.rollback()
            print(f"❌ Error saving: {e}")
        finally:
            session.close()
            
        return config

    def put_writes(self, config: RunnableConfig, writes: list, task_id: str) -> None:
        pass

    def list(self, config: RunnableConfig, *, filter: Optional[Dict[str, Any]] = None, before: Optional[RunnableConfig] = None, limit: Optional[int] = None) -> Iterator[CheckpointTuple]:
        return iter([])
    
    