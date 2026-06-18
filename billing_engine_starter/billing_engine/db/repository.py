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
        return customers


# ============================================================
# PLANS  +  PLAN TIERS
# ============================================================
class PlanRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, plan: Plan) -> Plan:
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO plans (name, pricing_type, billing_period, currency)
                VALUES (?, ?, ?, ?)
                """,
                (plan.name, plan.pricing_type.value, plan.billing_period.value, plan.currency)
            )
            plan.id = cursor.lastrowid
            return plan

    def get(self, plan_id: int) -> Optional[Plan]:
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, pricing_type, billing_period, currency FROM plans WHERE id = ?",
            (plan_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return Plan(
            id=row["id"],
            name=row["name"],
            pricing_type=PricingType(row["pricing_type"]),
            billing_period=BillingPeriod(row["billing_period"]),
            currency=row["currency"]
        )

    def list_all(self) -> list[Plan]:
        """Return all plans in the system."""
        query = """
            SELECT id, name, base_price
            FROM plans
        """
        plans = []
        with self.db.connect() as conn:
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            conn.close()

        from billing_engine.models import Money
        for row in rows:
            plans.append(
                Plan(
                    id=row["id"],
                    name=row["name"],
                    base_price=Money.from_storage(row["base_price"])
                )
            )
        return plans



class PlanTierRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, plan: Plan) -> Plan:
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO plans (name, pricing_type, billing_period, currency)
                VALUES (?, ?, ?, ?)
                """,
                (plan.name, plan.pricing_type.value, plan.billing_period.value, plan.currency)
            )
            plan.id = cursor.lastrowid
            return plan

    def list_for_plan(self, plan_id: str) -> list[PlanTier]:
        """Return all tiers belonging to a specific plan ordered by quantity."""
        query = """
            SELECT up_to_quantity, unit_price
            FROM plan_tiers
            WHERE plan_id = ?
            ORDER BY up_to_quantity ASC
        """
        tiers = []
        with self.db.connect() as conn:
            cursor = conn.execute(query, (plan_id,))
            rows = cursor.fetchall()
            conn.close()

        from billing_engine.models import Money, PlanTier
        for row in rows:
            tiers.append(
                PlanTier(
                    up_to_quantity=row["up_to_quantity"],
                    unit_price=Money.from_storage(row["unit_price"])
                )
            )
        return tiers

# ============================================================
# DISCOUNTS
# ============================================================
class DiscountRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, discount: Discount) -> Discount:
        """Insert and return a discount."""
        query = """
            INSERT INTO discounts (code, discount_type, amount)
            VALUES (?, ?, ?)
        """
        with self.db.connect() as conn:
            conn.execute(
                query,
                (discount.code, discount.discount_type, discount.amount.to_storage())
            )
            conn.close()
        return discount

    def get_by_code(self, code: str) -> Optional[Discount]:
        """Fetch a discount by its promo code string."""
        query = """
            SELECT code, discount_type, amount
            FROM discounts
            WHERE code = ?
        """
        with self.db.connect() as conn:
            cursor = conn.execute(query, (code,))
            row = cursor.fetchone()
            conn.close()

        if row is None:
            return None

        from billing_engine.models import Money
        return Discount(
            code=row["code"],
            discount_type=row["discount_type"],
            amount=Money.from_storage(row["amount"])
        )

# ============================================================
# SUBSCRIPTIONS
# ============================================================
class SubscriptionRepository:
    def __init__(self, db: Database):
        self.db = db

    def add(self, subscription: Subscription) -> Subscription:
        """Insert and return a subscription with its generated ID."""
        query = """
            INSERT INTO subscriptions (customer_id, plan_id, promo_code, status, current_period_start, current_period_end)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        with self.db.connect() as conn:
            cursor = conn.execute(
                query,
                (
                    subscription.customer_id,
                    subscription.plan_id,
                    subscription.promo_code,
                    subscription.status,
                    subscription.current_period_start.isoformat(),
                    subscription.current_period_end.isoformat()
                )
            )
            new_id = cursor.lastrowid
            conn.close()
        return replace(subscription, id=new_id)

    def get(self, subscription_id: int) -> Optional[Subscription]:
        """Fetch a subscription by its integer ID."""
        query = """
            SELECT id, customer_id, plan_id, promo_code, status, current_period_start, current_period_end
            FROM subscriptions
            WHERE id = ?
        """
        with self.db.connect() as conn:
            cursor = conn.execute(query, (subscription_id,))
            row = cursor.fetchone()
            conn.close()

        if row is None:
            return None

        from datetime import date
        return Subscription(
            id=row["id"],
            customer_id=row["customer_id"],
            plan_id=row["plan_id"],
            promo_code=row["promo_code"],
            status=row["status"],
            current_period_start=date.fromisoformat(row["current_period_start"]),
            current_period_end=date.fromisoformat(row["current_period_end"])
        )

    def get_due_for_billing(self, billing_date: date) -> list[Subscription]:
        """Fetch active subscriptions whose current period ends on or before the billing date."""
        query = """
            SELECT id, customer_id, plan_id, promo_code, status, current_period_start, current_period_end
            FROM subscriptions
            WHERE status = 'ACTIVE' AND current_period_end <= ?
        """
        subscriptions = []
        with self.db.connect() as conn:
            cursor = conn.execute(query, (billing_date.isoformat(),))
            rows = cursor.fetchall()
            conn.close()

        from datetime import date as dt_date
        for row in rows:
            subscriptions.append(
                Subscription(
                    id=row["id"],
                    customer_id=row["customer_id"],
                    plan_id=row["plan_id"],
                    promo_code=row["promo_code"],
                    status=row["status"],
                    current_period_start=dt_date.fromisoformat(row["current_period_start"]),
                    current_period_end=dt_date.fromisoformat(row["current_period_end"])
                )
            )
        return subscriptions

    def update_period(self, subscription_id: int, start_date: date, end_date: date) -> None:
        """Update the period start and end dates for a subscription."""
        query = """
            UPDATE subscriptions
            SET current_period_start = ?, current_period_end = ?
            WHERE id = ?
        """
        with self.db.connect() as conn:
            conn.execute(query, (start_date.isoformat(), end_date.isoformat(), subscription_id))
            conn.close()

    def update_status(self, subscription_id: int, status: str) -> None:
        """Update the operational status string of a subscription."""
        query = """
            UPDATE subscriptions
            SET status = ?
            WHERE id = ?
        """
        with self.db.connect() as conn:
            conn.execute(query, (status, subscription_id))
            conn.close()

    def list_all(self) -> list[Subscription]:
        """Return all subscriptions in the system."""
        query = """
            SELECT id, customer_id, plan_id, promo_code, status, current_period_start, current_period_end
            FROM subscriptions
        """
        subscriptions = []
        with self.db.connect() as conn:
            cursor = conn.execute(query)
            rows = cursor.fetchall()
            conn.close()

        from datetime import date as dt_date
        for row in rows:
            subscriptions.append(
                Subscription(
                    id=row["id"],
                    customer_id=row["customer_id"],
                    plan_id=row["plan_id"],
                    promo_code=row["promo_code"],
                    status=row["status"],
                    current_period_start=dt_date.fromisoformat(row["current_period_start"]),
                    current_period_end=dt_date.fromisoformat(row["current_period_end"])
                )
            )
        return subscriptions
# ============================================================
# USAGE
# ============================================================
class UsageRecordRepository:
    def __init__(self, db: Database):
        self.db = db

    def add_usage(self, subscription_id: int, quantity: int, usage_date: date) -> None:
        with self.db.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO usage_records (subscription_id, quantity, usage_date) VALUES (?, ?, ?)",
                (subscription_id, quantity, usage_date.isoformat())
            )

    def count_for_subscription(self, subscription_id: int, start_date: date, end_date: date) -> int:
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT SUM(quantity) as total 
            FROM usage_records 
            WHERE subscription_id = ? AND usage_date >= ? AND usage_date < ?
            """,
            (subscription_id, start_date.isoformat(), end_date.isoformat())
        )
        row = cursor.fetchone()
        return row["total"] if row["total"] is not None else 0



# ============================================================
# INVOICES + LINE ITEMS
# ============================================================
class InvoiceRepository:
    def __init__(self, db: Database):
        self.db = db

    def add(self, invoice: Invoice) -> Invoice:
        """Insert and return an invoice with its generated ID."""
        query = """
            INSERT INTO invoices (subscription_id, period_start, period_end, amount_due, is_paid)
            VALUES (?, ?, ?, ?, ?)
        """
        with self.db.connect() as conn:
            cursor = conn.execute(
                query,
                (
                    invoice.subscription_id,
                    invoice.period_start.isoformat(),
                    invoice.period_end.isoformat(),
                    invoice.amount_due.to_storage(),
                    1 if invoice.is_paid else 0
                )
            )
            new_id = cursor.lastrowid
            conn.close()
        return replace(invoice, id=new_id)

    def count_for_subscription(self, subscription_id: int) -> int:
        """Return the count of invoices generated for a subscription."""
        query = """
            SELECT COUNT(*) as invoice_count 
            FROM invoices 
            WHERE subscription_id = ?
        """
        with self.db.connect() as conn:
            cursor = conn.execute(query, (subscription_id,))
            row = cursor.fetchone()
            conn.close()
        return row["invoice_count"] if row else 0

    def mark_paid(self, invoice_id: int) -> None:
        """Update an invoice status to paid."""
        query = """
            UPDATE invoices 
            SET is_paid = 1 
            WHERE id = ?
        """
        with self.db.connect() as conn:
            conn.execute(query, (invoice_id,))
            conn.close()


class InvoiceLineItemRepository:
    def __init__(self, db: Database):
        self.db = db

    def add(self, line_item: InvoiceLineItem) -> InvoiceLineItem:
        """Insert and return an invoice line item."""
        query = """
            INSERT INTO invoice_line_items (invoice_id, description, amount)
            VALUES (?, ?, ?)
        """
        with self.db.connect() as conn:
            conn.execute(
                query,
                (line_item.invoice_id, line_item.description, line_item.amount.to_storage())
            )
            conn.close()
        return line_item

    def list_for_invoice(self, invoice_id: int) -> list[InvoiceLineItem]:
        """Return all line items matching an invoice ID."""
        query = """
            SELECT invoice_id, description, amount 
            FROM invoice_line_items 
            WHERE invoice_id = ?
        """
        line_items = []
        with self.db.connect() as conn:
            cursor = conn.execute(query, (invoice_id,))
            rows = cursor.fetchall()
            conn.close()

        from billing_engine.models import Money
        for row in rows:
            line_items.append(
                InvoiceLineItem(
                    invoice_id=row["invoice_id"],
                    description=row["description"],
                    amount=Money.from_storage(row["amount"])
                )
            )
        return line_item

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
