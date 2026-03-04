## Pipeline Overview

This document describes the end-to-end data flow for the **Clara Agent Automation** project.

### High-Level Flow

1. **Input transcripts**
   - Demo call transcripts in `data/demo_calls/`.
   - Onboarding call transcripts in `data/onboarding_calls/`.
2. **Extraction**
   - `extractor.py` parses each transcript using rule-based logic.
   - Outputs a partial account data structure plus notes about missing or ambiguous information.
3. **Initial generation (v1)**
   - `agent_generator.py` converts extracted data into:
     - `memo.json`: Structured account memo.
     - `agent_spec.json`: Retell-style agent specification with system prompts.
   - Files are written to `outputs/accounts/<account_id>/v1/`.
4. **Onboarding updates (v2)**
   - `updater.py` merges onboarding extraction results with the existing `v1` memo.
   - `agent_generator.py` regenerates `memo.json` (v2) and `agent_spec.json` (v2).
   - Files are written to `outputs/accounts/<account_id>/v2/`.
5. **Diff and changelog**
   - `diff_engine.py` compares `v1` and `v2` memos (and agent specs where relevant).
   - Produces a concise changelog JSON saved at `changelog/<account_id>.json`.
6. **Batch orchestration**
   - `run_pipeline.py` orchestrates the entire process for all transcripts.
   - Provides logging and a batch summary at the end of execution.

### Components in Detail

#### 1. Extractor (`scripts/extractor.py`)

Responsibilities:

- Load raw transcript text.
- Use simple heuristics and pattern matching to extract:
  - `company_name`
  - `business_hours` (days, start, end, timezone)
  - `office_address`
  - `services_supported`
  - `emergency_definition`
  - `emergency_routing_rules`
  - `non_emergency_routing_rules`
  - `call_transfer_rules`
  - `integration_constraints`
  - `after_hours_flow_summary`
  - `office_hours_flow_summary`
  - `notes`
- Return:
  - A dictionary with any confidently extracted fields.
  - A list of human-readable messages describing any missing or ambiguous data.

The extractor **never guesses**. If a field cannot be reliably filled, it is left out and a note is added for `questions_or_unknowns`.

#### 2. Agent Generator (`scripts/agent_generator.py`)

Responsibilities:

- Accept:
  - `account_id`
  - Extracted data (partial)
  - A `version` string (`"v1"` or `"v2"`).
- Build a **complete account memo** with all required keys, inserting:
  - Defaults where appropriate (e.g. empty lists/strings).
  - All extractor notes into `questions_or_unknowns`.
- Build a **Retell-style agent spec** with:
  - `agent_name` derived from company name or account ID.
  - `voice_style` as a simple descriptive string.
  - `system_prompt` that explicitly encodes both:
    - **Business Hours Flow** (8 steps).
    - **After Hours Flow** (9 steps).
  - `key_variables` summarizing critical pieces of configuration.
  - `call_transfer_protocol` and `fallback_protocol` based on memo details.
  - `version` (`"v1"` or `"v2"`).

The system prompt is strictly natural language: it does not mention internal tools, APIs, or function calls.

#### 3. Updater (`scripts/updater.py`)

Responsibilities:

- Accept:
  - Existing `v1` memo for an account.
  - New extraction results from an onboarding transcript.
- Merge logic:
  - For each field where onboarding provides a new value:
    - Update the memo with this new value.
  - For each field not mentioned in onboarding:
    - Keep the existing value from `v1`.
- Combine `questions_or_unknowns`:
  - Preserve prior questions, appending any new uncertainties from the onboarding extraction.
- Return the updated memo suitable for use as `v2`.

#### 4. Diff Engine (`scripts/diff_engine.py`)

Responsibilities:

- Compare:
  - `v1` vs `v2` memos.
  - Optionally, selected fields of `v1` vs `v2` agent specs for additional context.
- Produce a **changelog dictionary** summarizing:
  - Which logical areas changed (e.g. `"business_hours"`, `"emergency_definition"`, `"routing_rules"`).
  - A short, human-readable description of how they changed.
- Write the changelog to:

  - `changelog/<account_id>.json`

The changelog is intentionally simple and easy to read for non-technical stakeholders.

#### 5. Utils (`scripts/utils.py`)

Responsibilities:

- JSON I/O:
  - `read_json(path)` and `write_json(path, data)` with pretty formatting and robust error handling.
- Filesystem helpers:
  - Ensure directories exist before writing.
  - Discover `.txt` transcripts in input folders.
- Account ID handling:
  - Derive a stable `account_id` from filenames (e.g. strip `_demo` / `_onboarding`, normalize case).
- Logging:
  - Configure a basic logger used by all scripts.
- Batch summaries:
  - Provide a helper to collate counts of processed accounts and errors.

#### 6. Runner (`scripts/run_pipeline.py`)

Responsibilities:

- Initialize logging and summarize configuration.
- Process demo calls:
  - Scan `data/demo_calls/`.
  - For each `.txt` file:
    - Derive `account_id`.
    - Extract structured data from the transcript.
    - Generate `v1` memo and agent spec.
    - Write to `outputs/accounts/<account_id>/v1/`.
- Process onboarding calls:
  - Scan `data/onboarding_calls/`.
  - For each `.txt` file:
    - Derive `account_id`.
    - If a matching `v1` memo exists:
      - Extract onboarding data.
      - Merge into `v1` to produce `v2`.
      - Generate `v2` agent spec.
      - Write to `outputs/accounts/<account_id>/v2/`.
      - Use `diff_engine.py` to create/update `changelog/<account_id>.json`.
    - If no `v1` memo exists:
      - Log a warning and skip (by design).
- At the end:
  - Print a concise batch summary:
    - Number of demo accounts processed.
    - Number of onboarding updates applied.
    - Number of changelogs generated.

### Idempotency and Safety

- Running `python scripts/run_pipeline.py` multiple times:
  - Regenerates outputs in a deterministic way based on the current transcript contents.
  - Overwrites existing `memo.json`, `agent_spec.json`, and `changelog` files for each account.
  - Does not append duplicate data or create conflicting versions.

### Extensibility

The system is designed so that you can:

- Add new extraction rules in `extractor.py` without changing the rest of the pipeline.
- Extend the memo schema or agent spec with additional fields.
- Plug in alternative transcript sources (e.g. different folders or formats) by adjusting only the runner and/or utils.

