"""
Loads seed/products_seed.csv into the products table, then generates and
loads price history for each. Run once against a fresh DB:

    cd backend
    python -m seed.load_seed_data
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.models import Base, PriceHistory, Product
from app.db.session import SessionLocal, engine
from seed.generate_price_history import generate_history

SEED_CSV = Path(__file__).parent / "products_seed.csv"


def load_products(db) -> list[Product]:
    products = []
    with open(SEED_CSV, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing = db.query(Product).filter_by(name=row["name"]).first()
            if existing:
                products.append(existing)
                continue
            product = Product(
                name=row["name"],
                category=row["category"],
                unit_price=float(row["unit_price"]),
                unit=row["unit"],
                nutrition_tags=row["nutrition_tags"],
            )
            db.add(product)
            products.append(product)
    db.commit()
    return products


def load_price_history(db, products: list[Product], days: int = 90):
    for i, product in enumerate(products):
        already = db.query(PriceHistory).filter_by(product_id=product.id).first()
        if already:
            continue
        history = generate_history(product.unit_price, product.category, days=days, seed=i)
        db.bulk_save_objects(
            [PriceHistory(product_id=product.id, price=point["price"], recorded_at=point["date"]) for point in history]
        )
    db.commit()


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        products = load_products(db)
        print(f"Loaded {len(products)} products.")
        load_price_history(db, products)
        print(f"Generated {90}-day price history for each product.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
