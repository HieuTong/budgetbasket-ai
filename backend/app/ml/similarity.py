"""
Item-item similarity and substitution ranking for DecisionOS.

MVP approach:
- TF-IDF over product name, category, brand, and nutrition tags.
- Candidate filtering uses product concept and package compatibility.
- Practical product keys group duplicate source SKUs.
- Cosine similarity for candidate ranking.
- Cheaper substitutes are filtered by price and ranked using:
    similarity + savings + user preference.

Why TF-IDF?
- Fast and deterministic.
- No external API or embedding infrastructure.
- Easy to inspect and explain.
- Appropriate for an MVP before introducing learned embeddings.

The public interface is intentionally small so the underlying
similarity implementation can later be replaced by embeddings.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.ml.package import Package, parse_package_size


@dataclass
class Product:
    """Lightweight product representation used by the ML layer."""

    id: int
    name: str
    category: str
    unit_price: float
    brand: str = ""
    sub_category: str = ""
    product_group: str = ""
    package_size: str = ""
    nutrition_tags: str = ""

    def text(self) -> str:
        """
        Build the text representation used by TF-IDF.

        Package size is intentionally excluded because package
        compatibility is handled explicitly by the candidate filter.
        """
        return (
            f"{self.name} "
            f"{self.category} "
            f"{self.brand} "
            f"{self.sub_category} "
            f"{self.product_group} "
            f"{self.nutrition_tags}"
        )

    def identity_text(self) -> str:
        """
        Build a normalized product identity representation.

        This is used to prevent multiple source SKUs with the exact same
        descriptive attributes from being returned as separate
        recommendations.
        """
        return " ".join(
            self.text()
            .lower()
            .split()
        )


def product_concept(
    product: Product,
) -> tuple[str, str]:
    """
    Return the source taxonomy used to define a product concept.

    Products with the same product group and sub-category represent
    the same broad purchasing need in the MVP substitution model.
    """
    return (
        product.product_group.strip().lower(),
        product.sub_category.strip().lower(),
    )


def practical_product_key(
    product: Product,
) -> tuple[str, str, str, str]:
    """
    Return a recommendation-level product grouping key.

    Multiple source SKUs can represent the same practical product
    option while having different source product IDs.

    The key uses:
    - product group
    - sub-category
    - brand
    - normalized package size
    """
    package = parse_package_size(
        product.package_size
    )

    if package is None:
        package_key = ""
    else:
        package_key = (
            f"{package.quantity:g} {package.unit}"
        )

    return (
        product.product_group.strip().lower(),
        product.sub_category.strip().lower(),
        product.brand.strip().lower(),
        package_key,
    )


def select_representatives(
    products: list[Product],
    transaction_counts: dict[int, int],
) -> list[Product]:
    """
    Select one representative SKU for each practical product group.

    The representative is the SKU with the highest observed transaction
    count. Ties are broken deterministically using the product ID.

    This does not modify or delete source products. It only reduces
    duplicate SKUs at recommendation time.

    Products with no transaction evidence remain eligible when they are
    the only SKU in their practical product group.
    """
    grouped: dict[
        tuple[str, str, str, str],
        list[Product],
    ] = {}

    for product in products:
        key = practical_product_key(product)

        grouped.setdefault(
            key,
            [],
        ).append(product)

    representatives = []

    for group in grouped.values():
        representative = min(
            group,
            key=lambda product: (
                -transaction_counts.get(product.id, 0),
                product.id,
            ),
        )

        representatives.append(
            representative
        )

    return representatives


def package_compatible(
    base: Package | None,
    candidate: Package | None,
) -> bool:
    """
    Determine whether two package sizes are comparable.

    If either package size cannot be parsed, the candidate is allowed
    through because we do not have enough information to reject it.

    Known compatible units must match exactly:
        10 LB -> 5 LB   compatible
        10 LB -> 15 LB  compatible
        10 LB -> 60 CT  incompatible
    """
    if base is None or candidate is None:
        return True

    return base.unit == candidate.unit


def compatible_candidates(
    base: Product,
    products: list[Product],
) -> list[Product]:
    """
    Generate plausible substitution candidates.

    Candidates must:
    - not be the base product itself
    - belong to the same product concept
    - use a compatible package unit

    This is candidate generation, not final ranking.
    """
    base_concept = product_concept(base)
    base_package = parse_package_size(
        base.package_size
    )

    candidates = []

    for product in products:
        if product.id == base.id:
            continue

        if product_concept(product) != base_concept:
            continue

        candidate_package = parse_package_size(
            product.package_size
        )

        if not package_compatible(
            base_package,
            candidate_package,
        ):
            continue

        candidates.append(product)

    return candidates


class SimilarityIndex:
    """TF-IDF item similarity index."""

    def __init__(
        self,
        products: list[Product],
    ):
        self.products = products

        self._vectorizer = TfidfVectorizer(
            stop_words="english",
        )

        if products:
            self._matrix = self._vectorizer.fit_transform(
                [
                    product.text()
                    for product in products
                ]
            )
        else:
            self._matrix = None

    def recommend_similar(
        self,
        product_id: int,
        top_k: int = 5,
    ) -> list[tuple[Product, float]]:
        """
        Return the most similar compatible products.

        Candidate generation happens before similarity ranking:
        - same product concept
        - compatible package unit
        - exclude the requested product

        This prevents unrelated products from entering the similarity
        ranking simply because their text happens to overlap.
        """

        if (
            not self.products
            or self._matrix is None
        ):
            return []

        base_product = next(
            (
                product
                for product in self.products
                if product.id == product_id
            ),
            None,
        )

        if base_product is None:
            return []

        candidates = compatible_candidates(
            base=base_product,
            products=self.products,
        )

        if not candidates:
            return []

        candidate_ids = {
            product.id
            for product in candidates
        }

        product_index = next(
            (
                index
                for index, product in enumerate(
                    self.products
                )
                if product.id == product_id
            ),
            None,
        )

        if product_index is None:
            return []

        similarities = cosine_similarity(
            self._matrix[product_index],
            self._matrix,
        ).flatten()

        ranked_indices = np.argsort(
            -similarities,
        )

        results = []

        for index in ranked_indices:
            candidate = self.products[index]

            if candidate.id not in candidate_ids:
                continue

            if (
                candidate.identity_text()
                == base_product.identity_text()
            ):
                continue

            results.append(
                (
                    candidate,
                    float(similarities[index]),
                )
            )

            if len(results) >= top_k:
                break

        return results

    def cheaper_substitutes(
        self,
        product_id: int,
        top_k: int = 3,
    ) -> list[tuple[Product, float]]:
        """
        Return similar products that are strictly cheaper.

        Candidates are first generated from the similarity index and
        then filtered by price. Similarity remains the primary ranking
        signal, with a small adjustment for price savings.
        """

        if (
            not self.products
            or self._matrix is None
        ):
            return []

        base_product = next(
            (
                product
                for product in self.products
                if product.id == product_id
            ),
            None,
        )

        if base_product is None:
            return []

        if base_product.unit_price <= 0:
            return []

        candidates = self.recommend_similar(
            product_id=product_id,
            top_k=max(
                top_k * 3,
                10,
            ),
        )

        cheaper = [
            (
                product,
                similarity,
            )
            for product, similarity in candidates
            if (
                product.unit_price > 0
                and product.unit_price < base_product.unit_price
            )
        ]

        cheaper.sort(
            key=lambda item: (
                item[1]
                - 0.01
                * (
                    base_product.unit_price
                    - item[0].unit_price
                )
            ),
            reverse=True,
        )

        return cheaper[:top_k]