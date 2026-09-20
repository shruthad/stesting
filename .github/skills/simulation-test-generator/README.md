# Simulation Test Generator Skill

This skill generates validated JSONL simulation test cases from a golden dataset. It is project-independent: bring a new dataset, choose variation types, and generate a simulation dataset without changing the skill code.

It is installed here as a project skill under `.github/skills/`, which VS Code and GitHub Copilot discover automatically. To reuse it in another repository, copy the complete `simulation-test-generator` directory into that repository's `.github/skills/`. To use one installation across local projects, place it under `~/.copilot/skills/` instead.

## Invoke In Copilot Chat

Example:

```text
Use the simulation-test-generator skill with .github/skills/simulation-test-generator/examples/golden_dataset.jsonl.
```

The skill will show the 18 variation types and ask for a selection and quantity. A compact reply can be `V01,V02,V10; 2`, `A; 1`, or `all; 1`.

To skip the questions when you already know the settings:

```text
Use the simulation-test-generator skill with .github/skills/simulation-test-generator/examples/golden_dataset.jsonl.
Generate V01, V02, V10, and V17 with 1 variant per type per query using Copilot LLM.
Save the output as .github/skills/simulation-test-generator/examples/generated_simulation_dataset.jsonl.
```

## Example Copilot Chat Requests

Interactive selection using the bundled dataset:

```text
Use the simulation-test-generator skill with
.github/skills/simulation-test-generator/examples/golden_dataset.jsonl.
Show me the available variation options before generating anything.
```

Generate selected variations with the default Copilot LLM:

```text
Use the simulation-test-generator skill with data/golden_tests.jsonl.
Generate V01, V03, V10, and V17 with 2 variants per selected type per golden query.
Save the validated output to data/simulation_tests.jsonl.
```

Generate an entire group:

```text
Use the simulation-test-generator skill with tests/golden.csv.
Generate all Group A language variations, 1 variant per type per query.
```

Generate all 18 variation types:

```text
Use the simulation-test-generator skill with tests/golden.json.
Generate all variations with 1 variant per type per golden query.
Mark cases requiring unavailable project context as requires_review.
```

Use custom column names:

```text
Use the simulation-test-generator skill with data/approved_answers.xlsx.
Map id to case_id, user_question to query, and approved_answer to expected_response.
Generate V02 and V08 with 3 variants per type per query.
```

Provide project context for safer task-changing variants:

```text
Use the simulation-test-generator skill with data/support_golden.jsonl.
Generate V11, V12, V15, and V18 with 1 variant each.
Supported capabilities are order lookup, delivery ETA, cancellation, and refunds.
Use only the test entities in data/support_fixtures.json and do not invent customer facts.
```

Generate multilingual cases:

```text
Use the simulation-test-generator skill with data/golden.jsonl.
Generate V06 with 2 variants per query using Spanish and Hindi.
Use Copilot LLM and save the result to data/multilingual_simulations.jsonl.
```

Test the optional DeepEval engine:

```text
Use the simulation-test-generator skill with
.github/skills/simulation-test-generator/examples/golden_dataset.jsonl.
Generate V15 with 1 variant per query using DeepEval.
Do not fall back to Copilot. Mark any unsupported capability or uncertain variation mapping as requires_review.
```

## Required Dataset Fields

- `case_id`
- `query`
- `expected_response`

CSV, JSON, JSONL, and XLSX are supported. If your columns have different names, provide mappings such as:

```text
case_id=id, query=user_question, expected_response=approved_answer
```

The original golden dataset is never modified.

## Utility Commands

Inspect a golden dataset:

```bash
python3 .github/skills/simulation-test-generator/scripts/dataset_utils.py inspect .github/skills/simulation-test-generator/examples/golden_dataset.jsonl
```

Validate generated simulation output:

```bash
python3 .github/skills/simulation-test-generator/scripts/dataset_utils.py validate-sim .github/skills/simulation-test-generator/examples/simulation_dataset.jsonl
```

Check optional DeepEval availability:

```bash
python3 .github/skills/simulation-test-generator/scripts/dataset_utils.py deepeval-info
```

## Output

Generated records are JSONL objects with stable fields: `test_id`, `source_case_id`, `variation_id`, `variation_type`, `simulated_query`, `conversation`, `expected_response`, `expected_behavior`, `expected_response_policy`, and `validation_status`.

The default generator is the Copilot LLM in chat. The Python script does not call the model; it handles deterministic loading and validation.
