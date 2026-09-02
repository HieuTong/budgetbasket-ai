from pydantic import BaseModel


class BasketRequest(BaseModel):
    user_id: int
    budget: float


class ChatRequest(BaseModel):
    user_id: int
    message: str
