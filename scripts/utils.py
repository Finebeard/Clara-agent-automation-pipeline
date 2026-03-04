import json
import logging
import os
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple


LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"


def setup_logging() -> None:
    """Configure root logger for the pipeline."""
    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def ensure_dir(path: str) -> None:
    """Ensure that a directory exists."""
    os.makedirs(path, exist_ok=True)


def read_json(path: str) -> Dict[str, Any]:
    """Read a JSON file and return its contents as a dictionary."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, data: Dict[str, Any]) -> None:
    """Write a dictionary to a JSON file with pretty formatting."""
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def find_transcripts(folder: str) -> List[str]:
    """Return a list of absolute paths to .txt transcript files in the given folder."""
    if not os.path.isdir(folder):
        return []
    paths: List[str] = []
    for name in os.listdir(folder):
        if name.lower().endswith(".txt"):
            paths.append(os.path.join(folder, name))
    return sorted(paths)


def slugify_account_id(filename: str) -> str:
    """
    Derive a stable account_id from a transcript filename.

    Rules:
    - Strip directory and extension.
    - Remove known suffixes like '_demo' and '_onboarding'.
    - Lowercase and replace non-alphanumeric characters with underscores.
    """
    base = os.path.basename(filename)
    name, _ext = os.path.splitext(base)
    # Remove common suffixes
    name = re.sub(r"_(demo|onboarding)$", "", name, flags=re.IGNORECASE)
    # Normalize
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = name.strip("_")
    return name or "unknown_account"


@dataclass
class BatchSummary:
    """Simple batch processing summary."""

    demo_accounts_processed: int = 0
    onboarding_updates_applied: int = 0
    changelogs_written: int = 0
    errors: List[str] = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def log_batch_summary(summary: BatchSummary) -> None:
    """Log a concise batch processing summary."""
    logging.info("Batch processing summary:")
    logging.info("  Demo accounts processed: %d", summary.demo_accounts_processed)
    logging.info("  Onboarding updates applied: %d", summary.onboarding_updates_applied)
    logging.info("  Changelogs written: %d", summary.changelogs_written)
    if summary.errors:
        logging.warning("  Errors encountered (%d):", len(summary.errors))
        for msg in summary.errors:
            logging.warning("    - %s", msg)
    else:
        logging.info("  No errors encountered.")


def load_text(path: str) -> str:
    """Load the full contents of a text file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def safe_get(d: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Safe dictionary get with default."""
    return d.get(key, default)


def make_output_paths(base_output_dir: str, account_id: str, version: str) -> Tuple[str, str]:
    """
    Return absolute paths for memo.json and agent_spec.json for a given account/version.

    :param base_output_dir: Base directory (typically 'outputs/accounts').
    :param account_id: Logical account identifier.
    :param version: Version label, e.g. 'v1' or 'v2'.
    """
    account_dir = os.path.join(base_output_dir, account_id, version)
    memo_path = os.path.join(account_dir, "memo.json")
    spec_path = os.path.join(account_dir, "agent_spec.json")
    return memo_path, spec_path

