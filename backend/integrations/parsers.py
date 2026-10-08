"""Deterministic parsing of customer-supplied artifacts (OpenAPI spec, sample JSON)."""
from __future__ import annotations

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def parse_openapi(spec: dict | None) -> dict:
    """Return endpoints, auth schemes and declared fields from an OpenAPI document."""
    if not spec:
        return {"endpoints": [], "auth": [], "fields": []}
    endpoints = [
        (method.upper(), path)
        for path, ops in spec.get("paths", {}).items()
        for method in ops
        if method.lower() in HTTP_METHODS
    ]
    auth = list(spec.get("components", {}).get("securitySchemes", {}))
    return {"endpoints": endpoints, "auth": auth, "fields": list(spec.get("x-order-fields", []))}


def parse_sample(sample: dict | list | None) -> list[str]:
    """Top-level field names of a sample JSON record."""
    if isinstance(sample, list):
        sample = sample[0] if sample else {}
    return list(sample.keys()) if isinstance(sample, dict) else []
