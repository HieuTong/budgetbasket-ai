from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agent.agent import BudgetAgent
from app.agent.tracing import AgentTrace
from app.db.session import get_db
from app.schemas import ChatRequest
from app.services.basket import build_basket_candidates

router = APIRouter()

# Plain-language labels so users can see what the assistant actually did.
STEP_LABELS = {
    "find_products": "Searched the catalogue",
    "make_product_decision": "Checked buy or wait",
    "explain_price_trend": "Checked price history",
    "find_substitutes": "Looked for cheaper swaps",
    "run_budget_optimizer": "Optimised your basket",
    "retrieve_savings_tips": "Looked up savings tips",
}


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

    trace = AgentTrace()
    reply = BudgetAgent().run(
        req.message,
        context,
        db,
        trace=trace,
        history=[turn.model_dump() for turn in req.history],
    )

    return {
        "reply": reply,
        "steps": [
            {"tool": call.name, "label": STEP_LABELS.get(call.name, call.name), "ok": call.ok}
            for call in trace.tool_calls
        ],
    }
