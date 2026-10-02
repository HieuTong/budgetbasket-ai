from datetime import datetime
from decimal import Decimal

from seed.import_grocery_dataset import normalize_row


def test_normalize_grocery_row():
    row = {
        "index": "10",
        "Sku": "SKU-123",
        "Product_Name": "Test Pasta 500g",
        "Category": "Pantry",
        "Sub_category": "Pasta",
        "Product_Group": "Dry Pasta",
        "Package_price": "$2.50",
        "Price_per_unit": "$5.00",
        "package_size": "500g",
        "is_estimated": "False",
        "is_special": "True",
        "in_stock": "1",
        "Retail_price": "3.00",
        "Product_Url": "https://example.com/product",
        "Brand": "Test Brand",
        "RunDate": "2022-09-30",
        "unit_price": "5.00",
        "unit_price_unit": "kg",
        "Postal_code": "3000",
        "state": "VIC",
        "city": "Melbourne",
    }

    product, observation = normalize_row(row)

    assert product["name"] == "Test Pasta 500g"
    assert product["brand"] == "Test Brand"
    assert product["source_product_id"] == "SKU-123"
    assert product["barcode"] is None
    assert product["unit_price"] == 2.5

    assert observation["postal_code"] == "3000"
    assert observation["state"] == "VIC"
    assert observation["city"] == "Melbourne"
    assert observation["price"] == Decimal("2.50")
    assert observation["unit_price"] == Decimal("5.00")
    assert observation["is_special"] is True
    assert observation["in_stock"] is True
    assert observation["is_estimated"] is False
    assert observation["observed_at"] == datetime(2022, 9, 30)


def test_normalize_skips_invalid_price():
    row = {
        "Product_Name": "Broken Product",
        "Package_price": "not-a-price",
        "Retail_price": "",
        "RunDate": "2022-09-30",
    }

    assert normalize_row(row) is None
