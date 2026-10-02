from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.repositories.products import list_basket_products
from app.db.repositories.purchases import get_user_purchases
from app.db.session import get_db
from app.ml.optimizer import BasketItem, optimize_basket
from app.schemas import BasketRequest
from app.services.personalization import (
    build_personalization_profile,
    personalized_utility_from_fields,
    usual_quantity_from_profile,
)

router = APIRouter()


@router.post("/optimize")
def optimize(req: BasketRequest, db: Session = Depends(get_db)):
    products = list_basket_products(db)
    purchases = get_user_purchases(db, req.user_id)

    profile = build_personalization_profile(
        purchases
    )

    reference_date = max(
        (
            purchase.purchased_at
            for purchase in purchases
            if purchase.purchased_at is not None
        ),
        default=None,
    )

    candidates = []

    for product in products:
        product_id = product.id
        name = product.name
        unit_price = float(product.unit_price)
        category = product.category
        sub_category = product.sub_category

        utility = 0.5

        if reference_date is not None:
            utility = personalized_utility_from_fields(
                product_id=product_id,
                category=category,
                sub_category=sub_category,
                product_name=name,
                profile=profile,
                reference_date=reference_date,
            )

        usual_quantity = usual_quantity_from_profile(
            product_id,
            profile,
        )
        
        candidates.append(
            BasketItem(
                product_id=product_id,
                name=name,
                unit_price=unit_price,
                utility=utility,
                usual_quantity=usual_quantity,
                max_quantity=usual_quantity,
            )
        )

    result = optimize_basket(
        candidates,
        req.budget,
        max_distinct_products=14,
    )

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

