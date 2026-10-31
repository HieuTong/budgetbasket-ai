"""Load a product's price history and forecast. Shared by the forecast API route and the
chat assistant's explain_price_trend tool, so both always report the same numbers."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import Product, Purchase
from app.ml.forecasting import PricePoint, price_trend
from app.services.price_intelligence import build_product_price_history

DUNNHUMBY_SOURCE = "dunnhumby_complete_journey"


@dataclass
class ProductPriceTrend:
    product: Product
    points: list[PricePoint]
    observation_count: int
    forecast: dict


def load_price_trend(db: Session, product_id: int, horizon_weeks: int = 4) -> ProductPriceTrend | None:
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        return None
    purchases = (
        db.query(Purchase)
        .filter(Purchase.product_id == product_id, Purchase.source == DUNNHUMBY_SOURCE)
        .order_by(Purchase.purchased_at)
        .all()
    )
    history = build_product_price_history(product=product, purchases=purchases)
    points = [
        PricePoint(date=p.date, unit_price=p.unit_price, transaction_count=p.transaction_count)
        for p in history.points
    ]
    forecast = price_trend(history=points, forecast_horizon_weeks=horizon_weeks)
    return ProductPriceTrend(product, points, history.observation_count, forecast)


def summarise_for_assistant(trend: ProductPriceTrend, recent: int = 6) -> dict:
    """A compact, factual summary for the LLM: what the data shows, nothing about causes.

    The forecaster's own buy/wait 'recommendation' is left out on purpose: purchase decisions
    come only from make_product_decision, so the assistant can't give two conflicting answers.
    """
    last = trend.points[-recent:]
    change = None
    if len(last) >= 2 and last[0].unit_price:
        change = round(100 * (last[-1].unit_price - last[0].unit_price) / last[0].unit_price, 1)
    f = trend.forecast
    return {
        "product_id": trend.product.id,
        "product_name": trend.product.name,
        "recent_prices": [{"date": p.date.isoformat(), "price": p.unit_price} for p in last],
        "change_over_recent_points_percent": change,
        "trend": f.get("trend"),
        "forecast_change_percent": f.get("forecast_change_percent"),
        "forecast_confidence": f.get("confidence"),
        "observation_count": trend.observation_count,
        "data_note": "Based on historical transaction data, not live shelf prices. "
                     "The data shows what changed, not why.",
    }
