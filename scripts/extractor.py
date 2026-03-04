import logging
import re
from typing import Any, Dict, List, Tuple


def _extract_company_name(text: str) -> str:
    patterns = [
        r"\bcompany name is ([^\n\.]+)",
        r"\bthis is ([^\n\.]+) (heating|cooling|services|service|hvac)",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return ""


def _extract_office_address(text: str) -> str:
    patterns = [
        r"\boffice address is ([^\n]+)",
        r"\baddress is ([^\n]+)",
    ]
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            return m.group(1).strip().rstrip(".")
    return ""


def _extract_services(text: str) -> List[str]:
    services: List[str] = []
    bullet_block = re.search(
        r"we support.*?(including:|include:)(?P<body>[\s\S]+?)(\n\n|\Z)",
        text,
        flags=re.IGNORECASE,
    )
    if bullet_block:
        body = bullet_block.group("body")
        for line in body.splitlines():
            line = line.strip(" -\t")
            if not line:
                continue
            services.append(line.rstrip("."))
    # Fallback single-sentence pattern
    if not services:
        m = re.search(r"we (handle|do|offer) ([^\n\.]+)", text, flags=re.IGNORECASE)
        if m:
            parts = re.split(r",| and ", m.group(2))
            services = [p.strip() for p in parts if p.strip()]
    return services


def _extract_business_hours(text: str) -> List[Dict[str, Any]]:
    """
    Extract simple business hours rules.

    Returns a list of dicts with keys: day, start, end, timezone.
    """
    hours: List[Dict[str, Any]] = []

    # Pattern like "Monday through Friday, 8 AM to 5 PM Eastern Time"
    m = re.search(
        r"(monday through friday|monday to friday|mon\-fri)[, ]+([\d: ]+(am|pm)) to ([\d: ]+(am|pm)) ([a-z ]+time)",
        text,
        flags=re.IGNORECASE,
    )
    if m:
        start = m.group(2).strip()
        end = m.group(4).strip()
        tz = m.group(5).strip()
        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
            hours.append(
                {"day": day, "start": start, "end": end, "timezone": tz}
            )

    # Pattern like "Saturday ... 9 AM to 1 PM Eastern"
    m2 = re.search(
        r"(saturday)[^\.]*?(\d+ ?(?:am|pm)) to (\d+ ?(?:am|pm)) ([a-z ]+)",
        text,
        flags=re.IGNORECASE,
    )
    if m2:
        day = "Saturday"
        start = m2.group(2).strip()
        end = m2.group(3).strip()
        tz = m2.group(4).strip()
        hours.append({"day": day, "start": start, "end": end, "timezone": tz})

    return hours


def _extract_emergency_definition(text: str) -> str:
    block = re.search(
        r'("emergency" means[: ]|emergency definition[: ])(?P<body>[\s\S]+?)(\n\n|\Z)',
        text,
        flags=re.IGNORECASE,
    )
    if block:
        body = block.group("body").strip()
        return re.sub(r"\s+", " ", body)
    return ""


def _extract_emergency_routing(text: str) -> str:
    block = re.search(
        r"Emergency routing works like this:(?P<body>[\s\S]+?)(\n\n|\Z)",
        text,
        flags=re.IGNORECASE,
    )
    if block:
        body = block.group("body").strip()
        return re.sub(r"\s+", " ", body)
    return ""


def _extract_non_emergency_routing(text: str) -> str:
    block = re.search(
        r"Non-emergency routing:(?P<body>[\s\S]+?)(\n\n|\Z)",
        text,
        flags=re.IGNORECASE,
    )
    if block:
        body = block.group("body").strip()
        return re.sub(r"\s+", " ", body)
    return ""


def _extract_call_transfer_rules(text: str) -> str:
    block = re.search(
        r"Call transfer rules:(?P<body>[\s\S]+?)(\n\n|\Z)",
        text,
        flags=re.IGNORECASE,
    )
    if block:
        body = block.group("body").strip()
        return re.sub(r"\s+", " ", body)
    return ""


def _extract_integration_constraints(text: str) -> str:
    block = re.search(
        r"Integration constraints:(?P<body>[\s\S]+?)(\n\n|\Z)",
        text,
        flags=re.IGNORECASE,
    )
    if block:
        body = block.group("body").strip()
        return re.sub(r"\s+", " ", body)
    return ""


def _extract_flow_summary(label: str, text: str) -> str:
    pattern = rf"{label} flow summary:(?P<body>[\s\S]+?)(\n\n|\Z)"
    block = re.search(pattern, text, flags=re.IGNORECASE)
    if block:
        body = block.group("body").strip()
        return re.sub(r"\s+", " ", body)
    return ""


def extract_account_info(transcript_text: str) -> Tuple[Dict[str, Any], List[str]]:
    """
    Extract structured account information and questions/unknowns from a transcript.

    Returns:
        (data, questions)
        - data: partial account data (keys may be missing if not found).
        - questions: list of human-readable notes for missing or ambiguous info.
    """
    text = transcript_text
    data: Dict[str, Any] = {}
    questions: List[str] = []

    company_name = _extract_company_name(text)
    if company_name:
        data["company_name"] = company_name
    else:
        questions.append("Company name was not clearly identified in the transcript.")

    address = _extract_office_address(text)
    if address:
        data["office_address"] = address
    else:
        questions.append(
            "Office address was not clearly provided or recognized in the transcript."
        )

    services = _extract_services(text)
    if services:
        data["services_supported"] = services
    else:
        questions.append(
            "Services supported (e.g. HVAC, electrical, fire protection) were not clearly listed."
        )

    hours = _extract_business_hours(text)
    if hours:
        data["business_hours"] = hours
    else:
        questions.append(
            "Business hours (days, times, timezone) could not be confidently extracted."
        )

    emergency_def = _extract_emergency_definition(text)
    if emergency_def:
        data["emergency_definition"] = emergency_def
    else:
        questions.append("Emergency definition was not clearly described.")

    emergency_routing = _extract_emergency_routing(text)
    if emergency_routing:
        data["emergency_routing_rules"] = emergency_routing
    else:
        questions.append("Emergency routing rules were not clearly described.")

    non_emergency_routing = _extract_non_emergency_routing(text)
    if non_emergency_routing:
        data["non_emergency_routing_rules"] = non_emergency_routing
    else:
        questions.append("Non-emergency routing rules were not clearly described.")

    call_transfer = _extract_call_transfer_rules(text)
    if call_transfer:
        data["call_transfer_rules"] = call_transfer
    else:
        questions.append("Call transfer rules were not clearly described.")

    integration = _extract_integration_constraints(text)
    if integration:
        data["integration_constraints"] = integration
    else:
        questions.append("Integration constraints were not clearly described.")

    office_flow = _extract_flow_summary("Office-hours", text)
    if office_flow:
        data["office_hours_flow_summary"] = office_flow
    else:
        questions.append("Office-hours call flow summary was not clearly described.")

    after_hours_flow = _extract_flow_summary("After-hours", text)
    if after_hours_flow:
        data["after_hours_flow_summary"] = after_hours_flow
    else:
        questions.append("After-hours call flow summary was not clearly described.")

    return data, questions

