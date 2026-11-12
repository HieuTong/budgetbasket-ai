from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agent.agent import BudgetAgent
from app.agent.tracing import AgentTrace
from app.api.deps import get_current_user
from app.db.models import User
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


def basket_from_trace(trace: AgentTrace) -> dict | None:
    """The basket the assistant built in this reply, so the page can offer to use it.

    Taken from the trace, which already records each tool's result, so the agent loop
    doesn't change. If the optimiser ran more than once, the last successful run wins,
    because that is the basket the reply describes. Items without a product id are
    skipped: the page needs ids to edit the basket later.
    """
    for call in reversed(trace.tool_calls):
        if call.name != "run_budget_optimizer" or not call.ok:
            continue
        result = call.result if isinstance(call.result, dict) else {}
        items = [
            {
                "product_id": item["product_id"],
                "name": item["name"],
                "qty": item["qty"],
                "unit_price": item["unit_price"],
            }
            for item in result.get("items", [])
            if isinstance(item, dict) and item.get("product_id") is not None
        ]
        if not items:
            return None
        budget = call.args.get("budget")
        return {
            "budget": float(budget) if isinstance(budget, (int, float)) else None,
            "items": items,
            "total_cost": result.get("total_cost"),
        }
    return None


@router.post("/")
def chat(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # The same candidates the basket page uses, so "build me a basket" in chat
    # optimises the user's real products instead of an empty list.
    candidates, purchase_count = build_basket_candidates(db, user.id)

    context = {
        "user_id": user.id,
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
        # Offered to the user, never applied automatically: the page shows a button.
        "basket": basket_from_trace(trace),
    }
