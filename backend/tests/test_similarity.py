from app.ml.similarity import Product, SimilarityIndex


def test_empty_catalog_does_not_crash():
    index = SimilarityIndex([])

    assert index.recommend_similar(1) == []
    assert index.cheaper_substitutes(1) == []


def test_single_product_has_no_substitute():
    products = [
        Product(id=1, name="Milk", category="dairy", unit_price=3.50, nutrition_tags="calcium protein")
    ]

    index = SimilarityIndex(products)

    assert index.cheaper_substitutes(1) == []


def test_cheaper_similar_product_is_returned():
    products = [
        Product(id=1, name="Full Cream Milk", category="dairy", unit_price=3.50, nutrition_tags="calcium protein"),
        Product(id=2, name="Home Brand Milk", category="dairy", unit_price=2.80, nutrition_tags="calcium protein"),
    ]

    index = SimilarityIndex(products)
    substitutes = index.cheaper_substitutes(1)

    assert [product.id for product, _ in substitutes] == [2]
