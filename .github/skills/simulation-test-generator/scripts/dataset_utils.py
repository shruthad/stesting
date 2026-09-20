#!/usr/bin/env python3
"""Deterministic helpers for the simulation-test-generator skill."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


REQUIRED_LOGICAL_FIELDS = ("case_id", "query", "expected_response")
SIM_REQUIRED_FIELDS = (
    "test_id",
    "source_case_id",
    "variation_id",
    "variation_type",
    "simulated_query",
    "conversation",
    "expected_response",
    "expected_behavior",
    "expected_response_policy",
    "validation_status",
)
VARIATION_TYPES = {
    "V01": "paraphrasing",
    "V02": "typos",
    "V03": "casual_language",
    "V04": "formal_language",
    "V05": "abbreviations",
    "V06": "multilingual_queries",
    "V07": "verbose_queries",
    "V08": "contextual_noise",
    "V09": "ambiguous_requests",
    "V10": "missing_information",
    "V11": "entity_substitution",
    "V12": "additional_constraints",
    "V13": "output_format_changes",
    "V14": "conflicting_information",
    "V15": "multi_intent_queries",
    "V16": "multi_turn_conversations",
    "V17": "follow_up_corrections",
    "V18": "out_of_scope_requests",
}
POLICIES = {"reuse_reference", "derive_reference", "behavioral_rubric", "requires_review"}
STATUSES = {"passed", "requires_review", "rejected"}
MEANING_PRESERVING = {f"V{i:02d}" for i in range(1, 9)}


@dataclass
class ValidationIssue:
    level: str
    row: int | None
    message: str

    def as_dict(self) -> dict[str, Any]:
        return {"level": self.level, "row": self.row, "message": self.message}


def parse_mapping(items: Iterable[str] | None) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in items or []:
        if "=" not in item:
            raise ValueError(f"Mapping must use logical=actual syntax: {item}")
        logical, actual = item.split("=", 1)
        mapping[logical.strip()] = actual.strip()
    return mapping


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            value = json.loads(stripped)
            if not isinstance(value, dict):
                raise ValueError(f"Line {line_number} is not a JSON object")
            rows.append(value)
    return rows


def read_json(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(value, list):
        rows = value
    elif isinstance(value, dict):
        for key in ("records", "cases", "data"):
            if isinstance(value.get(key), list):
                rows = value[key]
                break
        else:
            rows = [value]
    else:
        raise ValueError("JSON input must be an object, list, or contain records/cases/data")
    if not all(isinstance(row, dict) for row in rows):
        raise ValueError("JSON rows must be objects")
    return list(rows)


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_xlsx(path: Path) -> list[dict[str, Any]]:
    try:
        import pandas as pd  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("XLSX support requires pandas plus an Excel engine such as openpyxl") from exc
    try:
        frame = pd.read_excel(path)
    except ImportError as exc:
        raise RuntimeError("XLSX support requires an installed Excel engine such as openpyxl") from exc
    return frame.where(frame.notna(), None).to_dict(orient="records")


def load_dataset(path: str | Path) -> list[dict[str, Any]]:
    input_path = Path(path)
    suffix = input_path.suffix.lower()
    if suffix == ".jsonl":
        return read_jsonl(input_path)
    if suffix == ".json":
        return read_json(input_path)
    if suffix == ".csv":
        return read_csv(input_path)
    if suffix in {".xlsx", ".xls"}:
        return read_xlsx(input_path)
    raise ValueError(f"Unsupported dataset extension: {suffix}")


def normalize_golden_rows(rows: list[dict[str, Any]], mapping: dict[str, str] | None = None) -> list[dict[str, Any]]:
    mapping = mapping or {}
    normalized: list[dict[str, Any]] = []
    for row in rows:
        output = dict(row)
        for logical in REQUIRED_LOGICAL_FIELDS:
            actual = mapping.get(logical, logical)
            output[logical] = row.get(actual)
        normalized.append(output)
    return normalized


def validate_golden_rows(rows: list[dict[str, Any]]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    seen_case_ids: set[str] = set()
    for index, row in enumerate(rows, start=1):
        for field in REQUIRED_LOGICAL_FIELDS:
            if row.get(field) in (None, ""):
                issues.append(ValidationIssue("error", index, f"Missing required field: {field}"))
        case_id = str(row.get("case_id", ""))
        if case_id:
            if case_id in seen_case_ids:
                issues.append(ValidationIssue("error", index, f"Duplicate case_id: {case_id}"))
            seen_case_ids.add(case_id)
    if not rows:
        issues.append(ValidationIssue("error", None, "Dataset contains no rows"))
    return issues


def write_jsonl(records: Iterable[dict[str, Any]], path: str | Path) -> None:
    output_path = Path(path)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def validate_simulation_records(records: list[dict[str, Any]]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    seen_test_ids: set[str] = set()
    seen_content: set[tuple[Any, ...]] = set()
    for index, record in enumerate(records, start=1):
        for field in SIM_REQUIRED_FIELDS:
            if field not in record:
                issues.append(ValidationIssue("error", index, f"Missing output field: {field}"))
        if record.get("test_id") in (None, ""):
            issues.append(ValidationIssue("error", index, "Missing test_id"))
        elif record["test_id"] in seen_test_ids:
            issues.append(ValidationIssue("error", index, f"Duplicate test_id: {record['test_id']}"))
        else:
            seen_test_ids.add(record["test_id"])

        variation_id = record.get("variation_id")
        expected_type = VARIATION_TYPES.get(variation_id)
        if expected_type is None:
            issues.append(ValidationIssue("error", index, f"Unknown variation_id: {variation_id}"))
        elif record.get("variation_type") != expected_type:
            issues.append(
                ValidationIssue(
                    "error",
                    index,
                    f"variation_type should be {expected_type} for {variation_id}",
                )
            )

        policy = record.get("expected_response_policy")
        if policy not in POLICIES:
            issues.append(ValidationIssue("error", index, f"Invalid expected_response_policy: {policy}"))

        status = record.get("validation_status")
        if status not in STATUSES:
            issues.append(ValidationIssue("error", index, f"Invalid validation_status: {status}"))

        conversation = record.get("conversation")
        simulated_query = record.get("simulated_query")
        if variation_id in {"V16", "V17"}:
            if not isinstance(conversation, list) or not conversation:
                issues.append(ValidationIssue("error", index, "Multi-turn variations require a non-empty conversation"))
        elif simulated_query in (None, ""):
            issues.append(ValidationIssue("error", index, "Single-turn variations require simulated_query"))

        if conversation is not None and not isinstance(conversation, list):
            issues.append(ValidationIssue("error", index, "conversation must be null or a list"))
        if isinstance(conversation, list) and not all(isinstance(item, str) and item.strip() for item in conversation):
            issues.append(ValidationIssue("error", index, "conversation messages must be non-empty strings"))

        if variation_id not in MEANING_PRESERVING and policy == "reuse_reference":
            issues.append(
                ValidationIssue(
                    "warning",
                    index,
                    "Task-changing variations should not reuse the reference unless explicitly justified",
                )
            )

        content_key = (
            record.get("source_case_id"),
            variation_id,
            simulated_query,
            tuple(conversation or []),
        )
        if content_key in seen_content:
            issues.append(ValidationIssue("error", index, "Duplicate generated test content"))
        seen_content.add(content_key)
    if not records:
        issues.append(ValidationIssue("error", None, "Simulation output contains no records"))
    return issues


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "records": len(records),
        "by_variation": dict(Counter(str(row.get("variation_id")) for row in records)),
        "by_status": dict(Counter(str(row.get("validation_status")) for row in records)),
        "by_policy": dict(Counter(str(row.get("expected_response_policy")) for row in records)),
    }


def deepeval_info() -> dict[str, Any]:
    info: dict[str, Any] = {"installed": False}
    try:
        import deepeval  # type: ignore[import-not-found]
    except ImportError:
        return info

    info["installed"] = True
    info["version"] = getattr(deepeval, "__version__", "unknown")
    try:
        from deepeval.synthesizer import Synthesizer  # type: ignore[import-not-found]

        info["synthesizer_available"] = True
        info["synthesizer_class"] = f"{Synthesizer.__module__}.{Synthesizer.__name__}"
    except Exception as exc:  # pragma: no cover - depends on optional package internals
        info["synthesizer_available"] = False
        info["synthesizer_error"] = str(exc)
    info["note"] = "DeepEval generation remains optional; verify configured model support before use."
    return info


def cmd_inspect(args: argparse.Namespace) -> int:
    rows = load_dataset(args.path)
    normalized = normalize_golden_rows(rows, parse_mapping(args.mapping))
    issues = validate_golden_rows(normalized)
    result = {
        "path": str(args.path),
        "rows": len(rows),
        "columns": sorted(rows[0].keys()) if rows else [],
        "required_fields": list(REQUIRED_LOGICAL_FIELDS),
        "issues": [issue.as_dict() for issue in issues],
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if any(issue.level == "error" for issue in issues) else 0


def cmd_validate_sim(args: argparse.Namespace) -> int:
    records = read_jsonl(Path(args.path))
    issues = validate_simulation_records(records)
    result = {"summary": summarize(records), "issues": [issue.as_dict() for issue in issues]}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if any(issue.level == "error" for issue in issues) else 0


def cmd_deepeval_info(args: argparse.Namespace) -> int:
    del args
    print(json.dumps(deepeval_info(), indent=2, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Utilities for simulation-test-generator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Inspect and validate a golden dataset")
    inspect_parser.add_argument("path", type=Path)
    inspect_parser.add_argument("--mapping", action="append", help="Field mapping in logical=actual form")
    inspect_parser.set_defaults(func=cmd_inspect)

    validate_parser = subparsers.add_parser("validate-sim", help="Validate generated simulation JSONL")
    validate_parser.add_argument("path", type=Path)
    validate_parser.set_defaults(func=cmd_validate_sim)

    deepeval_parser = subparsers.add_parser("deepeval-info", help="Report optional DeepEval availability")
    deepeval_parser.set_defaults(func=cmd_deepeval_info)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
