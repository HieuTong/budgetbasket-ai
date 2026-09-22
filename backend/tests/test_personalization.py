from datetime import datetime, timedelta

from app.db.models import Product, Purchase
from app.services.personalization import build_basket_candidates, personalized_utility


def test_new_user_gets_neutral_utility():
    product = Product(id=1, name="Milk", category="dairy", unit_price=3.5)
    assert personalized_utility(product, []) == 0.5


def test_frequently_purchased_recent_product_scores_higher_than_unseen():
    now = datetime(2026, 9, 22)
    product = Product(id=1, name="Milk", category="dairy", unit_price=3.5)
    bread = Product(id=2, name="Bread", category="bakery", unit_price=3.0)

    purchases = [
        Purchase(
            user_id=7,
            product_id=1,
            quantity=2,
            purchased_at=now - timedelta(days=2),
            product=product,
        ),
        Purchase(
            user_id=7,
            product_id=1,
            quantity=1,
            purchased_at=now - timedelta(days=10),
            product=product,
        ),
        Purchase(
            user_id=7,
            product_id=2,
            quantity=1,
            purchased_at=now - timedelta(days=5),
            product=bread,
        ),
    ]

    milk_score = personalized_utility(product, purchases, now=now)
    bread_score = personalized_utility(bread, purchases, now=now)

    assert milk_score > bread_score


def test_category_affinity_supports_unseen_product():
    purchased = Product(id=1, name="Milk", category="dairy", unit_price=3.5)
    unseen = Product(id=2, name="Yoghurt", category="dairy", unit_price=4.0)

    purchases = [
        Purchase(
            user_id=7,
            product_id=1,
            quantity=1,
            purchased_at=datetime(2026, 9, 20),
            product=purchased,
        )
    ]

    assert personalized_utility(unseen, purchases, now=datetime(2026, 9, 22)) > 0.1


def test_candidate_builder_uses_product_catalog():
    product = Product(id=1, name="Milk", category="dairy", unit_price=3.5)
    candidates = build_basket_candidates([product], [])

    assert len(candidates) == 1
    assert candidates[0]["product"] is product
    assert candidates[0]["utility"] == 0.5
