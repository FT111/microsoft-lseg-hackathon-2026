"""Automatic public-source collection for listed-company screening."""

import json
import os
from collections.abc import Iterable
from html.parser import HTMLParser
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse
from urllib.request import Request, urlopen

from .documents import PublicDocumentFetcher
from .models import Document, Stock

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
SEC_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data/"
FTSE_YASAAR_URL = "https://www.lseg.com/en/ftse-russell/indices/global-shariah"
SUPPORTED_SEC_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A"}
TRUSTED_SEARCH_DOMAINS = frozenset(
    {
        "sec.gov",
        "data.sec.gov",
        "lseg.com",
        "ftserussell.com",
        "investor.gov",
        "companieshouse.gov.uk",
        "company-information.service.gov.uk",
        "sedarplus.ca",
        "sedar.com",
        "asx.com.au",
        "hkex.com.hk",
        "londonstockexchange.com",
        "euronext.com",
        "sgx.com",
        "edinet-fsa.go.jp",
        "asic.gov.au",
    }
)


class _SearchResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[tuple[str, str]] = []
        self._link: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "a" and "result__a" in (attributes.get("class") or ""):
            href = attributes.get("href")
            if href:
                parsed = urlparse(href)
                self._link = unquote(parse_qs(parsed.query).get("uddg", [href])[0])
            self._text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._link:
            title = " ".join(self._text).strip()
            if title:
                self.results.append((self._link, title))
            self._link = None

    def handle_data(self, data: str) -> None:
        if self._link:
            self._text.append(" ".join(data.split()))


class TrustedWebSearchProvider:
    """Search public pages, retaining only explicitly trusted source domains."""

    def __init__(
        self,
        *,
        fetcher: PublicDocumentFetcher | None = None,
        trusted_domains: Iterable[str] = TRUSTED_SEARCH_DOMAINS,
        timeout: float = 10,
        max_results: int = 2,
    ) -> None:
        self.fetcher = fetcher or PublicDocumentFetcher(timeout=timeout)
        self.trusted_domains = frozenset(domain.lower() for domain in trusted_domains)
        self.timeout = timeout
        self.max_results = max_results

    def search(self, query: str) -> tuple[Document, ...]:
        if not query.strip():
            raise ValueError("web search query must not be empty")
        request = Request(
            f"https://html.duckduckgo.com/html/?q={quote_plus(query)}",
            headers={"User-Agent": self.fetcher.user_agent},
        )
        with urlopen(request, timeout=self.timeout) as response:
            html = response.read().decode("utf-8", errors="replace")
        parser = _SearchResultParser()
        parser.feed(html)
        documents: list[Document] = []
        for url, title in parser.results:
            if not self._is_trusted(url):
                continue
            try:
                documents.append(self.fetcher.fetch(url))
            except (OSError, ValueError):
                continue
            if len(documents) >= self.max_results:
                break
        return tuple(documents)

    def _is_trusted(self, url: str) -> bool:
        hostname = (urlparse(url).hostname or "").lower().removeprefix("www.")
        return any(
            hostname == domain or hostname.endswith(f".{domain}")
            for domain in self.trusted_domains
        )


class GlobalIssuerDocumentProvider:
    """Find official non-US issuer pages when a local filing API is unavailable."""

    SEARCH_DOMAINS = (
        "companieshouse.gov.uk",
        "sedarplus.ca",
        "asx.com.au",
        "hkex.com.hk",
        "londonstockexchange.com",
        "euronext.com",
        "sgx.com",
        "edinet-fsa.go.jp",
        "asic.gov.au",
    )

    def __init__(
        self,
        *,
        search_provider: TrustedWebSearchProvider | None = None,
        max_documents: int = 3,
    ) -> None:
        self.search_provider = search_provider or TrustedWebSearchProvider(max_results=1)
        self.max_documents = max_documents

    def collect(self, stock: Stock) -> tuple[Document, ...]:
        identity = f'"{stock.name or stock.ticker}" {stock.ticker}'
        documents: list[Document] = []
        for domain in self.SEARCH_DOMAINS:
            query = f"{identity} annual report financial statements site:{domain}"
            documents.extend(self.search_provider.search(query))
            if len(documents) >= self.max_documents:
                break
        unique = {}
        for document in documents:
            unique.setdefault(document.url, document)
        if not unique:
            raise LookupError(
                f"no trusted non-US issuer documents found for {stock.display_name}; "
                "provide a jurisdiction-specific filing source"
            )
        return tuple(unique.values())[: self.max_documents]


class SecEdgarDocumentProvider:
    """Find the latest SEC annual filing for a ticker and fetch its primary document."""

    supported_sec_forms = SUPPORTED_SEC_FORMS

    def __init__(
        self,
        *,
        user_agent: str | None = None,
        timeout: float = 15,
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
        debt = self._normalised_debt(facts)
        assets = self._latest_observation(facts.get("Assets"))
        if debt:
            value, unit, period = debt
            lines.append(
                f"Debt (normalised current + non-current): {value:,} {unit} ({period})"
            )
        else:
            lines.append("Debt (normalised current + non-current): unavailable")
        if debt and assets and assets[0]:
            ratio = debt[0] / assets[0]
            lines.append(
                f"Debt / total assets (deterministic calculation): {ratio:.6f} "
                f"({ratio:.2%}) using debt {debt[0]:,} and assets {assets[0]:,} "
                f"for reporting period {debt[2]}"
            )
        lines.append(
            "These reported facts are source data only; ratios and Shariah conclusions "
            "must be calculated and reviewed against the selected methodology."
        )
        return Document(
            url=SEC_FACTS_URL.format(cik=cik),
            title=f"{issuer_name} SEC Company Facts",
            text="\n".join(lines),
        )

    @classmethod
    def _normalised_debt(cls, facts: dict) -> tuple[float, str, str] | None:
        total_tags = (
            "LongTermDebtAndFinanceLeaseObligations",
        )
        for tag in total_tags:
            observation = cls._latest_observation(facts.get(tag))
            if observation:
                return observation
        current = cls._latest_observation(
            facts.get("LongTermDebtAndFinanceLeaseObligationsCurrent")
            or facts.get("LongTermDebtCurrent")
        )
        noncurrent = cls._latest_observation(facts.get("LongTermDebtNoncurrent"))
        if not current or not noncurrent or current[2] != noncurrent[2]:
            return None
        if current[1] != noncurrent[1]:
            return None
        return current[0] + noncurrent[0], current[1], current[2]

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
        global_provider: GlobalIssuerDocumentProvider | None = None,
        public_fetcher: PublicDocumentFetcher | None = None,
    ) -> None:
        self.sec_provider = sec_provider or SecEdgarDocumentProvider()
        self.global_provider = global_provider or GlobalIssuerDocumentProvider()
        self.public_fetcher = public_fetcher or PublicDocumentFetcher()

    def collect(self, stock: Stock) -> tuple[Document, ...]:
        try:
            documents = list(self.sec_provider.collect(stock))
            documents.append(self.sec_provider.collect_fundamentals(stock))
        except (LookupError, OSError, ValueError) as sec_error:
            try:
                documents = list(self.global_provider.collect(stock))
                documents.append(
                    Document(
                        url="https://www.gleif.org/en/lei-data/gleif-api",
                        title="GLEIF identity and source limitation note",
                        text=(
                            "SEC coverage was unavailable for this issuer. GLEIF provides "
                            "global legal-entity identity data, but it is not a financial "
                            "filing source. Jurisdiction-specific filing data must be "
                            "verified from the collected official issuer or registry pages."
                        ),
                    )
                )
            except LookupError as global_error:
                raise LookupError(
                    f"could not collect official documents for {stock.display_name}: "
                    f"SEC unavailable ({sec_error}); global fallback unavailable ({global_error})"
                ) from global_error
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
