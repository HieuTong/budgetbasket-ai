from fastapi import APIRouter

from app.agent.agent import BudgetAgent
from app.ml.optimizer import BasketItem
from app.schemas import ChatRequest

router = APIRouter()


@router.post("/")
def chat(req: ChatRequest):
    agent = BudgetAgent()
    candidates = [
        BasketItem(product_id=1, name="Milk 2L", unit_price=3.50, utility=0.9),
        BasketItem(product_id=2, name="Bread", unit_price=3.00, utility=0.8),
        BasketItem(product_id=3, name="Eggs 12pk", unit_price=6.50, utility=0.7),
    ]
    context = {"candidates": [c.__dict__ for c in candidates], "products": []}
    reply = agent.run(req.message, context)
    return {"reply": reply}
