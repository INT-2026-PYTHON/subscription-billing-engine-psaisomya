"""
Repositories — the ONLY place SQL lives.

Each repository wraps the Database connection and exposes methods that
take/return domain dataclasses (defined in billing_engine/models/).

⚠️ YOU IMPLEMENT every method body marked TODO.
   The signatures, docstrings, and the LedgerRepository's append-only
   guarantee are already in place — do not change them.

Conventions:
  - Always use parameterized queries (`?` placeholders) — NEVER f-string SQL.
  - Money values are persisted as TEXT using `money.to_storage()`.
  - Dates are persisted as ISO strings (`date.isoformat()`).
"""

from __future__ import annotations
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from billing_engine.db.database import Database
from billing_engine.money import Money
from billing_engine.models import (
    Customer,
    Plan, PricingType, BillingPeriod,
    Subscription, SubscriptionStatus,
    Invoice, InvoiceStatus, InvoiceLineItem, LineItemKind,
    LedgerEntry, LedgerDirection,
)


# ============================================================
# CUSTOMERS
# ============================================================
class CustomerRepository:
    def __init__(self, db: Database) -> None:
        self.db = db
    def add(self, customer: Customer) -> Customer:
        """Insert and return the customer with `id` populated."""
        query = """
            INSERT INTO customers (name, email, country_code, state_code)
            VALUES (?, ?, ?, ?)
        """
        with self.db.connect() as conn:
            cursor = conn.execute(
                query, 
                (customer.name, customer.email, customer.country_code, customer.state_code)
            )
            new_id = cursor.lastrowid
            conn.close()
            
        return replace(customer, id=new_id)
    
    def get(self, customer_id: int) -> Optional[Customer]:
        query = """
            SELECT id, name, email, country_code, state_code
            FROM customers
            WHERE id = ?
        """
        with self.db.connect() as conn:
            cursor = conn.execute(query, (customer_id,))
            row = cursor.fetchone()
            conn.close()

        if row is None:
            return None

        return Customer(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            country_code=row["country_code"],
            state_code=row["state_code"]
        )
    def find_by_email(self, email: str) -> Optional[Customer]:
        query = """
            SELECT id, name, email, country_code, state_code
            FROM customers
            WHERE email = ?
        """
        with self.db.connect() as conn:
            cursor = conn.execute(query, (email,))
            row = cursor.fetchone()
            conn.close()

        if row is None:
            return None

        return Customer(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            country_code=row["country_code"],
            state_code=row["state_code"]
        )
    def list_all(self) -> list[Customer]:
        query = """
            SELECT id, name, email, country_code, state_code
            FROM customers
        """
        customers = []
        with self.db.connect() as conn:
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            conn.close()

        for row in rows:
            customers.append(
                Customer(
                    id=row["id"],
                    name=row["name"],
                    email=row["email"],
                    country_code=row["country_code"],
                    state_code=row["state_code"]
                )
            )
        return customers


# ============================================================
# PLANS  +  PLAN TIERS
# ============================================================
class PlanRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, plan: Plan) -> Plan:
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement PlanRepository.add")

    def get(self, plan_id: int) -> Optional[Plan]:
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement PlanRepository.get")

    def list_all(self) -> list[Plan]:
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement PlanRepository.list_all")


class PlanTierRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, plan_id: int, from_units: int, to_units: Optional[int], unit_price: Money) -> int:
        """Insert a tier; return new id."""
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement PlanTierRepository.add")

    def list_for_plan(self, plan_id: int, currency: str) -> list[tuple[int, Optional[int], Money]]:
        """Return [(from_units, to_units, unit_price)] ordered by from_units.

        Currency is passed in (the plan_tiers table stores only the amount;
        currency lives on the parent plan).
        """
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement PlanTierRepository.list_for_plan")


# ============================================================
# DISCOUNTS
# ============================================================
class DiscountRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, code: str, discount_type: str, value: str, currency: Optional[str] = None) -> int:
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement DiscountRepository.add")

    def get_by_code(self, code: str) -> Optional[dict]:
        """Return raw row as dict, or None. (Discount has no dataclass yet — we use a dict for now.)"""
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement DiscountRepository.get_by_code")


# ============================================================
# SUBSCRIPTIONS
# ============================================================
class SubscriptionRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, subscription: Subscription) -> Subscription:
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement SubscriptionRepository.add")

    def get(self, subscription_id: int) -> Optional[Subscription]:
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement SubscriptionRepository.get")

    def list_all(self) -> list[Subscription]:
        """All subscriptions, regardless of status. Used by BillingCycle trial scan."""
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement SubscriptionRepository.list_all")

    def get_due_for_billing(self, as_of: date) -> list[Subscription]:
        """Subscriptions whose current_period_end <= as_of AND status is ACTIVE.
        (Hint: trial subscriptions whose trial_end <= as_of should also become billable —
         either handle that here or transition them to ACTIVE first in BillingCycle.)
        """
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement SubscriptionRepository.get_due_for_billing")

    def update_period(self, subscription_id: int, new_start: date, new_end: date) -> None:
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement SubscriptionRepository.update_period")

    def update_status(
        self,
        subscription_id: int,
        new_status: SubscriptionStatus,
        past_due_since: Optional[date] = None,
    ) -> None:
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement SubscriptionRepository.update_status")

    def update_plan(self, subscription_id: int, new_plan_id: int) -> None:
        """Switch the subscription to a different plan (used by upgrade flow)."""
        # TODO Day 4.
        raise NotImplementedError("Day 4: implement SubscriptionRepository.update_plan")


# ============================================================
# USAGE
# ============================================================
class UsageRecordRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, subscription_id: int, metric: str, quantity: int) -> int:
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement UsageRecordRepository.add")

    def sum_for_period(
        self, subscription_id: int, metric: str, period_start: date, period_end: date
    ) -> int:
        # TODO Day 2: SELECT COALESCE(SUM(quantity), 0) ...
        raise NotImplementedError("Day 2: implement UsageRecordRepository.sum_for_period")


# ============================================================
# INVOICES + LINE ITEMS
# ============================================================
class InvoiceRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, invoice: Invoice) -> Invoice:
        """Insert invoice (NOT line items — that's the other repo).

        Must respect the UNIQUE(subscription_id, period_start) constraint.
        If a duplicate is attempted, raise sqlite3.IntegrityError naturally
        (caller is responsible for handling it — this gives idempotency).
        """
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement InvoiceRepository.add")

    def get(self, invoice_id: int) -> Optional[Invoice]:
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement InvoiceRepository.get")

    def count_for_subscription(self, subscription_id: int) -> int:
        """Used by FirstMonthFree discount."""
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement InvoiceRepository.count_for_subscription")

    def mark_paid(self, invoice_id: int) -> None:
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement InvoiceRepository.mark_paid")

    def mark_failed(self, invoice_id: int) -> None:
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement InvoiceRepository.mark_failed")

    def set_pdf_path(self, invoice_id: int, path: str) -> None:
        # TODO Day 4.
        raise NotImplementedError("Day 4: implement InvoiceRepository.set_pdf_path")


class InvoiceLineItemRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, line_item: InvoiceLineItem) -> InvoiceLineItem:
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement InvoiceLineItemRepository.add")

    def list_for_invoice(self, invoice_id: int) -> list[InvoiceLineItem]:
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement InvoiceLineItemRepository.list_for_invoice")


# ============================================================
# LEDGER — APPEND-ONLY (do not implement update/delete)
# ============================================================
class LedgerRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, entry: LedgerEntry) -> LedgerEntry:
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement LedgerRepository.add")

    def list_for_customer(self, customer_id: int) -> list[LedgerEntry]:
        # TODO Day 2.
        raise NotImplementedError("Day 2: implement LedgerRepository.list_for_customer")

    # ✅ These two methods are intentionally implemented to REJECT — do not override.
    def update(self, *args, **kwargs):
        raise NotImplementedError("Ledger is append-only. Post a reversing entry instead.")

    def delete(self, *args, **kwargs):
        raise NotImplementedError("Ledger is append-only. Post a reversing entry instead.")


# ============================================================
# PAYMENT ATTEMPTS
# ============================================================
class PaymentAttemptRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(
        self,
        invoice_id: int,
        attempt_no: int,
        status: str,
        failure_reason: Optional[str],
        next_retry_at: Optional[datetime],
    ) -> int:
        # TODO Day 3.
        raise NotImplementedError("Day 3: implement PaymentAttemptRepository.add")

    def list_for_invoice(self, invoice_id: int) -> list[dict]:
        # TODO Day 3.
        raise NotImplementedError("Day 3: implement PaymentAttemptRepository.list_for_invoice")

    def count_for_invoice(self, invoice_id: int) -> int:
        # TODO Day 3.
        raise NotImplementedError("Day 3: implement PaymentAttemptRepository.count_for_invoice")
