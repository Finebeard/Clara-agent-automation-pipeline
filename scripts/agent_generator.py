import logging
from typing import Any, Dict, List


def _build_questions(questions_from_extractor: List[str]) -> List[str]:
    """Return a clean list of questions/unknowns."""
    return [q.strip() for q in questions_from_extractor if q.strip()]


def build_account_memo(
    account_id: str,
    extracted: Dict[str, Any],
    questions_from_extractor: List[str],
) -> Dict[str, Any]:
    """
    Normalize extracted data into the canonical account memo JSON structure.

    Missing or ambiguous fields are noted in `questions_or_unknowns`; the function
    does not invent values.
    """
    questions = _build_questions(questions_from_extractor)

    def ensure_or_question(key: str, label: str, default: Any) -> Any:
        if key in extracted and extracted[key]:
            return extracted[key]
        questions.append(f"{label} is missing or ambiguous in the available transcripts.")
        return default

    memo: Dict[str, Any] = {
        "account_id": account_id,
        "company_name": ensure_or_question("company_name", "Company name", ""),
        "business_hours": ensure_or_question("business_hours", "Business hours", []),
        "office_address": ensure_or_question("office_address", "Office address", ""),
        "services_supported": ensure_or_question(
            "services_supported", "Services supported", []
        ),
        "emergency_definition": ensure_or_question(
            "emergency_definition", "Emergency definition", ""
        ),
        "emergency_routing_rules": ensure_or_question(
            "emergency_routing_rules", "Emergency routing rules", ""
        ),
        "non_emergency_routing_rules": ensure_or_question(
            "non_emergency_routing_rules", "Non-emergency routing rules", ""
        ),
        "call_transfer_rules": ensure_or_question(
            "call_transfer_rules", "Call transfer rules", ""
        ),
        "integration_constraints": ensure_or_question(
            "integration_constraints", "Integration constraints", ""
        ),
        "after_hours_flow_summary": ensure_or_question(
            "after_hours_flow_summary", "After-hours flow summary", ""
        ),
        "office_hours_flow_summary": ensure_or_question(
            "office_hours_flow_summary", "Office-hours flow summary", ""
        ),
        "questions_or_unknowns": questions,
        "notes": extracted.get("notes", ""),
    }
    return memo


def _build_system_prompt(memo: Dict[str, Any]) -> str:
    """
    Build the system prompt string for the AI voice agent.

    The prompt includes both business-hours and after-hours flows and uses only
    natural language (no references to tools or internal implementation).
    """
    company = memo.get("company_name") or memo.get("account_id")
    emergency_def = memo.get("emergency_definition", "")
    emergency_routing = memo.get("emergency_routing_rules", "")
    non_emergency_routing = memo.get("non_emergency_routing_rules", "")
    transfer_rules = memo.get("call_transfer_rules", "")
    office_flow = memo.get("office_hours_flow_summary", "")
    after_hours_flow = memo.get("after_hours_flow_summary", "")

    lines: List[str] = []
    lines.append(
        f"You are a professional phone agent for {company}. "
        "You must be polite, concise, and follow the company's call-handling rules exactly."
    )
    if emergency_def:
        lines.append(f"An emergency is defined as: {emergency_def}")
    if emergency_routing:
        lines.append(f"For emergencies, follow this routing: {emergency_routing}")
    if non_emergency_routing:
        lines.append(
            f"For non-emergencies, follow this routing: {non_emergency_routing}"
        )
    if transfer_rules:
        lines.append(f"Call transfer rules: {transfer_rules}")

    if office_flow:
        lines.append(f"Additional office-hours guidance: {office_flow}")
    if after_hours_flow:
        lines.append(f"Additional after-hours guidance: {after_hours_flow}")

    lines.append("")
    lines.append("BUSINESS HOURS FLOW:")
    lines.append(
        "1) Greet the caller warmly using the company name and introduce yourself briefly."
    )
    lines.append("2) Ask for the purpose of the call in natural language.")
    lines.append(
        "3) Politely collect the caller's full name and best callback phone number."
    )
    lines.append(
        "4) Determine whether the call is an emergency or non-emergency, then route or transfer the call according to the business-hours routing rules."
    )
    lines.append(
        "5) If a transfer fails or no one answers within the allowed time, return to the caller, apologize, and follow the fallback protocol."
    )
    lines.append(
        "6) Clearly confirm the next steps, including who will follow up and approximately when."
    )
    lines.append("7) Ask if there is anything else you can help with.")
    lines.append("8) Close the call politely and thank the caller for contacting the company.")

    lines.append("")
    lines.append("AFTER HOURS FLOW:")
    lines.append(
        "1) Greet the caller, mention that they have reached the company's after-hours answering service, and introduce yourself briefly."
    )
    lines.append("2) Ask for the purpose of the call in natural language.")
    lines.append("3) Confirm whether the situation is an emergency based on the company's definition.")
    lines.append(
        "4) If it is an emergency, immediately collect the caller's full name, callback phone number, and service address."
    )
    lines.append(
        "5) Attempt to reach the designated emergency contact or on-call technician according to the emergency routing rules."
    )
    lines.append(
        "6) If the emergency transfer fails or no one answers, apologize to the caller, explain that someone will follow up as soon as possible, and clearly state the next step."
    )
    lines.append(
        "7) If the situation is not an emergency, collect detailed information about the issue and clearly state that someone from the company will follow up on the next business day."
    )
    lines.append("8) Ask if there is anything else the caller needs.")
    lines.append("9) Close the call politely and thank the caller for contacting the company.")

    return "\n".join(lines)


def build_agent_spec(memo: Dict[str, Any], version: str) -> Dict[str, Any]:
    """
    Build the agent specification JSON from an account memo.
    """
    company = memo.get("company_name") or memo.get("account_id")
    agent_name = f"{company} Voice Agent v{version[-1]}" if version else f"{company} Voice Agent"
    system_prompt = _build_system_prompt(memo)

    key_variables = {
        "account_id": memo.get("account_id"),
        "company_name": company,
        "has_emergency_routing": bool(memo.get("emergency_routing_rules")),
        "has_non_emergency_routing": bool(memo.get("non_emergency_routing_rules")),
        "supports_after_hours": bool(memo.get("after_hours_flow_summary")),
    }

    call_transfer_protocol = memo.get(
        "call_transfer_rules",
        "Announce the caller, attempt transfer, and return to the caller if no one answers.",
    )
    fallback_protocol = (
        "If a transfer fails or no one answers, apologize, explain that someone will follow up, "
        "and document the caller's name, phone number, and reason for calling."
    )

    spec: Dict[str, Any] = {
        "agent_name": agent_name,
        "voice_style": "friendly, concise, professional US English",
        "system_prompt": system_prompt,
        "key_variables": key_variables,
        "call_transfer_protocol": call_transfer_protocol,
        "fallback_protocol": fallback_protocol,
        "version": version,
    }
    return spec

