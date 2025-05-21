### message.py
import json
import socket
import time
import uuid
from enum import Enum

class MessageType(Enum):
    DISCOVERY = "discovery"
    PAIRING_REQUEST = "pairing_request"
    PAIRING_RESPONSE = "pairing_response"
    CLIPBOARD_DATA = "clipboard_data"
    PING = "ping"
    
class Message:
    def __init__(self, msg_type, data=None, sender_ip=None, sender_name=None):
        self.type = msg_type
        self.data = data or {}
        self.sender_ip = sender_ip
        self.sender_name = sender_name
        self.timestamp = time.time()
        self.id = str(uuid.uuid4())
        
    def to_json(self):
        return json.dumps({
            "type": self.type.value if isinstance(self.type, MessageType) else self.type,
            "data": self.data,
            "sender_ip": self.sender_ip,
            "sender_name": self.sender_name,
            "timestamp": self.timestamp,
            "id": self.id
        })
        
    @classmethod
    def from_json(cls, json_str):
        try:
            data = json.loads(json_str)
            msg = cls(
                MessageType(data["type"]) if isinstance(data["type"], str) else data["type"],
                data["data"],
                data["sender_ip"],
                data["sender_name"]
            )
            msg.timestamp = data["timestamp"]
            msg.id = data["id"]
            return msg
        except Exception as e:
            print(f"Error parsing message: {e}")
            return None