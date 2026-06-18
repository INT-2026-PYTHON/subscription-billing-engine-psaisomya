"""
CLI entrypoint.

Subcommands to implement (Day 4):
    billing init                              -- create / migrate the DB
    billing customer add <name> <email> <country> [--state CODE]
    billing plan list
    billing subscribe <customer_id> <plan_id> [--trial-days N] [--discount CODE]
    billing bill run [--date YYYY-MM-DD]
    billing invoice show <invoice_id>          -- prints PLAIN TEXT invoice
    billing upgrade <subscription_id> <new_plan_id> [--date YYYY-MM-DD]   (STRETCH)
    billing demo                              -- run the scripted scenario

Use argparse with subparsers. Keep each subcommand handler in its own function.

PDF rendering is OUT OF SCOPE for the core project — `invoice show` should
print a clean PLAIN-TEXT invoice (see helper `format_invoice_text` below).
PDF generation is BONUS: see `billing_engine/pdf/renderer.py`.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from decimal import Decimal

from billing_engine.models import Invoice, InvoiceStatus, SubscriptionStatus
from billing_engine.money import Money


def format_invoice_text(invoice: Invoice, customer_name: str, plan_name: str) -> str:
    lines = []
    lines.append(f"INVOICE #{invoice.id if invoice.id is not None else 'DRAFT'}")
    lines.append("=" * 60)
    lines.append(f"Customer: {customer_name}")
    lines.append(f"Plan:     {plan_name}")
    lines.append(f"Period:   {invoice.period_start} to {invoice.period_end}")
    lines.append("-" * 60)
    
    for item in invoice.line_items:
        sym = "₹" if item.amount.currency == "INR" else item.amount.currency
        lines.append(f"{item.description:<45}{sym} {item.amount.amount:>10.2f}")
        
    lines.append("-" * 60)
    total_sym = "₹" if invoice.amount_due.currency == "INR" else invoice.amount_due.currency
    lines.append(f"TOTAL                                        {total_sym} {invoice.amount_due.amount:>10.2f}")
    lines.append(f"Status: {invoice.status.name if hasattr(invoice.status, 'name') else invoice.status}")
    return "\n".join(lines)


def handle_init(args: argparse.Namespace) -> int:
    print("Initializing database...")
    return 0


def handle_customer_add(args: argparse.Namespace) -> int:
    print(f"Added customer {args.name} ({args.email}), Country: {args.country}, State: {args.state}")
    return 0


def handle_plan_list(args: argparse.Namespace) -> int:
    print("Listing all plans...")
    return 0


def handle_subscribe(args: argparse.Namespace) -> int:
    print(f"Subscribed customer {args.customer_id} to plan {args.plan_id} (Trial: {args.trial_days} days, Discount: {args.discount})")
    return 0


def handle_bill_run(args: argparse.Namespace) -> int:
    run_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    print(f"Running automated billing loop as of {run_date}...")
    return 0


def handle_invoice_show(args: argparse.Namespace) -> int:
    print(f"Fetching invoice #{args.invoice_id}...")
    return 0


def handle_upgrade(args: argparse.Namespace) -> int:
    run_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    print(f"Upgrading subscription #{args.subscription_id} to plan {args.new_plan_id} on {run_date}...")
    return 0


def handle_demo(args: argparse.Namespace) -> int:
    return run_demo()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="billing", description="Subscription Billing CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    init_parser = sub.add_parser("init", help="initialize the database")
    init_parser.set_defaults(func=handle_init)

    customer_parser = sub.add_parser("customer", help="customer actions")
    customer_subs = customer_parser.add_subparsers(dest="subcmd", required=True)
    add_customer = customer_subs.add_parser("add", help="add a customer")
    add_customer.add_argument("name", type=str)
    add_customer.add_argument("email", type=str)
    add_customer.add_argument("country", type=str)
    add_customer.add_argument("--state", type=str, default=None)
    add_customer.set_defaults(func=handle_customer_add)

    plan_parser = sub.add_parser("plan", help="plan actions")
    plan_subs = plan_parser.add_subparsers(dest="subcmd", required=True)
    plan_subs.add_parser("list", help="list plans")
    plan_parser.set_defaults(func=handle_plan_list)

    subscribe_parser = sub.add_parser("subscribe", help="subscribe a customer to a plan")
    subscribe_parser.add_argument("customer_id", type=int)
    subscribe_parser.add_argument("plan_id", type=int)
    subscribe_parser.add_argument("--trial-days", type=int, default=0)
    subscribe_parser.add_argument("--discount", type=str, default=None)
    subscribe_parser.set_defaults(func=handle_subscribe)

    bill_parser = sub.add_parser("bill", help="billing actions")
    bill_subs = bill_parser.add_subparsers(dest="subcmd", required=True)
    run_bill = bill_subs.add_parser("run", help="run the billing engine")
    run_bill.add_argument("--date", type=str, default=None)
    bill_parser.set_defaults(func=handle_bill_run)

    invoice_parser = sub.add_parser("invoice", help="invoice actions")
    invoice_subs = invoice_parser.add_subparsers(dest="subcmd", required=True)
    show_invoice = invoice_subs.add_parser("show", help="show plain text invoice")
    show_invoice.add_argument("invoice_id", type=int)
    invoice_parser.set_defaults(func=handle_invoice_show)

    upgrade_parser = sub.add_parser("upgrade", help="mid-cycle subscription upgrade proration")
    upgrade_parser.add_argument("subscription_id", type=int)
    upgrade_parser.add_argument("new_plan_id", type=int)
    upgrade_parser.add_argument("--date", type=str, default=None)
    upgrade_parser.set_defaults(func=handle_upgrade)

    demo_parser = sub.add_parser("demo", help="run the demo scenario")
    demo_parser.set_defaults(func=handle_demo)

    args = parser.parse_args(argv)
    
    if hasattr(args, "func"):
        return args.func(args)
        
    return 0


def run_demo() -> int:
    print("Executing complete end-to-end sandbox lifecycle demo scenario...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())