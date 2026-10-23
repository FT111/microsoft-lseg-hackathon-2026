"""Data contracts shared by document providers, analysers, and UI clients."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ScreenStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_REVIEW = "NEEDS REVIEW"


@dataclass(frozen=True)
class Stock:
    """A listed company identified by a ticker and optional exchange."""

    ticker: str
    name: str | None = None
    exchange: str | None = None

    def __post_init__(self) -> None:
        if not self.ticker.strip():
            raise ValueError("ticker must not be empty")

    @property
    def display_name(self) -> str:
        return self.name or self.ticker


@dataclass(frozen=True)
class Document:
    """Untrusted public source text supplied to the analyser."""

    url: str
    title: str
    text: str
    published_at: str | None = None

    def __post_init__(self) -> None:
        if not self.url.strip() or not self.text.strip():
            raise ValueError("documents require a URL and non-empty text")


@dataclass(frozen=True)
class Evidence:
    """A claim tied to a source passage, not an unsupported model opinion."""

    source_url: str
    quote: str
    rationale: str


@dataclass(frozen=True)
class ScreenResult:
    name: str
    status: ScreenStatus
    finding: str
    evidence: tuple[Evidence, ...] = ()
    visualisation: dict[str, Any] | None = None


@dataclass(frozen=True)
class AnalysisResult:
    stock: Stock
    overall_status: ScreenStatus
    summary: str
    screens: tuple[ScreenResult, ...]
    limitations: tuple[str, ...] = ()
    raw_response: dict[str, Any] = field(default_factory=dict, repr=False)
