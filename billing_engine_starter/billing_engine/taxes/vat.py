"""
VATCalculator — single-rate VAT (e.g. 19% in Germany).
"""

from decimal import Decimal

from billing_engine.money import Money
from billing_engine.taxes.base import TaxCalculator, TaxContext, TaxBreakdown


class VATCalculator(TaxCalculator):
    def __init__(self, rate: Decimal, label: str = "VAT") -> None:
        if not isinstance(rate, Decimal):
            raise TypeError("Rate must be Decimal")
        if not (Decimal('0') <= rate <= Decimal('1')):
            raise ValueError("Rate must be between 0 and 1")
        self.rate = rate
        self.label = label

    def apply(self, taxable: Money, context: TaxContext = None) -> TaxBreakdown:
        tax_amount = taxable * self.rate
        components = [(self.label, tax_amount)]
        return TaxBreakdown(components=components, total=tax_amount) 