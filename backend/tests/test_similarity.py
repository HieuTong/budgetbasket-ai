from app.ml.package import parse_package_size
from app.ml.similarity import (
    Product,
    package_compatible,
    practical_product_key,
    select_representatives,
)


def test_package_compatible_within_quantity_range():
    base = parse_package_size("500g")
    candidate = parse_package_size("750g")

    assert package_compatible(
        base,
        candidate,
    )


def test_package_compatible_rejects_too_small_package():
    base = parse_package_size("500g")
    candidate = parse_package_size("50g")

    assert not package_compatible(
        base,
        candidate,
    )


def test_package_compatible_rejects_too_large_package():
    base = parse_package_size("500g")
    candidate = parse_package_size("2kg")

    assert not package_compatible(
        base,
        candidate,
    )


def test_package_compatible_rejects_different_units():
    base = parse_package_size("500g")
    candidate = parse_package_size("4 pack")

    assert not package_compatible(
        base,
        candidate,
    )


def test_unknown_package_is_allowed():
    base = parse_package_size("500g")

    assert package_compatible(
        base,
        None,
    )


def test_practical_product_key_normalizes_package():
    product = Product(
        id=1,
        name="Test Granola",
        category="Pantry",
        unit_price=8.50,
        brand="Jordans",
        sub_category="Granola",
        product_group="Breakfast",
        package_size="500g",
    )

    assert practical_product_key(product) == (
        "breakfast",
        "granola",
        "jordans",
        "500 G",
    )


def test_select_representative_by_transaction_count():
    products = [
        Product(
            id=100,
            name="Russet Potatoes",
            category="PRODUCE",
            unit_price=5.00,
            brand="National",
            sub_category="POTATOES RUSSET",
            product_group="POTATOES",
            package_size="10 LB",
        ),
        Product(
            id=200,
            name="Russet Potatoes",
            category="PRODUCE",
            unit_price=4.50,
            brand="National",
            sub_category="POTATOES RUSSET",
            product_group="POTATOES",
            package_size="10 LB",
        ),
        Product(
            id=300,
            name="Russet Potatoes",
            category="PRODUCE",
            unit_price=4.00,
            brand="National",
            sub_category="POTATOES RUSSET",
            product_group="POTATOES",
            package_size="5 LB",
        ),
    ]

    transaction_counts = {
        100: 1,
        200: 5,
        300: 13,
    }

    representatives = select_representatives(
        products,
        transaction_counts,
    )

    representative_ids = {
        product.id
        for product in representatives
    }

    assert representative_ids == {
        200,
        300,
    }


def test_select_representative_breaks_ties_by_product_id():
    products = [
        Product(
            id=200,
            name="Test Product",
            category="Pantry",
            unit_price=5.00,
            brand="Brand",
            sub_category="Test",
            product_group="Group",
            package_size="500g",
        ),
        Product(
            id=100,
            name="Test Product",
            category="Pantry",
            unit_price=5.00,
            brand="Brand",
            sub_category="Test",
            product_group="Group",
            package_size="500g",
        ),
    ]

    transaction_counts = {
        100: 3,
        200: 3,
    }

    representatives = select_representatives(
        products,
        transaction_counts,
    )

    assert len(representatives) == 1
    assert representatives[0].id == 100
