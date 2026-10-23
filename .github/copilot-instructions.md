# Copilot instructions - Halal Stock Analyst

Hackathon project (Microsoft x LSEG, 2026): a Streamlit app that screens US stocks
for Shariah compliance, ranks the compliant ones for an individual Muslim investor,
and explains each pick. Read `PLAN.md` first for the idea, timeline and demo script.

## Layout

- `app.py` - Streamlit UI, 5 tabs (Screening, Stock picks, Allocation, Stress test &
  purification, Ask).
- `shariah/edgar.py` - SEC EDGAR company facts + 10-K "Item 1" text (needs a
  `User-Agent`; set `SEC_USER_AGENT` in `.env`).
- `shariah/screen.py` - FTSE Shariah and AAOIFI ratio rules -> PASS / FAIL / REVIEW.
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
  source. When data is missing or borderline, return REVIEW - never guess.
- Never commit `.env` or put the API key in code.
- Keep the disclaimer: educational project, not financial advice, not a fatwa.
- Frame outputs as "invest and hold" candidates, not trading signals.
- Run `python smoke_test.py` after changing anything in `shariah/`.

## Run

`streamlit run app.py` (after `pip install openai python-dotenv streamlit pandas plotly requests yfinance`).
