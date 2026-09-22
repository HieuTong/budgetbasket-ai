"""Import the public Australian grocery snapshot into the canonical schema.

The CSV is intentionally kept outside the repository. Download
Australia_Grocery_2022Sep.csv from the Kaggle dataset and pass its path:

    python -m seed.import_grocery_dataset /path/to/Australia_Grocery_2022Sep.csv

Use --dry-run first. This importer only maps fields we currently need.
It does not pretend that state/city is a retailer and therefore leaves
price_observations.store_id NULL until a retailer-specific source is added.
"""

import argparse
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from app.db.models import PriceObservation, Product
from app.db.session import SessionLocal


SOURCE = "kaggle_australia_grocery_2022"
REQUIRED_COLUMNS = {
    "Sku",
    "Product_Name",
    "Sub_category",
    "Retail_price",
    "unit_price",
    "unit_price_unit",
    "RunDate",
}


def clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def parse_decimal(value: str | None) -> Decimal | None:
    value = clean(value)
    if not value:
        return None
    value = value.replace("$", "").replace(",", "")
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def parse_bool(value: str | None) -> bool | None:
    value = clean(value)
    if value is None:
        return None
    if value.lower() in {"true", "1", "yes", "y"}:
        return True
    if value.lower() in {"false", "0", "no", "n"}:
        return False
    return None


def parse_datetime(value: str | None) -> datetime | None:
    value = clean(value)
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return None


def normalize_row(row: dict[str, str]) -> tuple[dict, dict] | None:
    price = parse_decimal(row.get("Package_price"))
    if price is None:
        price = parse_decimal(row.get("Retail_price"))
    observed_at = parse_datetime(row.get("RunDate"))

    if not clean(row.get("Product_Name")) or price is None or observed_at is None:
        return None

    product_data = {
        "name": clean(row.get("Product_Name")),
        "brand": clean(row.get("Brand")),
        "category": clean(row.get("Category")),
        "sub_category": clean(row.get("Sub_category")),
        "product_group": clean(row.get("Product_Group")),
        # Sku is a retailer/source identifier, not a barcode.\n        "barcode": None,
        "package_size": clean(row.get("package_size")),
        "unit_price": float(price),
        "unit": clean(row.get("unit_price_unit")) or "each",
        "source": SOURCE,
        "source_product_id": clean(row.get("Sku")),
    }

    record_id = "|".join(
        clean(row.get(key)) or ""
        for key in ("Sku", "state", "city", "RunDate", "index")
    )

    observation_data = {
        "price": price,
        "unit_price": parse_decimal(row.get("unit_price")),
        "unit_price_unit": clean(row.get("unit_price_unit")),
        "retail_price": parse_decimal(row.get("Retail_price")),
        "is_special": parse_bool(row.get("is_special")) or False,
        "in_stock": parse_bool(row.get("in_stock")),
        "is_estimated": parse_bool(row.get("is_estimated")),
        "observed_at": observed_at,
        "source": SOURCE,
        "source_record_id": record_id,
        "source_url": clean(row.get("Product_Url")),
    }
    return product_data, observation_data


def import_csv(csv_path: Path, dry_run: bool = False) -> tuple[int, int]:
    products_created = 0
    observations_created = 0
    seen_products: dict[tuple, Product] = {}

    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        columns = set(reader.fieldnames or [])
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(f"Missing required columns: {sorted(missing)}")

        db = SessionLocal()
        try:
            for row_number, row in enumerate(reader, start=2):
                normalized = normalize_row(row)
                if normalized is None:
                    continue

                product_data, observation_data = normalized
                key = (
                    product_data["name"],
                    product_data["brand"],
                    product_data["package_size"],
                    product_data["category"],
                )

                product = seen_products.get(key)
                if product is None:
                    product = (
                        db.query(Product)
                        .filter(
                            Product.name == product_data["name"],
                            Product.brand == product_data["brand"],
                            Product.package_size == product_data["package_size"],
                            Product.category == product_data["category"],
                        )
                        .first()
                    )
                    if product is None:
                        product = Product(**product_data)
                        db.add(product)
                        db.flush()
                        products_created += 1
                    seen_products[key] = product

                if not dry_run:
                    existing = (
                        db.query(PriceObservation)
                        .filter_by(
                            source=SOURCE,
                            source_record_id=observation_data["source_record_id"],
                        )
                        .first()
                    )
                    if existing is None:
                        db.add(
                            PriceObservation(
                                product_id=product.id,
                                **observation_data,
                            )
                        )
                        observations_created += 1

            if dry_run:
                db.rollback()
            else:
                db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    return products_created, observations_created


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    products, observations = import_csv(args.csv_path, dry_run=args.dry_run)
    mode = "Would create" if args.dry_run else "Created"
    print(f"{mode} {products} products and {observations} price observations.")


if __name__ == "__main__":
    main()
