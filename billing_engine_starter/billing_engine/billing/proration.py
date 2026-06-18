"""
Proration — Day 4 stretch.

Mid-cycle plan change: customer is on Plan A from period_start to period_end,
but on `switch_date` they upgrade (or downgrade) to Plan B.

Day-count proration:
    total_days     = (period_end - period_start).days
    used_days      = (switch_date - period_start).days
    remaining_days = total_days - used_days

    credit = old_price * (remaining_days / total_days)
    charge = new_price * (remaining_days / total_days)

Tax MUST be recalculated on BOTH legs (reverse-tax on the credit,
fresh tax on the new charge). Tax is NOT prorated linearly — the tax
on a proration credit/charge is just `tax_calc.apply(credit_or_charge)`.

The two legs are returned as TAX-INCLUSIVE Money values for the
PRORATION_CREDIT (negative) and PRORATION_CHARGE (positive) line items.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from billing_engine.money import Money
from billing_engine.taxes.base import TaxCalculator, TaxContext


@dataclass(frozen=True)
class ProrationResult:
    credit_amount: Money     
    charge_amount: Money     
    credit_tax: Money        
    charge_tax: Money        


def compute_proration(
    old_plan_price: Money,
    new_plan_price: Money,
    period_start: date,
    period_end: date,
    switch_date: date,
    tax_calc: TaxCalculator,
    tax_context: TaxContext,
) -> ProrationResult:
    total_days = (period_end - period_start).days
    used_days = (switch_date - period_start).days
    remaining_days = total_days - used_days

    currency = old_plan_price.currency
    
    if total_days <= 0 or remaining_days <= 0:
        zero_money = Money(amount=Decimal("0.00"), currency=currency)
        return ProrationResult(zero_money, zero_money, zero_money, zero_money)

    ratio = Decimal(remaining_days) / Decimal(total_days)
    
    credit_subtotal = old_plan_price.amount * ratio
    charge_subtotal = new_plan_price.amount * ratio

    credit_tax_res = tax_calc.apply(credit_subtotal, tax_context)
    charge_tax_res = tax_calc.apply(charge_subtotal, tax_context)

    return ProrationResult(
        credit_amount=Money(amount=credit_subtotal, currency=currency),
        charge_amount=Money(amount=charge_subtotal, currency=currency),
        credit_tax=Money(amount=credit_tax_res.total, currency=currency),
        charge_tax=Money(amount=charge_tax_res.total, currency=currency)
    )