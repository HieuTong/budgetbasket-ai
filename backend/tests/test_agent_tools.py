from app.agent.tools import find_substitutes_tool
from app.db.models import Product
from app.db.session import SessionLocal


def test_missing_product_returns_no_substitutes():
    db = SessionLocal()

    try:
        result = find_substitutes_tool(
            product_id=-1,
            db=db,
        )

        assert result == []
    finally:
        db.close()