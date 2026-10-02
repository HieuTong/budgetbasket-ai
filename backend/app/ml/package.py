import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Package:
    quantity: float
    unit: str


def parse_package_size(value: str | None) -> Package | None:
    if not value:
        return None

    text = value.upper().strip()

    match = re.search(r"(\d+(?:\.\d+)?)\s*(LB|OZ|KG|G|CT|PACK)", text)

    if not match:
        return None

    quantity = float(match.group(1))
    unit = match.group(2)

    if unit == "PACK":
        unit = "CT"

    return Package(
        quantity=quantity,
        unit=unit,
    )