from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agent.agent import BudgetAgent
from app.db.repositories.purchases import get_user_purchases
from app.db.session import get_db
from app.schemas import ChatRequest


router = APIRouter()


@router.post("/")
def chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
):
    purchases = get_user_purchases(
        db,
        req.user_id,
    )

    context = {
        "user_id": req.user_id,
        "purchase_history_count": len(purchases),
    }

    reply = BudgetAgent().run(
        req.message,
        context,
        db,
    )

    return {
        "reply": reply,
    }