"""
Discrete tools the agent can call. Each tool wraps one piece of the
ML/RAG stack behind a narrow, typed interface -- this is what makes
it an "agent" and not a chatbot: the LLM plans which tools to call
and in what order, but the actual computation (optimization, retrieval,
similarity) happens in deterministic code, not in the model's head.
"""
from app.ml.forecasting import PricePoint, price_trend
from app.ml.optimizer import BasketItem, optimize_basket
from app.ml.similarity import Product, SimilarityIndex
from app.rag.retriever import Retriever

_retriever = Retriever()


def get_purchase_history_tool(user_id: int, db) -> list[dict]:
    """Fetch a user's recent purchases. Returns [{product_id, name, qty, price}]."""
    # Wire to real DB query in production; stubbed here for interface clarity.
    raise NotImplementedError("Wire to app.db.session query in production")


def run_budget_optimizer_tool(candidates: list[BasketItem], budget: float) -> dict:
    """Run the LP-based optimizer over candidate items within a budget."""
    result = optimize_basket(candidates, budget)
    return {
        "items": [{"name": c.name, "qty": q, "unit_price": c.unit_price} for c, q in result.items],
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
    """Return a buy-now-vs-wait signal for a product based on recent price history."""
    return price_trend(history)


def retrieve_savings_tips_tool(query: str) -> list[dict]:
    """RAG lookup: ground substitution/savings claims in the knowledge base."""
    return _retriever.retrieve(query)


TOOL_REGISTRY = {
    "run_budget_optimizer": run_budget_optimizer_tool,
    "find_substitutes": find_substitutes_tool,
    "check_price_trend": check_price_trend_tool,
    "retrieve_savings_tips": retrieve_savings_tips_tool,
}
