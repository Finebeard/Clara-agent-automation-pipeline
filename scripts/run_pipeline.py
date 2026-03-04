import logging
import os
from typing import Dict

from extractor import extract_account_info
from agent_generator import build_account_memo, build_agent_spec
from updater import merge_memo_with_updates
from diff_engine import build_changelog
from utils import (
    BatchSummary,
    ensure_dir,
    find_transcripts,
    load_text,
    log_batch_summary,
    make_output_paths,
    read_json,
    setup_logging,
    slugify_account_id,
    write_json,
)


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")
DEMO_DIR = os.path.join(DATA_DIR, "demo_calls")
ONBOARDING_DIR = os.path.join(DATA_DIR, "onboarding_calls")
OUTPUT_ACCOUNTS_DIR = os.path.join(ROOT_DIR, "outputs", "accounts")
CHANGELOG_DIR = os.path.join(ROOT_DIR, "changelog")


def process_demo_transcripts(summary: BatchSummary) -> Dict[str, str]:
    """
    Process all demo transcripts and generate v1 memos and agent specs.

    Returns a mapping of account_id -> path_to_v1_memo for later use.
    """
    logging.info("Scanning demo transcripts in %s", DEMO_DIR)
    transcripts = find_transcripts(DEMO_DIR)
    account_to_memo_path: Dict[str, str] = {}

    for path in transcripts:
        try:
            logging.info("Processing demo transcript: %s", path)
            text = load_text(path)
            account_id = slugify_account_id(path)
            extracted, questions = extract_account_info(text)
            memo = build_account_memo(account_id, extracted, questions)
            memo_path, spec_path = make_output_paths(OUTPUT_ACCOUNTS_DIR, account_id, "v1")
            spec = build_agent_spec(memo, "v1")
            write_json(memo_path, memo)
            write_json(spec_path, spec)
            account_to_memo_path[account_id] = memo_path
            summary.demo_accounts_processed += 1
        except Exception as exc:  # noqa: BLE001
            msg = f"Error processing demo transcript {path}: {exc}"
            logging.exception(msg)
            summary.errors.append(msg)

    return account_to_memo_path


def process_onboarding_transcripts(
    summary: BatchSummary,
    existing_accounts: Dict[str, str],
) -> None:
    """
    Process onboarding transcripts, update memos/specs to v2, and write changelogs.
    """
    logging.info("Scanning onboarding transcripts in %s", ONBOARDING_DIR)
    transcripts = find_transcripts(ONBOARDING_DIR)
    ensure_dir(CHANGELOG_DIR)

    for path in transcripts:
        try:
            logging.info("Processing onboarding transcript: %s", path)
            text = load_text(path)
            account_id = slugify_account_id(path)
            if account_id not in existing_accounts:
                logging.warning(
                    "No existing v1 memo found for account_id '%s'; skipping onboarding transcript %s",
                    account_id,
                    path,
                )
                continue

            memo_v1_path = existing_accounts[account_id]
            memo_v1 = read_json(memo_v1_path)

            extracted, questions = extract_account_info(text)
            memo_v2 = merge_memo_with_updates(memo_v1, extracted, questions)

            memo_v2_path, spec_v2_path = make_output_paths(
                OUTPUT_ACCOUNTS_DIR, account_id, "v2"
            )
            spec_v2 = build_agent_spec(memo_v2, "v2")

            write_json(memo_v2_path, memo_v2)
            write_json(spec_v2_path, spec_v2)

            # Build changelog
            changelog = build_changelog(memo_v1, memo_v2)
            changelog_path = os.path.join(CHANGELOG_DIR, f"{account_id}.json")
            write_json(changelog_path, changelog)

            summary.onboarding_updates_applied += 1
            summary.changelogs_written += 1
        except Exception as exc:  # noqa: BLE001
            msg = f"Error processing onboarding transcript {path}: {exc}"
            logging.exception(msg)
            summary.errors.append(msg)


def main() -> None:
    """Run the full pipeline for all available transcripts."""
    setup_logging()
    logging.info("Starting Clara Agent Automation pipeline.")

    ensure_dir(OUTPUT_ACCOUNTS_DIR)
    ensure_dir(CHANGELOG_DIR)

    summary = BatchSummary()

    existing_accounts = process_demo_transcripts(summary)
    process_onboarding_transcripts(summary, existing_accounts)

    log_batch_summary(summary)
    logging.info("Pipeline execution complete.")


if __name__ == "__main__":
    main()

