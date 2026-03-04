## Clara Agent Automation

This project provides a **zero-cost, local-only automation pipeline** that converts call transcripts into structured AI voice agent configurations for Clara-style answering services.

The system reads demo and onboarding call transcripts, extracts structured account information, generates account memos and Retell-style agent specs, and maintains versioned outputs plus changelogs.

### Repository Structure

- **README.md**: Project overview and usage.
- **requirements.txt**: Python dependencies (all standard library; no external installs required).
- **data/**: Input transcript files.
  - **demo_calls/**: Demo call transcripts (`*.txt`) used to generate initial `v1` configurations.
  - **onboarding_calls/**: Onboarding call transcripts (`*.txt`) used to update configurations to `v2`.
- **scripts/**: Core pipeline logic.
  - **run_pipeline.py**: Entry point to run the full pipeline end-to-end.
  - **extractor.py**: Rule-based transcript parser that extracts structured account information.
  - **agent_generator.py**: Builds account memo JSON and Retell-style agent spec JSON, including the system prompt flows.
  - **updater.py**: Applies onboarding updates to an existing account memo.
  - **diff_engine.py**: Compares `v1` and `v2` memos/specs and generates a changelog.
  - **utils.py**: Shared utilities for JSON I/O, logging, path handling, and batch summaries.
- **outputs/**:
  - **accounts/**: Versioned outputs per account (`outputs/accounts/<account_id>/v1/` and `/v2/`).
- **changelog/**:
  - Per-account changelog JSON (`changelog/<account_id>.json`).
- **workflows/**:
  - **pipeline_overview.md**: Detailed description of the pipeline data flow and components.

### Installation

- **Python version**: Python 3.9+ is recommended.
- **Dependencies**: The project uses only the Python standard library; no external packages are required.

Steps:

1. Clone or copy this repository into a local folder.
2. Ensure `python` (or `python3`) is available on your PATH.
3. (Optional) Create and activate a virtual environment if you want isolation, though it is not strictly necessary since there are no external dependencies.

### Input Conventions

- Place **demo call** transcripts as `.txt` files in `data/demo_calls/`.
- Place **onboarding call** transcripts as `.txt` files in `data/onboarding_calls/`.
- Filenames are used to derive a stable `account_id`. By default, the pipeline:
  - Strips the extension.
  - Removes known suffixes like `_demo` and `_onboarding`.
  - Lowercases and normalizes to a simple slug.
- Example:
  - `acme_hvac_demo.txt` → `account_id = "acme_hvac"`.
  - `acme_hvac_onboarding.txt` → `account_id = "acme_hvac"`.

For the included examples, this convention is already followed.

### Running the Pipeline

From the repository root (`clara-agent-automation/`), run:

```bash
python scripts/run_pipeline.py
```

What this does:

1. Scans `data/demo_calls/` for demo transcripts.
2. For each demo transcript:
   - Extracts structured account information using rule-based logic.
   - Generates `memo.json` (account memo) and `agent_spec.json` (Retell-style agent spec).
   - Saves them under `outputs/accounts/<account_id>/v1/`.
3. Scans `data/onboarding_calls/` for onboarding transcripts.
4. For each onboarding transcript with a matching existing account:
   - Extracts updated information from the onboarding transcript.
   - Merges updates into the existing `memo.json` to produce a `v2` memo.
   - Regenerates `agent_spec.json` with version `v2`.
   - Saves them under `outputs/accounts/<account_id>/v2/`.
   - Uses `diff_engine.py` to compare `v1` and `v2` and writes a changelog to `changelog/<account_id>.json`.
5. Prints a batch processing summary to the console.

The pipeline is designed to be **repeatable and idempotent**: re-running it will overwrite existing `v1`/`v2` outputs and changelogs with deterministic content based on the transcripts.

### Output Formats

#### Account Memo (`memo.json`)

Each account memo JSON contains at least:

- `account_id`
- `company_name`
- `business_hours` (list of objects with `day`, `start`, `end`, `timezone`)
- `office_address`
- `services_supported`
- `emergency_definition`
- `emergency_routing_rules`
- `non_emergency_routing_rules`
- `call_transfer_rules`
- `integration_constraints`
- `after_hours_flow_summary`
- `office_hours_flow_summary`
- `questions_or_unknowns`
- `notes`

**Important rule**: If information cannot be confidently extracted, the pipeline does **not** guess. Instead, it adds a human-readable note to `questions_or_unknowns` describing what is missing or ambiguous.

#### Agent Spec (`agent_spec.json`)

Each agent spec JSON contains:

- `agent_name`
- `voice_style`
- `system_prompt`
- `key_variables`
- `call_transfer_protocol`
- `fallback_protocol`
- `version`

The `system_prompt` is generated automatically from the account memo and always includes **two explicit flows**:

- **Business Hours Flow**:
  1. Greeting
  2. Ask purpose of call
  3. Collect name and phone number
  4. Route or transfer call
  5. Fallback if transfer fails
  6. Confirm next steps
  7. Ask if anything else
  8. Close call politely

- **After Hours Flow**:
  1. Greeting
  2. Ask purpose
  3. Confirm if emergency
  4. If emergency, collect name, phone, and address immediately
  5. Attempt transfer
  6. If transfer fails, apologize and promise follow-up
  7. If non-emergency, collect details for next business day
  8. Ask if anything else
  9. Close call

The prompt **does not mention internal tools or function calls**.

### Changelog

For each account that receives onboarding updates, a changelog JSON is written to:

- `changelog/<account_id>.json`

The changelog is a simple, human-readable summary of what changed between `v1` and `v2`, e.g.:

```json
{
  "business_hours": "updated",
  "emergency_definition": "added sprinkler leak as emergency condition",
  "routing_rules": "modified"
}
```

The exact keys and messages are generated by `diff_engine.py` based on field-level differences in the memos and, when relevant, the agent specs.

### System Architecture & Data Flow

High-level architecture:

- **Extractor (`extractor.py`)**:
  - Parses transcript text with simple rule-based and pattern-based logic.
  - Extracts fields such as business hours, services, emergency definitions, routing rules, and addresses.
  - Returns a partially filled account data structure plus notes about missing fields.
- **Agent Generator (`agent_generator.py`)**:
  - Normalizes the extracted data into the canonical account memo structure.
  - Ensures required fields exist, injecting `questions_or_unknowns` notes as needed.
  - Generates the Retell-style agent spec, including a tailored system prompt.
- **Updater (`updater.py`)**:
  - Loads an existing `v1` memo.
  - Applies updates from onboarding extraction, preferring new values when present.
  - Preserves prior values when onboarding is silent about a field.
- **Diff Engine (`diff_engine.py`)**:
  - Compares `v1` and `v2` memos (and optionally agent specs).
  - Produces a concise changelog JSON keyed by logical areas (business hours, emergency definition, routing rules, etc.).
- **Utils (`utils.py`)**:
  - Handles JSON I/O, directory creation, slugification of account IDs, and logging setup.
- **Runner (`run_pipeline.py`)**:
  - Orchestrates all pipeline stages over all available transcripts.

See `workflows/pipeline_overview.md` for a step-by-step walkthrough of this data flow.

### Limitations

- The extractor uses **simple rule-based heuristics** designed to work well with reasonably structured transcripts (e.g. phrases like "Business hours are ...", "Our office address is ...").
- Arbitrary, noisy, or highly informal transcripts may lead to more information being pushed into `questions_or_unknowns` rather than fully structured fields.
- Time parsing is intentionally conservative to avoid guessing; ambiguous mentions of hours or days will be treated as unknowns.
- Emergency definitions and routing rules rely on keyword and pattern matching; highly unconventional wording may require manual review.

### Importing Agent Specs into Retell

The generated `agent_spec.json` files are designed to be easily **manually imported** into a Retell-like system:

- **agent_name**: Use as the display name for the agent.
- **voice_style**: Map to the closest available voice preset or style.
- **system_prompt**: Copy-paste into the agent's system prompt / instruction field.
- **key_variables**: Reference for any configuration variables or metadata needed when wiring up integrations.
- **call_transfer_protocol** and **fallback_protocol**: Use as implementation notes when configuring call routing and failover behavior.
- **version**: Tag the agent configuration in your system as `v1` or `v2` to match the pipeline outputs.

Because everything is stored as local JSON and uses only the Python standard library, the project is **zero-cost** and can be run entirely offline.

