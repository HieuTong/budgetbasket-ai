"""
Generates synthetic price history per product for demo/dev purposes.

This is explicitly SYNTHETIC, not scraped -- but it isn't arbitrary noise
either: the patterns are grounded in documented real behaviour of Australian
grocery pricing (see github.com/tjhowse/aus_grocery_price_database), namely:
  - fresh produce oscillates on a roughly 2-week promo cycle
  - packaged/pantry staples drift slowly with small random noise
  - occasional short-lived "specials" dip prices ~15-25% for a few days

Swap this out for app.integrations.open_prices_client once deployed with
real internet access and enough contributed AU data points to rely on.
"""
import random
from datetime import datetime, timedelta

PRODUCE_CATEGORIES = {"produce", "meat"}


def generate_history(base_price: float, category: str, days: int = 90, seed: int | None = None) -> list[dict]:
    rng = random.Random(seed)
    history = []
    price = base_price
    today = datetime.utcnow()

    is_volatile = category in PRODUCE_CATEGORIES

    for day_offset in range(days, -1, -1):
        date = today - timedelta(days=day_offset)

        if is_volatile:
            # ~2-week oscillation + noise
            cycle = 0.08 * base_price * (1 if (day_offset // 14) % 2 == 0 else -1)
            noise = rng.uniform(-0.05, 0.05) * base_price
            price = max(0.5, base_price + cycle + noise)
        else:
            # slow drift + small noise, occasional specials
            drift = rng.uniform(-0.002, 0.003) * base_price
            price = max(0.5, price + drift)
            if rng.random() < 0.03:  # ~3% chance of a short special
                price = price * rng.uniform(0.75, 0.88)

        history.append({"date": date, "price": round(price, 2)})

    return history


if __name__ == "__main__":
    sample = generate_history(base_price=3.50, category="produce", days=30, seed=42)
    for point in sample[-10:]:
        print(point["date"].date(), point["price"])
