from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agent.agent import BudgetAgent
from app.db.session import get_db
from app.schemas import ChatRequest
from app.services.basket import build_basket_candidates

router = APIRouter()


@router.post("/")
def chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
):
    # The same candidates the basket page uses, so "build me a basket" in chat
    # optimises the user's real products instead of an empty list.
    candidates, purchase_count = build_basket_candidates(db, req.user_id)

    context = {
        "user_id": req.user_id,
        "purchase_history_count": purchase_count,
        "candidates": candidates,
    }

    reply = BudgetAgent().run(
        req.message,
        context,
        db,
    )

    return {
        "reply": reply,
    }
