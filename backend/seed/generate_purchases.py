"""
Generate synthetic grocery purchase history for demo/development.

This data is SYNTHETIC and must not be presented as real customer
transaction data.

The generated purchases are designed to provide realistic behavioral
signals for SpendingProfile development:
- recurring shopping behavior
- category preferences
- purchase frequency
- recency
- quantity patterns

Purchase records intentionally do not contain prices because the current
Purchase model represents behavioral transactions, while market prices
belong to PriceObservation.
"""

import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.models import Product, Purchase, User
from app.db.session import SessionLocal


SOURCE = "synthetic_demo"

NUM_USERS = 20
DAYS = 365
MIN_BASKET_SIZE = 5
MAX_BASKET_SIZE = 14

CATEGORY_WEIGHTS = {
    "produce": 0.20,
    "dairy": 0.15,
    "meat": 0.12,
    "bakery": 0.10,
    "pantry": 0.18,
    "beverages": 0.10,
    "snacks": 0.08,
    "frozen": 0.07,
}


def get_products_by_category(db) -> dict[str, list[Product]]:
    products = db.query(Product).all()

    grouped: dict[str, list[Product]] = {}

    for product in products:
        category = (product.category or "other").strip().lower()
        grouped.setdefault(category, []).append(product)

    return grouped


def choose_category(rng: random.Random, categories: list[str]) -> str:
    available = [
        category
        for category in CATEGORY_WEIGHTS
        if category in categories
    ]

    if not available:
        return rng.choice(categories)

    weights = [CATEGORY_WEIGHTS[category] for category in available]
    return rng.choices(available, weights=weights, k=1)[0]


def choose_quantity(rng: random.Random, product: Product) -> float:
    category = (product.category or "").lower()

    if category in {"produce", "dairy", "bakery"}:
        return float(rng.choices([1, 2, 3], weights=[0.65, 0.28, 0.07])[0])

    if category in {"meat", "frozen"}:
        return float(rng.choices([1, 2], weights=[0.75, 0.25])[0])

    return float(rng.choices([1, 2, 3], weights=[0.78, 0.18, 0.04])[0])


def create_users(db) -> list[User]:
    users = []

    for index in range(1, NUM_USERS + 1):
        email = f"demo.user{index}@budgetbasket.local"

        user = db.query(User).filter(User.email == email).first()

        if user is None:
            user = User(
                name=f"Demo User {index}",
                email=email,
            )
            db.add(user)
            db.flush()

        users.append(user)

    db.commit()
    return users


def purchase_exists(
    db,
    user_id: int,
    product_id: int,
    purchased_at: datetime,
) -> bool:
    return (
        db.query(Purchase)
        .filter(
            Purchase.user_id == user_id,
            Purchase.product_id == product_id,
            Purchase.purchased_at == purchased_at,
        )
        .first()
        is not None
    )


def generate_user_history(
    db,
    user: User,
    products_by_category: dict[str, list[Product]],
    days: int,
    seed: int,
) -> int:
    rng = random.Random(seed)

    categories = list(products_by_category)

    if not categories:
        return 0

    today = datetime.utcnow().replace(
        hour=12,
        minute=0,
        second=0,
        microsecond=0,
    )

    start = today - timedelta(days=days)

    # Each user has a few preferred categories.
    preferred_categories = rng.sample(
        categories,
        k=min(3, len(categories)),
    )

    inserted = 0

    # Simulate roughly weekly/biweekly grocery shopping.
    current = start + timedelta(days=rng.randint(0, 6))

    while current <= today:
        basket_size = rng.randint(MIN_BASKET_SIZE, MAX_BASKET_SIZE)

        chosen_products: set[int] = set()

        for _ in range(basket_size):
            # Most purchases come from preferred categories.
            if rng.random() < 0.65:
                category = rng.choice(preferred_categories)
            else:
                category = choose_category(rng, categories)

            candidates = products_by_category.get(category, [])

            if not candidates:
                continue

            product = rng.choice(candidates)

            if product.id in chosen_products:
                continue

            chosen_products.add(product.id)

            # A small number of products become recurring staples.
            quantity = choose_quantity(rng, product)

            # Give transactions slightly different times of day.
            purchased_at = current.replace(
                hour=rng.randint(8, 20),
                minute=rng.randint(0, 59),
            )

            if purchase_exists(
                db,
                user.id,
                product.id,
                purchased_at,
            ):
                continue

            db.add(
                Purchase(
                    user_id=user.id,
                    product_id=product.id,
                    quantity=quantity,
                    purchased_at=purchased_at,
                )
            )
            inserted += 1

        # Most users shop every 7 days, with some variation.
        current += timedelta(days=rng.randint(6, 10))

    return inserted


def main() -> None:
    db = SessionLocal()

    try:
        products_by_category = get_products_by_category(db)

        if not products_by_category:
            raise RuntimeError(
                "No products found. Load the product catalog first."
            )

        users = create_users(db)

        inserted = 0

        for index, user in enumerate(users):
            inserted += generate_user_history(
                db=db,
                user=user,
                products_by_category=products_by_category,
                days=DAYS,
                seed=10_000 + index,
            )

        db.commit()

        purchase_count = db.query(Purchase).count()

        print(f"Source: {SOURCE}")
        print(f"Users: {len(users)}")
        print(f"Inserted purchases: {inserted}")
        print(f"Total purchases in database: {purchase_count}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
