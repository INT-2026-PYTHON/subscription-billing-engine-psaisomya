"""
TieredPricing — different price per unit depending on the tier the quantity falls into.

This is the "cumulative" / "stacked" tier model, NOT the "volume" model:
    Tiers: [(0, 1000, ₹2.00), (1000, 5000, ₹1.50), (5000, None, ₹1.00)]
    Quantity = 6000:
        First 1000 units  @ ₹2.00 = ₹2000
        Next  4000 units  @ ₹1.50 = ₹6000
        Last  1000 units  @ ₹1.00 = ₹1000
        ------------------------------------
        Total                     = ₹9000

A tier with `to_units = None` is the open-ended top tier.

Tier boundaries are HALF-OPEN on the right: a tier (from, to, price)
covers units strictly less than `to` (i.e. [from, to)).
"""

from dataclasses import dataclass
from typing import Optional

from billing_engine.money import Money
from billing_engine.pricing.base import PricingStrategy


@dataclass(frozen=True)
class Tier:
    from_units: int
    to_units: Optional[int]   
    unit_price: Money


class TieredPricing(PricingStrategy):

    def __init__(self, tiers: list[Tier]) -> None:
        if not tiers:
            raise ValueError("Tiers list cannot be empty")
        self.tiers = sorted(tiers, key=lambda t: t.from_units)

    def calculate(self, quantity: int) -> Money:
        if quantity <= 0:
            return Money(0, self.tiers[0].unit_price.currency)

        total_amount = Money(0, self.tiers[0].unit_price.currency)
        remaining = quantity

        for tier in self.tiers:
            if remaining <= 0:
                break

            tier_span = (tier.to_units - tier.from_units) if tier.to_units is not None else remaining
            units_in_tier = min(remaining, tier_span)

            total_amount += tier.unit_price * units_in_tier
            remaining -= units_in_tier

        return total_amount
