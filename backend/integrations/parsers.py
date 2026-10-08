"""Deterministic parsing of customer-supplied artifacts.

Accepts OpenAPI documents as dicts or JSON/YAML text, and sample records as
JSON (object or list) or CSV text. Nothing here guesses: a field or endpoint is
only reported if it appears in the input.
"""
from __future__ import annotations

import csv
import io
import json
import re

import yaml

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def load_openapi(raw: dict | str | None) -> dict | None:
    """Normalise an OpenAPI document given as a dict or JSON/YAML text."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, dict):
        return raw
    doc = yaml.safe_load(raw)  # YAML is a superset of JSON
    if not isinstance(doc, dict) or "paths" not in doc:
        raise ValueError("not an OpenAPI document (no 'paths')")
    return doc


def load_sample(raw: dict | list | str | None) -> dict | list | None:
    """Normalise a sample given as JSON data, JSON text or CSV text."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, (dict, list)):
        return raw
    text = raw.strip()
    if text[:1] in "{[":
        return json.loads(text)
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise ValueError("CSV sample has a header but no rows")
    return rows


def _schema_props(schema: dict, schemas: dict, seen: set[str]) -> list[str]:
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        if name in seen:
            return []
        seen.add(name)
        return _schema_props(schemas.get(name, {}), schemas, seen)
    props = list(schema.get("properties", {}))
    for part in schema.get("allOf", []):
        props += _schema_props(part, schemas, seen)
    return props


def parse_openapi(spec: dict | None) -> dict:
    """Return title, endpoints, auth schemes and declared field names."""
    if not spec:
        return {"title": None, "endpoints": [], "auth": [], "fields": []}
    endpoints = [
        (method.upper(), path)
        for path, ops in spec.get("paths", {}).items()
        for method in ops
        if method.lower() in HTTP_METHODS
    ]
    components = spec.get("components", {})
    schemas = components.get("schemas", {})
    fields: list[str] = list(spec.get("x-order-fields", []))
    # Root schemas are the business entities; schemas referenced by others are nested parts.
    referenced = {ref.rsplit("/", 1)[-1] for ref in re.findall(r"#/components/schemas/[\w.-]+", json.dumps(schemas))}
    roots = [n for n in schemas if n not in referenced] or list(schemas)
    for name in roots:
        fields += _schema_props({"$ref": f"#/components/schemas/{name}"}, schemas, set())
    return {
        "title": spec.get("info", {}).get("title"),
        "endpoints": endpoints,
        "auth": list(components.get("securitySchemes", {})),
        "fields": list(dict.fromkeys(fields)),  # dedupe, keep order
    }


def parse_sample(sample: dict | list | None) -> list[str]:
    """Top-level field names of a sample record."""
    if isinstance(sample, list):
        sample = sample[0] if sample else {}
    return list(sample.keys()) if isinstance(sample, dict) else []
