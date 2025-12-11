import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, Iterator, Tuple
from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointTuple
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
import uuid

class JSONCheckpointSaver(BaseCheckpointSaver):
    """Saves conversation state to JSON files using thread_id as filename."""
    
    def __init__(self, sessions_folder: str = "sessions"):
        self.sessions_folder = Path(sessions_folder)
        self.sessions_folder.mkdir(exist_ok=True)
    
    def _get_file_path(self, thread_id: str) -> Path:
        """Get JSON file path for a thread_id."""
        return self.sessions_folder / f"{thread_id}.json"
    
    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Load checkpoint tuple from JSON file."""
        thread_id = config["configurable"]["thread_id"]
        file_path = self._get_file_path(thread_id)
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Deserialize messages
            messages = []
            for msg_data in data.get("messages", []):
                msg = self._deserialize_message(msg_data)
                if msg:
                    messages.append(msg)
            
            # Create checkpoint
            checkpoint = {
                "v": 1,
                "id": data.get("checkpoint_id", str(uuid.uuid4())),
                "ts": data.get("timestamp", ""),
                "channel_values": {
                    "messages": messages
                },
                "channel_versions": {},
                "versions_seen": {}
            }
            
            checkpoint_tuple = CheckpointTuple(
                config=config,
                checkpoint=checkpoint,
                metadata=data.get("metadata", {}),
                parent_config=None
            )
            
            print(f"✅ Loaded checkpoint from: {file_path} ({len(messages)} messages)")
            return checkpoint_tuple
            
        except Exception as e:
            print(f"❌ Error loading checkpoint: {e}")
            return None
    
    # def put(self, config: RunnableConfig, checkpoint: Checkpoint, metadata: dict, new_versions: dict) -> RunnableConfig:
    #     """Save checkpoint to JSON file."""
    #     thread_id = config["configurable"]["thread_id"]
    #     file_path = self._get_file_path(thread_id)
        
    #     try:
    #         # Extract messages from checkpoint
    #         messages = checkpoint.get("channel_values", {}).get("messages", [])
            
    #         # Serialize messages
    #         serialized_messages = []
    #         for msg in messages:
    #             serialized_msg = self._serialize_message(msg)
    #             if serialized_msg:
    #                 serialized_messages.append(serialized_msg)
            
    #         # Create data structure
    #         data = {
    #             "thread_id": thread_id,
    #             "checkpoint_id": checkpoint.get("id", str(uuid.uuid4())),
    #             "timestamp": checkpoint.get("ts", ""),
    #             "messages": serialized_messages,
    #             "metadata": metadata,
    #             "new_versions": new_versions
    #         }
            
    #         # Save to file
    #         with open(file_path, 'w', encoding='utf-8') as f:
    #             json.dump(data, f, indent=2, ensure_ascii=False)
            
    #         print(f"✅ Saved checkpoint to: {file_path} ({len(serialized_messages)} messages)")
            
    #     except Exception as e:
    #         print(f"❌ Error saving checkpoint: {e}")
        
    #     return config

    # def _serialize_message(self, msg: Any) -> Optional[Dict]:
    #     """Convert message object to JSON-serializable dict."""
    #     try:
    #         if isinstance(msg, BaseMessage):
    #             return {
    #                 "type": msg.type,
    #                 "content": msg.content,
    #                 "additional_kwargs": getattr(msg, "additional_kwargs", {}),
    #                 "response_metadata": getattr(msg, "response_metadata", {})
    #             }
    #         elif isinstance(msg, dict):
    #             return msg
    #         else:
    #             return {"type": "unknown", "content": str(msg)}
    #     except Exception as e:
    #         print(f"Error serializing message: {e}")
    #         return None

    def put(self, config: RunnableConfig, checkpoint: Checkpoint, metadata: dict, new_versions: dict) -> RunnableConfig:
        """Save checkpoint to JSON file."""
        thread_id = config["configurable"]["thread_id"]
        file_path = self._get_file_path(thread_id)
        
        try:
            # Extract messages from checkpoint
            messages = checkpoint.get("channel_values", {}).get("messages", [])
            
            # Filter: Keep only human and AI messages (remove tool messages and duplicates)
            conversation_messages = []
            seen_content = set()
            
            for msg in messages:
                # Only keep human and AI messages
                if hasattr(msg, 'type') and msg.type in ['human', 'ai']:
                    # Create unique identifier to avoid duplicates
                    content_key = f"{msg.type}:{msg.content[:100]}"
                    
                    if content_key not in seen_content:
                        seen_content.add(content_key)
                        serialized_msg = self._serialize_message(msg)
                        if serialized_msg:
                            conversation_messages.append(serialized_msg)
            
            # Create data structure
            data = {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint.get("id", str(uuid.uuid4())),
                "timestamp": checkpoint.get("ts", ""),
                "messages": conversation_messages,
                "metadata": metadata,
                "new_versions": new_versions
            }
            
            # Save to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Saved checkpoint to: {file_path} ({len(conversation_messages)} conversation messages)")
            
        except Exception as e:
            print(f"❌ Error saving checkpoint: {e}")
        
        return config
    
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

    def put_writes(self, config: RunnableConfig, writes: list, task_id: str) -> None:
        """Store intermediate writes - not needed for simple JSON storage."""
        # For simple file-based storage, we don't need to track individual writes
        # This method is required by the interface but can be a no-op
        pass
    
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
    
    def list(self, config: RunnableConfig, *, filter: Optional[Dict[str, Any]] = None, before: Optional[RunnableConfig] = None, limit: Optional[int] = None) -> Iterator[CheckpointTuple]:
        """List checkpoints - returns empty iterator for simplicity."""
        return iter([])