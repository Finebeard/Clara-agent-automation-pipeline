from typing import Any, Dict


def _changed(old: Any, new: Any) -> bool:
    return old != new


def build_changelog(
    memo_v1: Dict[str, Any],
    memo_v2: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Produce a simple changelog dictionary describing differences between v1 and v2 memos.

    The changelog is intentionally high-level and human-readable.
    """
    changelog: Dict[str, Any] = {}

    if _changed(memo_v1.get("business_hours"), memo_v2.get("business_hours")):
        changelog["business_hours"] = "updated"

    if _changed(
        memo_v1.get("emergency_definition"), memo_v2.get("emergency_definition")
    ):
        changelog["emergency_definition"] = "updated"

    routing_changed = any(
        _changed(memo_v1.get(field), memo_v2.get(field))
        for field in ("emergency_routing_rules", "non_emergency_routing_rules")
    )
    if routing_changed:
        changelog["routing_rules"] = "modified"

    if _changed(
        memo_v1.get("integration_constraints"), memo_v2.get("integration_constraints")
    ):
        changelog["integration_constraints"] = "updated"

    if _changed(
        memo_v1.get("services_supported"), memo_v2.get("services_supported")
    ):
        changelog["services_supported"] = "updated"

    if _changed(memo_v1.get("office_address"), memo_v2.get("office_address")):
        changelog["office_address"] = "updated"

    if _changed(
        memo_v1.get("after_hours_flow_summary"),
        memo_v2.get("after_hours_flow_summary"),
    ):
        changelog["after_hours_flow_summary"] = "updated"

    if _changed(
        memo_v1.get("office_hours_flow_summary"),
        memo_v2.get("office_hours_flow_summary"),
    ):
        changelog["office_hours_flow_summary"] = "updated"

    if _changed(
        memo_v1.get("call_transfer_rules"), memo_v2.get("call_transfer_rules")
    ):
        changelog["call_transfer_rules"] = "updated"

    if _changed(
        memo_v1.get("questions_or_unknowns"), memo_v2.get("questions_or_unknowns")
    ):
        changelog["questions_or_unknowns"] = "updated (new questions added)"

    return changelog

