import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "skills"
    / "simulation-test-generator"
    / "scripts"
    / "dataset_utils.py"
)
spec = importlib.util.spec_from_file_location("dataset_utils", MODULE_PATH)
dataset_utils = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["dataset_utils"] = dataset_utils
spec.loader.exec_module(dataset_utils)


class DatasetUtilsTests(unittest.TestCase):
    def test_load_and_validate_golden_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "golden.jsonl"
            path.write_text(
                '{"id":"G1","question":"What is my balance?","answer":"Your balance is $10."}\n',
                encoding="utf-8",
            )

            rows = dataset_utils.load_dataset(path)
            normalized = dataset_utils.normalize_golden_rows(
                rows,
                {"case_id": "id", "query": "question", "expected_response": "answer"},
            )
            issues = dataset_utils.validate_golden_rows(normalized)

            self.assertEqual(normalized[0]["case_id"], "G1")
            self.assertEqual(issues, [])

    def test_validate_simulation_records_accepts_valid_record(self):
        records = [
            {
                "test_id": "SIM-001",
                "source_case_id": "G001",
                "variation_id": "V01",
                "variation_type": "paraphrasing",
                "simulated_query": "Where is my order?",
                "conversation": None,
                "expected_response": "It is in transit.",
                "expected_behavior": "Report the order status.",
                "expected_response_policy": "reuse_reference",
                "validation_status": "passed",
            }
        ]

        issues = dataset_utils.validate_simulation_records(records)

        self.assertEqual(issues, [])

    def test_validate_simulation_records_flags_duplicate_content(self):
        base = {
            "source_case_id": "G001",
            "variation_id": "V01",
            "variation_type": "paraphrasing",
            "simulated_query": "Where is my order?",
            "conversation": None,
            "expected_response": "It is in transit.",
            "expected_behavior": "Report the order status.",
            "expected_response_policy": "reuse_reference",
            "validation_status": "passed",
        }
        records = [dict(base, test_id="SIM-001"), dict(base, test_id="SIM-002")]

        issues = dataset_utils.validate_simulation_records(records)

        self.assertTrue(any("Duplicate generated test content" in issue.message for issue in issues))

    def test_validate_simulation_records_requires_conversation_for_multi_turn(self):
        records = [
            {
                "test_id": "SIM-001",
                "source_case_id": "G001",
                "variation_id": "V16",
                "variation_type": "multi_turn_conversations",
                "simulated_query": None,
                "conversation": None,
                "expected_response": None,
                "expected_behavior": "Use prior context.",
                "expected_response_policy": "behavioral_rubric",
                "validation_status": "passed",
            }
        ]

        issues = dataset_utils.validate_simulation_records(records)

        self.assertTrue(any("Multi-turn variations require" in issue.message for issue in issues))

    def test_validate_command_outputs_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sim.jsonl"
            record = {
                "test_id": "SIM-001",
                "source_case_id": "G001",
                "variation_id": "V13",
                "variation_type": "output_format_changes",
                "simulated_query": "Answer in bullets.",
                "conversation": None,
                "expected_response": None,
                "expected_behavior": "Provide the same information as bullets.",
                "expected_response_policy": "behavioral_rubric",
                "validation_status": "passed",
            }
            path.write_text(json.dumps(record) + "\n", encoding="utf-8")

            records = dataset_utils.read_jsonl(path)
            summary = dataset_utils.summarize(records)

            self.assertEqual(summary["records"], 1)
            self.assertEqual(summary["by_variation"]["V13"], 1)


if __name__ == "__main__":
    unittest.main()
