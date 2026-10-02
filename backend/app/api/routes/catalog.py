from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.repositories.prices import list_product_prices
from app.db.repositories.products import get_product
from app.db.session import get_db
from app.services.catalog import list_catalog

router = APIRouter()


@router.get("/products")
def products(
    category: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return {
        "items": list_catalog(
            db,
            category=category,
            search=search,
            limit=limit,
        )
    }


@router.get("/products/{product_id}/prices")
def product_prices(product_id: int, db: Session = Depends(get_db)):
    product = get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="product_not_found")

    observations = list_product_prices(db, product_id)
    return {
        "product_id": product_id,
        "product_name": product.name,
        "items": [
            {
                "price": float(observation.price),
                "observed_at": observation.observed_at,
                "source": observation.source,
                "store_id": observation.store_id,
                "is_estimated": observation.is_estimated,
            }
            for observation in observations
        ],
    }
