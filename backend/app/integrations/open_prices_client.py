"""
Client for Open Food Facts' Open Prices API — a real, open, community-sourced
database of grocery prices (https://prices.openfoodfacts.org), licensed under
ODbL. Includes Australian entries contributed by shoppers.

This is genuine external data, not synthetic. It will NOT resolve from an
environment with a locked-down network allowlist (e.g. a sandboxed dev
container) — it needs normal outbound internet, which a real deployment
(DigitalOcean/Railway/Fly.io droplet) has.

Docs: https://prices.openfoodfacts.org/api/docs
License requirement: any redistribution of this data must credit
"Open Food Facts / Open Prices" per the ODbL license.
"""
import time
from dataclasses import dataclass

import requests

BASE_URL = "https://prices.openfoodfacts.org/api/v1"


@dataclass
class ExternalPrice:
    product_name: str
    price: float
    currency: str
    date: str
    location_country: str | None
    barcode: str | None


def fetch_au_prices(page_size: int = 50, max_pages: int = 5) -> list[ExternalPrice]:
    """
    Pull recent Australian grocery price entries. Paginates and rate-limits
    politely (the API is community-run and free -- don't hammer it).
    """
    results: list[ExternalPrice] = []
    for page in range(1, max_pages + 1):
        resp = requests.get(
            f"{BASE_URL}/prices",
            params={
                "location_country": "Australia",
                "size": page_size,
                "page": page,
                "order_by": "-date",
            },
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
        items = payload.get("items", [])
        if not items:
            break

        for item in items:
            product = item.get("product") or {}
            results.append(
                ExternalPrice(
                    product_name=product.get("product_name") or item.get("category_tag", "unknown"),
                    price=item["price"],
                    currency=item.get("currency", "AUD"),
                    date=item.get("date", ""),
                    location_country=(item.get("location") or {}).get("country"),
                    barcode=product.get("code"),
                )
            )

        if len(items) < page_size:
            break
        time.sleep(0.5)  # be a polite API citizen

    return results


if __name__ == "__main__":
    prices = fetch_au_prices(max_pages=2)
    print(f"Fetched {len(prices)} AU price entries from Open Prices.")
    for p in prices[:10]:
        print(f"  {p.product_name[:40]:40s} ${p.price:.2f} {p.currency}  ({p.date})")
