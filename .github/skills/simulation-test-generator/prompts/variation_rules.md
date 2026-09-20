# Variation Rules

Use these rules when generating simulation test records. Preserve the original source case link and do not invent project facts.

## Group A - Language Variations

These preserve original intent and critical information. Use `expected_response_policy: reuse_reference` when the expected response still applies.

- `V01` paraphrasing: Reword the query while retaining meaning.
- `V02` typos: Add realistic spelling, grammar, or punctuation mistakes. Do not corrupt critical identifiers.
- `V03` casual_language: Use informal, conversational wording.
- `V04` formal_language: Use professional wording.
- `V05` abbreviations: Use commonly understood shorthand without obscuring meaning.
- `V06` multilingual_queries: Translate or naturally code-mix. Use supported languages when supplied; otherwise state the chosen language in metadata or expected behavior.
- `V07` verbose_queries: Add extra wording without changing the request.
- `V08` contextual_noise: Add realistic irrelevant context around the request while keeping the objective clear.

## Group B - Information and Constraints

These may change expected outcome. Do not automatically reuse the original expected response.

- `V09` ambiguous_requests: Make multiple interpretations plausible. Expected behavior should ask for clarification or choose a safe interpretation if project policy says so.
- `V10` missing_information: Remove information required to complete the task. Expected behavior should request the missing detail.
- `V11` entity_substitution: Replace a relevant entity with another valid entity. Use supplied fixtures for real entities. If fixtures are absent, mark `requires_review`.
- `V12` additional_constraints: Add a realistic filter, date range, or condition the project can evaluate. If capability is unknown, mark `requires_review`.
- `V13` output_format_changes: Ask for the answer in another format, such as bullets, table, JSON, or a short answer.
- `V14` conflicting_information: Introduce contradiction that requires resolution or clarification.

## Group C - Conversations and Tasks

- `V15` multi_intent_queries: Add a second related supported request. If support is unknown, mark `requires_review`.
- `V16` multi_turn_conversations: Split the original task into a short ordered conversation. Put user messages in `conversation` and set `simulated_query` to `null`.
- `V17` follow_up_corrections: Create a conversation where a later user turn corrects an earlier detail. Expected behavior follows the latest valid user instruction.
- `V18` out_of_scope_requests: Add or modify the request with an unsupported task. Use documented project capabilities; if unavailable, flag for review rather than inventing policy.

## Policy Defaults

- `V01`-`V08`: usually `reuse_reference`.
- `V09`, `V10`, `V14`, `V18`: usually `behavioral_rubric` or `requires_review`.
- `V11`, `V12`, `V15`: `derive_reference` only when input fixtures/context verify the facts; otherwise `requires_review`.
- `V13`: `derive_reference` if formatting can be deterministically derived from the reference; otherwise `behavioral_rubric`.
- `V16`, `V17`: usually `behavioral_rubric`; use `reuse_reference` only when the final task exactly preserves the original request.

## Rejection Rules

Reject or mark `requires_review` when a candidate:

- loses the original source case link,
- fabricates customer, account, document, policy, or business facts,
- changes protected critical identifiers in a meaning-preserving variant,
- uses an unsupported variation ID,
- provides an exact expected response for a changed task without verified facts,
- contains no usable user query or conversation.
