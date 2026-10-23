# Halal Stock Analyst - Shariah screener with an AI investment committee

Educational hackathon project (Microsoft x LSEG 2026). **Not financial advice. Not a fatwa** -
passing these screens is not a religious ruling or a guarantee of compliance.

The app screens 32 US companies against **one** Shariah standard at a time (FTSE Yasaar or
AAOIFI, never mixed), ranks only the companies that pass every screen, splits an investor's
money across them, stress-tests the result and works out purification. A four-agent committee
then explains any single stock, with the Shariah Compliance Checker in charge.

## Setup

```bash
cp .env.example .env          # add OPENAI_API_KEY (team key) and SEC_USER_AGENT (your name + email)
uv sync                       # or: pip install openai python-dotenv streamlit pandas plotly requests
uv run python warm_cache.py   # first run: downloads SEC data, prices, 10-K text and AI readings (~5 min)
uv run streamlit run app.py
```

Everything downloaded or produced by the AI is cached in `data_cache/`, so after `warm_cache.py`
the app runs offline. `warm_cache.py --committee MSFT JPM AAPL` also pre-runs the committee.

Tests (fictional data, no network): `uv run python -m unittest discover -s tests -t .`
Real-data check: `uv run python smoke_test.py`

## Results: PASS / FAIL / NEEDS REVIEW

Every screen gets one of three statuses; the company's overall status is the worst of them.

- **PASS** - the rule was checked with the data available and is met.
- **FAIL** - the rule is broken, on calculated figures or a verified 10-K quote.
- **NEEDS REVIEW** - the rule could not be checked: a figure is missing or stale, a quote could not
  be found in the filing, an AI estimate is low-confidence, or a value sits in FTSE's monitoring band.
  We flag rather than guess.

Only PASS companies are ranked or held - `portfolio.build()` refuses anything else. The only
non-equity holding is non-interest-bearing cash.

## Methodologies (checked 23 Oct 2026)

| | FTSE Yasaar | AAOIFI SS 21 |
|---|---|---|
| Source | [Ground Rules v4.6, Feb 2026](https://www.lseg.com/content/dam/ftse-russell/en_us/documents/ground-rules/ftse-yasaar-global-equity-shariah-index-series-ground-rules.pdf), rules 4.3.1-4.4 | Clause 3/4 as published in the [MSX Shariah Services Guide](https://www.msx.om/MSMDOCS/downloads/en_1701852937802_MSX%20Shariah%20%20Index%20rulebook%20E%20Updated.pdf) (official AAOIFI text is subscription-only) |
| Business activities | non-permitted income <= 5% of revenue: conventional finance & insurance, alcohol (whole chain incl. retail), pork & non-halal food, entertainment (casinos, gambling, cinema, music, pornography, hotels), tobacco (incl. vapes) & cannabis, weapons & defence | prohibited revenue <= 5%: conventional finance & insurance, alcohol & tobacco, pork, gambling, cinema, music, adult entertainment, hotels, arms & defence |
| Debt | < 33.333% of total assets | <= 30% of 12-month average market value |
| Cash & interest-bearing items | < 33.333% of total assets | <= 30% of 12-month average market value |
| Receivables + cash | < 50% of total assets | - |
| Interest + non-compliant income | <= 5% of total revenue | <= 5% of total revenue |
| Purification | dividends x non-compliant share (4.4) | non-compliant income per share x shares held (3/4/6) |

All rules, with clause numbers and quoted wording, live in `shariah/methodology.py`.

## How it works

```
SEC XBRL financials ─► edgar.py ─► screen.py (Python ratios) ──────────┐
SEC 10-K text ───────► llm.py (AI reads activities; every quote        ├─► PASS / FAIL / NEEDS REVIEW
                       checked word-for-word in Python) ───────────────┘          │
                                                                                  ▼
                        signals.py (rank PASS only) ─► portfolio.py (allocate, stress test, purification)
                                                                                  │
                        agents/: Shariah gate ─► Bull + Bear ─► Risk reviewer ─► Shariah audit
```

**The AI reads and explains; Python decides every number and status.**

### The investment committee (`shariah/agents/`)

1. **Shariah Compliance Checker (highest priority)** - a *gate* before anyone argues and an
   *audit* afterwards. A FAIL stops the committee. NEEDS REVIEW makes everything conditional. The
   audit removes statements with forbidden wording ("halal", "certified"...), prohibited instruments
   (margin, short selling, derivatives, interest-bearing products), overclaims or soft-pedalled
   compliance risk. Nothing downstream can change its status.
2. **Bull analyst** and 3. **Bear analyst** - run in parallel, independently, on a numbered
   evidence pack. Every point must cite fact IDs; any number not found in the cited facts is removed.
4. **Risk reviewer** - weighs both cases, names unsupported claims and key risks, may add a flag.
   It cannot change a score, weight or status.

Design notes: `docs/agent-architecture.md`.

## Limitations

- US companies only (SEC EDGAR). Figures are whatever companies tagged in XBRL; untagged items are
  NEEDS REVIEW, not zero.
- Business activities come from the latest 10-K: Item 1 (first 12,000 characters) plus every
  sentence in the filing that mentions a screened activity. Revenue shares are often not disclosed,
  so retailers and conglomerates frequently land in NEEDS REVIEW.
- "Cash and interest-bearing items" uses cash + short-term investments; long-term interest-bearing
  securities are shown separately and send a screen to NEEDS REVIEW if they would break the limit.
- FTSE's quarter-on-quarter monitoring rule needs history the app does not check.
- AAOIFI rules were verified through an exchange's published guide, not the AAOIFI text itself.
- Stress tests use past calendar years; they are not forecasts.

## Layout

- `app.py` - Streamlit UI (screening, committee, picks, portfolio, stress test & purification, Ask, methodology).
- `amanat_app.py`, `amanat/` - the team's separate LLM-led analyser prototype and its test UI (unchanged).
- `shariah/methodology.py` - the two standards as data, with sources.
- `shariah/edgar.py`, `prices.py`, `cache.py` - data retrieval and the offline cache.
- `shariah/screen.py`, `pipeline.py` - deterministic screening.
- `shariah/llm.py` - Azure OpenAI calls (key from `OPENAI_API_KEY`, never in code).
- `shariah/signals.py`, `portfolio.py` - ranking, allocation, stress test, purification.
- `shariah/agents/` - evidence pack, Shariah Compliance Checker, analysts, committee.
- `tests/` - unit tests on fictional data.
