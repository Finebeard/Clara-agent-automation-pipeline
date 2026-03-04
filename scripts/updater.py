from typing import Any, Dict, List, Tuple


def merge_memo_with_updates(
    base_memo: Dict[str, Any],
    onboarding_extracted: Dict[str, Any],
    new_questions: List[str],
) -> Dict[str, Any]:
    """
    Merge onboarding extraction into an existing account memo.

    Fields in `onboarding_extracted` take precedence over `base_memo` when present
    and non-empty. `questions_or_unknowns` from the base memo are preserved and
    extended with new questions.
    """
    merged = dict(base_memo)  # shallow copy is fine for our simple structure

    # Keys that we allow onboarding to update directly if present.
    updatable_keys = [
        "company_name",
        "business_hours",
        "office_address",
        "services_supported",
        "emergency_definition",
        "emergency_routing_rules",
        "non_emergency_routing_rules",
        "call_transfer_rules",
        "integration_constraints",
        "after_hours_flow_summary",
        "office_hours_flow_summary",
        "notes",
    ]

    for key in updatable_keys:
        if key in onboarding_extracted and onboarding_extracted[key]:
            merged[key] = onboarding_extracted[key]

    # Merge questions/unknowns
    merged_questions = list(base_memo.get("questions_or_unknowns", []))
    for q in new_questions:
        q_clean = q.strip()
        if q_clean and q_clean not in merged_questions:
            merged_questions.append(q_clean)
    merged["questions_or_unknowns"] = merged_questions

    return merged

