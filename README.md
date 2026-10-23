# AMANAT - Shariah stock screening with an AI investment committee

Educational hackathon project (Microsoft x LSEG 2026). **Not financial advice. Not a fatwa** -
passing these screens is not a religious ruling or a guarantee of compliance.

Two pages. **Check a company**: search any listed company (UK first) and get Pass / Fail / Needs
review against **one** Shariah standard at a time (FTSE Yasaar or AAOIFI, never mixed), every ratio
against its limit, the annual-report evidence, and a four-agent investment committee led by the
Shariah compliance check. **Build my portfolio**: screen a stock list, rank only the companies that
pass every screen, split the money (max 10% each), stress-test past bad years and work out
purification. Team notes: `HANDOFF.md`.

## Setup

```bash
cp .env.example .env          # add OPENAI_API_KEY (team key) and SEC_USER_AGENT (your name + email)
uv sync                       # or: pip install openai python-dotenv streamlit pandas plotly requests yfinance
uv run python warm_cache.py   # first run: downloads SEC + Yahoo data, prices, 10-K text and AI readings (~8 min)
uv run streamlit run app.py
```

Everything downloaded or produced by the AI is cached in `data_cache/`, so after `warm_cache.py`
the app runs offline. `warm_cache.py --committee MSFT JPM AAPL` also pre-runs the committee.

### Pitch deck (7 slides, ~8 minutes)

```bash
uv run streamlit run presentation.py      # or: streamlit run presentation.py
```

Click the deck once, then use **← / →** (or Space / PageUp / PageDown), **1-7** to jump, **N** for
speaker notes (with speaking time per slide), **T** for the 8:00 timer. The full script is also in
an expander under the deck. For projecting, use **Download standalone deck (.html)**, open the
file in a browser and press **F** for full screen; `deck.html#4` opens straight on slide 4.

- The Microsoft and JPMorgan figures are **demo data typed from the annual reports** (not fetched
  live). `shariah/deck_demo.py` calculates every percentage and takes each limit from
  `methodology.py`. It also checks each figure against the cached SEC XBRL data and shows
  "SEC match" or "not cross-checked".
- The Microsoft ratios are **preliminary**: the input definitions are not verified, and the activity
  and income screens are not part of the demo, so the slide shows overall NEEDS REVIEW.
- JPMorgan's 52.31% (net interest income / total net revenue) is an **illustrative indicator, not
  the FTSE non-compliant-income ratio**. The business-activity outcome comes from the real screening
  engine (`pipeline.screen_one`, rule 4.3.1), using evidence from the 10-K, not from the ticker.

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

- US companies: SEC EDGAR XBRL figures, whatever companies tagged; untagged items are NEEDS REVIEW,
  not zero. UK / non-SEC companies: Yahoo Finance's copy of the accounts (a vendor copy, not the
  filing), with lease liabilities excluded from debt like the SEC path.
- US business activities come from the latest 10-K: Item 1 (first 12,000 characters) plus every
  sentence in the filing that mentions a screened activity. Revenue shares are often not disclosed,
  so retailers and conglomerates frequently land in NEEDS REVIEW.
- UK business activities come from the industry classification only. That can exclude a company
  (banks, brewers, tobacco, gambling, hotels) but can never clear one, so every other UK company is
  NEEDS REVIEW until an annual-report source is wired in for the AI reading.
- "Cash and interest-bearing items" uses cash + short-term investments; long-term interest-bearing
  securities are shown separately and send a screen to NEEDS REVIEW if they would break the limit.
- FTSE's quarter-on-quarter monitoring rule needs history the app does not check.
- AAOIFI rules were verified through an exchange's published guide, not the AAOIFI text itself.
- Stress tests use past calendar years; they are not forecasts.

## Layout

- `app.py` - the AMANAT website (check a company + committee; build a portfolio).
- `analyser_test.py`, `amanat/` - the team's separate LLM-led analyser prototype and its test UI (unchanged).
- `shariah/methodology.py` - the two standards as data, with sources.
- `shariah/edgar.py`, `yahoo.py`, `prices.py`, `cache.py` - US (SEC) and UK (Yahoo) data, prices, offline cache.
- `shariah/screen.py`, `pipeline.py` - deterministic screening.
- `shariah/llm.py` - Azure OpenAI calls (key from `OPENAI_API_KEY`, never in code).
- `shariah/signals.py`, `portfolio.py` - ranking, allocation, stress test, purification.
- `shariah/agents/` - evidence pack, Shariah Compliance Checker, analysts, committee.
- `tests/` - unit tests on fictional data.
