from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class Message(BaseModel):
    """Represents a single message in the chat conversation"""
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_call_id: str | None = Field(default=None)  # Used to link tool responses to their calls
    name: str | None = Field(default=None)  # Name of the tool being called

class OpenAIRequest(BaseModel):
    """Mirrors the OpenAI chat completion request structure"""
    model: str
    messages: list[Message]
    temperature: Optional[float] = None
    top_p: Optional[int] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    user: Optional[str] = None
    stream: Optional[bool] = None
    tools: Optional[list[dict]]  # Tool definitions following OpenAI's format 