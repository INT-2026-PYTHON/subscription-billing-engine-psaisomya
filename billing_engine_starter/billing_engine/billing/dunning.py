"""
DunningProcess — finite state machine for failed-payment retries.

States:
    PENDING       (initial)  →  RETRYING  on first failure
    RETRYING      ──→ SUCCEEDED    when a retry succeeds
                  ──→ FAILED_FINAL after 3 total failures
    SUCCEEDED     (terminal)
    FAILED_FINAL  (terminal — also flips subscription to PAST_DUE)

Retry schedule:
    attempt 2 scheduled at  now + 1 day
    attempt 3 scheduled at  now + 3 days
    (no attempt 4 — after the 3rd failure we mark FAILED_FINAL)

After the subscription has been PAST_DUE for 7 days with no recovery,
the BillingCycle.run (Day 2 work) may flip it to CANCELLED — that
transition does NOT live in this file.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Optional

from billing_engine.db import (
    InvoiceRepository, LedgerRepository, SubscriptionRepository,
    PaymentAttemptRepository,
)
from billing_engine.models import Invoice, LedgerEntry, LedgerDirection, SubscriptionStatus
from billing_engine.payments.gateway import PaymentGateway, PaymentResult


class DunningState(str, Enum):
    PENDING = "PENDING"
    RETRYING = "RETRYING"
    SUCCEEDED = "SUCCEEDED"
    FAILED_FINAL = "FAILED_FINAL"


@dataclass(frozen=True)
class DunningOutcome:
    state: DunningState
    attempt_no: int
    next_retry_at: Optional[datetime]


RETRY_DELAYS_DAYS = {1: 1, 2: 3}
MAX_ATTEMPTS = 3


class DunningProcess:
    def __init__(
        self,
        gateway: PaymentGateway,
        invoice_repo: InvoiceRepository,
        ledger_repo: LedgerRepository,
        subscription_repo: SubscriptionRepository,
        attempt_repo: PaymentAttemptRepository,
    ) -> None:
        self.gateway = gateway
        self.invoice_repo = invoice_repo
        self.ledger_repo = ledger_repo
        self.subscription_repo = subscription_repo
        self.attempt_repo = attempt_repo

    def attempt(self, invoice: Invoice, customer_id: int, now: datetime) -> DunningOutcome:
        existing_attempts = self.attempt_repo.list_for_invoice(invoice.id) [cite: 131, 169]
        current_attempt_no = len(existing_attempts) + 1 [cite: 393]

        payment_result = self.gateway.charge(invoice.amount_due, customer_id)
        
        self.attempt_repo.add(invoice.id, "SUCCESS" if payment_result.success else "FAIL", now.date()) [cite: 131, 158]

        if payment_result.success:
            self.invoice_repo.mark_paid(invoice.id) [cite: 132, 147]
            self.subscription_repo.update_status(invoice.subscription_id, SubscriptionStatus.ACTIVE) [cite: 139]
            return DunningOutcome(DunningState.SUCCEEDED, current_attempt_no, None)

        if current_attempt_no >= MAX_ATTEMPTS: [cite: 141]
            self.invoice_repo.mark_failed(invoice.id) [cite: 135, 200]
            self.subscription_repo.update_status(
                invoice.subscription_id, 
                SubscriptionStatus.PAST_DUE, 
                past_due_since=now.date()
            ) [cite: 138, 202]
            return DunningOutcome(DunningState.FAILED_FINAL, current_attempt_no, None)

        delay_days = RETRY_DELAYS_DAYS.get(current_attempt_no, 1) [cite: 394]
        next_retry_at = now + timedelta(days=delay_days) [cite: 386]
        
        self.subscription_repo.update_status(
            invoice.subscription_id, 
            SubscriptionStatus.PAST_DUE, 
            past_due_since=now.date()
        ) [cite: 138, 202]
        
        return DunningOutcome(DunningState.RETRYING, current_attempt_no, next_retry_at)

    @staticmethod
    def should_cancel(past_due_since: date, today: date, grace_days: int = 7) -> bool:
        if not past_due_since:
            return False
        return (today - past_due_since).days >= grace_days [cite: 141, 292]