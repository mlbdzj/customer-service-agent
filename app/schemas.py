from pydantic import BaseModel

class ChatRequest(BaseModel):
    session_id: str
    user_id: str
    message: str

class ConfirmRequest(BaseModel):
    session_id: str
    confirmed: bool