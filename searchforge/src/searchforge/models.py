"""Typed, dependency-free models for SearchForge's constrained basket planner."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ProductCandidate:
    """A product that can satisfy one requested basket slot.

    Prices use integer cents to avoid floating-point currency errors.
    Nutrition values are per selected package/quantity for this prototype.
    """

    product_id: str
    name: str
    price_cents: int
    protein_g: float = 0.0
    fiber_g: float = 0.0
    tags: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.product_id.strip():
            raise ValueError("product_id must not be empty")
        if not self.name.strip():
            raise ValueError("name must not be empty")
        if self.price_cents < 0:
            raise ValueError("price_cents must be non-negative")
        if self.protein_g < 0 or self.fiber_g < 0:
            raise ValueError("nutrition values must be non-negative")


@dataclass(frozen=True, slots=True)
class BasketSlot:
    """One required item/category and its eligible substitution candidates."""

    slot_id: str
    candidates: tuple[ProductCandidate, ...]

    def __post_init__(self) -> None:
        if not self.slot_id.strip():
            raise ValueError("slot_id must not be empty")


@dataclass(frozen=True, slots=True)
class BasketConstraints:
    """Hard constraints that a completed basket must satisfy."""

    budget_cents: int
    min_protein_g: float = 0.0
    min_fiber_g: float = 0.0
    forbidden_tags: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if self.budget_cents < 0:
            raise ValueError("budget_cents must be non-negative")
        if self.min_protein_g < 0 or self.min_fiber_g < 0:
            raise ValueError("minimum nutrition values must be non-negative")


@dataclass(frozen=True, slots=True)
class BasketPlan:
    """Optimal feasible basket and diagnostics for evaluation."""

    selected_products: tuple[ProductCandidate, ...]
    total_price_cents: int
    total_protein_g: float
    total_fiber_g: float
    expanded_nodes: int
    generated_nodes: int

    @property
    def total_price_aud(self) -> float:
        return self.total_price_cents / 100
