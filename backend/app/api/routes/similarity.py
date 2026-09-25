from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Product, Purchase
from app.db.session import get_db
from app.services.similarity import (
    find_cheaper_substitutes,
    find_similar_products,
)


router = APIRouter(
    prefix="/similarity",
    tags=["similarity"],
)


@router.get("/{product_id}")
def get_similar_products(
    product_id: int,
    top_k: int = 5,
    db: Session = Depends(get_db),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    products = (
        db.query(Product)
        .all()
    )

    results = find_similar_products(
        product=product,
        products=products,
        top_k=top_k,
    )

    return {
        "product_id": product.id,
        "product_name": product.name,
        "brand": product.brand,
        "category": product.category,
        "results": [
            {
                "product_id": candidate.id,
                "product_name": candidate.name,
                "brand": candidate.brand,
                "category": candidate.category,
                "unit_price": candidate.unit_price,
                "similarity": round(
                    similarity,
                    4,
                ),
            }
            for candidate, similarity in results
        ],
    }


@router.get("/{product_id}/substitutes")
def get_cheaper_substitutes(
    product_id: int,
    top_k: int = 5,
    user_id: int | None = None,
    db: Session = Depends(get_db),
):
    product = (
        db.query(Product)
        .filter(Product.id == product_id)
        .first()
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    products = (
        db.query(Product)
        .filter(Product.unit_price > 0)
        .all()
    )

    purchases = []

    if user_id is not None:
        purchases = (
            db.query(Purchase)
            .filter(
                Purchase.user_id == user_id,
            )
            .all()
        )

    results = find_cheaper_substitutes(
        product=product,
        products=products,
        purchases=purchases,
        top_k=top_k,
    )

    return {
        "product_id": product.id,
        "product_name": product.name,
        "brand": product.brand,
        "category": product.category,
        "base_price": product.unit_price,
        "results": [
            {
                "product_id": item["product"].id,
                "product_name": item["product"].name,
                "brand": item["product"].brand,
                "category": item["product"].category,
                "unit_price": item["product"].unit_price,
                "similarity": item["similarity"],
                "savings": item["savings"],
                "savings_percent": item["savings_percent"],
                "preference": item["preference"],
                "score": item["score"],
            }
            for item in results
        ],
    }
