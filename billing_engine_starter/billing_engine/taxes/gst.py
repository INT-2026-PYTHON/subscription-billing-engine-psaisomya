"""
GSTCalculator — Indian Goods & Services Tax.

The rule:
    - If customer_state == seller_state (or seller_state is "")  =>  intra-state
        -> charge CGST + SGST (split equally, e.g. 9% + 9% = 18%)
    - Else  =>  inter-state
        -> charge IGST (e.g. 18%)

Customers without a state code default to IGST (safe choice).
"""

from decimal import Decimal

from billing_engine.money import Money
from billing_engine.taxes.base import TaxCalculator, TaxContext, TaxBreakdown


class GSTCalculator(TaxCalculator):
    def __init__(self, cgst: Decimal, sgst: Decimal, igst: Decimal) -> None:
        if not all(isinstance(r, Decimal) for r in [cgst, sgst, igst]):
            raise TypeError("Rates must be Decimal")
        if not all(Decimal('0') <= r <= Decimal('1') for r in [cgst, sgst, igst]):
            raise ValueError("Rates must be between 0 and 1")
        if cgst + sgst != igst:
            raise ValueError("cgst + sgst must equal igst")
            
        self.cgst = cgst
        self.sgst = sgst
        self.igst = igst

    def apply(self, taxable: Money, context: TaxContext) -> TaxBreakdown:
        intra = bool(context.customer_state) and context.customer_state == context.seller_state
        
        components = []
        
        if intra:
            cgst_amount = taxable * self.cgst
            sgst_amount = taxable * self.sgst
            
            components.append((f"CGST {self.cgst * 100}%", cgst_amount))
            components.append((f"SGST {self.sgst * 100}%", sgst_amount))
            total_tax = cgst_amount + sgst_amount
        else:
            igst_amount = taxable * self.igst
            components.append((f"IGST {self.igst * 100}%", igst_amount))
            total_tax = igst_amount

        return TaxBreakdown(components=components, total=total_tax)
        