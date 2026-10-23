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


class TwoPassInference:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str]] = []

    def complete(self, *, system: str, user: str) -> str:
        self.calls.append((system, user))
        return self.responses[len(self.calls) - 1]


class FakeSearch:
    def __init__(self, documents: tuple[Document, ...]) -> None:
        self.documents = documents
        self.queries: list[str] = []

    def search(self, query: str) -> tuple[Document, ...]:
        self.queries.append(query)
        return self.documents


def document() -> Document:
    return Document(
        url="https://example.com/report",
        title="Annual report",
        text="Revenue was 100. The company does not operate in prohibited activities.",
    )


class StockAnalyserTests(unittest.TestCase):
    def test_search_requests_are_limited_to_one_final_pass(self) -> None:
        response = json.dumps(
            {
                "overall_status": "NEEDS REVIEW",
                "summary": "Need evidence.",
                "screens": [],
                "web_search_requests": [
                    {"query": "query", "reason": "missing"},
                ],
            }
        )
        final = json.dumps(
            {
                "overall_status": "NEEDS REVIEW",
                "summary": "Still unresolved.",
                "screens": [],
                "research": {
                    "used_web_research": False,
                    "searches": [],
                    "source_urls": [],
                    "impact": "No trusted result.",
                    "changes": [],
                },
            }
        )
        inference = TwoPassInference([response, final])
        result = StockAnalyser(
            inference,
            web_search_provider=FakeSearch(()),
        ).analyse(Stock("ABC"), [document()])
        self.assertEqual(len(inference.calls), 2)
        self.assertFalse(result.research["used_web_research"])

    def test_analyser_returns_typed_result_and_keeps_source_evidence(self) -> None:
        client = FakeInference(
            json.dumps(
                {
                    "overall_status": "PASS",
                    "summary": "The supplied evidence supports a pass.",
                    "summary_visualisation": {
                        "type": "metric",
                        "title": "Screen count",
                        "labels": ["Screens"],
                        "values": [1],
                        "unit": "screen",
                    },
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
                                    "visualisation": {
                                        "type": "metric",
                                        "title": "Reported revenue",
                                        "labels": ["Revenue"],
                                        "values": [100],
                                        "unit": "USD",
                                    },
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
        self.assertEqual(result.summary_visualisation["values"], [1])
        self.assertEqual(result.screens[0].evidence[0].visualisation["values"], [100])
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

    def test_search_requests_trigger_second_inference_with_sources(self) -> None:
        first = json.dumps(
            {
                "overall_status": "NEEDS REVIEW",
                "summary": "Need official evidence.",
                "screens": [],
                "web_search_requests": [
                    {"query": "Example Corp official annual report", "reason": "Missing filing"}
                ],
            }
        )
        second = json.dumps(
            {
                "overall_status": "PASS",
                "summary": "Evidence is sufficient.",
                "screens": [
                    {
                        "name": "Business activities",
                        "status": "PASS",
                        "finding": "No prohibited activity found.",
                        "evidence": [
                            {
                                "source_url": "https://sec.gov/example",
                                "quote": "No prohibited activity",
                                "rationale": "Official filing evidence.",
                            }
                        ],
                    }
                ],
            }
        )
        search_document = Document(
            url="https://sec.gov/example",
            title="SEC result",
            text="No prohibited activity",
        )
        inference = TwoPassInference([first, second])
        search = FakeSearch((search_document,))
        result = StockAnalyser(inference, web_search_provider=search).analyse(
            Stock("ABC"), [document()]
        )

        self.assertEqual(search.queries, ["Example Corp official annual report"])
        self.assertEqual(len(inference.calls), 2)
        self.assertIn("TRUSTED WEB SOURCE", inference.calls[1][1])
        self.assertIs(result.overall_status, ScreenStatus.PASS)
        self.assertTrue(result.research["used_web_research"])
        self.assertIn("https://sec.gov/example", result.research["source_urls"])
