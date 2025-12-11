import json
import uuid
from typing import Optional, Dict, Any, Iterator, Tuple, List
from datetime import datetime

# SQLAlchemy Imports
from sqlalchemy import create_engine, Column, String, Text, Integer, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.exc import SQLAlchemyError

# LangChain/LangGraph Imports
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointTuple
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import (
    BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
)

# --- Database Setup ---

Base = declarative_base()

class LanggraphMessage(Base):
    __tablename__ = 'langgraph_messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    checkpoint_id = Column(String(255), ForeignKey('langgraph_checkpoints.id'), index=True, nullable=False)
    thread_id = Column(String(255), index=True, nullable=False)
    idx = Column(Integer, nullable=False)
    message_json = Column(Text, nullable=False)
    
    checkpoint = relationship("LanggraphCheckpoint", back_populates="messages")

class LanggraphCheckpoint(Base):
    __tablename__ = 'langgraph_checkpoints'

    id = Column(String(255), primary_key=True)
    thread_id = Column(String(255), index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    checkpoint_data = Column(Text, nullable=False)
    metadata_json = Column(Text, default="{}")
    new_versions_json = Column(Text, default="{}")
    
    messages = relationship(
        "LanggraphMessage",
        order_by="LanggraphMessage.idx", 
        back_populates="checkpoint",
        cascade="all, delete-orphan"
    )

# --- Custom Checkpoint Saver ---

class PostgresCheckpointSaver(BaseCheckpointSaver):
    """
    Saves conversation state to PostgreSQL using SQLAlchemy.
    Includes logic to filter duplicates and maintain clean history.
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
            else:
                return None
        except Exception as e:
            print(f"Error serializing message: {e}")
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
                
        except Exception as e:
            print(f"Error deserializing message: {e}")
            return None

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        thread_id = config["configurable"]["thread_id"]
        session = self.Session()
        
        try:
            latest_checkpoint = session.query(LanggraphCheckpoint) \
                .filter(LanggraphCheckpoint.thread_id == thread_id) \
                .order_by(LanggraphCheckpoint.timestamp.desc()) \
                .first()

            if not latest_checkpoint:
                return None

            checkpoint = json.loads(latest_checkpoint.checkpoint_data)
            metadata = json.loads(latest_checkpoint.metadata_json)
            
            messages = []
            for msg_record in latest_checkpoint.messages:
                msg_data = json.loads(msg_record.message_json)
                msg = self._deserialize_message(msg_data)
                if msg:
                    messages.append(msg)

            checkpoint["channel_values"]["messages"] = messages
            
            return CheckpointTuple(
                config=config,
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=None
            )

        except Exception as e:
            print(f"❌ Error loading checkpoint: {e}")
            return None
        finally:
            session.close()

    def put(self, config: RunnableConfig, checkpoint: Checkpoint, metadata: dict, new_versions: dict) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        session = self.Session()
        
        try:
            # 1. Extract messages
            raw_messages = checkpoint.get("channel_values", {}).get("messages", [])
            
            # 2. FILTERING LOGIC (Restored from original json_checkpointer.py)
            # This prevents infinite duplication and token explosion
            conversation_messages = []
            seen_content = set()
            
            for msg in raw_messages:
                # Keep only Human and AI messages (ignoring tool calls/intermediate steps)
                # This matches your original file's behavior.
                msg_type = getattr(msg, 'type', None) or msg.get('type') if isinstance(msg, dict) else None
                msg_content = getattr(msg, 'content', "") or msg.get('content') if isinstance(msg, dict) else ""
                
                if msg_type in ['human', 'ai']:
                    # Create unique identifier to avoid duplicates
                    content_key = f"{msg_type}:{msg_content[:100]}"
                    
                    if content_key not in seen_content:
                        seen_content.add(content_key)
                        conversation_messages.append(msg)

            # 3. Prepare checkpoint data (excluding raw messages list)
            checkpoint_data_to_save = checkpoint.copy()
            if "channel_values" in checkpoint_data_to_save:
                checkpoint_data_to_save["channel_values"] = checkpoint_data_to_save["channel_values"].copy()
                checkpoint_data_to_save["channel_values"]["messages"] = [] 

            checkpoint_id = checkpoint.get("id", str(uuid.uuid4()))
            ts_str = checkpoint.get("ts")
            
            if ts_str:
                try:
                    ts = datetime.strptime(ts_str, '%Y-%m-%dT%H:%M:%S.%f%z')
                except ValueError:
                    ts = datetime.utcnow()
            else:
                ts = datetime.utcnow()
            
            # 4. Create DB Records
            new_checkpoint = LanggraphCheckpoint(
                id=checkpoint_id,
                thread_id=thread_id,
                timestamp=ts,
                checkpoint_data=json.dumps(checkpoint_data_to_save, default=str),
                metadata_json=json.dumps(metadata, default=str),
                new_versions_json=json.dumps(new_versions, default=str),
            )
            
            message_records = []
            for idx, msg in enumerate(conversation_messages):
                serialized_msg = self._serialize_message(msg)
                if serialized_msg:
                    message_record = LanggraphMessage(
                        checkpoint_id=checkpoint_id,
                        thread_id=thread_id,
                        idx=idx,
                        message_json=json.dumps(serialized_msg, default=str)
                    )
                    message_records.append(message_record)

            session.add(new_checkpoint)
            session.add_all(message_records)
            session.commit()
            
        except Exception as e:
            session.rollback()
            print(f"❌ Error saving checkpoint: {e}")
        finally:
            session.close()
            
        return config

    def put_writes(self, config: RunnableConfig, writes: list, task_id: str) -> None:
        pass

    def list(self, config: RunnableConfig, *, filter: Optional[Dict[str, Any]] = None, before: Optional[RunnableConfig] = None, limit: Optional[int] = None) -> Iterator[CheckpointTuple]:
        return iter([])
    
    