from fastapi import APIRouter

from app.ml.optimizer import BasketItem, optimize_basket
from app.schemas import BasketRequest

router = APIRouter()


@router.post("/optimize")
def optimize(req: BasketRequest):
    # In production: build `candidates` from the user's purchase history +
    # catalog (utility score derived from purchase frequency + nutrition fit).
    # Placeholder candidates for demoability without full DB wiring:
    candidates = [
        BasketItem(product_id=1, name="Milk 2L", unit_price=3.50, utility=0.9, usual_quantity=1),
        BasketItem(product_id=2, name="Bread", unit_price=3.00, utility=0.8, usual_quantity=2),
        BasketItem(product_id=3, name="Eggs 12pk", unit_price=6.50, utility=0.7, usual_quantity=1),
        BasketItem(product_id=4, name="Chicken Breast 1kg", unit_price=9.00, utility=0.85, usual_quantity=1),
        BasketItem(product_id=5, name="Rice 1kg", unit_price=2.80, utility=0.6, usual_quantity=1),
    ]
    result = optimize_basket(candidates, req.budget)
    return {
        "items": [{"name": c.name, "qty": q, "unit_price": c.unit_price} for c, q in result.items],
        "total_cost": result.total_cost,
        "total_utility": result.total_utility,
    }
