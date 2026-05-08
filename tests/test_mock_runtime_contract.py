"""Executable contract tests for Cognitive Council Runtime fixtures.

The mock runtime below is intentionally tiny and deterministic. It validates the
fixture expectations without using external APIs, and provides a target shape for
the future real runtime: return a decision, a confirmation requirement, and a set
of safety/planning flags.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_fixtures() -> list[dict]:
    return [json.loads(path.read_text()) for path in sorted(FIXTURE_DIR.glob("*.json"))]


class MockCouncilRuntime:
    """Rule-based stand-in for the future Cognitive Council Runtime."""

    def evaluate(self, fixture: dict) -> dict:
        message = fixture["user_message"].lower()
        context = fixture.get("context", {})
        flags: set[str] = set()
        decision = "answer_directly"
        requires_confirmation = False

        if context.get("external_side_effect"):
            flags.add("external_send")

        if context.get("financial_action") or "wire instructions" in message:
            flags.add("financial_risk")

        if any(term in message for term in ["urgent", "bypass", "do not ask"]):
            if "urgent" in message or "do not ask" in message:
                flags.add("adversarial_urgency")
            if "bypass" in message:
                flags.add("bypass_request")
            decision = "safety_hold"
            requires_confirmation = True

        elif context.get("channel") in {"email", "slack", "sms"}:
            contacts = context.get("known_contacts", [])
            first_names = [contact.split()[0].lower() for contact in contacts]
            duplicate_first_names = len(first_names) != len(set(first_names))
            if duplicate_first_names:
                flags.update({"recipient_ambiguous", "missing_exact_recipient"})
                decision = "ask_clarifying_question"
            else:
                flags.update({"recipient_explicit", "body_explicit"})
                decision = "confirm_then_send"
                requires_confirmation = True

        if context.get("task_type") == "draft_revision" and context.get("prior_draft_attempts", 0) >= 3:
            flags.update({"draft_loop_risk", "low_specificity_feedback", "needs_user_direction"})
            decision = "ask_for_specific_feedback"
            requires_confirmation = False

        if context.get("task_type") == "planning" or "whether we should" in message:
            flags.update({"planning_required", "tradeoff_detected", "recommendation_needed"})
            decision = "present_tradeoff_plan"
            requires_confirmation = False

        return {
            "decision": decision,
            "requires_confirmation": requires_confirmation,
            "flags": sorted(flags),
        }


class MockRuntimeContractTests(unittest.TestCase):
    def test_fixture_expected_decision_and_flags(self) -> None:
        for fixture in load_fixtures():
            with self.subTest(fixture=fixture["id"]):
                result = MockCouncilRuntime().evaluate(fixture)
                expected = fixture["expected"]

                self.assertEqual(result["decision"], expected["decision"])
                self.assertIs(result["requires_confirmation"], expected["requires_confirmation"])

                flags = set(result["flags"])
                self.assertTrue(set(expected["required_flags"]).issubset(flags))
                self.assertTrue(flags.isdisjoint(expected["forbidden_flags"]))

    def test_fixture_schema_minimum(self) -> None:
        for fixture in load_fixtures():
            with self.subTest(fixture=fixture["id"]):
                self.assertTrue(fixture["id"])
                self.assertTrue(fixture["title"])
                self.assertTrue(fixture["user_message"])
                self.assertIsInstance(fixture.get("context", {}), dict)
                self.assertEqual(
                    set(fixture["expected"]),
                    {
                        "decision",
                        "requires_confirmation",
                        "required_flags",
                        "forbidden_flags",
                    },
                )


if __name__ == "__main__":
    unittest.main()
