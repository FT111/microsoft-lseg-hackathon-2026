# AMANAT - handoff (2026-10-23)

**Start here.** What AMANAT is, how to run it, where things live, what was decided
and what's next. The full conversation that produced this is in
[`docs/claude-session-2026-10-23.md`](docs/claude-session-2026-10-23.md).

> Educational hackathon project (Microsoft x LSEG 2026). Not financial advice. Not a fatwa.

## What AMANAT is

A Shariah stock-screening website for everyday Muslim investors, **UK first**.
Search any listed company and get Pass / Fail / Needs review against the Shariah
rules, with every ratio shown against its limit and the evidence behind the
answer. A second page builds a screened portfolio: ranking, allocation, a
"bad year" stress test in money, and dividend purification (what to give to charity).

**Rule we keep:** the AI reads and explains; plain Python calculates every number.

## See the website

```bash
git pull
pip install openai python-dotenv streamlit pandas plotly requests yfinance
copy .env.example .env        # macOS/Linux: cp - then put the team key in OPENAI_API_KEY
python warm_cache.py          # optional, first time: pre-loads US + UK data (a few minutes)
streamlit run app.py          # opens http://localhost:8501
```

- **On the same wifi as someone running it:** Streamlit prints a "Network URL" - teammates can open that.
- **Public link (not set up yet):** deploy on [Streamlit Community Cloud](https://share.streamlit.io) -
  connect this repo, main file `app.py`, and put `OPENAI_API_KEY` and `SEC_USER_AGENT` in the app's
  Secrets. Never commit `.env`.

## What's on the site

| Page | What it does |
|---|---|
| 🔎 **Check a company** (home) | Search by name or ticker (London listings first). Report: verdict, plain-English reason, each financial ratio vs its limit, business-activity evidence, 5-year price chart, sources & limitations. "AI analyst review" card is a placeholder for Frederick's analyser. |
| 📊 **Build my portfolio** | Screens a stock list (UK FTSE 100 sample by default, or US), ranks passes for the investor's risk appetite, allocates (max 10% each), stress-tests 2008/2020/2022, purification. Tabs: Shariah check, Stock picks, Your portfolio, Bad years & charity, Ask the analyst. |

Sidebar: market (UK £ / US $), amount, risk appetite, number of stocks; "More options" has the
standard (FTSE Shariah / AAOIFI), sukuk share and the stock list.

## Where things live

| Path | What |
|---|---|
| `app.py` | **The website.** One file, both pages. |
| `shariah/yahoo.py` | UK / non-US data: company search + fundamentals via `yfinance`, currency-corrected market cap. |
| `shariah/edgar.py` | US data: SEC EDGAR filings (XBRL numbers + 10-K business text). |
| `shariah/screen.py` | FTSE Shariah and AAOIFI ratio rules -> PASS / FAIL / REVIEW; industry rules for business activity. |
| `shariah/signals.py`, `portfolio.py`, `prices.py`, `llm.py` | Ranking, allocation/stress/purification, price history, Azure OpenAI. |
| `shariah/universe.py` | `UK_UNIVERSE` (36 FTSE 100 names) and `UNIVERSE` (32 US). |
| `amanat/` | **Frederick's AI analyser** (reads filings, returns per-screen verdicts with quotes). |
| `analyser_test.py` | Frederick's test page for his analyser (`streamlit run analyser_test.py`). Not the website. |
| `data_cache/` | Every download / AI answer, so the demo runs offline. Not committed yet (27 MB) - commit at feature freeze. |

## Decisions made today (and why)

1. **One website, named AMANAT.** The static "Amanat" mock (fake data, hard-coded demo login) was
   removed; its look (colours, fonts, cards, crescent-shield logo) now styles the real, data-driven app.
   The mock is still in git history (`amanat_mock.py`, commit `78cb707`).
2. **UK data from Yahoo Finance (`yfinance`).** SEC only covers US filers. Yahoo gives UK balance
   sheets, revenue, interest income, sector and **search by company name**. US companies still use
   SEC filings (more traceable).
3. **Currency fix for AAOIFI.** London prices are in pence and many UK firms report in US dollars
   (e.g. BP), so market cap is converted to the reporting currency before ratios are compared.
4. **Business activity for UK companies = industry rule** (banks, insurers, alcohol, tobacco,
   gambling -> fail; defence, property, asset managers -> needs review) until the AI analyser is wired in.
5. **Search is the home page; portfolio is page two** - matches `AGENTS.md` core feature #1.
6. **Frederick's `app.py` (test UI) was kept as `analyser_test.py`** rather than overwritten.

Sanity results (FTSE standard): AstraZeneca, BP pass · Tesco fails on debt (38% vs 33%) · HSBC,
Diageo fail · BAE Systems needs review.

## Next steps (priority order)

1. **Wire Frederick's analyser into the company report** - the placeholder card in `company_report()`
   in `app.py` ("AI analyst review"). It currently only reads SEC filings, so UK companies need a UK
   annual-report source (company IR site / Companies House).
2. **Pick one standard.** `AGENTS.md` says don't mix FTSE Yasaar with AAOIFI, but the sidebar offers both.
3. **Verify thresholds** in `shariah/screen.py` against the official FTSE methodology before the demo.
4. **Tesco check:** Yahoo's "Total Debt" includes leases; FTSE's definition may not - confirm by hand.
5. Sukuk ETF (`SPSK`) is US-listed; find a UK option or keep sukuk off for UK.
6. Commit `data_cache/` at feature freeze so the demo works offline.
7. Optional: public link via Streamlit Community Cloud (above).

## Working together

- `app.py` is the website - **pull before editing and don't replace it wholesale**; that happened once today.
- Add files explicitly (`git add <file>`), never `git add -A`. Never commit `.env`.
- Run `python smoke_test.py` after changing anything in `shariah/`; `python -m pytest tests` for `amanat/`.

## Continue with Claude

A Claude session can't be copied between accounts, but this file plus the transcript gives a
new session the full context:

- **Claude Code:** open this repo and say:
  *"Read HANDOFF.md and docs/claude-session-2026-10-23.md, then continue from the next steps."*
- **claude.ai:** add `HANDOFF.md` and `docs/claude-session-2026-10-23.md` to a Project (or attach
  them to a chat) and say the same.
