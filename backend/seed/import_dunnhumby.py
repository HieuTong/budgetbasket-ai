"""Import a representative subset of the Dunnhumby Complete Journey dataset.

Usage:
    python -m seed.import_dunnhumby \
        --data-dir "/path/to/dunnhumby_The-Complete- Journey CSV" \
        --households 100

The importer loads:
    - product.csv
    - transaction_data.csv

It creates:
    - Product
    - User
    - Store
    - Basket
    - Purchase

Only the first N households encountered in transaction_data.csv are imported.

Dunnhumby DAY is a relative day value. We map it to a normalized timeline
beginning at 2000-01-01 so temporal ordering is preserved without pretending
the dates are real-world calendar dates.
"""

import argparse
import csv
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from app.db.models import Basket, Product, Purchase, Store, User
from app.db.session import SessionLocal


SOURCE = "dunnhumby_complete_journey"
DEFAULT_CHUNK_SIZE = 10_000
NORMALIZED_START_DATE = datetime(2000, 1, 1)


def clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def normalized_datetime(day_value: str | None) -> datetime:
    """Convert Dunnhumby's relative DAY value to a normalized datetime."""

    try:
        day = int(day_value or 1)
    except ValueError:
        day = 1

    return NORMALIZED_START_DATE + timedelta(days=max(day - 1, 0))


def validate_columns(
    reader: csv.DictReader,
    required_columns: set[str],
    filename: str,
) -> None:
    columns = set(reader.fieldnames or [])
    missing = required_columns - columns

    if missing:
        raise ValueError(
            f"{filename} is missing columns: {sorted(missing)}"
        )


def load_products(
    db,
    product_csv: Path,
) -> dict[str, Product]:
    """Load Dunnhumby products using a single existing-product lookup."""

    print("Reading product.csv...")

    rows: list[dict[str, str]] = []

    with product_csv.open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        reader = csv.DictReader(handle)

        validate_columns(
            reader,
            {
                "PRODUCT_ID",
                "DEPARTMENT",
                "BRAND",
                "COMMODITY_DESC",
                "SUB_COMMODITY_DESC",
                "CURR_SIZE_OF_PRODUCT",
            },
            "product.csv",
        )

        for row in reader:
            source_product_id = clean(row.get("PRODUCT_ID"))

            if source_product_id:
                rows.append(row)

    source_ids = {
        clean(row.get("PRODUCT_ID"))
        for row in rows
    }

    source_ids.discard(None)

    existing_products = (
        db.execute(
            select(Product).where(
                Product.source == SOURCE,
                Product.source_product_id.in_(source_ids),
            )
        )
        .scalars()
        .all()
    )

    products = {
        product.source_product_id: product
        for product in existing_products
        if product.source_product_id is not None
    }

    new_products = []

    for row in rows:
        source_product_id = clean(row.get("PRODUCT_ID"))

        if not source_product_id:
            continue

        if source_product_id in products:
            continue

        commodity = clean(row.get("COMMODITY_DESC"))
        sub_commodity = clean(row.get("SUB_COMMODITY_DESC"))

        if commodity and sub_commodity:
            name = f"{commodity} - {sub_commodity}"
        elif commodity:
            name = commodity
        else:
            name = f"Product {source_product_id}"

        product = Product(
            name=name,
            brand=clean(row.get("BRAND")),
            category=clean(row.get("DEPARTMENT")),
            sub_category=sub_commodity,
            product_group=commodity,
            package_size=clean(row.get("CURR_SIZE_OF_PRODUCT")),
            # Dunnhumby product.csv does not provide a current market price.
            # Keep this out of price-based optimization for now.
            unit_price=0.0,
            unit="each",
            source=SOURCE,
            source_product_id=source_product_id,
        )

        new_products.append(product)

    if new_products:
        db.bulk_save_objects(new_products)
        db.commit()

    # Re-query once so newly-created products have database IDs.
    all_products = (
        db.execute(
            select(Product).where(
                Product.source == SOURCE,
                Product.source_product_id.in_(source_ids),
            )
        )
        .scalars()
        .all()
    )

    products = {
        product.source_product_id: product
        for product in all_products
        if product.source_product_id is not None
    }

    print(f"Loaded {len(products):,} products.")

    return products


def select_households(
    transaction_csv: Path,
    household_limit: int,
) -> set[str]:
    """Scan the CSV once to determine the first N households."""

    print(
        f"Selecting first {household_limit:,} households..."
    )

    selected: set[str] = set()

    with transaction_csv.open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        reader = csv.DictReader(handle)

        validate_columns(
            reader,
            {"household_key"},
            "transaction_data.csv",
        )

        for row in reader:
            household_key = clean(row.get("household_key"))

            if not household_key:
                continue

            selected.add(household_key)

            if len(selected) >= household_limit:
                break

    print(
        f"Selected {len(selected):,} households."
    )

    return selected


def load_existing_users(
    db,
    household_keys: set[str],
) -> dict[str, User]:
    """Load existing Dunnhumby users in one query."""

    if not household_keys:
        return {}

    emails = {
        f"dunnhumby.household.{key}@budgetbasket.local"
        for key in household_keys
    }

    existing = (
        db.execute(
            select(User).where(User.email.in_(emails))
        )
        .scalars()
        .all()
    )

    users = {}

    for user in existing:
        if user.email:
            prefix = "dunnhumby.household."
            suffix = "@budgetbasket.local"

            if user.email.startswith(prefix):
                household_key = user.email[
                    len(prefix):-len(suffix)
                ]
                users[household_key] = user

    new_users = []

    for household_key in household_keys:
        if household_key in users:
            continue

        new_users.append(
            User(
                name=f"Dunnhumby Household {household_key}",
                email=(
                    f"dunnhumby.household."
                    f"{household_key}"
                    f"@budgetbasket.local"
                ),
            )
        )

    if new_users:
        db.bulk_save_objects(new_users)
        db.commit()

        existing = (
            db.execute(
                select(User).where(User.email.in_(emails))
            )
            .scalars()
            .all()
        )

        users = {}

        for user in existing:
            if user.email:
                prefix = "dunnhumby.household."
                suffix = "@budgetbasket.local"

                if user.email.startswith(prefix):
                    household_key = user.email[
                        len(prefix):-len(suffix)
                    ]
                    users[household_key] = user

    return users


def load_existing_stores(
    db,
    store_ids: set[str],
) -> dict[str, Store]:
    """Load or create stores in batches."""

    if not store_ids:
        return {}

    names = {
        f"dunnhumby_store_{store_id}"
        for store_id in store_ids
    }

    existing = (
        db.execute(
            select(Store).where(Store.name.in_(names))
        )
        .scalars()
        .all()
    )

    stores = {
        store.name.replace("dunnhumby_store_", "", 1): store
        for store in existing
    }

    new_stores = []

    for store_id in store_ids:
        if store_id in stores:
            continue

        new_stores.append(
            Store(name=f"dunnhumby_store_{store_id}")
        )

    if new_stores:
        db.bulk_save_objects(new_stores)
        db.commit()

        existing = (
            db.execute(
                select(Store).where(Store.name.in_(names))
            )
            .scalars()
            .all()
        )

        stores = {
            store.name.replace("dunnhumby_store_", "", 1): store
            for store in existing
        }

    return stores


def import_transactions(
    db,
    transaction_csv: Path,
    products: dict[str, Product],
    household_keys: set[str],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> tuple[int, int]:
    """Import selected household transactions efficiently."""

    print("Reading selected transactions...")

    # ------------------------------------------------------------------
    # First pass:
    # collect the selected rows and store IDs.
    #
    # This is still a sequential CSV read, but there are no database
    # queries inside the transaction loop.
    # ------------------------------------------------------------------

    selected_rows: list[tuple[int, dict[str, str]]] = []
    store_ids: set[str] = set()

    with transaction_csv.open(
        newline="",
        encoding="utf-8-sig",
    ) as handle:
        reader = csv.DictReader(handle)

        validate_columns(
            reader,
            {
                "household_key",
                "BASKET_ID",
                "DAY",
                "PRODUCT_ID",
                "QUANTITY",
                "SALES_VALUE",
                "STORE_ID",
                "RETAIL_DISC",
                "COUPON_DISC",
                "COUPON_MATCH_DISC",
            },
            "transaction_data.csv",
        )

        for csv_row_number, row in enumerate(reader, start=2):
            household_key = clean(row.get("household_key"))

            if household_key not in household_keys:
                continue

            store_id = clean(row.get("STORE_ID"))

            if store_id:
                store_ids.add(store_id)

            selected_rows.append(
                (csv_row_number, row)
            )

    print(
        f"Selected {len(selected_rows):,} transaction rows."
    )

    users = load_existing_users(
        db,
        household_keys,
    )

    stores = load_existing_stores(
        db,
        store_ids,
    )

    # ------------------------------------------------------------------
    # Load existing baskets for the selected source IDs.
    # ------------------------------------------------------------------

    basket_ids = {
        clean(row.get("BASKET_ID"))
        for _, row in selected_rows
    }

    basket_ids.discard(None)

    existing_baskets = (
        db.execute(
            select(Basket).where(
                Basket.source_basket_id.in_(basket_ids)
            )
        )
        .scalars()
        .all()
    )

    baskets = {
        basket.source_basket_id: basket
        for basket in existing_baskets
        if basket.source_basket_id is not None
    }

    # ------------------------------------------------------------------
    # Load existing purchase source IDs.
    #
    # The source transaction ID is the original CSV row number.
    # ------------------------------------------------------------------

    source_transaction_ids = {
        str(csv_row_number)
        for csv_row_number, _ in selected_rows
    }

    existing_purchases = (
        db.execute(
            select(Purchase).where(
                Purchase.source == SOURCE,
                Purchase.source_transaction_id.in_(
                    source_transaction_ids
                ),
            )
        )
        .scalars()
        .all()
    )

    existing_purchase_ids = {
        purchase.source_transaction_id
        for purchase in existing_purchases
        if purchase.source_transaction_id is not None
    }

    # ------------------------------------------------------------------
    # Create missing baskets first.
    # ------------------------------------------------------------------

    new_baskets = []

    for csv_row_number, row in selected_rows:
        source_basket_id = clean(row.get("BASKET_ID"))

        if not source_basket_id:
            continue

        if source_basket_id in baskets:
            continue

        household_key = clean(row.get("household_key"))

        if household_key not in users:
            continue

        store_id = clean(row.get("STORE_ID"))
        store = stores.get(store_id) if store_id else None

        new_baskets.append(
            Basket(
                user_id=users[household_key].id,
                source_basket_id=source_basket_id,
                store_id=store.id if store else None,
                purchased_at=normalized_datetime(
                    row.get("DAY")
                ),
            )
        )

    if new_baskets:
        db.bulk_save_objects(new_baskets)
        db.commit()

    # Re-query baskets once so IDs are available.
    existing_baskets = (
        db.execute(
            select(Basket).where(
                Basket.source_basket_id.in_(basket_ids)
            )
        )
        .scalars()
        .all()
    )

    baskets = {
        basket.source_basket_id: basket
        for basket in existing_baskets
        if basket.source_basket_id is not None
    }

    # ------------------------------------------------------------------
    # Build purchases in memory and insert in batches.
    # ------------------------------------------------------------------

    purchases_created = 0
    skipped_existing = 0
    malformed = 0

    purchase_batch: list[Purchase] = []

    for csv_row_number, row in selected_rows:
        source_transaction_id = str(csv_row_number)

        if source_transaction_id in existing_purchase_ids:
            skipped_existing += 1
            continue

        household_key = clean(row.get("household_key"))
        product_source_id = clean(row.get("PRODUCT_ID"))
        source_basket_id = clean(row.get("BASKET_ID"))

        if (
            not household_key
            or not product_source_id
            or not source_basket_id
        ):
            continue

        user = users.get(household_key)
        product = products.get(product_source_id)
        basket = baskets.get(source_basket_id)

        if user is None or product is None or basket is None:
            continue

        try:
            quantity = float(row.get("QUANTITY") or 0)

            sales_value = Decimal(
                row.get("SALES_VALUE") or "0"
            )

            retail_discount = Decimal(
                row.get("RETAIL_DISC") or "0"
            )

            coupon_discount = Decimal(
                row.get("COUPON_DISC") or "0"
            )

            coupon_match_discount = Decimal(
                row.get("COUPON_MATCH_DISC") or "0"
            )

        except Exception:
            malformed += 1
            continue

        purchase_batch.append(
            Purchase(
                user_id=user.id,
                product_id=product.id,
                basket_id=basket.id,
                quantity=quantity,
                sales_value=sales_value,
                retail_discount=retail_discount,
                coupon_discount=coupon_discount,
                coupon_match_discount=coupon_match_discount,
                purchased_at=normalized_datetime(
                    row.get("DAY")
                ),
                source=SOURCE,
                source_transaction_id=source_transaction_id,
            )
        )

        if len(purchase_batch) >= chunk_size:
            db.bulk_save_objects(purchase_batch)
            db.commit()

            purchases_created += len(purchase_batch)

            print(
                f"Imported {purchases_created:,} purchases..."
            )

            purchase_batch.clear()

    if purchase_batch:
        db.bulk_save_objects(purchase_batch)
        db.commit()

        purchases_created += len(purchase_batch)

    print(
        f"Imported {purchases_created:,} purchases."
    )

    if skipped_existing:
        print(
            f"Skipped {skipped_existing:,} existing purchases."
        )

    if malformed:
        print(
            f"Skipped {malformed:,} malformed rows."
        )

    return len(baskets), purchases_created


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Import a representative Dunnhumby "
            "Complete Journey subset."
        )
    )

    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help=(
            "Directory containing product.csv "
            "and transaction_data.csv"
        ),
    )

    parser.add_argument(
        "--households",
        type=int,
        default=100,
        help="Number of households to import.",
    )

    parser.add_argument(
        "--transaction-file",
        default="transaction_data.csv",
        help="Transaction CSV filename.",
    )

    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="Number of purchases inserted per batch.",
    )

    args = parser.parse_args()

    if args.households <= 0:
        raise ValueError(
            "--households must be greater than zero"
        )

    if args.chunk_size <= 0:
        raise ValueError(
            "--chunk-size must be greater than zero"
        )

    product_csv = args.data_dir / "product.csv"
    transaction_csv = args.data_dir / args.transaction_file

    if not product_csv.exists():
        raise FileNotFoundError(
            f"Product CSV not found: {product_csv}"
        )

    if not transaction_csv.exists():
        raise FileNotFoundError(
            f"Transaction CSV not found: {transaction_csv}"
        )

    db = SessionLocal()

    try:
        products = load_products(
            db,
            product_csv,
        )

        household_keys = select_households(
            transaction_csv,
            args.households,
        )

        baskets_created, purchases_created = import_transactions(
            db=db,
            transaction_csv=transaction_csv,
            products=products,
            household_keys=household_keys,
            chunk_size=args.chunk_size,
        )

        print()
        print("Import complete.")
        print(f"Households: {len(household_keys):,}")
        print(f"Baskets:    {baskets_created:,}")
        print(f"Purchases:  {purchases_created:,}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
