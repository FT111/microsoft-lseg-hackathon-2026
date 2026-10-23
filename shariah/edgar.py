"""SEC EDGAR: structured financials (XBRL company facts) and the 10-K business
section. Free, no key. SEC requires a User-Agent with a contact email."""
import os
import re
import time

import requests
from dotenv import load_dotenv

from .cache import cached

load_dotenv()
# SEC asks for a real contact: set SEC_USER_AGENT="Your Name your@email" in .env
HEADERS = {"User-Agent": os.getenv("SEC_USER_AGENT", "LSEG hackathon team research-contact@example.org")}
_last_call = [0.0]


def _get(url: str) -> requests.Response:
    # SEC allows ~10 requests/second; stay well under.
    wait = 0.15 - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    _last_call[0] = time.time()
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r


def ticker_to_cik() -> dict:
    def produce():
        data = _get("https://www.sec.gov/files/company_tickers.json").json()
        return {row["ticker"]: str(row["cik_str"]).zfill(10) for row in data.values()}
    return cached("edgar_tickers", produce)


def company_facts(ticker: str) -> dict:
    cik = ticker_to_cik()[ticker.upper()]
    def produce():
        facts = _get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json").json()
        # keep only what we use - the full file is several MB
        keep = {}
        for ns in ("us-gaap", "dei"):
            for name, body in facts.get("facts", {}).get(ns, {}).items():
                if name in CONCEPTS_USED:
                    keep[name] = body.get("units", {})
        return {"cik": cik, "name": facts.get("entityName"), "facts": keep}
    return cached(f"edgar_facts_{ticker}", produce)


def submissions(ticker: str) -> dict:
    cik = ticker_to_cik()[ticker.upper()]
    def produce():
        s = _get(f"https://data.sec.gov/submissions/CIK{cik}.json").json()
        recent = s.get("filings", {}).get("recent", {})
        tenk = None
        for form, acc, doc, date in zip(recent.get("form", []), recent.get("accessionNumber", []),
                                        recent.get("primaryDocument", []), recent.get("filingDate", [])):
            if form == "10-K":
                tenk = {"accession": acc, "doc": doc, "date": date,
                        "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/{doc}"}
                break
        return {"name": s.get("name"), "sic": s.get("sic"), "sicDescription": s.get("sicDescription"),
                "latest_10k": tenk}
    return cached(f"edgar_subs_{ticker}", produce)


def business_section(ticker: str, max_chars: int = 12000) -> dict:
    """Text of 10-K 'Item 1. Business' (best effort), plus the source URL."""
    sub = submissions(ticker)
    tenk = sub.get("latest_10k")
    if not tenk:
        return {"text": "", "url": None}
    def produce():
        html = _get(tenk["url"]).text
        text = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
        text = re.sub(r"(?s)<[^>]+>", " ", text)
        text = re.sub(r"&#160;|&nbsp;", " ", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"\s+", " ", text)
        # find the real Item 1 (skip the table of contents: take the last match
        # that is followed by a lot of text before Item 1A)
        starts = [m.start() for m in re.finditer(r"(?i)item\s*1\.?\s*business", text)]
        body = ""
        for s in starts:
            end = re.search(r"(?i)item\s*1a\.?\s*risk\s*factors", text[s + 200:])
            chunk = text[s: s + 200 + end.start()] if end else text[s: s + max_chars]
            if len(chunk) > len(body):
                body = chunk
        return {"text": (body or text[:max_chars])[:max_chars], "url": tenk["url"], "date": tenk["date"]}
    return cached(f"edgar_10k_item1_{ticker}", produce)


# ---------- picking values out of XBRL ----------

DEBT = ["LongTermDebt", "LongTermDebtNoncurrent", "LongTermDebtCurrent", "DebtCurrent",
        "ShortTermBorrowings", "CommercialPaper", "LongTermDebtAndCapitalLeaseObligations",
        "DebtLongtermAndShorttermCombinedAmount"]
CASH = ["CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "ShortTermInvestments", "MarketableSecuritiesCurrent", "AvailableForSaleSecuritiesDebtSecuritiesCurrent"]
RECEIVABLES = ["AccountsReceivableNetCurrent", "ReceivablesNetCurrent"]
REVENUE = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet",
           "RevenueFromContractWithCustomerIncludingAssessedTax"]
INTEREST_INCOME = ["InvestmentIncomeInterest", "InterestIncomeOther", "InvestmentIncomeInterestAndDividend",
                   "InterestAndOtherIncome"]
DIVIDENDS = ["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"]
CONCEPTS_USED = set(DEBT + CASH + RECEIVABLES + REVENUE + INTEREST_INCOME + DIVIDENDS +
                    ["Assets", "EntityCommonStockSharesOutstanding"])


def _latest(facts: dict, concept: str, duration: bool):
    """Latest reported value. Balance-sheet items (instants): the most recent 10-K or
    10-Q. Income items (durations): the most recent ~12-month period.
    Returns (value, period_end) or None."""
    units = facts["facts"].get(concept)
    if not units:
        return None
    rows = units.get("USD") or units.get("shares") or next(iter(units.values()))
    best = None
    for r in rows:
        if r.get("form") not in ("10-K", "10-K/A", "10-Q", "10-Q/A"):
            continue
        if duration:
            if "start" not in r:
                continue
            days = (_d(r["end"]) - _d(r["start"]))
            if not 300 <= days <= 380:
                continue
        if best is None or r["end"] > best["end"] or (r["end"] == best["end"] and r.get("filed", "") > best.get("filed", "")):
            best = r
    return (best["val"], best["end"]) if best else None


def _d(s: str) -> int:
    y, m, d = map(int, s.split("-"))
    return y * 365 + m * 30 + d


def _first(facts, concepts, duration=False):
    for c in concepts:
        v = _latest(facts, c, duration)
        if v:
            return v[0], c, v[1]
    return None, None, None


def financials(ticker: str) -> dict:
    """Numbers the Shariah ratio screens need, each with the XBRL concept it came from."""
    f = company_facts(ticker)
    out = {"ticker": ticker, "name": f["name"], "sources": {}}

    assets, c, end = _first(f, ["Assets"])
    out["total_assets"], out["sources"]["total_assets"], out["period_end"] = assets, c, end

    # Debt: total long-term (incl. current portion) if reported, else parts; plus short-term borrowings.
    lt, lt_c, _ = _first(f, ["LongTermDebt", "DebtLongtermAndShorttermCombinedAmount",
                              "LongTermDebtAndCapitalLeaseObligations"])
    if lt is None:
        nc, nc_c, _ = _first(f, ["LongTermDebtNoncurrent"])
        cur, cur_c, _ = _first(f, ["LongTermDebtCurrent", "DebtCurrent"])
        lt = (nc or 0) + (cur or 0)
        lt_c = "+".join(x for x in (nc_c, cur_c) if x) or None
    st, st_c, _ = _first(f, ["ShortTermBorrowings", "CommercialPaper"])
    out["total_debt"] = (lt or 0) + (st or 0)
    out["sources"]["total_debt"] = "+".join(x for x in (lt_c, st_c) if x) or "not reported"

    cash, cash_c, _ = _first(f, ["CashAndCashEquivalentsAtCarryingValue",
                                  "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"])
    sti, sti_c, _ = _first(f, ["ShortTermInvestments", "MarketableSecuritiesCurrent",
                                "AvailableForSaleSecuritiesDebtSecuritiesCurrent"])
    out["cash_and_interest_bearing"] = (cash or 0) + (sti or 0)
    out["sources"]["cash_and_interest_bearing"] = "+".join(x for x in (cash_c, sti_c) if x) or "not reported"

    rec, rec_c, _ = _first(f, RECEIVABLES)
    out["receivables"], out["sources"]["receivables"] = rec or 0, rec_c or "not reported"

    rev, rev_c, _ = _first(f, REVENUE, duration=True)
    out["revenue"], out["sources"]["revenue"] = rev, rev_c

    ii, ii_c, _ = _first(f, INTEREST_INCOME, duration=True)
    out["interest_income"], out["sources"]["interest_income"] = ii or 0, ii_c or "not reported"

    dv, dv_c, _ = _first(f, DIVIDENDS, duration=True)
    out["dividends_paid"], out["sources"]["dividends_paid"] = dv or 0, dv_c or "not reported"

    sh, sh_c, _ = _first(f, ["EntityCommonStockSharesOutstanding"])
    out["shares_outstanding"], out["sources"]["shares_outstanding"] = sh, sh_c
    return out
