"""Guards against the N+1 query problem in basket building.

Uses a real (in-memory SQLite) database and counts every SQL statement sent.
Before the fix, 100 purchases caused 102 queries; it must stay constant as data grows.
"""
from datetime import datetime, timedelta

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, Product, Purchase, User
from app.services.basket import build_basket_candidates


def _database(n_purchases: int):
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(User(id=1, **({"email": "test@example.com"} if hasattr(User, "email") else {})))
    for i in range(1, n_purchases + 1):
        session.add(Product(id=i, name=f"Product {i}", unit_price=2.0, category="Pantry", sub_category="Misc"))
        session.add(Purchase(user_id=1, product_id=i, quantity=1,
                             purchased_at=datetime(2026, 9, 1) + timedelta(days=i % 30)))
    session.commit()
    session.close()
    return engine, sessionmaker(bind=engine)()


def _queries_for(n_purchases: int) -> int:
    engine, session = _database(n_purchases)
    count = 0

    def on_query(*_args, **_kwargs):
        nonlocal count
        count += 1

    event.listen(engine, "before_cursor_execute", on_query)
    candidates, purchase_count = build_basket_candidates(session, 1)
    assert len(candidates) == n_purchases and purchase_count == n_purchases
    return count


def test_query_count_does_not_grow_with_purchases():
    small, large = _queries_for(10), _queries_for(200)
    assert small == large, f"{small} queries for 10 purchases but {large} for 200: N+1 is back"
    assert large <= 4
