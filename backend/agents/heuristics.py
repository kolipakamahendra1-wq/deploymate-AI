"""Offline, rule-based versions of the agents.

Used when no LLM key is set (or a live call fails) for any customer other than
the recorded demo. They are deliberately conservative: anything not stated in
the brief, spec or sample is emitted as an assumption or unknown, never a fact.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

from ..integrations.parsers import parse_openapi, parse_sample
from ..schemas.models import (
    ArchComponent, ArchFlow, Architecture, FieldMapping, PipelineState, Provenance,
    Question, Requirement, Risk, SecurityBoundary, System, Task, TestCase,
)

# ---------------------------------------------------------------- systems

_KINDS = r"(?:platform|system|service|app|application|crm|erp|database|warehouse|wms|api|portal|store|shop|ledger|backend|tool)"
_SYSTEM_RE = re.compile(
    rf"\b(?:our|the|their|an?|its)\s+((?:[a-z][a-z-]*\s){{0,2}}?{_KINDS})\b", re.I
)
_VENDORS = [
    "Shopify", "SAP", "Salesforce", "Stripe", "NetSuite", "HubSpot", "Zendesk", "Snowflake",
    "Workday", "ServiceNow", "Magento", "BigCommerce", "Oracle", "Dynamics", "Marketo", "Twilio",
    "Jira", "Slack", "QuickBooks", "Xero", "ShipStation", "Epic", "Cerner",
]
_DROP = {"internal", "existing", "legacy", "new", "current", "own", "main", "central", "in-house", "whole"}
_GENERIC = {"system", "platform", "service", "app", "application", "api", "tool", "backend"}


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def detect_system_names(brief: str) -> list[str]:
    found: list[tuple[int, str]] = []
    for m in _SYSTEM_RE.finditer(brief):
        words = [w for w in m.group(1).split() if w.lower() not in _DROP]
        if len(words) < 2 and words and words[0].lower() in _GENERIC:
            continue  # "the system" alone names nothing
        if words:
            found.append((m.start(), " ".join(w.capitalize() if w.islower() else w for w in words)))
    for v in _VENDORS:
        for m in re.finditer(rf"\b{re.escape(v)}\b", brief):
            found.append((m.start(), v))
    names: list[str] = []
    for _, n in sorted(found):
        if not any(n.lower() == x.lower() or n.lower() in x.lower().split() for x in names):
            names.append(n)
    return names[:6]


def _overlap(a: str, b: str) -> int:
    ta = {w for w in re.findall(r"[a-z]+", a.lower()) if w not in _GENERIC}
    tb = {w for w in re.findall(r"[a-z]+", b.lower()) if w not in _GENERIC}
    return len(ta & tb)


def build_systems(state: PipelineState) -> list[System]:
    """Systems named in the brief. Only one backed by a spec is confirmed."""
    spec = parse_openapi(state.openapi)
    names = detect_system_names(state.brief) or ["Source System", "Target System"]
    if len(names) == 1:
        names.append("Target System")
    spec_owner = None
    if spec["title"]:
        scored = sorted(names, key=lambda n: -_overlap(n, spec["title"]))
        spec_owner = scored[0] if _overlap(scored[0], spec["title"]) else names[0]
    elif state.openapi:
        spec_owner = names[0]
    out = []
    for i, n in enumerate(names):
        role = "source" if i == 0 else "target" if i == 1 else "participant"
        if n == spec_owner:
            out.append(System(id=slug(n), name=n, role=role, confirmed=True,
                              provenance=Provenance.fact, source=f"openapi:{spec['title'] or 'spec'}"))
        else:
            out.append(System(id=slug(n), name=n, role=role, confirmed=False, provenance=Provenance.unknown))
    return out


# ---------------------------------------------------------------- requirements

_NEED = re.compile(r"\b(need|needs|must|should|want|wants|require|requires|has to|have to|expect|goal)\b", re.I)
_NFR = [
    ("Throughput", re.compile(r"\b(spike|spikes|peak|burst|volume|per (second|minute|hour|day)|thousands?|millions?)\b", re.I)),
    ("Latency", re.compile(r"\b(real[- ]time|within \d+|latency|immediately|instant)\b", re.I)),
    ("Security", re.compile(r"\b(secure|security|pii|gdpr|hipaa|encrypt\w*|sensitive|compliance|sox|pci)\b", re.I)),
    ("Availability", re.compile(r"\b(24/7|all day|always available|uptime|availability|around the clock)\b", re.I)),
    ("Auditability", re.compile(r"\b(audit\w*|traceab\w*|log every)\b", re.I)),
    ("Delivery mode", re.compile(r"\b(every (few )?(minutes?|hours?|day|night)|nightly|batch|both directions|bidirectional|events?|stream\w*|webhooks?|poll\w*)\b", re.I)),
    ("Resilience", re.compile(r"\b(retr(y|ies)|dead[- ]letter|failover|is down)\b", re.I)),
]
_NUMBER = re.compile(r"\d")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n{2,}", text.replace("\n", " ")) if s.strip()]


def _clean(clause: str) -> str:
    clause = re.sub(r"^(we|i|they|our team)\s+(need|needs|must|should|want|wants|require|requires|have to|has to|expect)\s+(to\s+)?", "", clause.strip(), flags=re.I)
    clause = clause.strip(" .,;")
    return clause[:1].upper() + clause[1:]


def extract_requirements(state: PipelineState, systems: list[System]) -> list[Requirement]:
    reqs: list[Requirement] = []

    def add(text: str, kind: str, prov: Provenance, source: str | None):
        if len(text) > 6 and not any(r.text.lower() == text.lower() for r in reqs):
            reqs.append(Requirement(id=f"R{len(reqs) + 1}", text=text, kind=kind, provenance=prov, source=source))

    for s in _sentences(state.brief):
        main, *purposes = re.split(r"\bso that\b|\bso\b|\bin order to\b", s, flags=re.I)
        # "Changes must appear within 5 minutes" is a quality constraint, not a feature.
        if _NEED.search(s) and not any(rx.search(main) for _, rx in _NFR):
            add(_clean(main), "functional", Provenance.fact, "brief")
            for p in purposes:
                for part in re.split(r"\band\b(?=\s+(?:the\s+)?[a-z]+\s+(?:see|get|receive|are|is|can))", p, flags=re.I):
                    add(_clean(part), "functional", Provenance.fact, "brief")
        for label, rx in _NFR:
            if rx.search(s):
                # A stated number makes it a fact; a vague mention is an assumption about the need.
                stated = label in ("Security", "Auditability", "Delivery mode", "Resilience")
                prov = Provenance.fact if _NUMBER.search(s) or stated else Provenance.assumption
                add(f"{label}: {_clean(s)}", "non-functional", prov, "brief")
    for sysm in systems:
        if not sysm.confirmed:
            add(f"{sysm.name} API contract", "functional", Provenance.unknown, None)
    return reqs


# ---------------------------------------------------------------- ambiguity detection

_PATTERNS = {
    "throughput": re.compile(r"\d[\d,.]*\s*k?\s*(?:\w+\s){0,2}(?:per|/|an?|each|every)\s*(?:second|sec|minute|min|hour|day)", re.I),
    "sla": re.compile(r"\b(sla|within \d+|\d+\s*(ms|milliseconds|seconds|minutes|hours)|latency)\b", re.I),
    "data-ownership": re.compile(r"\b(source of truth|owns|owner|master data|system of record)\b", re.I),
    "failure": re.compile(r"\b(retr(y|ies)|fail\w*|outage|downtime|error\w*|dead[- ]letter|rollback)\b", re.I),
    "mode": re.compile(r"\b(real[- ]time|batch|nightly|hourly|daily|scheduled?|webhooks?|events?|stream\w*)\b", re.I),
    "pii": re.compile(r"\b(pii|gdpr|hipaa|personal data|privacy|ccpa)\b", re.I),
}
_PII_FIELDS = re.compile(r"(email|phone|address|ship_to|ssn|dob|birth|name)", re.I)


def detect_questions(state: PipelineState, systems: list[System]) -> list[Question]:
    text = state.brief
    spec = parse_openapi(state.openapi)
    fields = spec["fields"] or parse_sample(state.sample)
    qs: list[Question] = []

    def ask(text_: str, cat: str, prio: str):
        qs.append(Question(id=f"Q{len(qs) + 1}", text=text_, category=cat, priority=prio))

    for s in systems:
        if not s.confirmed:
            ask(f"How does the {s.name} authenticate API clients, and can we get its API documentation?", "auth", "high")
        elif not spec["auth"]:
            ask(f"The {s.name} spec declares no security scheme. What credentials will the integration use?", "auth", "high")
    if not _PATTERNS["throughput"].search(text):
        ask("What peak volume (records per minute) must the integration handle?", "throughput", "high")
    if not _PATTERNS["sla"].search(text):
        ask("What is the maximum acceptable delay from a change in the source to it appearing in the target?", "sla", "medium")
    if not _PATTERNS["data-ownership"].search(text):
        shared = ", ".join(f for f in fields if _PII_FIELDS.search(f))[:80] or "the shared records"
        ask(f"Which system is the source of truth for {shared} once data is synced?", "data-ownership", "medium")
    if not _PATTERNS["failure"].search(text):
        ask("What should happen when the target system is down or rejects a record?", "failure", "high")
    if not _PATTERNS["mode"].search(text):
        ask("Should data flow in real time (events) or in scheduled batches?", "other", "medium")
    if any(_PII_FIELDS.search(f) for f in fields) and not _PATTERNS["pii"].search(text):
        ask("The data includes personal fields. Which privacy rules (for example GDPR) apply?", "other", "medium")
    return qs


# ---------------------------------------------------------------- field mapping

_SYN = {
    "email": {"mail", "e_mail", "email_address", "emailaddress"},
    "customer": {"recipient", "client", "buyer", "user", "contact", "consignee", "patient", "member"},
    "address": {"ship_to", "shipping_address", "addr", "destination", "delivery_address"},
    "location": {"warehouse", "site", "depot"},
    "pay": {"salary", "gross_pay", "wage", "wages", "compensation"},
    "updated": {"updated_at", "last_updated", "modified", "modified_at", "updatedat"},
    "quantity": {"qty", "count", "units", "amount_units"},
    "items": {"line_items", "lines", "products", "order_lines", "lineitems"},
    "id": {"ref", "reference", "key", "number", "no", "identifier", "code"},
    "status": {"state", "stage", "phase"},
    "amount": {"total", "price", "cost", "value", "sum", "total_amount", "grand_total"},
    "sku": {"product_id", "product_code", "item_code", "part_number", "item_id"},
    "phone": {"tel", "telephone", "mobile", "phone_number"},
    "name": {"full_name", "display_name", "fullname"},
    "created": {"date", "timestamp", "created_at", "createdat", "time", "datetime"},
    "currency": {"ccy", "currency_code"},
    "tracking": {"tracking_no", "tracking_number", "awb", "trackingnumber"},
}
_CANON = {alias: canon for canon, aliases in _SYN.items() for alias in aliases | {canon}}


def _norm(field: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", field).lower().replace("-", "_")


def _tokens(field: str) -> set[str]:
    snake = _norm(field)
    if snake in _CANON:
        return {_CANON[snake]}
    return {_CANON.get(t, t) for t in snake.split("_") if t}


def field_score(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    jac = len(ta & tb) / len(ta | tb) if ta | tb else 0.0
    ratio = SequenceMatcher(None, a.lower(), b.lower()).ratio() * 0.8
    score = max(jac, ratio)
    if "id" in ta and "id" in tb:
        score = max(score, 0.55)  # both are identifiers; plausible but unconfirmed
    return round(min(score, 1.0), 2)


def _transform(a: str, b: str) -> str:
    t = _tokens(a) | _tokens(b)
    if "address" in t:
        return "restructure address"
    if "items" in t:
        return "map nested items"
    if "status" in t:
        return "enum mapping needed"
    if "id" in t:
        return "check id format"
    if "amount" in t:
        return "check currency and decimals"
    return "copy"


def map_fields(state: PipelineState) -> list[FieldMapping]:
    src = parse_openapi(state.openapi)["fields"]
    dst = parse_sample(state.sample)
    if not src or not dst:
        return []
    pairs = sorted(((field_score(a, b), a, b) for a in src for b in dst), reverse=True)
    used_a: set[str] = set()
    used_b: set[str] = set()
    out: dict[str, FieldMapping] = {}
    for score, a, b in pairs:
        if score < 0.35 or a in used_a or b in used_b:
            continue
        used_a.add(a)
        used_b.add(b)
        # Only an identical field name is a fact; synonym matches are inferences to confirm.
        exact = _norm(a) == _norm(b)
        out[a] = FieldMapping(
            source_field=a, target_field=b, confidence=1.0 if exact else min(score, 0.9),
            provenance=Provenance.fact if exact else Provenance.assumption,
            source="spec+sample" if exact else None, transform=_transform(a, b),
        )
    for a in src:
        if a not in out:
            out[a] = FieldMapping(source_field=a, target_field="?", confidence=0.0, provenance=Provenance.unknown)
    return [out[a] for a in src]


# ---------------------------------------------------------------- architecture and plan

def build_architecture(state: PipelineState, shape: str) -> Architecture:
    spec = parse_openapi(state.openapi)
    systems = state.systems
    src = next((s for s in systems if s.role == "source"), systems[0])
    targets = [s for s in systems if s is not src] or [src]
    paths = " ".join(p for _, p in spec["endpoints"]).lower()
    comps = [ArchComponent(id=f"c-{s.id}", name=s.name, layer="client",
                           description=("API documented" if s.confirmed else "API contract unknown")) for s in systems]
    if shape == "batch":
        ingress = ArchComponent(id="ingress", name="Batch Scheduler", layer="api", description=f"Pulls changes from {src.name} on a schedule")
        comps.append(ArchComponent(id="staging", name="Staging Store", layer="data", description="Holds each batch for replay"))
    elif shape == "file":
        ingress = ArchComponent(id="ingress", name="File Drop Watcher", layer="api", description="Picks up exported files over SFTP")
    elif shape == "poll" or ("webhook" not in paths and "event" not in paths and spec["endpoints"]):
        ingress = ArchComponent(id="ingress", name="Change Poller", layer="api", description=f"Polls {src.name} for new or changed records")
    else:
        ingress = ArchComponent(id="ingress", name="Webhook Receiver", layer="api", description="Verifies and accepts events")
    comps += [
        ingress,
        ArchComponent(id="queue", name="Queue", layer="integration", description="Buffers spikes and decouples systems"),
        ArchComponent(id="mapper", name="Mapper", layer="integration", description="Transforms records between schemas"),
        ArchComponent(id="ledger", name="Sync Ledger", layer="data", description="Idempotency keys and delivery status"),
    ]
    flows = [ArchFlow(source=f"c-{src.id}", target="ingress", label="changes"),
             ArchFlow(source="ingress", target="queue", label="enqueue"),
             ArchFlow(source="queue", target="mapper", label="records")]
    if shape == "batch":
        flows.append(ArchFlow(source="ingress", target="staging", label="store batch"))
    for t in targets:
        aid = f"adapter-{t.id}"
        comps.append(ArchComponent(id=aid, name=f"{t.name} Adapter", layer="integration",
                                   description="Calls the target with retries and a dead-letter queue"))
        flows += [ArchFlow(source="mapper", target=aid, label="mapped payload"),
                  ArchFlow(source=aid, target=f"c-{t.id}", label="write"),
                  ArchFlow(source=aid, target="ledger", label="record result")]
    if re.search(r"\b(status|tracking|update|sync back|write back|confirm)\w*", state.brief, re.I) or re.search(r"\b(PATCH|PUT)\b", " ".join(m for m, _ in spec["endpoints"])):
        flows.append(ArchFlow(source=f"adapter-{targets[0].id}", target=f"c-{src.id}", label="status write-back"))
    internal = [c.id for c in comps if c.layer in ("integration", "data")] + [f"c-{t.id}" for t in targets if not t.confirmed]
    return Architecture(
        components=comps, flows=flows,
        security_boundaries=[SecurityBoundary(name="Public edge", components=["ingress"]),
                             SecurityBoundary(name="Internal network", components=internal)],
    )


def build_plan(state: PipelineState) -> list[Task]:
    tasks: list[Task] = []

    def add(title: str, deps: list[str], days: float) -> str:
        tid = f"T{len(tasks) + 1}"
        tasks.append(Task(id=tid, title=title, depends_on=deps, estimate_days=days))
        return tid

    confirms = [add(f"Confirm {s.name} API contract and auth", [], 2) for s in state.systems if not s.confirmed]
    ingress = next((c.name for c in state.architecture.components if c.id == "ingress"), "Ingress")
    t_in = add(f"Build {ingress.lower()} with authentication", [], 2)
    t_q = add("Queue and idempotent sync ledger", [t_in], 3)
    t_map = add("Field mapper with validation", confirms, 3)
    adapters = [add(c.name + " with retry and dead-letter", confirms + [t_q, t_map], 4)
                for c in state.architecture.components if c.id.startswith("adapter-")]
    if any(f.label == "status write-back" for f in state.architecture.flows):
        adapters.append(add("Status write-back to source", adapters[:1], 2))
    t_obs = add("Monitoring, alerting and runbook", adapters, 2)
    add("End-to-end test and customer UAT", adapters + [t_obs], 3)
    return tasks


def build_tests(state: PipelineState) -> list[TestCase]:
    tests: list[TestCase] = []

    def add(title: str, covers: list[str], expected: str):
        tests.append(TestCase(id=f"TC{len(tests) + 1}", title=title, covers=covers, expected=expected))

    functional = [r for r in state.requirements if r.kind == "functional" and r.provenance != Provenance.unknown]
    for r in functional:
        add(f"Happy path: {r.text}", [r.id], "Record arrives in the target with mapped fields")
    if functional:
        add("Duplicate event is processed once", [functional[0].id], "Ledger blocks the second delivery")
        add("Target outage triggers retry then dead-letter", [functional[0].id], "No data loss; alert raised")
    for r in state.requirements:
        if r.kind == "non-functional" and r.provenance != Provenance.unknown:
            label = r.text.split(":")[0]
            expected = {"Throughput": "Peak load is queued and drained without loss",
                        "Latency": "End-to-end delay within the agreed limit",
                        "Security": "Data encrypted in transit; secrets not logged",
                        "Availability": "Integration recovers automatically after restarts",
                        "Auditability": "Every delivery traceable in the ledger"}.get(label, "Requirement verified")
            add(f"{label} check", [r.id], expected)
    for m in state.mappings:
        if m.provenance == Provenance.assumption:
            add(f"Mapping {m.source_field} -> {m.target_field} confirmed with sample data", [], "Customer signs off the mapping")
    return tests


def build_risks(state: PipelineState) -> list[Risk]:
    risks: list[Risk] = []

    def add(title: str, sev: str, mitigation: str):
        risks.append(Risk(id=f"K{len(risks) + 1}", title=title, severity=sev, mitigation=mitigation))

    for s in state.systems:
        if not s.confirmed:
            add(f"{s.name} API contract unknown", "high", "Obtain API docs and credentials before build starts")
    for q in state.questions:
        if q.priority == "high" and q.category != "auth":
            add(f"Unanswered: {q.text}", "medium", "Resolve with the customer in the next discovery call")
    for m in state.mappings:
        if m.provenance != Provenance.fact and m.target_field != "?" and m.confidence < 0.6:
            add(f"Low-confidence mapping {m.source_field} -> {m.target_field}", "medium", "Validate with sample records")
    unmapped = [m.source_field for m in state.mappings if m.target_field == "?"]
    if unmapped:
        add(f"No target field for {', '.join(unmapped[:4])}", "low", "Confirm whether these fields are needed downstream")
    fields = parse_openapi(state.openapi)["fields"] + parse_sample(state.sample)
    if any(_PII_FIELDS.search(f) for f in fields):
        add("Personal data moves between systems", "medium", "Encrypt in transit, mask in logs, agree retention")
    return risks
