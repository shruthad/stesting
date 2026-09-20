---
name: simulation-test-generator
description: Generate reusable simulation test datasets from a golden dataset for AI assistants and agents. Use this skill whenever the user wants synthetic user-query variations, simulation tests, golden-dataset expansion, or validated JSONL test cases for an AI assistant, even if they do not explicitly say "simulation test generator".
---

# Simulation Test Generator

Use this skill to generate simulated user queries from an existing golden dataset. The skill is project-independent: load the user's dataset, ask only for missing choices, generate selected variation types with the current Copilot LLM by default, validate the output, and save JSONL simulation records. Do not execute the generated tests against an assistant.

## Required Inputs

The user must provide a golden dataset in CSV, XLSX, JSON, or JSONL format. Never modify or overwrite it.

Minimum logical fields:

- `case_id`: unique source case identifier
- `query`: original user request
- `expected_response`: approved reference response

Support column mapping. If the dataset uses different names, ask for or infer mappings such as `id -> case_id`, `question -> query`, or `answer -> expected_response`.

Optional fields may include intent, expected agent, conversation history, project context, supported capabilities, fixtures, supported languages, and metadata. Use optional fields when present; do not require them.

## Workflow

1. Identify the golden dataset file. If the path is already provided, use it.
2. Resolve `<skill-directory>` as the directory containing this `SKILL.md`, then run `python3 <skill-directory>/scripts/dataset_utils.py inspect <path>` to check format and columns. Pass `--mapping logical=actual` arguments if needed.
3. Apply the interaction contract below. Do not generate until a variation selection is known.
4. Ask which engine only if the user specified no engine and appears to need a non-default choice. Otherwise use `Copilot LLM` silently.
5. Read `prompts/variation_rules.md`.
6. Generate variants with Copilot LLM unless the user explicitly selected DeepEval.
7. Save records to JSONL, then run `python3 <skill-directory>/scripts/dataset_utils.py validate-sim <output.jsonl>` and fix or mark any issues.
8. Report the output path, counts by variation/status, skipped cases, and review-required cases.

Do not force ordinary users to edit config files. If all required choices are in the user's first message, proceed directly.

## Interaction Contract

Collect only values that are missing from the user's request:

- If the dataset path is missing, ask for it first. Do not repeat this question after a usable path is supplied.
- If variation types are missing, display the complete numbered menu below and ask the user to select IDs, ranges, a group (`A`, `B`, or `C`), or `all`. Never silently select variation types.
- At the same time, ask how many variants to create **per selected type, per golden query**. State that the default is `1`; if the user omits the count in their reply, use `1` without asking again.
- Accept compact replies such as `V01,V02,V10; 2`, `A; 1`, `V01-V08; 3`, or `all; 1`.
- Normalize and briefly confirm the interpreted selection before generation, for example: `Generating V01, V02, and V10; 2 each per golden query.`
- If the dataset, selection, and count are already present, do not show the menu or ask redundant questions.

When choices are missing, end the intake response with this prompt after the menu:

```text
Which variations should I generate, and how many variants per selected type per golden query? (Default: 1)
Reply with, for example: V01,V02,V10; 2 | A; 1 | all; 1
```

## Variation Menu

Group A - Language variations, meaning-preserving:

1. `V01` Paraphrasing
2. `V02` Typos
3. `V03` Casual language
4. `V04` Formal language
5. `V05` Abbreviations
6. `V06` Multilingual queries
7. `V07` Verbose queries
8. `V08` Contextual noise

Group B - Information and constraints, may change expected outcome:

9. `V09` Ambiguous requests
10. `V10` Missing information
11. `V11` Entity substitution
12. `V12` Additional constraints
13. `V13` Output-format changes
14. `V14` Conflicting information

Group C - Conversations and tasks:

15. `V15` Multi-intent queries
16. `V16` Multi-turn conversations
17. `V17` Follow-up corrections
18. `V18` Out-of-scope requests

Do not add prompt-injection, jailbreak, unauthorized-access, tool-failure, or fourth-group scenarios in version 1.

## Generation Engines

### Default: Copilot LLM

Use the current Copilot Chat model to produce candidate records from the golden cases and the selected variation rules. Local scripts cannot call Copilot's model directly, so scripts are only for loading, validation, dedupe, summaries, and export.

For each source case and selected variation, generate the requested number of variants. Preserve the source `case_id` in every record.

### Optional: DeepEval

Use DeepEval only when the user explicitly selects it. First run:

```bash
python3 <skill-directory>/scripts/dataset_utils.py deepeval-info
```

If DeepEval or its model configuration is unavailable, report that clearly and stop the DeepEval path. Do not silently switch to Copilot. Do not assume DeepEval supports all 18 variation types; use only installed APIs that are actually present and mark unsupported requested types as skipped with reasons.

## Expected-Response Handling

Use these policies exactly:

- `reuse_reference`: the original expected response remains applicable.
- `derive_reference`: a modified expected response can be derived from verified information supplied in the input.
- `behavioral_rubric`: evaluate behavior rather than exact text.
- `requires_review`: insufficient information is available to establish a reliable expectation.

Meaning-preserving variants (`V01`-`V08`) usually reuse the original expected response if critical entities and execution context are unchanged.

Task-changing variants (`V09`-`V18`) must not blindly copy the original expected response. Prefer a short, testable `expected_behavior`; use `derive_reference` only when the needed facts are verified in the input. Never fabricate reference facts.

## Output Schema

Write JSONL. Each record must contain:

```json
{
  "test_id": "SIM-001",
  "source_case_id": "G001",
  "variation_id": "V01",
  "variation_type": "paraphrasing",
  "simulated_query": "How much money is available in my account ending in 1234?",
  "conversation": null,
  "expected_response": "Your available balance is $5,000.",
  "expected_behavior": "Identify the correct account and report its available balance.",
  "expected_response_policy": "reuse_reference",
  "validation_status": "passed"
}
```

For multi-turn cases (`V16`, `V17`), set `conversation` to an ordered array of user messages and `simulated_query` to `null` unless a final query is required for compatibility.

## Validation Guidance

Use Python checks for structure, required fields, duplicate records, known variation IDs, allowed policies, and allowed statuses. Use Copilot semantic review for whether the transformation truly matches the selected type, whether meaning-preserving cases kept intent and critical entities, and whether project facts were invented.

Statuses:

- `passed`: usable as generated.
- `requires_review`: plausible but needs project or human review.
- `rejected`: invalid or unsafe to use as a simulation case.

Do not discard uncertain cases without explanation. Keep review-required cases in the main JSONL or a separate review file.

## Practical Copilot Prompt Pattern

After inspecting the dataset, use this compact generation prompt:

```text
Using the simulation-test-generator skill and prompts/variation_rules.md, generate <N> variant(s) per selected variation for each source case in <golden path>.
Selected variations: <V IDs>.
Column mapping: <mapping>.
Project context/fixtures/languages: <provided context or none>.
Return records in the required JSONL schema. Preserve source_case_id. Do not invent project facts. Mark uncertain cases requires_review.
```

Then save the JSONL and validate it with `dataset_utils.py validate-sim`.
