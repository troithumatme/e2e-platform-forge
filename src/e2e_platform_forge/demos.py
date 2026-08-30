"""Tiny synthetic capabilities for the four framework domains."""

from __future__ import annotations

import math
from copy import deepcopy

from .models import Target
from .registry import Capability, CapabilityRegistry
from .validation import Finding


_SAMPLES: dict[str, dict[str, object]] = {
    "automation": {
        "steps": ["EXAMPLE_PREPARE", "EXAMPLE_COMPLETE"],
    },
    "delivery": {
        "items": [
            {"id": "EXAMPLE_ITEM_A", "ready": True},
            {"id": "EXAMPLE_ITEM_B", "ready": True},
        ],
    },
    "governance": {
        "checks": [
            {"name": "EXAMPLE_CHECK_A", "passed": True},
            {"name": "EXAMPLE_CHECK_B", "passed": True},
        ],
    },
    "intelligence": {
        "observations": [
            {"label": "EXAMPLE_SIGNAL_A", "value": 2.0},
            {"label": "EXAMPLE_SIGNAL_B", "value": 4.0},
        ],
    },
}


def demo_domains() -> tuple[str, ...]:
    return tuple(sorted(_SAMPLES))


def demo_input(domain: str) -> dict[str, object]:
    try:
        return deepcopy(_SAMPLES[domain])
    except KeyError as error:
        raise LookupError(f"unknown demo domain: {domain}") from error


def _exact_root_field(subject: object, field: str) -> tuple[Finding, ...]:
    if not isinstance(subject, dict):
        return ()
    if set(subject) != {field}:
        return (
            Finding(
                "$",
                "unexpected_fields",
                f"input must contain exactly the '{field}' field",
            ),
        )
    return ()


def _automation_integrity(subject: object) -> tuple[Finding, ...]:
    findings = list(_exact_root_field(subject, "steps"))
    if findings or not isinstance(subject, dict):
        return tuple(findings)
    steps = subject["steps"]
    if not isinstance(steps, list) or any(not isinstance(step, str) for step in steps):
        findings.append(Finding("$.steps", "string_list_required", "steps must be a string list"))
    return tuple(findings)


def _automation_rules(subject: object) -> tuple[Finding, ...]:
    if not isinstance(subject, dict) or not isinstance(subject.get("steps"), list):
        return ()
    steps = subject["steps"]
    if not steps:
        return (Finding("$.steps", "steps_required", "at least one step is required"),)
    if len(set(steps)) != len(steps):
        return (Finding("$.steps", "unique_steps_required", "step names must be unique"),)
    if any(not step.strip() for step in steps):
        return (Finding("$.steps", "named_steps_required", "step names must not be blank"),)
    return ()


def _automation_handler(payload: dict[str, object]) -> dict[str, object]:
    steps = list(payload["steps"])
    return {
        "domain": "automation",
        "example": "DEMO",
        "status": "DEMO_READY",
        "step_count": len(steps),
        "steps": steps,
    }


def _automation_publication(subject: object) -> tuple[Finding, ...]:
    if not isinstance(subject, dict):
        return ()
    steps = subject.get("steps")
    if (
        not isinstance(steps, list)
        or subject.get("status") != "DEMO_READY"
        or subject.get("step_count") != len(steps)
    ):
        return (
            Finding(
                "$",
                "automation_result_incomplete",
                "automation demo result is incomplete",
            ),
        )
    return ()


def _records_integrity(
    subject: object,
    root_field: str,
    name_field: str,
    value_field: str,
    value_type: type,
) -> tuple[Finding, ...]:
    findings = list(_exact_root_field(subject, root_field))
    if findings or not isinstance(subject, dict):
        return tuple(findings)
    records = subject[root_field]
    if not isinstance(records, list):
        return (
            Finding(
                f"$.{root_field}",
                "record_list_required",
                "value must be a record list",
            ),
        )
    for index, record in enumerate(records):
        path = f"$.{root_field}[{index}]"
        if not isinstance(record, dict) or set(record) != {name_field, value_field}:
            findings.append(
                Finding(
                    path,
                    "record_shape_required",
                    "record fields do not match the demo schema",
                )
            )
            continue
        if not isinstance(record[name_field], str):
            findings.append(
                Finding(
                    f"{path}.{name_field}",
                    "string_required",
                    "value must be a string",
                )
            )
        value = record[value_field]
        if value_type is bool:
            valid_value = isinstance(value, bool)
        else:
            valid_value = isinstance(value, int | float) and not isinstance(value, bool)
        if not valid_value:
            findings.append(
                Finding(
                    f"{path}.{value_field}",
                    "value_type_required",
                    "value has the wrong type",
                )
            )
    return tuple(findings)


def _nonempty_unique_records(
    subject: object,
    root_field: str,
    name_field: str,
) -> tuple[Finding, ...]:
    if not isinstance(subject, dict) or not isinstance(subject.get(root_field), list):
        return ()
    records = subject[root_field]
    if not records:
        return (
            Finding(
                f"$.{root_field}",
                "records_required",
                "at least one record is required",
            ),
        )
    names = [record[name_field] for record in records]
    if any(not name.strip() for name in names):
        return (
            Finding(
                f"$.{root_field}",
                "named_records_required",
                "record names must not be blank",
            ),
        )
    if len(set(names)) != len(names):
        return (
            Finding(
                f"$.{root_field}",
                "unique_records_required",
                "record names must be unique",
            ),
        )
    return ()


def _delivery_integrity(subject: object) -> tuple[Finding, ...]:
    return _records_integrity(subject, "items", "id", "ready", bool)


def _delivery_rules(subject: object) -> tuple[Finding, ...]:
    return _nonempty_unique_records(subject, "items", "id")


def _delivery_handler(payload: dict[str, object]) -> dict[str, object]:
    items = payload["items"]
    ready_ids = [item["id"] for item in items if item["ready"]]
    return {
        "domain": "delivery",
        "example": "DEMO",
        "item_count": len(items),
        "ready_ids": ready_ids,
        "status": "DEMO_READY" if len(ready_ids) == len(items) else "DEMO_PENDING",
    }


def _delivery_publication(subject: object) -> tuple[Finding, ...]:
    if isinstance(subject, dict) and subject.get("status") != "DEMO_READY":
        return (
            Finding(
                "$.status",
                "items_not_ready",
                "all demo items must be ready for publication",
            ),
        )
    return ()


def _governance_integrity(subject: object) -> tuple[Finding, ...]:
    return _records_integrity(subject, "checks", "name", "passed", bool)


def _governance_rules(subject: object) -> tuple[Finding, ...]:
    return _nonempty_unique_records(subject, "checks", "name")


def _governance_handler(payload: dict[str, object]) -> dict[str, object]:
    checks = payload["checks"]
    passed_names = [check["name"] for check in checks if check["passed"]]
    return {
        "check_count": len(checks),
        "decision": "DEMO_APPROVED" if len(passed_names) == len(checks) else "DEMO_REVIEW",
        "domain": "governance",
        "example": "DEMO",
        "passed_names": passed_names,
    }


def _governance_publication(subject: object) -> tuple[Finding, ...]:
    if isinstance(subject, dict) and subject.get("decision") != "DEMO_APPROVED":
        return (
            Finding(
                "$.decision",
                "checks_not_passed",
                "all demo checks must pass for publication",
            ),
        )
    return ()


def _intelligence_integrity(subject: object) -> tuple[Finding, ...]:
    return _records_integrity(subject, "observations", "label", "value", float)


def _intelligence_rules(subject: object) -> tuple[Finding, ...]:
    findings = list(_nonempty_unique_records(subject, "observations", "label"))
    if findings or not isinstance(subject, dict):
        return tuple(findings)
    observations = subject["observations"]
    values = [item["value"] for item in observations]
    if any(
        (isinstance(value, float) and not math.isfinite(value))
        or abs(value) > 1e300
        for value in values
    ):
        findings.append(
            Finding(
                "$.observations",
                "bounded_finite_values_required",
                "observation values must be finite and within the demo range",
            )
        )
    return tuple(findings)


def _intelligence_handler(payload: dict[str, object]) -> dict[str, object]:
    observations = payload["observations"]
    values = [float(item["value"]) for item in observations]
    return {
        "domain": "intelligence",
        "example": "DEMO",
        "mean": sum(values) / len(values),
        "observation_count": len(values),
        "status": "DEMO_READY",
    }


def _intelligence_publication(subject: object) -> tuple[Finding, ...]:
    if not isinstance(subject, dict):
        return ()
    mean = subject.get("mean")
    if (
        subject.get("status") != "DEMO_READY"
        or not isinstance(mean, int | float)
        or isinstance(mean, bool)
        or not math.isfinite(float(mean))
    ):
        return (Finding("$", "summary_not_ready", "intelligence demo summary is not publishable"),)
    return ()


def build_demo_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    registry.register(
        Capability(
            target=Target("automation", "example"),
            description="Run a synthetic ordered-step example.",
            handler=_automation_handler,
            input_integrity_validators=(_automation_integrity,),
            domain_rule_validators=(_automation_rules,),
            publication_readiness_validators=(_automation_publication,),
        )
    )
    registry.register(
        Capability(
            target=Target("delivery", "example"),
            description="Publish a synthetic ready-item example.",
            handler=_delivery_handler,
            input_integrity_validators=(_delivery_integrity,),
            domain_rule_validators=(_delivery_rules,),
            publication_readiness_validators=(_delivery_publication,),
        )
    )
    registry.register(
        Capability(
            target=Target("governance", "example"),
            description="Evaluate synthetic pass-or-review checks.",
            handler=_governance_handler,
            input_integrity_validators=(_governance_integrity,),
            domain_rule_validators=(_governance_rules,),
            publication_readiness_validators=(_governance_publication,),
        )
    )
    registry.register(
        Capability(
            target=Target("intelligence", "example"),
            description="Summarize synthetic numeric observations.",
            handler=_intelligence_handler,
            input_integrity_validators=(_intelligence_integrity,),
            domain_rule_validators=(_intelligence_rules,),
            publication_readiness_validators=(_intelligence_publication,),
        )
    )
    return registry
