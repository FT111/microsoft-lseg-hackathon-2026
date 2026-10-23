# Copilot instructions - Halal Stock Analyst

Hackathon project (Microsoft x LSEG, 2026): a Streamlit app that screens US stocks
for Shariah compliance, ranks the compliant ones for an individual Muslim investor,
and explains each pick. Read `PLAN.md` first for the idea, timeline and demo script.

## Layout

- `app.py` - the AMANAT website: page 1 checks any company (with the AI investment committee),
  page 2 builds a screened portfolio.
- `shariah/edgar.py` - SEC EDGAR company facts + 10-K "Item 1" text (needs a
  `User-Agent`; set `SEC_USER_AGENT` in `.env`).
- `shariah/methodology.py` - FTSE Yasaar and AAOIFI rules as data (clause, wording, limit, operator, source).
  The two standards are never mixed.
- `shariah/screen.py` - deterministic screens -> PASS / FAIL / NEEDS REVIEW per screen; overall = worst.
- `shariah/pipeline.py` - screens one stock end to end (used by app, warm_cache, committee).
- `shariah/agents/` - Shariah Compliance Checker (gate + audit, highest priority), Bull, Bear, Risk reviewer.
- `shariah/signals.py` - ranking: momentum, volatility, drawdown, compliance headroom;
  risk-appetite weight profiles.
- `shariah/portfolio.py` - allocation, stress test, purification.
- `shariah/prices.py` - Yahoo chart API, Stooq fallback.
- `shariah/yahoo.py` - company search + fundamentals for UK (.L) and other non-SEC companies (yfinance).
- `shariah/llm.py` - Azure OpenAI (organisers' endpoint), key from `OPENAI_API_KEY`.
- `shariah/cache.py` - every network and LLM result is cached in `data_cache/`.

## Rules

- **The AI reads and explains; Python decides numbers.** Don't move ratios, ranking,
  weights or stress tests into the LLM.
- Every verdict must carry its reason and, where the AI was used, a quote from the
  source. When data is missing or borderline, return NEEDS REVIEW - never guess.
- Never commit `.env` or put the API key in code.
- Keep the disclaimer: educational project, not financial advice, not a fatwa.
- Frame outputs as "invest and hold" candidates, not trading signals.
- Run `python -m unittest discover -s tests -t .` and `python smoke_test.py` after changing anything in `shariah/`.
- Only PASS stocks may be ranked or held; `portfolio.build()` enforces it.

## Run

`streamlit run app.py` (after `pip install openai python-dotenv streamlit pandas plotly requests yfinance`).
