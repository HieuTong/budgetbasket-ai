from __future__ import annotations

import re


CANONICAL_CATEGORIES = {
    "Bakery",
    "Dairy, eggs & fridge",
    "Drinks",
    "Fruit & vegetables",
    "Meat & seafood",
    "Pantry",
}


def normalize_text(value: str | None) -> str:
    """Normalize category/product text for deterministic matching."""
    if not value:
        return ""

    value = value.upper().strip()
    value = re.sub(r"[^A-Z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value)


def canonical_category(
    category: str | None,
    sub_category: str | None = None,
    product_name: str | None = None,
) -> str | None:
    """
    Map source-specific product taxonomy into the DecisionOS taxonomy.

    The function intentionally uses deterministic rules rather than
    fuzzy matching so the resulting preference signal is explainable.
    """

    category_norm = normalize_text(category)
    subcategory_norm = normalize_text(sub_category)
    name_norm = normalize_text(product_name)

    text = " ".join(
        value
        for value in (
            category_norm,
            subcategory_norm,
            name_norm,
        )
        if value
    )

    # Current DecisionOS catalog categories.
    if category in CANONICAL_CATEGORIES:
        return category

    # Fruit and vegetables.
    if category_norm in {
        "PRODUCE",
        "FRUIT VEGETABLES",
        "FRUIT AND VEGETABLES",
    }:
        return "Fruit & vegetables"

    if any(
        keyword in text
        for keyword in (
            "FRUIT",
            "VEGETABLE",
            "POTATO",
            "ONION",
            "TOMATO",
            "PEPPER",
            "SALAD MIX",
        )
    ):
        return "Fruit & vegetables"

    # Meat and seafood.
    if category_norm in {
        "MEAT",
        "MEAT PCKGD",
        "MEAT SEAFOOD",
    }:
        return "Meat & seafood"

    if any(
        keyword in text
        for keyword in (
            "BEEF",
            "PORK",
            "CHICKEN",
            "POULTRY",
            "LAMB",
            "MEAT",
            "SAUSAGE",
            "HAM",
            "BACON",
            "SEAFOOD",
            "FISH",
            "SHRIMP",
            "TURKEY",
        )
    ):
        return "Meat & seafood"

    # Bakery.
    if category_norm in {
        "PASTRY",
        "BAKERY",
    }:
        return "Bakery"

    if any(
        keyword in text
        for keyword in (
            "BREAD",
            "BAKED",
            "BAKERY",
            "CAKE",
            "COOKIE",
            "COOKIES",
            "DONUT",
            "DONUTS",
            "PASTRY",
            "SWEET GOODS",
            "BUN",
            "ROLLS",
        )
    ):
        return "Bakery"

    # Dairy, eggs and refrigerated products.
    if category_norm in {
        "DAIRY EGGS FRIDGE",
        "DAIRY",
    }:
        return "Dairy, eggs & fridge"

    if any(
        keyword in text
        for keyword in (
            "MILK",
            "CHEESE",
            "YOGURT",
            "YOGHURT",
            "EGG",
            "EGGS",
            "CREAM",
            "BUTTER",
        )
    ):
        return "Dairy, eggs & fridge"

    # Drinks.
    if category_norm in {
        "DRINKS",
        "BEVERAGES",
    }:
        return "Drinks"

    if any(
        keyword in text
        for keyword in (
            "SOFT DRINK",
            "WATER",
            "COFFEE",
            "TEA",
            "DRINK",
            "BEVERAGE",
            "JUICE",
            "ISOTONIC",
            "ENERGY DRINK",
            "SPORTS DRINK",
        )
    ):
        return "Drinks"

    # Everything else from grocery/general merchandise is treated
    # as pantry only when there is a reasonable food/pantry signal.
    if any(
        keyword in text
        for keyword in (
            "PANTRY",
            "SAUCE",
            "SAUCES",
            "CONDIMENT",
            "DRESSING",
            "PASTA",
            "NOODLE",
            "RICE",
            "BEAN",
            "FLOUR",
            "BAKING",
            "SUGAR",
            "SWEETENER",
            "CEREAL",
            "BREAKFAST",
            "JAM",
            "HONEY",
            "SPREAD",
            "OIL",
            "VINEGAR",
            "SNACK",
            "CHIP",
            "CRACKER",
            "CANDY",
            "CHOCOLATE",
            "CONFECTIONERY",
            "COOKIES",
            "SPICES",
            "SEASONING",
            "SOUP",
            "FROZEN",
            "DOG FOOD",
            "PET FOOD",
        )
    ):
        return "Pantry"

    return None
