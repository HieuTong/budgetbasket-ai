from app.db.models import Product as DBProduct, Purchase
from app.db.repositories.purchases import get_user_purchase_summary
from app.ml.forecasting import PricePoint, price_trend
from app.ml.optimizer import BasketItem, optimize_basket
from app.ml.similarity import Product, SimilarityIndex
from app.rag.retriever import Retriever
from app.services.catalog import list_catalog
from app.services.decision import make_product_decision
from app.services.price_trend import load_price_trend, summarise_for_assistant

_retriever = Retriever()


def get_purchase_history_tool(user_id: int, db) -> list[dict]:
    return get_user_purchase_summary(db, user_id)


def run_budget_optimizer_tool(
    candidates: list[BasketItem],
    budget: float,
    max_distinct_products: int | None = None,
) -> dict:
    result = optimize_basket(candidates, budget, max_distinct_products=max_distinct_products)

    return {
        "items": [
            {
                "name": c.name,
                "qty": q,
                "unit_price": c.unit_price,
            }
            for c, q in result.items
        ],
        "total_cost": result.total_cost,
        "total_utility": result.total_utility,
    }


def find_substitutes_tool(
    product_id: int,
    db,
) -> list[dict]:
    target = (
        db.query(DBProduct)
        .filter(DBProduct.id == product_id)
        .first()
    )

    if target is None:
        return []

    priced_products = (
        db.query(DBProduct)
        .filter(DBProduct.unit_price > 0)
        .all()
    )

    products = [
        Product(
            id=p.id,
            name=p.name,
            category=p.category or "",
            unit_price=float(p.unit_price),
            brand=p.brand or "",
            sub_category=p.sub_category or "",
            product_group=p.product_group or "",
            package_size=p.package_size or "",
            nutrition_tags=p.nutrition_tags or "",
        )
        for p in priced_products
    ]

    index = SimilarityIndex(products)

    subs = index.cheaper_substitutes(product_id)

    return [
        {
            "name": p.name,
            "price": p.unit_price,
            "similarity": round(sim, 2),
        }
        for p, sim in subs
    ]


def check_price_trend_tool(
    history: list[PricePoint],
) -> dict:
    return price_trend(history)


def retrieve_savings_tips_tool(
    query: str,
) -> list[dict]:
    return _retriever.retrieve(query)


def make_product_decision_tool(
    product_id: int,
    db,
    user_id: int | None = None,
) -> dict:
    product = (
        db.query(DBProduct)
        .filter(DBProduct.id == product_id)
        .first()
    )

    if product is None:
        return {
            "error": f"Product {product_id} not found."
        }

    purchases = (
        db.query(Purchase)
        .filter(
            Purchase.source == "dunnhumby_complete_journey",
        )
        .all()
    )

    products = (
        db.query(DBProduct)
        .filter(DBProduct.unit_price > 0)
        .all()
    )

    result = make_product_decision(
        product=product,
        purchases=purchases,
        products=products,
    )

    response = {
        "product_id": product.id,
        "product_name": product.name,
        "decision": result.decision.value,
        "confidence": result.confidence,
        "reason": result.reason,
    }

    if result.price_probability is not None:
        response["price_probability"] = (
            result.price_probability.as_dict()
        )

    return response


def find_products_tool(query: str, db, limit: int = 5) -> list[dict]:
    """Turn a product name the user typed ("milk") into catalogue products with IDs."""
    return [
        {"product_id": p["product_id"], "name": p["name"], "brand": p["brand"], "price": p["price"]}
        for p in list_catalog(db, search=query, limit=limit)
    ]


def explain_price_trend_tool(product_id: int, db) -> dict:
    trend = load_price_trend(db, product_id)
    if trend is None:
        return {"error": f"Product {product_id} not found."}
    if not trend.points:
        return {"product_id": product_id, "product_name": trend.product.name,
                "error": "No price history is available for this product."}
    return summarise_for_assistant(trend)


TOOL_REGISTRY = {
    "find_products": find_products_tool,
    "explain_price_trend": explain_price_trend_tool,
    "run_budget_optimizer": run_budget_optimizer_tool,
    "find_substitutes": find_substitutes_tool,
    "check_price_trend": check_price_trend_tool,
    "retrieve_savings_tips": retrieve_savings_tips_tool,
    "make_product_decision": make_product_decision_tool,
}
