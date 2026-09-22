"""
Discrete tools the agent can call.

The LLM plans which tools to call, while actual computation happens in
deterministic application code.
"""
from app.db.repositories.purchases import get_user_purchase_summary
from app.ml.forecasting import PricePoint, price_trend
from app.ml.optimizer import BasketItem, optimize_basket
from app.ml.similarity import Product, SimilarityIndex
from app.rag.retriever import Retriever

_retriever = Retriever()


def get_purchase_history_tool(user_id: int, db) -> list[dict]:
    """Fetch a user's purchase summary from PostgreSQL."""
    return get_user_purchase_summary(db, user_id)


def run_budget_optimizer_tool(candidates: list[BasketItem], budget: float) -> dict:
    """Run the LP-based optimizer over candidate items within a budget."""
    result = optimize_basket(candidates, budget)
    return {
        "items": [
            {"name": c.name, "qty": q, "unit_price": c.unit_price}
            for c, q in result.items
        ],
        "total_cost": result.total_cost,
        "total_utility": result.total_utility,
    }


def find_substitutes_tool(product_id: int, products: list[Product]) -> list[dict]:
    if not products:
        return []

    index = SimilarityIndex(products)
    subs = index.cheaper_substitutes(product_id)
    return [
        {"name": p.name, "price": p.unit_price, "similarity": round(sim, 2)}
        for p, sim in subs
    ]


def check_price_trend_tool(history: list[PricePoint]) -> dict:
    """Return a buy-now-vs-wait signal from price history."""
    return price_trend(history)


def retrieve_savings_tips_tool(query: str) -> list[dict]:
    """Retrieve grounded savings/substitution facts from the knowledge base."""
    return _retriever.retrieve(query)


TOOL_REGISTRY = {
    "run_budget_optimizer": run_budget_optimizer_tool,
    "find_substitutes": find_substitutes_tool,
    "check_price_trend": check_price_trend_tool,
    "retrieve_savings_tips": retrieve_savings_tips_tool,
}
