"""Automatic public-source collection for listed-company screening."""

import json
import os
from collections.abc import Iterable
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from .documents import PublicDocumentFetcher
from .models import Document, Stock

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SEC_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data/"
FTSE_YASAAR_URL = "https://www.lseg.com/en/ftse-russell/indices/global-shariah"
SUPPORTED_SEC_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}


class SecEdgarDocumentProvider:
    """Find the latest SEC annual filing for a ticker and fetch its primary document."""

    supported_sec_forms = SUPPORTED_SEC_FORMS

    def __init__(
        self,
        *,
        user_agent: str | None = None,
        timeout: float = 20,
        max_chars: int = 60_000,
    ) -> None:
        self.user_agent = user_agent or os.getenv(
            "SEC_USER_AGENT", "Amanat/0.1 contact@example.com"
        )
        self.timeout = timeout
        self.fetcher = PublicDocumentFetcher(
            timeout=timeout, max_chars=max_chars, user_agent=self.user_agent
        )

    def collect(self, stock: Stock) -> tuple[Document, ...]:
        cik, issuer_name = self._find_issuer(stock.ticker)
        submissions = self._get_json(SEC_SUBMISSIONS_URL.format(cik=cik))
        recent = submissions.get("filings", {}).get("recent", {})
        for index, form in enumerate(recent.get("form", [])):
            if form not in SUPPORTED_SEC_FORMS:
                continue
            accession = recent["accessionNumber"][index]
            primary_document = recent["primaryDocument"][index]
            filing_url = urljoin(
                SEC_ARCHIVES_URL,
                f"{cik}/{accession.replace('-', '')}/{primary_document}",
            )
            document = self.fetcher.fetch(filing_url)
            return (
                Document(
                    url=document.url,
                    title=f"{issuer_name} {form} ({recent['filingDate'][index]})",
                    text=document.text,
                    published_at=recent["filingDate"][index],
                ),
            )
        raise LookupError(f"no recent annual SEC filing found for {stock.ticker}")

    def collect_fundamentals(self, stock: Stock) -> Document:
        """Create a cited, human-readable snapshot from SEC Company Facts."""

        cik, issuer_name = self._find_issuer(stock.ticker)
        payload = self._get_json(SEC_FACTS_URL.format(cik=cik))
        facts = payload.get("facts", {}).get("us-gaap", {})
        fields = {
            "Revenue": ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"),
            "Net income": ("NetIncomeLoss",),
            "Total assets": ("Assets",),
            "Total liabilities": ("Liabilities", "LiabilitiesAndStockholdersEquity"),
            "Cash and equivalents": ("CashAndCashEquivalentsAtCarryingValue",),
            "Debt": (
                "LongTermDebtAndFinanceLeaseObligationsCurrent",
                "LongTermDebtCurrent",
                "LongTermDebtNoncurrent",
            ),
            "Stockholders equity": ("StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"),
            "Shares outstanding": ("EntityCommonStockSharesOutstanding",),
        }
        lines = [f"{issuer_name} SEC Company Facts (ticker {stock.ticker})"]
        for label, tags in fields.items():
            fact = next((facts.get(tag) for tag in tags if facts.get(tag)), None)
            observation = self._latest_observation(fact)
            if observation is None:
                lines.append(f"{label}: unavailable in SEC Company Facts")
                continue
            value, unit, period = observation
            lines.append(f"{label}: {value:,} {unit} ({period})")
        lines.append(
            "These reported facts are source data only; ratios and Shariah conclusions "
            "must be calculated and reviewed against the selected methodology."
        )
        return Document(
            url=SEC_FACTS_URL.format(cik=cik),
            title=f"{issuer_name} SEC Company Facts",
            text="\n".join(lines),
        )

    @staticmethod
    def _latest_observation(fact: dict | None) -> tuple[float, str, str] | None:
        if not fact:
            return None
        units = fact.get("units", {})
        unit_name, observations = next(iter(units.items()), (None, []))
        annual = [
            item for item in observations
            if item.get("form") in SUPPORTED_SEC_FORMS and item.get("fy")
        ]
        candidates = annual or observations
        if not candidates:
            return None
        latest = max(candidates, key=lambda item: item.get("filed", ""))
        period = latest.get("end") or latest.get("filed", "unknown date")
        return float(latest["val"]), unit_name or "reported units", period

    def _find_issuer(self, ticker: str) -> tuple[str, str]:
        records = self._get_json(SEC_TICKERS_URL)
        for record in records.values():
            if record["ticker"].upper() == ticker.upper():
                return f"{int(record['cik_str']):010d}", record["title"]
        raise LookupError(f"SEC EDGAR has no issuer matching ticker {ticker.upper()}")

    def _get_json(self, url: str) -> dict:
        request = Request(url, headers={"User-Agent": self.user_agent})
        with urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))


class AutomaticDocumentProvider:
    """Combine primary issuer filings with the methodology used to interpret them."""

    def __init__(
        self,
        *,
        sec_provider: SecEdgarDocumentProvider | None = None,
        public_fetcher: PublicDocumentFetcher | None = None,
    ) -> None:
        self.sec_provider = sec_provider or SecEdgarDocumentProvider()
        self.public_fetcher = public_fetcher or PublicDocumentFetcher()

    def collect(self, stock: Stock) -> tuple[Document, ...]:
        documents = list(self.sec_provider.collect(stock))
        documents.append(self.sec_provider.collect_fundamentals(stock))
        try:
            documents.append(self.public_fetcher.fetch(FTSE_YASAAR_URL))
        except (OSError, ValueError) as error:
            raise RuntimeError(
                "issuer filing was found, but the official FTSE methodology could not be fetched"
            ) from error
        return tuple(documents)


def source_urls(documents: Iterable[Document]) -> tuple[str, ...]:
    """Return source URLs for UI audit displays."""

    return tuple(document.url for document in documents)
