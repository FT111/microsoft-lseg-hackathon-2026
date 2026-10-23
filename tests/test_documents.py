import unittest

from amanat.documents import PublicDocumentFetcher


class DocumentFetcherTests(unittest.TestCase):
    def test_fetcher_rejects_non_http_urls(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported document URL"):
            PublicDocumentFetcher().fetch("file:///etc/passwd")
