from unittest.mock import MagicMock

from app.agent.tools import find_substitutes_tool
from app.db.models import Product


def test_missing_product_returns_no_substitutes():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    result = find_substitutes_tool(
        product_id=-1,
        db=db,
    )

    assert result == []
    db.query.assert_called_once_with(Product)
    db.query.return_value.filter.return_value.first.assert_called_once()