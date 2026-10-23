import json
import unittest

from amanat.analyser import StockAnalyser
from amanat.models import Document, ScreenStatus, Stock


class FakeInference:
    def __init__(self, response: str) -> None:
        self.response = response
        self.system = ""
        self.user = ""

    def complete(self, *, system: str, user: str) -> str:
        self.system, self.user = system, user
        return self.response


def document() -> Document:
    return Document(
        url="https://example.com/report",
        title="Annual report",
        text="Revenue was 100. The company does not operate in prohibited activities.",
    )


class StockAnalyserTests(unittest.TestCase):
    def test_analyser_returns_typed_result_and_keeps_source_evidence(self) -> None:
        client = FakeInference(
            json.dumps(
                {
                    "overall_status": "PASS",
                    "summary": "The supplied evidence supports a pass.",
                    "screens": [
                        {
                            "name": "Business activities",
                            "status": "PASS",
                            "finding": "No prohibited activity found.",
                            "evidence": [
                                {
                                    "source_url": "https://example.com/report",
                                    "quote": "does not operate in prohibited activities",
                                    "rationale": "The report describes the business.",
                                }
                            ],
                        }
                    ],
                    "limitations": ["Only one public document was supplied."],
                }
            )
        )
        result = StockAnalyser(client).analyse(Stock("ABC", "Example Corp"), [document()])

        self.assertIs(result.overall_status, ScreenStatus.PASS)
        self.assertEqual(result.screens[0].evidence[0].source_url, document().url)
        self.assertIn("untrusted source", client.system)
        self.assertIn(document().url, client.user)

    def test_analyser_requires_documents(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one"):
            StockAnalyser(FakeInference("{}")).analyse(Stock("ABC"), [])

    def test_invalid_model_json_is_explicit(self) -> None:
        with self.assertRaisesRegex(ValueError, "screening schema"):
            StockAnalyser(FakeInference('{"overall_status":"PASS"}')).analyse(
                Stock("ABC"), [document()]
            )

    def test_unknown_evidence_source_is_rejected(self) -> None:
        response = json.dumps(
            {
                "overall_status": "PASS",
                "summary": "summary",
                "screens": [
                    {
                        "name": "business",
                        "status": "PASS",
                        "finding": "finding",
                        "evidence": [
                            {
                                "source_url": "https://not-supplied.test",
                                "quote": "quote",
                                "rationale": "reason",
                            }
                        ],
                    }
                ],
            }
        )
        with self.assertRaisesRegex(ValueError, "screening schema"):
            StockAnalyser(FakeInference(response)).analyse(Stock("ABC"), [document()])

    def test_clear_failed_screen_controls_overall_status(self) -> None:
        response = json.dumps(
            {
                "overall_status": "PASS",
                "summary": "incorrect aggregate supplied by model",
                "screens": [
                    {
                        "name": "Business activities",
                        "status": "FAIL",
                        "finding": "Prohibited core activity.",
                        "evidence": [],
                        "visualisation": {
                            "type": "metric",
                            "labels": ["Pass"],
                            "values": [0],
                            "unit": "screen",
                        },
                    }
                ],
            }
        )
        result = StockAnalyser(FakeInference(response)).analyse(Stock("ABC"), [document()])
        self.assertIs(result.overall_status, ScreenStatus.FAIL)
        self.assertEqual(result.screens[0].visualisation["values"], [0])
