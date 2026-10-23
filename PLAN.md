# Halal Stock Analyst - plan, timeline and sketch

**One sentence:** an AI analyst for everyday Muslim investors with $100,000 - it
screens stocks for Shariah compliance with the evidence for every verdict, ranks
the compliant ones, explains each pick, and shows what a bad year would do to
your money.

> Educational hackathon project. Not financial advice. Not a fatwa - the output is
> the evidence a Shariah board or scholar would review, not a ruling.

## The client

An individual Muslim investor (persona: *Aisha, 28, inherited $100k, wants halal
growth, doesn't have time to read 50 annual reports*). Needs:
- only Shariah-compliant companies (no interest-heavy debt, no prohibited business),
- a short list of good candidates for their risk appetite,
- reasons they can understand, and what to give to charity (purification).

Framing: **invest and hold**, not short-term trading - many scholars discourage
speculation, and short selling / margin are not permitted.

## How it works

```
 SEC EDGAR financials ──► ratio screen (Python) ──┐
                                                  ├─► PASS / FAIL / REVIEW ──► rank (Python) ──► allocate ──► stress test
 SEC 10-K "Item 1" text ──► business screen (AI) ─┘     + evidence quote       momentum, risk,     top N      2008/2020/2022
                                                                               drawdown, headroom            + purification
                       AI analyst note per stock · AI answers questions ONLY from these results
```

- **AI reads, maths decides.** The AI reads 10-K text (share of non-compliant
  revenue, with a quote) and writes explanations. Ratios, ranking, weights and
  stress tests are plain Python - repeatable and explainable.
- **Two standards, one toggle:** FTSE Shariah (LSEG's own index; ratios vs total
  assets) and AAOIFI (ratios vs market cap).
- **Compliance headroom:** how far a stock sits below the nearest Shariah limit.
  Near a limit = risk of having to sell. Ordinary screeners ignore this.
- **REVIEW, not guess:** missing data or a borderline AI estimate goes to a person.

## Screens

| Tab | Shows |
|---|---|
| 1 Screening | PASS / FAIL / REVIEW for 32 US stocks, ratios, reasons, 10-K quote |
| 2 Stock picks | 0-100 score, signal, bar chart; AI analyst note for any stock |
| 3 Allocation | The $ split across the top picks (max 10% each), sukuk optional |
| 4 Stress test & purification | 2008 / 2020 / 2022 in dollars; dividends to donate |
| 5 Ask | Preset questions + chat, answered only from the app's results |

Sidebar: amount, standard (FTSE / AAOIFI), risk appetite (Cautious / Balanced /
Adventurous - changes ranking weights), number of stocks.

## Run it

```
copy .env.example .env      # then put the team key in OPENAI_API_KEY
pip install openai python-dotenv streamlit pandas plotly requests yfinance
python warm_cache.py        # first time only: downloads + AI screens everything (~3 min)
streamlit run app.py
```

`data_cache/` holds every download and AI answer, so after `warm_cache.py` the
app runs offline.

## Timeline (today)

| Time | Goal | Who |
|---|---|---|
| 13:15-13:45 | Everyone pulls and runs the app | all |
| 13:45-14:45 | "Your plan" summary at the top | Chuen |
| | PASS list vs SPUS / HLAL holdings -> agreement % | Saba |
| | Fix META interest-income ratio; INTC / XOM 10-K text | Frederick |
| | Persona, slides skeleton, demo script | Benjamin |
| 14:45-15:30 | Polish analyst notes; optional news alert | Chuen + Frederick |
| 15:30-16:00 | Theme, captions, backup screen recording | all |
| **16:00** | **FEATURE FREEZE** - commit `data_cache/` | |
| 16:00-17:30 | Rehearse the 8-minute demo out loud twice | all |

## 8-minute demo

1. **(1 min)** Aisha: $100k, wants halal growth, no time to read annual reports.
2. **(2 min)** Screening: a bank and a defence company fail with quotes; Apple goes
   to REVIEW (AI unsure, near the 5% limit) - "we flag rather than guess".
   Toggle FTSE -> AAOIFI.
3. **(2 min)** Stock picks: switch Cautious -> Adventurous, the ranking changes.
   Open one analyst note. Point at a stock flagged "near a Shariah limit".
4. **(1 min)** Allocation + stress test: "in a 2008-type year, $100k -> ~$76k".
   Purification: "give $X of your dividends to charity".
5. **(1 min)** Ask: "Why is Merck a strong candidate?"
6. **(1 min)** Why trust it: AI reads, maths decides; agreement % with real Shariah
   ETFs; built on LSEG's FTSE Shariah rules; not a fatwa.

## Q&A prep

- *How accurate is it?* -> agreement % with SPUS / HLAL, plus what we checked by hand.
- *Why not let the AI pick stocks?* -> not repeatable or auditable.
- *Can I trade on it?* -> it's for choosing compliant stocks to hold, not speculation.
- *Is this a fatwa?* -> no; it's the evidence pack a scholar would review.
