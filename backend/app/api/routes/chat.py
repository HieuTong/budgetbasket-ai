from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agent.agent import BudgetAgent
from app.db.repositories.products import list_products
from app.db.repositories.purchases import get_user_purchases
from app.db.session import get_db
from app.ml.optimizer import BasketItem
from app.schemas import ChatRequest
from app.services.personalization import personalized_utility

router = APIRouter()


@router.post("/")
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    products = list_products(db)
    purchases = get_user_purchases(db, req.user_id)

    candidates = [
        BasketItem(
            product_id=product.id,
            name=product.name,
            unit_price=product.unit_price,
            utility=personalized_utility(product, purchases),
            usual_quantity=1,
        )
        for product in products
        if product.unit_price > 0
    ]

    product_context = [
        {
            "id": product.id,
            "name": product.name,
            "category": product.category or "",
            "unit_price": product.unit_price,
            "nutrition_tags": product.nutrition_tags or "",
        }
        for product in products
    ]

    context = {
        "user_id": req.user_id,
        "candidates": [candidate.__dict__ for candidate in candidates],
        "products": product_context,
        "purchase_history_count": len(purchases),
    }

    reply = BudgetAgent().run(req.message, context)
    return {"reply": reply}
