import unittest

from amanat.models import Document, Stock
from amanat.sources import (
    GlobalIssuerDocumentProvider,
    SecEdgarDocumentProvider,
    TrustedWebSearchProvider,
)


class SecSourceTests(unittest.TestCase):
    def test_supported_annual_forms_are_explicit(self) -> None:
        self.assertEqual(
            SecEdgarDocumentProvider.supported_sec_forms,
            {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"},
        )

    def test_latest_observation_prefers_annual_facts(self) -> None:
        fact = {
            "units": {
                "USD": [
                    {"val": 1, "form": "10-Q", "filed": "2026-08-01", "end": "2026-06-30"},
                    {"val": 2, "form": "10-K", "fy": 2025, "filed": "2026-02-01", "end": "2025-12-31"},
                ]
            }
        }
        self.assertEqual(
            SecEdgarDocumentProvider._latest_observation(fact),
            (2.0, "USD", "2025-12-31"),
        )

    def test_normalised_debt_adds_current_and_noncurrent_same_period(self) -> None:
        facts = {
            "LongTermDebtCurrent": {
                "units": {"USD": [{"val": 25, "form": "10-K", "fy": 2025, "filed": "2026-02-01", "end": "2025-12-31"}]}
            },
            "LongTermDebtNoncurrent": {
                "units": {"USD": [{"val": 75, "form": "10-K", "fy": 2025, "filed": "2026-02-01", "end": "2025-12-31"}]}
            },
        }
        self.assertEqual(
            SecEdgarDocumentProvider._normalised_debt(facts),
            (100.0, "USD", "2025-12-31"),
        )

    def test_web_search_accepts_only_trusted_domains(self) -> None:
        provider = TrustedWebSearchProvider(trusted_domains={"sec.gov"})
        self.assertTrue(provider._is_trusted("https://www.sec.gov/Archives/report"))
        self.assertFalse(provider._is_trusted("https://example.com/report"))

    def test_global_provider_searches_non_us_official_domains(self) -> None:
        class Search:
            def __init__(self) -> None:
                self.queries = []

            def search(self, query: str) -> tuple[Document, ...]:
                self.queries.append(query)
                return (
                    Document(
                        url="https://www.asx.com.au/company/report",
                        title="Issuer report",
                        text="Official annual report",
                    ),
                )

        search = Search()
        documents = GlobalIssuerDocumentProvider(
            search_provider=search, max_documents=1
        ).collect(Stock("ABC", "Example PLC", "LSE"))

        self.assertEqual(len(documents), 1)
        self.assertIn("site:companieshouse.gov.uk", search.queries[0])
