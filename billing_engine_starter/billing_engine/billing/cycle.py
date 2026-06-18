"""
BillingCycle — finds due subscriptions, generates invoices, posts ledger DEBITs,
advances the subscription period. Must be IDEMPOTENT (safe to run twice).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable, Optional

from billing_engine.db import (
    Database,
    CustomerRepository, PlanRepository, SubscriptionRepository,
    UsageRecordRepository, InvoiceRepository, InvoiceLineItemRepository,
    LedgerRepository,
)
from billing_engine.models import Subscription
from .pipeline import build_invoice
from .proration import compute_proration


@dataclass
class BillingResult:
    invoices_created: int
    invoices_skipped_duplicate: int
    trials_activated: int


class BillingCycle:

    def __init__(
        self,
        db: Database,
        customer_repo: CustomerRepository,
        plan_repo: PlanRepository,
        subscription_repo: SubscriptionRepository,
        usage_repo: UsageRecordRepository,
        invoice_repo: InvoiceRepository,
        line_item_repo: InvoiceLineItemRepository,
        ledger_repo: LedgerRepository,
        strategy_factory: Callable,
        discount_factory: Callable,
        tax_factory: Callable,
    ) -> None:
        self.db = db
        self.customer_repo = customer_repo
        self.plan_repo = plan_repo
        self.subscription_repo = subscription_repo
        self.usage_repo = usage_repo
        self.invoice_repo = invoice_repo
        self.line_item_repo = line_item_repo
        self.ledger_repo = ledger_repo
        self.strategy_factory = strategy_factory
        self.discount_factory = discount_factory
        self.tax_factory = tax_factory

    def run(self, as_of: date) -> BillingResult:
        result = BillingResult(invoices_created=0, invoices_skipped_duplicate=0, trials_activated=0)
        due_subscriptions = self.subscription_repo.find_due_subscriptions(as_of)

        for sub in due_subscriptions:
            with self.db.transaction():
                existing_invoice = self.invoice_repo.find_by_period(
                    subscription_id=sub.id,
                    period_start=sub.current_period_start,
                    period_end=sub.current_period_end
                )
                if existing_invoice:
                    result.invoices_skipped_duplicate += 1
                    continue

                if sub.status == "trialing":
                    if sub.trial_end and sub.trial_end <= as_of:
                        sub.status = "active"
                        result.trials_activated += 1
                        sub.current_period_start = sub.trial_end
                        sub.current_period_end = sub.trial_end + timedelta(days=30) 
                
                customer = self.customer_repo.get_by_id(sub.customer_id)
                plan = self.plan_repo.get_by_id(sub.plan_id)
                usage_records = self.usage_repo.get_for_period(sub.id, sub.current_period_start, sub.current_period_end)
                
                invoice = build_invoice(
                    customer=customer,
                    plan=plan,
                    subscription=sub,
                    usage_records=usage_records,
                    strategy_factory=self.strategy_factory,
                    discount_factory=self.discount_factory,
                    tax_factory=self.tax_factory,
                    period_start=sub.current_period_start,
                    period_end=sub.current_period_end
                )
                
                self.invoice_repo.save(invoice)
                for item in invoice.line_items:
                    self.line_item_repo.save(item)
                
                self.ledger_repo.post_debit(
                    customer_id=sub.customer_id,
                    amount=invoice.total_amount,
                    description=f"Invoice #{invoice.id} for period {sub.current_period_start} to {sub.current_period_end}",
                    reference_id=invoice.id
                )
                
                days_in_period = (sub.current_period_end - sub.current_period_start).days
                sub.current_period_start = sub.current_period_end
                sub.current_period_end = sub.current_period_start + timedelta(days=days_in_period)
                
                self.subscription_repo.save(sub)
                result.invoices_created += 1

        return result

    def upgrade_subscription(self, subscription_id: int, new_plan_id: int, switch_date: date) -> None:
        with self.db.transaction():
            sub = self.subscription_repo.get_by_id(subscription_id)
            if not sub:
                raise ValueError(f"Subscription {subscription_id} not found.")
                
            old_plan = self.plan_repo.get_by_id(sub.plan_id)
            new_plan = self.plan_repo.get_by_id(new_plan_id)
            customer = self.customer_repo.get_by_id(sub.customer_id)
            
            proration_result = compute_proration(
                old_plan=old_plan,
                new_plan=new_plan,
                period_start=sub.current_period_start,
                period_end=sub.current_period_end,
                switch_date=switch_date
            )
            
            if proration_result.net_amount > 0:
                pass 
                
            if proration_result.net_amount != 0:
                self.ledger_repo.post_transaction(
                    customer_id=sub.customer_id,
                    amount=proration_result.net_amount,
                    description=f"Proration adjustment: Upgraded from {old_plan.name} to {new_plan.name}",
                    reference_id=sub.id
                )
                
            sub.plan_id = new_plan_id
            self.subscription_repo.save(sub)