from app.agent.tools import find_substitutes_tool


def test_empty_products_return_no_substitutes():
    assert find_substitutes_tool(product_id=1, products=[]) == []
