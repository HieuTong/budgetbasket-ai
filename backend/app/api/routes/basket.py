from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.repositories.products import list_products
from app.db.repositories.purchases import get_user_purchases
from app.db.session import get_db
from app.ml.optimizer import BasketItem, optimize_basket
from app.schemas import BasketRequest
from app.services.personalization import personalized_utility

router = APIRouter()


@router.post("/optimize")
def optimize(req: BasketRequest, db: Session = Depends(get_db)):
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

    result = optimize_basket(candidates, req.budget)
    return {
        "user_id": req.user_id,
        "items": [
            {
                "product_id": item.product_id,
                "name": item.name,
                "qty": quantity,
                "unit_price": item.unit_price,
                "utility": item.utility,
            }
            for item, quantity in result.items
        ],
        "total_cost": result.total_cost,
        "total_utility": result.total_utility,
        "candidate_count": len(candidates),
        "purchase_history_count": len(purchases),
    }
