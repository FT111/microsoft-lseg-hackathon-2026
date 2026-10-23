# AMANAT - handoff (2026-10-23)

**Start here.** What AMANAT is, how to run it, where things live, what was decided
and what's next. The full conversation that produced this is in
[`docs/claude-session-2026-10-23.md`](docs/claude-session-2026-10-23.md).

> Educational hackathon project (Microsoft x LSEG 2026). Not financial advice. Not a fatwa.

## Update (23 Oct, later): verified screens + AI investment committee merged in

Branch `shariah-agent-committee` was merged into `main`. The website is still Chuen's two-page
AMANAT app, now driven by a verified screening engine and with the "AI analyst review"
placeholder replaced by a four-agent **investment committee**:

1. **Shariah compliance check** (Python; decides first, audits last, can only exclude).
2. **The case for** and 3. **the case against** (AI, independent; every claim cites a numbered fact).
4. **Risk check** (AI; weighs both, may add a flag, cannot change any number or status).
5. **Shariah audit** (rules + AI) removes statements with forbidden wording ("halal", "certified"),
   prohibited instruments (margin, shorting, derivatives, interest products) or soft-pedalled risk.

Engine changes (all in `shariah/`): `methodology.py` holds FTSE Yasaar (Ground Rules v4.6, Feb 2026)
and AAOIFI SS 21 (via the MSX guide) as separate rule sets with clause numbers and quoted wording;
the status is `NEEDS REVIEW` everywhere; missing figures are never 0; interest income counts in the
5% screen; the full excluded-activity lists are in; every AI quote is checked word-for-word against
the 10-K; only `PASS` stocks can be ranked or held (`portfolio.build()` refuses anything else).

**Known gap for UK:** business activity for non-SEC companies still comes from the Yahoo industry
code, which can *exclude* (HSBC, Diageo, BAT fail) but can never *clear* a company, so every UK
company that isn't excluded is `NEEDS REVIEW` and the UK portfolio page has nothing to hold.
Fix = give the AI a UK annual-report source (company IR PDF / Companies House) and run
`llm.business_screen` on it, exactly as the US path does. Until then, demo the portfolio page on
the US market.

Data-finder: the SEC lookups now cover bank-style tags (JPMorgan / BofA debt and loans), and when a
required figure is still untagged the AI searches the filing text for it (quote and number verified
in Python, labelled "AI-found", can never make a screen PASS on its own).

Frederick's `amanat/` analyser and `analyser_test.py` are unchanged and still separate.

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
| 🔎 **Check a company** (home) | Search by name or ticker (London listings first). Report: verdict, plain-English reason, each financial ratio vs its limit, business-activity evidence, 5-year price chart, sources & limitations. "AI investment committee" card: Shariah gate first, then bull/bear/risk analysts and a Shariah audit. |
| 📊 **Build my portfolio** | Screens a stock list (UK FTSE 100 sample by default, or US), ranks passes for the investor's risk appetite, allocates (max 10% each), stress-tests 2008/2020/2022, purification. Tabs: Shariah check, Stock picks, Your portfolio, Bad years & charity, Ask the analyst. |

No sidebar: everything sits on the page. Under the AMANAT top bar there is a TradingView-style ticker
tape (watchlist + the market's stock list, each with its last close, daily change and a green/red/amber dot
for its Shariah status), then the page switch, then a collapsed **⚙️ Settings** expander in three columns:
Objective (goal - Hajj/Umrah, home, education, wealth, endowment - sets the default horizon and risk
profile), Market and amount (UK £ / US $, amount, number of holdings, share in Shariah-screened equities;
the rest is non-interest cash), Screening (FTSE Yasaar or AAOIFI from `shariah/methodology.py`, "Also
exclude" fossil fuels / mining as a personal value - flagged in reports and left out of the portfolio, never
a Shariah result -, the AI toggle and the stock list). The company report adds a watchlist star and a
candlestick + volume chart with 1M-5Y ranges (`prices.ohlc`); the "AI analyst review" placeholder is now the
four-agent investment committee (`render_committee`, `shariah/agents/`).

## Where things live

| Path | What |
|---|---|
| `app.py` | **The website.** One file, both pages. |
| `shariah/yahoo.py` | UK / non-US data: company search + fundamentals via `yfinance`, currency-corrected market cap. |
| `shariah/edgar.py` | US data: SEC EDGAR filings (XBRL numbers + 10-K business text). |
| `shariah/methodology.py` | The two standards as data (clause, quoted rule, limit, operator, source). Never mixed. |
| `shariah/screen.py` | Deterministic screens -> PASS / FAIL / NEEDS REVIEW per screen; industry/SIC fallbacks; quote check. |
| `shariah/pipeline.py` | Screens one stock end to end (SEC path with AI reading, or Yahoo path). |
| `shariah/agents/` | Shariah compliance checker (gate + audit), bull, bear, risk reviewer, evidence pack, committee. |
| `shariah/signals.py`, `portfolio.py`, `prices.py`, `llm.py` | Ranking, allocation/stress/purification, price history, Azure OpenAI. |
| `shariah/universe.py` | `UK_UNIVERSE` (36 FTSE 100 names) and `UNIVERSE` (32 US). |
| `amanat/` | **Frederick's AI analyser** (reads filings, returns per-screen verdicts with quotes). |
| `analyser_test.py` | Frederick's test page for his analyser (`streamlit run analyser_test.py`). Not the website. |
| `tests/` | Unit tests on fictional data: `python -m unittest discover -s tests -t .` |
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

1. **UK annual-report source for the AI business screen** (see the update above) - the one thing that
   stops UK companies passing.
2. ~~Pick one standard~~ - done differently: both kept, applied strictly separately (`methodology.py`).
3. ~~Verify thresholds~~ - done against FTSE Yasaar Ground Rules v4.6; AAOIFI via the MSX guide.
4. ~~Tesco debt~~ - UK debt now = Long Term Debt + Current Debt (leases excluded), like the SEC path.
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
