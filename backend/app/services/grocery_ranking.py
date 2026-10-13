"""Deterministic intent ranking for grocery search results."""

from difflib import SequenceMatcher
import re


def _tokens(value: str | None) -> list[str]:
    return re.findall(r"[a-z0-9]+", (value or "").lower())


def _contains_term(tokens: list[str], target: str) -> bool:
    return any(
        token == target
        or (
            len(token) >= 5
            and SequenceMatcher(None, token, target).ratio() >= 0.78
        )
        for token in tokens
    )


def _intent(query: str) -> str | None:
    tokens = _tokens(query)
    if not _contains_term(tokens, "milk"):
        return None

    # Match specific milk types before applying general ranking.
    for term in ("oat", "almond", "soy", "soya", "coconut", "rice"):
        if _contains_term(tokens, term):
            return {
                "soya": "soy",
            }.get(term, term) + "_milk"

    return "chicken" if _contains_term(tokens, "chicken") else None


def _is_milk_product(product) -> bool:
    category = _tokens(getattr(product, "category", ""))
    sub_category = _tokens(getattr(product, "sub_category", ""))
    return "milk" in sub_category or "dairy" in category


def _is_non_beverage(product) -> bool:
    taxonomy = set(
        _tokens(getattr(product, "category", ""))
        + _tokens(getattr(product, "sub_category", ""))
    )
    return bool(
        taxonomy
        & {"confectionery", "chocolate", "snacks", "chips", "sauces", "sauce"}
    )


def _priority(product, intent: str) -> int:
    name_tokens = _tokens(getattr(product, "name", ""))
    category = " ".join(_tokens(getattr(product, "category", "")))
    sub_category = " ".join(_tokens(getattr(product, "sub_category", "")))
    taxonomy = f"{category} {sub_category}"

    if intent.endswith("_milk"):
        target = intent.removesuffix("_milk")
        aliases = {"soy": {"soy", "soya"}}
        terms = aliases.get(target, {target})
        has_type = any(term in name_tokens for term in terms)

        if has_type and _is_milk_product(product) and not _is_non_beverage(product):
            return 5
        return -5

    if intent == "chicken":
        if "poultry" in sub_category:
            return 4
        if "chicken" in name_tokens and any(
            term in taxonomy
            for term in ("snack", "chips", "confectionery")
        ):
            return -2

    return 0


def rerank_grocery_products(products: list, query: str | None) -> list:
    """Prioritise requested grocery types and exclude misleading matches."""
    query_text = query or ""
    intent = _intent(query_text)

    if not intent:
        # Chicken typo tolerance is handled separately from milk intents.
        if _contains_term(_tokens(query_text), "chicken"):
            intent = "chicken"
        else:
            return products

    if intent.endswith("_milk"):
        matched = [
            product
            for product in products
            if _priority(product, intent) > 0
        ]
        return matched

    indexed = list(enumerate(products))
    indexed.sort(key=lambda item: (-_priority(item[1], intent), item[0]))
    return [product for _, product in indexed]
