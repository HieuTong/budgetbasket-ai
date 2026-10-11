import logging

from scripts.benchmark_product_search import (
    FallbackCapture,
    is_relevant,
    percentile95,
    precision_at_k,
)


def test_percentile95_returns_none_for_empty_input():
    assert percentile95([]) is None


def test_percentile95_uses_nearest_rank():
    assert percentile95([1, 2, 3, 4, 5]) == 5
    assert percentile95(list(range(1, 21))) == 19


def test_precision_at_k_uses_k_as_denominator():
    products = [
        {"name": "Unsweetened Almond Milk", "sub_category": "Milk"},
        {"name": "Regular Soy Milk", "sub_category": "Milk"},
    ]
    assert precision_at_k("almond milk", products, 5) == 0.2


def test_chicken_relevance_requires_poultry_subcategory():
    assert is_relevant(
        "chicken",
        {"name": "Chicken Breast", "sub_category": "Poultry"},
    )
    assert not is_relevant(
        "chicken",
        {"name": "Chicken Sauce", "sub_category": "Sauces"},
    )


def test_confectionery_is_excluded():
    assert not is_relevant(
        "coconut milk",
        {
            "name": "Coconut Milk Chocolate Block",
            "category": "Pantry",
            "sub_category": "Confectionery",
        },
    )


def test_soy_milk_accepts_soya_spelling():
    assert is_relevant(
        "soy milk",
        {"name": "Soya Milk", "sub_category": "Milk"},
    )


def test_fallback_capture_counts_only_postgresql_fallback_warnings():
    capture = FallbackCapture()

    def make_record(message):
        return logging.LogRecord(
            name="app.services.catalog",
            level=logging.WARNING,
            pathname=__file__,
            lineno=1,
            msg=message,
            args=(),
            exc_info=None,
        )

    capture.emit(make_record("Some unrelated warning"))
    assert capture.count == 0

    capture.emit(
        make_record("OpenSearch unavailable; falling back to PostgreSQL")
    )
    assert capture.count == 1
