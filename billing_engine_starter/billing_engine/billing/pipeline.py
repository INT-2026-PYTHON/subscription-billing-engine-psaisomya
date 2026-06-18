"""
build_invoice — PURE function that turns inputs into an Invoice dataclass.

⚠️ NO database calls here. No `datetime.now()`. No PDF. Just math.

The order is FIXED:
    1. base       = strategy.calculate(usage)
    2. discount   = discount.apply(base) if discount else 0
    3. taxable    = base - discount
    4. tax        = tax_calc.apply(taxable)
    5. total      = taxable + tax.total
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from billing_engine.money import Money
from billing_engine.models import (
    Invoice, InvoiceStatus, InvoiceLineItem, LineItemKind, Subscription, Plan,
)
from billing_engine.pricing.base import PricingStrategy
from billing_engine.discounts.base import Discount, DiscountContext
from billing_engine.taxes.base import TaxCalculator, TaxContext


def build_invoice(
    subscription: Subscription,
    plan: Plan,
    strategy: PricingStrategy,
    discount: Optional[Discount],
    tax_calc: TaxCalculator,
    tax_context: TaxContext,
    usage_quantity: int,
    period_start: date,
    period_end: date,
    invoice_count_so_far: int,
) -> Invoice:
    base_price = strategy.calculate(usage_quantity)
    
    currency = base_price.currency
    line_items = []
    
    line_items.append(InvoiceLineItem(
        id=None,
        invoice_id=None,
        description=f"Base plan charges for {plan.name}",
        amount=base_price.amount,
        quantity=1,
        unit_price=base_price.amount,
        kind=LineItemKind.BASE
    ))

    discount_amount = 0
    if discount:
        context = DiscountContext(invoice_count_so_far=invoice_count_so_far)
        discount_amount = discount.apply(base_price.amount, context)
        if discount_amount > 0:
            line_items.append(InvoiceLineItem(
                id=None,
                invoice_id=None,
                description=f"Applied discount: {discount.name}",
                amount=-discount_amount,
                quantity=1,
                unit_price=-discount_amount,
                kind=LineItemKind.DISCOUNT
            ))

    taxable_amount = max(0, base_price.amount - discount_amount)
    
    tax_res = tax_calc.apply(taxable_amount, tax_context)
    for tax_line in tax_res.lines:
        line_items.append(InvoiceLineItem(
            id=None,
            invoice_id=None,
            description=f"Tax: {tax_line.name} ({tax_line.rate * 100}%)",
            amount=tax_line.amount,
            quantity=1,
            unit_price=tax_line.amount,
            kind=LineItemKind.TAX
        ))

    final_total = taxable_amount + tax_res.total

    return Invoice(
        id=None,
        subscription_id=subscription.id,
        customer_id=subscription.customer_id,
        period_start=period_start,
        period_end=period_end,
        amount_due=Money(amount=final_total, currency=currency),
        status=InvoiceStatus.DRAFT,
        line_items=line_items
    )