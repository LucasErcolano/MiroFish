# Adapted repository runner — PILOT-ARG-2025-Q1

Date: 2026-05-22

## Why this exists

The requested fork CLI command `mirofish run` is not available in this repository or PATH. Inspection shows this checkout is the upstream-style MiroFish backend/frontend application: Flask APIs, Vue frontend, Graphiti/Zep graph workflows, OASIS social-simulation scripts, and report-agent services. It does not expose a packaged CLI named `mirofish`.

To keep the pilot auditable, I added a conservative fallback runner under the current repo:

`backend/scripts/run_case_pilot_arg_2025_q1.py`

Root npm shortcut:

`npm run pilot:arg2025q1`

Equivalent direct command:

`python backend/scripts/run_case_pilot_arg_2025_q1.py --case-dir cases/PILOT-ARG-2025-Q1`

## What the adapted runner does

- Reads only `input_pack_pre_x/` and `prompt_frozen/`.
- Does not read `answer_key_post_x/`.
- Validates source dates, `allowed_before_x`, local file presence and SHA256 hashes.
- Scans seed/excerpts for forbidden post-cutoff strings.
- Builds `model_output_raw/artifacts/adapted_input_packet.md` from:
  - `input_pack_pre_x/seed_bundle.md`
  - `input_pack_pre_x/manifest.csv`
  - `input_pack_pre_x/excerpts/*.md`
  - extracted/truncated local sources; PDFs use system `pdftotext` if present.
- Calls an OpenAI-compatible chat-completions endpoint using:
  - `LLM_API_KEY`
  - `LLM_BASE_URL`, default `https://api.openai.com/v1`
  - `LLM_MODEL_NAME`, default `gemma-4-31b-it`
- Runs 3 seeds by default: 20250131, 20250132, 20250133.
- Writes raw unedited outputs to `model_output_raw/mirofish_report_raw.md` and per-run artifacts if the LLM call succeeds.
- Writes `model_output_raw/verdict_raw.json` either as completed adapted run or blocked record.

## Deviations from requested `mirofish run`

This is not a full OASIS/Zep/Graphiti social simulation.

Documented deviations:

1. No `mirofish` CLI exists in this checkout.
2. No Twitter/Reddit/OASIS agent interaction is executed.
3. No Graphiti/Zep persistent memory graph is built or queried.
4. No web, browsing, external RAG or post-cutoff data is used.
5. Evidence is passed as one local pre-cutoff packet to an OpenAI-compatible LLM.
6. `num_agents` and `num_rounds` are not applicable in this fallback and are logged as unsupported/not used.

## Dependency inspection result

`uv lock` initially failed because the repo dependency graph tries to combine:

- `graphiti-core==0.28.2`, which requires `neo4j>=5.26.0`;
- `camel-oasis==0.2.5`, which pins `neo4j==5.23.0`.

I did not keep dependency-lock changes in `backend/pyproject.toml` / `backend/uv.lock`, because that would materially alter the upstream app dependency model. Instead, I documented the OASIS side of the conflict in a separate helper file:

`backend/requirements-oasis.txt`

The adapted pilot runner is intentionally stdlib-only plus system `pdftotext`, so it does not require resolving the full backend/OASIS/Graphiti environment.

Verification after adaptation:

- `python -m py_compile backend/scripts/run_case_pilot_arg_2025_q1.py` succeeded.
- `python backend/scripts/run_case_pilot_arg_2025_q1.py --case-dir cases/PILOT-ARG-2025-Q1` reached pre-cutoff validation PASS and then blocked only on missing `LLM_API_KEY`.

## Current execution status

Command executed:

`python backend/scripts/run_case_pilot_arg_2025_q1.py --case-dir cases/PILOT-ARG-2025-Q1 > cases/PILOT-ARG-2025-Q1/model_output_raw/stdout.log 2> cases/PILOT-ARG-2025-Q1/model_output_raw/stderr.log`

Final result:

`COMPLETED_ADAPTED_REPO_RUN`

Exit code captured in:

`model_output_raw/exit_code.txt`

Final model used:

`gemini-2.5-flash-lite`

Reason for model deviation:

The user-provided `gemini-2.0-flash-lite` and `gemini-2.0-flash-lite-001` returned HTTP 404 from Gemini OpenAI-compatible endpoint: model no longer available to new users. The available newer fallback `gemini-2.5-flash-lite` completed successfully.

Gemini endpoint compatibility note:

The Gemini OpenAI-compatible endpoint rejected the OpenAI `seed` field with HTTP 400. The runner now omits the HTTP `seed` parameter for `generativelanguage.googleapis.com` while still recording intended seeds in config/verdict for auditability.

## Evaluation note

`verdict_raw.json` now has `is_model_output: true`; evaluators may score `model_output_raw/mirofish_report_raw.md` as raw model output from the adapted runner. It must still be treated as an adapted-repo fallback, not as a full OASIS/Zep/Graphiti MiroFish simulation.
