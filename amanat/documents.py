"""Small, dependency-free adapter for fetching public HTML documents."""

from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .models import Document


class _TextExtractor(HTMLParser):
    _ignored = {"script", "style", "noscript", "svg"}

    def __init__(self) -> None:
        super().__init__()
        self._ignored_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._ignored:
            self._ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._ignored and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            value = " ".join(data.split())
            if value:
                self.parts.append(value)


class PublicDocumentFetcher:
    """Fetch public HTTP(S) pages while preserving their source URL."""

    def __init__(
        self,
        *,
        timeout: float = 15,
        max_chars: int = 40_000,
        user_agent: str = "Amanat/0.1 (public-document-analysis)",
    ) -> None:
        self.timeout = timeout
        self.max_chars = max_chars
        self.user_agent = user_agent

    def fetch(self, url: str) -> Document:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"unsupported document URL: {url!r}")

        request = Request(
            url,
            headers={"User-Agent": self.user_agent},
        )
        with urlopen(request, timeout=self.timeout) as response:
            payload = response.read(self.max_chars * 4)
            charset = response.headers.get_content_charset() or "utf-8"
            html = payload.decode(charset, errors="replace")

        parser = _TextExtractor()
        parser.feed(html)
        text = " ".join(parser.parts)[: self.max_chars].strip()
        if not text:
            raise ValueError(f"document contained no readable text: {url}")
        return Document(url=url, title=parsed.netloc, text=text)
