from types import SimpleNamespace

from app.services.grocery_ranking import rerank_grocery_products


def product(name, category, sub_category):
    return SimpleNamespace(
        name=name,
        category=category,
        sub_category=sub_category,
    )


def test_chicken_prioritises_poultry_over_flavoured_snacks():
    snack = product("Chicken Chips", "Pantry", "Chips, crackers & snacks")
    poultry = product("Chicken Breast", "Meat & seafood", "Poultry")

    result = rerank_grocery_products([snack, poultry], "chicken")

    assert result == [poultry, snack]


def test_typo_chiken_still_prioritises_poultry():
    snack = product("Chicken Chips", "Pantry", "Chips, crackers & snacks")
    poultry = product("Chicken Breast", "Meat & seafood", "Poultry")

    result = rerank_grocery_products([snack, poultry], "chiken")

    assert result == [poultry, snack]


def test_real_oat_milk_is_prioritised_over_chocolate():
    chocolate = product("Chocolate Block Oat Milk", "Pantry", "Confectionery")
    oat_milk = product("Oat Milk", "Dairy, eggs & fridge", "Milk")

    result = rerank_grocery_products([chocolate, oat_milk], "oat milk")

    assert result == [oat_milk]


def test_unrelated_search_preserves_original_order():
    first = product("Apples", "Fruit & vegetables", "Fruit")
    second = product("Bananas", "Fruit & vegetables", "Fruit")

    assert rerank_grocery_products([first, second], "fruit") == [first, second]



def test_oat_milk_returns_no_false_matches_when_unavailable():
    dairy_milk = product("Light Milk", "Dairy, eggs & fridge", "Milk")
    chocolate = product("Chocolate Block Oat Milk", "Pantry", "Confectionery")

    result = rerank_grocery_products([dairy_milk, chocolate], "oat milk")

    assert result == []



def test_soy_milk_excludes_unrelated_almond_milk():
    almond = product("Unsweetened Almond Milk", "Dairy, eggs & fridge", "Milk")
    soy = product("Regular Soy Milk", "Dairy, eggs & fridge", "Milk")

    assert rerank_grocery_products([almond, soy], "soy milk") == [soy]


def test_coconut_milk_excludes_chocolate_confectionery():
    chocolate = product("Coconut Milk Chocolate Block", "Pantry", "Confectionery")
    coconut = product(
        "Organic Coconut Milk",
        "Dairy, eggs & fridge",
        "Milk",
    )

    assert rerank_grocery_products([chocolate, coconut], "coconut milk") == [coconut]


def test_almond_milk_matches_real_almond_milk():
    almond = product("Creamy Almond Milk", "Dairy, eggs & fridge", "Milk")
    soy = product("Regular Soy Milk", "Dairy, eggs & fridge", "Milk")

    assert rerank_grocery_products([soy, almond], "almond milk") == [almond]
