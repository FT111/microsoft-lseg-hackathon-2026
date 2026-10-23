import unittest

from amanat.sources import SecEdgarDocumentProvider


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
