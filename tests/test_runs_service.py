"""Stdlib tests for the local /runs service contract.

These tests intentionally avoid pytest fixtures/plugins and make no network
calls. They exercise the future /runs API shape through the synchronous local
service.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runs_service import LocalRunsService, request_from_fixture
from schemas import validate_approval, validate_receipt, validate_run_record, validate_run_request
import server

FIXTURES = ROOT / "tests" / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class LocalRunsServiceTests(unittest.TestCase):
    def test_create_run_from_fixture_retrieve_completed_with_receipt(self) -> None:
        fixture = load_fixture("quick_send.json")
        with tempfile.TemporaryDirectory() as tmp:
            service = LocalRunsService(Path(tmp))
            request = request_from_fixture(fixture, profile="balanced", requested_by="unit-test")

            validate_run_request(request)
            created = service.create_run(request)
            fetched = service.get_run(created["run_id"])

        self.assertEqual(created, fetched)
        self.assertEqual(fetched["status"], "completed")
        self.assertEqual(fetched["result"]["task_id"], fixture["id"])
        self.assertEqual(fetched["result"]["decision"], fixture["expected"]["decision"])
        validate_run_record(fetched)

        receipt = fetched["receipt"]
        validate_receipt(receipt)
        self.assertEqual(receipt["run_id"], fetched["run_id"])
        self.assertEqual(receipt["status"], "completed")
        self.assertEqual(receipt["task_id"], fixture["id"])
        self.assertIn("confidence", receipt["result_summary"])
        self.assertIn("flags", receipt["result_summary"])
        self.assertIn("top_influences", receipt["result_summary"])

    def test_approval_shape_for_confirmation_case(self) -> None:
        fixture = load_fixture("quick_send.json")
        with tempfile.TemporaryDirectory() as tmp:
            record = LocalRunsService(Path(tmp)).create_run(request_from_fixture(fixture))

        approval = record["receipt"]["approval"]
        validate_approval(approval)
        self.assertEqual(
            set(approval),
            {"required", "kind", "status", "reason", "action"},
        )
        self.assertTrue(approval["required"])
        self.assertEqual(approval["kind"], "confirmation")
        self.assertEqual(approval["status"], "pending")
        self.assertEqual(approval["action"]["type"], "ask_confirmation")
        self.assertIsInstance(approval["action"]["message"], str)

    def test_approval_shape_for_action_hold_case(self) -> None:
        fixture = load_fixture("adversarial_urgency.json")
        with tempfile.TemporaryDirectory() as tmp:
            record = LocalRunsService(Path(tmp)).create_run(request_from_fixture(fixture))

        approval = record["receipt"]["approval"]
        validate_approval(approval)
        self.assertTrue(approval["required"])
        self.assertEqual(approval["kind"], "action")
        self.assertEqual(approval["status"], "pending")
        self.assertEqual(approval["action"]["type"], "hold")
        self.assertIn("urgency", approval["reason"].lower())

    def test_approval_shape_for_no_approval_case(self) -> None:
        fixture = load_fixture("planning_tradeoff.json")
        with tempfile.TemporaryDirectory() as tmp:
            record = LocalRunsService(Path(tmp)).create_run(request_from_fixture(fixture))

        approval = record["receipt"]["approval"]
        validate_approval(approval)
        self.assertFalse(approval["required"])
        self.assertEqual(approval["kind"], "none")
        self.assertEqual(approval["status"], "not_required")
        self.assertEqual(approval["action"]["type"], "respond")

    def test_fastapi_runs_endpoint_returns_canonical_record(self) -> None:
        fixture_path = "tests/fixtures/quick_send.json"
        with tempfile.TemporaryDirectory() as tmp:
            old_runs_dir = server.RUNS_DIR
            server.RUNS_DIR = Path(tmp)
            try:
                client = TestClient(server.app)
                response = client.post(
                    "/runs",
                    json={"fixture": fixture_path, "profile": "operator", "requestedBy": "unit-test"},
                )
                self.assertEqual(response.status_code, 200, response.text)
                created = response.json()
                validate_run_record(created)
                self.assertIn("run_id", created)
                self.assertIn("receipt", created)
                self.assertIn("approval", created["receipt"])
                self.assertEqual(created["status"], "completed")
                self.assertEqual(created["result"]["decision"], "confirm_then_send")
                self.assertTrue(created["receipt"]["approval"]["required"])

                fetched = client.get(f"/runs/{created['run_id']}")
                self.assertEqual(fetched.status_code, 200, fetched.text)
                self.assertEqual(fetched.json(), created)
            finally:
                server.RUNS_DIR = old_runs_dir


if __name__ == "__main__":
    unittest.main(verbosity=2)
