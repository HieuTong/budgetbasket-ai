"""
Playground: tweak the utility scores below and see how the optimizer's
choice changes. Run with: python -m ml_playground (from backend/)

Utility is a 0-1 score meaning "how well this item matches what the
user actually wants right now." Try scenarios like:
  - "mostly vegetarian this week" -> raise Rice/Bread, lower Chicken
  - "stocking up, price doesn't matter much" -> flatten all utilities
    close to equal, watch it just fill the budget efficiently
  - "strict, only buy what I always buy" -> set utility = usual_quantity
    match strength, most items near 0 except your regulars
"""
import sys
sys.path.insert(0, ".")

from app.ml.optimizer import BasketItem, optimize_basket

# --- EDIT THESE ---
BUDGET = 40

CANDIDATES = [
    BasketItem(product_id=1, name="Milk 2L", unit_price=3.50, utility=0.9, max_quantity=3),
    BasketItem(product_id=2, name="Bread", unit_price=3.00, utility=0.8, max_quantity=3),
    BasketItem(product_id=3, name="Eggs 12pk", unit_price=6.50, utility=0.7, max_quantity=3),
    BasketItem(product_id=4, name="Chicken Breast 1kg", unit_price=9.00, utility=0.85, max_quantity=3),
    BasketItem(product_id=5, name="Rice 1kg", unit_price=2.80, utility=0.6, max_quantity=3),
]
# --- END EDIT ---

if __name__ == "__main__":
    result = optimize_basket(CANDIDATES, BUDGET)
    print(f"Budget: ${BUDGET}\n")
    for item, qty in result.items:
        print(f"  {qty}x {item.name:20s} @ ${item.unit_price:.2f} (utility={item.utility})")
    print(f"\nTotal spent:   ${result.total_cost}")
    print(f"Total utility: {result.total_utility}")
    print(f"Unspent:       ${BUDGET - result.total_cost:.2f}")
