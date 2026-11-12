from typing import Literal

from pydantic import BaseModel, Field


class BasketRequest(BaseModel):
    # No user_id: the server takes the user from the login token, never from the request.
    budget: float


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    # Earlier turns of this conversation, oldest first, so follow-up questions make sense.
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
