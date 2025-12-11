import json
from typing import Optional, Dict, Any, Iterator, Tuple, List
import uuid

# LangGraph/LangChain imports
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointTuple
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from datetime import datetime, timezone

# SQLAlchemy imports
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, LargeBinary, select
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

# --- 1. Define the SQLAlchemy Base and Checkpoint Table Model ---
Base = declarative_base()

class CheckpointModel(Base):
    """SQLAlchemy Model for the LangGraph Checkpoint."""
    __tablename__ = "checkpoints"

    # The thread_id is used as the primary key for simple overwriting
    thread_id = Column(String, primary_key=True, index=True)
    
    # Store the actual checkpoint data (serialized JSON)
    checkpoint_data = Column(Text, nullable=False)
    
    # Store the timestamp for tracking
    timestamp = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    
    # Store metadata (serialized JSON)
    metadata_json = Column(Text, default="{}")

    # The LangGraph 'id' field (checkpoint version)
    checkpoint_id = Column(String, nullable=False, default=lambda: str(uuid.uuid4()))

    def __repr__(self):
        return (f"CheckpointModel(thread_id='{self.thread_id}', "
                f"checkpoint_id='{self.checkpoint_id}', "
                f"timestamp='{self.timestamp}')")

# --- 2. The Checkpoint Saver Class ---

class PostgresCheckpointSaver(BaseCheckpointSaver):
    """Saves conversation state to a PostgreSQL database using SQLAlchemy."""
    
    def __init__(self, postgres_url: str):
        """
        Initializes the checkpointer with the PostgreSQL connection string.

        :param postgres_url: The full PostgreSQL connection URL (e.g., "postgresql+psycopg2://user:pass@host:port/dbname")
        """
        self.engine = create_engine(postgres_url)
        # Create the table if it doesn't exist
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Mapping of message types for deserialization (same as your JSON logic)
        self._message_type_map = {
            "human": HumanMessage,
            "ai": AIMessage,
            "system": SystemMessage,
            "tool": ToolMessage,
            # Fallback for others (like 'function', 'chat', etc.)
            "default": HumanMessage 
        }

    def _get_thread_id(self, config: RunnableConfig) -> str:
        """Helper to safely extract the thread_id."""
        return config["configurable"]["thread_id"]

    def _serialize_message(self, msg: Any) -> Optional[Dict]:
        """Convert message object to JSON-serializable dict."""
        if not isinstance(msg, BaseMessage):
            return None
        return {
            "type": msg.type,
            "content": msg.content,
            "additional_kwargs": getattr(msg, "additional_kwargs", {}),
            "response_metadata": getattr(msg, "response_metadata", {})
        }

    def _deserialize_message(self, msg_data: Dict) -> Optional[BaseMessage]:
        """Convert dict back to a BaseMessage object."""
        msg_type = msg_data.get("type", "human")
        content = msg_data.get("content", "")
        
        MessageClass = self._message_type_map.get(msg_type, self._message_type_map["default"])
        
        try:
            if MessageClass in [HumanMessage, SystemMessage]:
                return MessageClass(content=content)
            elif MessageClass == AIMessage:
                return AIMessage(
                    content=content,
                    additional_kwargs=msg_data.get("additional_kwargs", {}),
                    response_metadata=msg_data.get("response_metadata", {})
                )
            elif MessageClass == ToolMessage:
                return ToolMessage(
                    content=content,
                    tool_call_id=msg_data.get("tool_call_id", "")
                )
        except Exception as e:
            print(f"Error deserializing message type {msg_type}: {e}")
            return None
        return None

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Load checkpoint tuple from the database."""
        thread_id = self._get_thread_id(config)
        
        with self.SessionLocal() as session:
            try:
                # Retrieve the latest checkpoint for the thread_id
                stmt = select(CheckpointModel).where(CheckpointModel.thread_id == thread_id)
                model_instance = session.execute(stmt).scalars().first()

                if not model_instance:
                    return None
                
                # Deserialize the stored data
                data = json.loads(model_instance.checkpoint_data)
                metadata = json.loads(model_instance.metadata_json)
                
                # Reconstruct the Checkpoint structure
                checkpoint: Checkpoint = {
                    "v": data.get("v", 1), # Use stored version or default
                    "id": model_instance.checkpoint_id,
                    "ts": model_instance.timestamp.isoformat() if model_instance.timestamp else "",
                    # The 'messages' list is deserialized here
                    "channel_values": {
                        "messages": [
                            self._deserialize_message(msg_data)
                            for msg_data in data.get("channel_values", {}).get("messages", [])
                            if self._deserialize_message(msg_data) is not None
                        ]
                    },
                    "channel_versions": data.get("channel_versions", {}),
                    "versions_seen": data.get("versions_seen", {})
                }
                
                checkpoint_tuple = CheckpointTuple(
                    config=config,
                    checkpoint=checkpoint,
                    metadata=metadata,
                    parent_config=None
                )
                
                print(f"✅ Loaded checkpoint for thread: {thread_id}")
                return checkpoint_tuple
            
            except SQLAlchemyError as e:
                print(f"❌ DB Error loading checkpoint: {e}")
                return None
            except Exception as e:
                print(f"❌ Deserialization Error loading checkpoint: {e}")
                return None

    def put(self, config: RunnableConfig, checkpoint: Checkpoint, metadata: dict, new_versions: dict) -> RunnableConfig:
        """Save checkpoint to the database."""
        thread_id = self._get_thread_id(config)
        
        # Your original logic: Filter to keep only human and AI messages and remove duplicates
        messages = checkpoint.get("channel_values", {}).get("messages", [])
        
        # Prepare the conversation messages for storage (serialized)
        # Note: We are storing the *full* checkpoint structure, but filtering the messages
        # before saving, just as your original JSON implementation did.
        conversation_messages = []
        seen_content = set()
        
        for msg in messages:
            if hasattr(msg, 'type') and msg.type in ['human', 'ai', 'system']:
                # The de-duplication logic
                content_key = f"{msg.type}:{getattr(msg, 'content', '')[:100]}"
                if content_key not in seen_content:
                    seen_content.add(content_key)
                    serialized_msg = self._serialize_message(msg)
                    if serialized_msg:
                        conversation_messages.append(serialized_msg)

        # Create the data structure to store in the 'checkpoint_data' column
        checkpoint_to_store = {
            "v": checkpoint.get("v", 1),
            "id": checkpoint.get("id"),
            "ts": checkpoint.get("ts"),
            "channel_values": {
                # Store the filtered messages here
                "messages": conversation_messages
            },
            "channel_versions": checkpoint.get("channel_versions", {}),
            "versions_seen": checkpoint.get("versions_seen", {})
        }

        # Prepare for DB
        checkpoint_json = json.dumps(checkpoint_to_store, ensure_ascii=False)
        metadata_json = json.dumps(metadata, ensure_ascii=False)
        
        with self.SessionLocal() as session:
            try:
                # Create a new model instance or update the existing one
                model_instance = session.get(CheckpointModel, thread_id)
                
                if model_instance:
                    # Update existing record
                    model_instance.checkpoint_data = checkpoint_json
                    model_instance.metadata_json = metadata_json
                    model_instance.timestamp = datetime.now(timezone.utc)
                    model_instance.checkpoint_id = checkpoint.get("id", str(uuid.uuid4()))
                    session.merge(model_instance)
                else:
                    # Insert new record
                    new_checkpoint = CheckpointModel(
                        thread_id=thread_id,
                        checkpoint_data=checkpoint_json,
                        metadata_json=metadata_json,
                        checkpoint_id=checkpoint.get("id", str(uuid.uuid4()))
                    )
                    session.add(new_checkpoint)

                session.commit()
                print(f"✅ Saved checkpoint to DB for thread: {thread_id}")
            
            except SQLAlchemyError as e:
                session.rollback()
                print(f"❌ DB Error saving checkpoint: {e}")
            
        return config

    def put_writes(self, config: RunnableConfig, writes: list, task_id: str) -> None:
        """Required by BaseCheckpointSaver, but not implemented for simple storage."""
        pass
        
    def list(self, config: RunnableConfig, *, filter: Optional[Dict[str, Any]] = None, before: Optional[RunnableConfig] = None, limit: Optional[int] = None) -> Iterator[CheckpointTuple]:
        """Required by BaseCheckpointSaver, returning empty iterator for simplicity."""
        return iter([])
    