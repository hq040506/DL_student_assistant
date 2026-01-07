import json
import os
import uuid
from typing import Dict, Any

HISTORY_FILE = "chat_history.json"

class ChatHistoryManager:
    def __init__(self):
        self.file_path = HISTORY_FILE
        self._ensure_file()

    def _ensure_file(self):
        if not os.path.exists(self.file_path):
            self.save_history({})

    def load_history(self) -> Dict[str, Any]:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading history: {e}")
            return {}

    def save_history(self, sessions: Dict[str, Any]):
        try:
            # Convert any non-serializable objects if necessary (e.g. DataFrames)
            # Since we store DataFrames in messages for display, we need to be careful.
            # Actually, for persistence, we might only want to store the text content and SQL.
            # Re-executing SQL to get DataFrame is safer than serializing DataFrame.
            # BUT, for simplicity, let's assume we strip 'data' (DataFrame) before saving, 
            # or convert it to dict/json.
            
            serializable_sessions = {}
            for sid, sess in sessions.items():
                serializable_messages = []
                for msg in sess["messages"]:
                    # Create a copy to modify
                    s_msg = msg.copy()
                    if "data" in s_msg:
                        # Don't save DataFrame object
                        del s_msg["data"]
                    if "plot" in s_msg:
                        # Don't save plot object if any
                        pass
                    serializable_messages.append(s_msg)
                
                serializable_sessions[sid] = {
                    "title": sess["title"],
                    "messages": serializable_messages,
                    "pending": None # Don't save pending state
                }

            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(serializable_sessions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")

    def create_session(self, title="新对话") -> str:
        return str(uuid.uuid4())
