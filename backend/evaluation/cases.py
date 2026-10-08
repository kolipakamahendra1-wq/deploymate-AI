"""Synthetic customer implementation cases with gold labels (PRD section 13).

10 integration domains x 4 brief variants = 40 cases. Each variant states or
omits throughput, SLA, failure behaviour, data ownership and delivery mode, so
the gold set of missing-question categories is known exactly.
"""
from __future__ import annotations

from dataclasses import dataclass, field

DOMAINS = [
    dict(company="Northwind", src="order platform", tgt="fulfillment system", entity="Order", pattern="webhook-queue",
         purpose=["paid orders are shipped automatically", "customers see tracking updates"],
         mapping={"order_id": "shipment_ref", "customer_email": "recipient_email", "shipping_address": "ship_to",
                  "line_items": "items", "status": "state", "total_amount": None}),
    dict(company="Lumen Retail", src="Shopify store", tgt="NetSuite ERP", entity="Sale", pattern="webhook-queue",
         purpose=["every sale is booked in the ledger", "finance sees revenue the same day"],
         mapping={"id": "external_id", "total_price": "amount", "currency": "currency", "customer_email": "email",
                  "created_at": "trandate", "discount_codes": None}),
    dict(company="Brightpath", src="CRM", tgt="billing system", entity="Account", pattern="crm-sync",
         purpose=["new accounts are billed without manual entry", "contact changes stay in sync"],
         mapping={"account_id": "customer_ref", "company_name": "company_name", "billing_email": "invoice_email",
                  "phone": "phone_number", "industry": None}),
    dict(company="Acme Labs", src="HR platform", tgt="payroll service", entity="Employee", pattern="polling-sync",
         purpose=["new hires are paid in their first cycle", "terminations stop payments"],
         mapping={"employee_id": "worker_ref", "full_name": "name", "salary": "gross_pay", "start_date": "start_date",
                  "department": None}),
    dict(company="Helio", src="ticketing tool", tgt="data warehouse", entity="Ticket", pattern="batch-etl",
         purpose=["support metrics are reported daily", "managers can analyse response times"],
         mapping={"ticket_id": "ticket_key", "status": "ticket_state", "created_at": "opened_at", "priority": "priority",
                  "assignee": None}),
    dict(company="CarePoint", src="EHR system", tgt="lab system", entity="LabOrder", pattern="webhook-queue",
         purpose=["lab orders reach the lab instantly", "results flow back to the chart"],
         mapping={"order_id": "requisition_id", "patient_id": "patient_ref", "test_code": "test_code",
                  "ordered_at": "collected_at", "notes": None}),
    dict(company="Fieldwise", src="inventory database", tgt="storefront app", entity="StockLevel", pattern="cdc",
         purpose=["the storefront never sells out-of-stock items", "stock changes appear quickly"],
         mapping={"sku": "product_code", "quantity": "available_qty", "warehouse_id": "location_id",
                  "updated_at": "last_updated", "bin": None}),
    dict(company="Orbit", src="Salesforce", tgt="marketing platform", entity="Lead", pattern="crm-sync",
         purpose=["qualified leads enter nurture campaigns", "unsubscribes are respected in both tools"],
         mapping={"lead_id": "contact_ref", "email": "email", "first_name": "given_name", "lead_source": "source",
                  "rating": None}),
    dict(company="Staywell", src="booking platform", tgt="accounting system", entity="Booking", pattern="batch-etl",
         purpose=["every booking produces an invoice", "refunds are reflected in the books"],
         mapping={"booking_id": "invoice_ref", "guest_email": "customer_email", "amount": "total",
                  "currency": "currency_code", "room_type": None}),
    dict(company="Gridline", src="legacy billing system", tgt="analytics platform", entity="Invoice", pattern="file-drop",
         purpose=["finance can analyse invoices", "the old CSV export keeps working"],
         mapping={"invoice_no": "invoice_number", "customer_name": "customer", "amount_due": "amount",
                  "due_date": "due_date", "terms": None}),
]

VARIANTS = [
    dict(volume=True, sla=True, failure=True, ownership=True, mode=True),
    dict(volume=False, sla=False, failure=False, ownership=False, mode=False),
    dict(volume=True, sla=False, failure=True, ownership=False, mode=True),
    dict(volume=False, sla=True, failure=False, ownership=True, mode=False),
]

MODE_TEXT = {
    "webhook-queue": "Updates should flow in real time as events.",
    "crm-sync": "Changes should sync every few minutes in both directions.",
    "polling-sync": "The source has no webhooks, so changes can be polled every few minutes.",
    "batch-etl": "A nightly batch load is fine.",
    "cdc": "Database changes should stream in real time.",
    "file-drop": "The legacy system can drop a CSV file on SFTP every night.",
}


@dataclass
class Case:
    id: str
    name: str
    brief: str
    openapi: dict
    sample: dict
    gold_requirements: list[str]
    gold_questions: set[str]
    gold_mapping: dict[str, str | None]
    gold_pattern: str
    systems: list[str] = field(default_factory=list)


def _title(s: str) -> str:
    return " ".join(w if w.isupper() or w[0].isupper() else w.capitalize() for w in s.split())


def build_cases() -> list[Case]:
    cases = []
    for d_i, d in enumerate(DOMAINS):
        for v_i, v in enumerate(VARIANTS):
            src, tgt = d["src"], d["tgt"]
            goal = f"connect our {src} to our {tgt}"
            sentences = [f"{d['company']} runs its operations on the {src}.",
                         f"We need to {goal} so {d['purpose'][0]} and {d['purpose'][1]}."]
            if v["volume"]:
                sentences.append("We expect about 1,200 records per minute at peak.")
            if v["sla"]:
                sentences.append("Changes must appear in the target within 5 minutes.")
            if v["failure"]:
                sentences.append("If the target is down, retry and send failures to a dead-letter queue.")
            if v["ownership"]:
                sentences.append(f"The {src} is the source of truth for {d['entity'].lower()} data.")
            if v["mode"]:
                sentences.append(MODE_TEXT[d["pattern"]])
            props = {f: {"type": "string"} for f in d["mapping"]}
            paths = {f"/{d['entity'].lower()}s": {"get": {}, "post": {}},
                     f"/{d['entity'].lower()}s/{{id}}": {"get": {}, "patch": {}}}
            if d["pattern"] == "webhook-queue":
                paths["/webhooks/events"] = {"post": {}}
            spec = {"openapi": "3.0.3", "info": {"title": f"{d['company']} {_title(src)} API"},
                    "components": {"securitySchemes": {"oauth": {"type": "oauth2"}},
                                   "schemas": {d["entity"]: {"type": "object", "properties": props}}},
                    "paths": paths}
            sample = {t: "x" for t in d["mapping"].values() if t} | {"extra_field": "x"}
            gold_q = {"auth"}  # the target never has a spec
            if not v["volume"]:
                gold_q.add("throughput")
            if not v["sla"]:
                gold_q.add("sla")
            if not v["failure"]:
                gold_q.add("failure")
            if not v["ownership"]:
                gold_q.add("data-ownership")
            cases.append(Case(
                id=f"C{d_i * len(VARIANTS) + v_i + 1:02d}", name=f"{d['company']}: {src} -> {tgt} (v{v_i + 1})",
                brief=" ".join(sentences), openapi=spec, sample=sample,
                gold_requirements=[goal, *d["purpose"]], gold_questions=gold_q,
                gold_mapping=d["mapping"], gold_pattern=d["pattern"], systems=[src, tgt],
            ))
    return cases
