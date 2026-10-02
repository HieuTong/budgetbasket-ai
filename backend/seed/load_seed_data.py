"""Load the Phase 1A grocery snapshot into PostgreSQL.

The CSV contains a small, intentionally simple Australian grocery catalog.
Its prices are indicative demo values. Price history is synthetic and clearly
marked as such so downstream decision/ML code can distinguish it from real
observations.

Run after Alembic has created the schema:

    cd backend
    python -m seed.load_seed_data
"""

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.models import PriceHistory, PriceObservation, Product
from app.db.session import SessionLocal
from seed.generate_price_history import generate_history

SEED_CSV = Path(__file__).parent / "products_seed.csv"
SOURCE = "synthetic_seed"


def load_products(db) -> list[Product]:
    products: list[Product] = []
    with SEED_CSV.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            product = db.query(Product).filter(Product.name == row["name"]).first()
            if product is None:
                product = Product(
                    name=row["name"],
                    category=row["category"],
                    unit_price=float(row["unit_price"]),
                    unit=row["unit"],
                    nutrition_tags=row["nutrition_tags"],
                )
                db.add(product)
            else:
                product.category = row["category"]
                product.unit_price = float(row["unit_price"])
                product.unit = row["unit"]
                product.nutrition_tags = row["nutrition_tags"]
            products.append(product)

    db.commit()
    return products


def load_price_data(db, products: list[Product], days: int = 90) -> int:
    inserted = 0

    for index, product in enumerate(products):
        history = generate_history(
            product.unit_price,
            product.category,
            days=days,
            seed=index,
        )

        for point in history:
            recorded_at = point["date"]
            source_record_id = f"{product.id}:{recorded_at.isoformat()}"

            exists = (
                db.query(PriceObservation)
                .filter(PriceObservation.source_record_id == source_record_id)
                .first()
            )
            if exists:
                continue

            db.add(
                PriceObservation(
                    product_id=product.id,
                    price=point["price"],
                    observed_at=recorded_at,
                    source=SOURCE,
                    source_record_id=source_record_id,
                    is_estimated=True,
                )
            )

            # Keep the legacy table populated while existing forecasting code
            # is migrated to the canonical observation table.
            db.add(
                PriceHistory(
                    product_id=product.id,
                    price=point["price"],
                    recorded_at=recorded_at,
                )
            )
            inserted += 1

    db.commit()
    return inserted


def main() -> None:
    db = SessionLocal()
    try:
        products = load_products(db)
        observations = load_price_data(db, products)
        print(f"Loaded {len(products)} products.")
        print(f"Inserted {observations} synthetic price observations.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
