from app.ml.optimizer import BasketItem, optimize_basket


def sample_candidates():
    return [
        BasketItem(product_id=1, name="Milk", unit_price=3.50, utility=0.9, max_quantity=2),
        BasketItem(product_id=2, name="Bread", unit_price=3.00, utility=0.8, max_quantity=2),
    ]


def test_basket_never_exceeds_budget():
    result = optimize_basket(sample_candidates(), budget=5.00)

    assert result.total_cost <= 5.00
    assert all(quantity <= item.max_quantity for item, quantity in result.items)


def test_zero_budget_returns_empty_basket():
    result = optimize_basket(sample_candidates(), budget=0)

    assert result.items == []
    assert result.total_cost == 0.0
    assert result.total_utility == 0.0


def test_empty_candidates_return_empty_basket():
    result = optimize_basket([], budget=50.00)

    assert result.items == []
    assert result.total_cost == 0.0
    assert result.total_utility == 0.0


def test_quantities_are_positive():
    result = optimize_basket(sample_candidates(), budget=20.00)

    assert all(quantity > 0 for _, quantity in result.items)


def test_optimizer_is_deterministic():
    first = optimize_basket(sample_candidates(), budget=10.00)
    second = optimize_basket(sample_candidates(), budget=10.00)

    assert first == second
