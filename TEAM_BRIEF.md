# Team brief - Microsoft x LSEG Hackathon 2026

_Shared notes for the team and for any AI assistant (ChatGPT, Copilot, Claude). Paste or upload this file at the start of a chat so it has the full context._

What was announced at 9:00 on 23 Oct, and what we plan to build.

## The challenge

> **Build the AI analyst.** A client has **$100,000** to invest. Using public
> data and LLMs, build a tool that recommends where the money should go and
> explains why.

*Educational hackathon project. Not financial advice.* - put this line in the app too.

### Pick a client (or choose your own)

1. A pension fund that wants steady, long-term growth
2. A charity that only invests ethically
3. A university endowment funding scholarships
4. A start-up investor looking for high growth
5. An insurance company that needs low risk
6. Or choose your own

### What every team must cover

| # | Item | Meaning |
|---|---|---|
| 01 | The client | Who they are and what they want |
| 02 | The data | Which public data the tool uses |
| 03 | What the AI does | How the LLMs turn the data into a recommendation |
| 04 | The recommendation and why | Where the $100,000 goes and how the tool explains it |
| 05 | Live demo | Show it working, not just slides |

### How it is judged - 5 criteria x 10 = 50

| Criterion | 1: Limited | 5: Competent | 10: Outstanding |
|---|---|---|---|
| Client focus | Client unclear or generic | Clear, solution loosely tailored | Solution designed around the client's objectives |
| Use of data and AI | AI adds little beyond a chatbot | AI analyses relevant data in a structured way | AI produces analysis that would be hard to do manually |
| Quality of recommendation | Vague or unsupported | Reasonable, some justification | Specific, well reasoned, logic easy to follow |
| Originality | Conventional | A distinctive element | Novel, stands out from the field |
| Execution | Demo fails / unclear | Working demo, clear | Polished live demo, presented with confidence |

A Microsoft judge in each room scores live. **Top three scores across all
rooms go to the final.**

## Our team

Frederick Taylor, Xi Chuen Lim, Benjamin Toze, Saba Zulfiqar.

## What we have to build with

**Models** - Azure OpenAI API via the organisers' portal (endpoint and per-team login from the organisers):
GPT 6.1 Sol (`gpt-6.1-sol`), GPT 6 Astra and Terra, GPT 5.6 Terra, MAI
Thinking 1, Text Embedding 3 Large (`text-embedding-3-large`). Keep the API key in a gitignored `.env` file - never commit it or paste it into shared docs.

**Data** - suggested public sources (others allowed):

| Source | Gives | Key? |
|---|---|---|
| Finnhub | Prices, company news, analyst ratings | Free key |
| Twelve Data | Share, ETF, currency prices | Free key |
| Yahoo Finance (`yfinance`) | Share, fund, ETF price history | None |
| FRED | Rates, inflation, economic data | Free key |
| World Bank Open Data | Country/global economics | None |
| SEC EDGAR | Company filings and financials | None |
| Kaggle | Ready-made historical finance datasets | Free account |

## Suggested idea - not yet agreed by the team

> **Proposal, not a decision**
> Written before the team discussed it. Replace this callout with what the
> team actually picks.

### Client: option 2 - a charity that only invests ethically

Why this one scores best against the rubric:

- **Client focus** - a charity's ethics are written down in its own
  investment policy, so "designed around the client" is literal: the tool
  takes *their* policy as input. Most teams will pick pension or start-up
  and end up generic.
- **Use of data and AI ("hard to do manually")** - ethical screening means
  reading annual reports, 10-K risk sections and news for every holding. A
  person can't do that for 30 companies in an afternoon; an LLM can, and it
  is a real reading job, not a chatbot.
- **Quality of recommendation** - every exclusion and inclusion can quote the
  sentence in the filing that caused it. Traceable to source is the thing
  LSEG cares about most.
- **Originality** - "ethics as a parameter, not a label": swap in a different
  charity's policy and the portfolio changes, live.

Fallback if the team wants something more numerical: option 3, university
endowment (needs ~4-5% a year to pay scholarships forever - a clear,
testable target).

### The product - working name "Mandate"

A Streamlit web app. The flow the demo walks through:

1. **Client** - paste the charity's ethical policy in plain English (have two
   ready, e.g. a cancer charity and an environmental charity). The LLM turns
   it into structured rules: exclude tobacco, fossil-fuel extraction,
   weapons...; prefer renewables, healthcare... Rules are shown and editable.
2. **Screen** - a fixed universe of ~25-30 large-cap stocks and ETFs. For
   each: pass / fail / *needs human review*, with the quoted evidence and a
   link to the source (EDGAR 10-K business + risk-factor sections, Finnhub
   news). Embeddings match policy clauses to filing passages; the chat model
   judges each match.
3. **Allocate** - plain Python, **not the LLM**: price history from
   `yfinance`, then a simple risk-aware split of $100,000 across the
   survivors (e.g. inverse-volatility weights with a per-holding cap). Show
   expected return, volatility and max drawdown against an unscreened
   benchmark ETF - i.e. "what being ethical costs you, or doesn't".
4. **Why** - the LLM writes a one-page memo to the trustees: where the money
   goes, why, the trade-offs, and an audit trail where every claim links back
   to a data point or quote. Uncertain screens are flagged, not guessed.

The line for the pitch:

> "We used the model to *read* - policy and filings - and deliberately not to
> *pick numbers*. The allocation is deterministic maths so it's repeatable,
> and every judgement links to the sentence that justified it."

### Suggested roles

| Who | Lane |
|---|---|
| Chuen | Repo, app skeleton, LLM pipeline (policy -> rules, screening, memo) |
| Frederick | Data: `yfinance` prices, EDGAR filing text, Finnhub news; caching |
| Saba | Client: the two charity policies, the stock universe, checking screens are right |
| Benjamin | Pitch: deck, demo script, the 8-min story; timekeeping |

### Timeline (from ~11:15)

| Time | Goal |
|---|---|
| 11:15-11:45 | Agree client + one-sentence demo goal; repo up; everyone added |
| by 12:00 | App runs end to end with hardcoded data and one LLM call |
| 12:00-14:00 | Real data in, cached to JSON; screening works on 10 companies |
| 14:00-16:00 | Full universe, allocation, memo, "why trust it" tab |
| **16:00** | **Feature freeze** |
| 16:00-17:30 | Deck, screen recording backup, rehearse out loud twice |

### Risks

- Shared wifi and rate limits - cache every API and LLM response the moment
  it works; the demo must run from cache.
- Over-claiming - never say the screen is "accurate"; say what was checked by
  hand (Saba spot-checks 5).
- EDGAR needs a `User-Agent` header with a contact email or it rejects requests.

## Standing out - niche angles

Worry raised in the team: everyone will build a dashboard for a high-growth
investor. The gap is **who** you build for and **how** the answer arrives,
not prettier charts. Ranked:

1. **Shariah-compliant investor** (family or mosque endowment). Screens are
   part numbers (debt roughly under a third of company size, cash held in
   interest-bearing deposits capped, non-compliant revenue ~5% max - *check
   exact thresholds against FTSE / AAOIFI methodology first*) and part
   reading (what share of revenue is alcohol, gambling, conventional
   banking). LSEG's FTSE Russell runs FTSE Shariah indices - a mini version
   of something LSEG sells. Malaysia is an Islamic finance hub.
2. **Risk in the client's own units** - not "volatility 14%" but "a
   2022-type year funds 9 scholarships instead of 12". Run the portfolio
   through real crisis years (2008, 2020, 2022). Cheap, works with any client.
3. **Time-travel demo** - run the analyst week by week through 2022 with only
   the news and prices known then, then reveal what happened. Proves the
   reasoning isn't hindsight. Riskiest to build: cap at ~3 months, cache all.
4. **AI investment committee** - Bull, Bear, Risk Officer, Client Advocate
   argue; output is minutes with recorded dissent. Gimmicky unless every
   argument cites data.
5. **Not a dashboard** - a trustee board pack (Excel + 3 slides), mirroring
   the Microsoft-LSEG data-into-Office partnership; or an ongoing alert ("X
   just bought a coal miner - breaks your policy, here's a swap").
6. **Unusual clients** - a 24-year-old who inherited $100k; a football academy
   needing cash on a fixed date; a small island nation's climate fund.

Pick suggested: **1 + 2**, alert from 5 as a stretch.

## Team's ideas - feedback

The team's list: Streamlit; higher-risk funds and emerging markets; news/RSS
to find upcoming market swings; blockchain.

| Idea | Verdict |
|---|---|
| Streamlit | Keep - fast to build. Neutral for scoring |
| High risk / emerging markets | Good but generic. Narrow to a **region** (Southeast Asia: EWM, VNM, EIDO, EPHE country ETFs) + World Bank macro + currency, and **name the client** |
| News to predict swings | **Reframe as event radar, not prediction** - "which headlines affect your holdings, how much of your money, why". Predicting prices invites "how accurate is it?" with no good answer |
| Blockchain | Cut, or shrink to a capped ~5% crypto slice (`BTC-USD`). A "tamper-proof" hashed log file makes the trust point without a chain |

One-sentence pitch from that:

> "An AI analyst for a young high-risk investor betting on Southeast Asia: it
> splits $100k across ASEAN markets, explains the split with real economic
> data, and keeps reading the news to warn you when an event hits your money."

## How we build it - Streamlit build guide

Our own versions of four patterns that make a finance app feel finished. Times
are rough.

### 1. A polished look (~20 min)

Own palette, not a copy of anyone's. `.streamlit/config.toml`:

```toml
[theme]
base = "dark"
primaryColor = "#3FB68B"
backgroundColor = "#0B0F14"
secondaryBackgroundColor = "#131A22"
textColor = "#E6E9EF"
font = "monospace"
```

- Headline numbers across the top: `st.columns` + `st.metric` - amount
  invested, expected return, worst year, number of holdings.
- Charts: Plotly with `template="plotly_dark"` and the accent colour.
- One small CSS block via `st.markdown("<style>...</style>", unsafe_allow_html=True)`
  to tighten spacing and add thin borders to the tiles.

### 2. AI coach (~45 min)

The app builds the context, not the user:

```python
context = {"client": client_profile, "allocation": weights_df.to_dict(),
           "stress_test": stress_results, "alerts": alerts}
if q := st.chat_input("Ask about this recommendation"):
    answer = ask(SYSTEM_PROMPT + json.dumps(context), q)
```

- Preset question buttons for the client: "Why this split?", "What happens in
  a 2022-type year?", "What would make you change this?" - polished, and keeps
  the demo safe.
- System prompt rule: answer only from the context; if it isn't there, say so.

### 3. Alert list - the news radar (~30 min)

- Plain Python rules rank the alerts: headline about a holding -> HIGH, with
  what happened, % of portfolio affected, suggested action; holding down >15%
  -> MEDIUM.
- The LLM only writes the one-line explanation. Rules decide severity.
- Show with `st.dataframe`, or coloured `st.container`s, HIGH on top.

### 4. Honesty when data is missing (~10 min)

Show "Not enough data - needs human review" instead of a made-up number.
Answers "how do you know it's right?" before the judges ask.

### Who builds what

| Piece | Owner |
|---|---|
| AI coach | Chuen |
| Data | Frederick |
| Alert rules + checking | Saba |
| Theme + slides | Benjamin |

## Research - what practitioners say

Reddit threads couldn't be read directly. Findings below come from articles about Reddit experiments, developer
write-ups and recent papers.

- **"AI picks stocks" doesn't survive questions.** A Redditor's $100
  ChatGPT micro-cap experiment was up ~24% in four weeks vs ~4% for the
  benchmark; the main pushback was that it simply took more risk (leaned into
  biotech), and a month proves nothing. A University of Florida researcher
  argues longer simulations show ChatGPT underperforming. Don't pitch returns.
- **News sentiment barely predicts prices.** A 2026 paper: best sentiment
  models label headlines ~75-80% right, but adding sentiment moved up/down
  prediction from ~52% to ~56% - near a coin flip. Supports "event radar".
- **LSEG has a tutorial on nearly this exact feature** - FinancialBERT
  sentiment on daily headlines + BART summaries, plotted against price, with
  no accuracy claims. Mention it and show we go further: headline -> holding
  -> impact -> explanation.
- **Data tools:**
  - `yfinance` broke after Yahoo's Feb 2025 redesign and broke twice more in
    a two-week test - history only, cached to files before the demo.
  - **Finnhub** - best free option for news and quotes, 60 calls/min.
  - **Stooq** - free price-history backup, no key, plain CSV into pandas.
  - Alpha Vantage - 25 calls/day free now; skip.

### Route this points to

| Layer | Tool | Why |
|---|---|---|
| Prices | `yfinance` cached, Stooq backup | Breaks without warning |
| News | Finnhub company news | Generous free tier |
| Macro (SE Asia) | World Bank API, no key | Inflation, GDP, debt by country |
| Reading + explaining | GPT 6.1 Sol | Headlines -> exposure + explanation |
| News-to-holding matching | `text-embedding-3-large` | Uses the second model we were given |
| Allocation | pandas / numpy, **not the LLM** | Repeatable, defensible |
| App | Streamlit | As planned |

**Avoid saying:** "our AI beats the market", "we predict swings", anything
about blockchain. **Say:** "The AI reads, the maths allocates, and every claim
links to its source" - plus one stress-test number in the client's terms.

Sources: [Benzinga - Redditor's ChatGPT experiment](https://www.benzinga.com/markets/equities/25/08/46783783/redditors-100-chatgpt-day-trading-experiment-trounces-two-benchmark-indexes-with-24-returns-here)
- [LLM news sentiment and stock prediction (arXiv 2026)](https://arxiv.org/html/2602.00086v2)
- [LSEG Developers - stock insights from news with LLMs](https://developers.lseg.com/en/article-catalog/article/ai-driven-stock-insights--analyzing-financial-news-with-llms)
- [Why yfinance broke](https://deepcharts.substack.com/p/why-did-the-yfinance-python-library)
- [Four free stock APIs tested](https://orthogonal.info/i-tested-4-free-stock-market-apis-heres-which-one-actually-works-for-side-projects/)

> **Still open**
> The team hasn't picked a client or route yet. When it does, replace the
> "Suggested idea" callout above with the decision.
Sources
1. LLM news sentiment and stock prediction (arXiv 2026)

Link: LLM news sentiment and stock prediction (arXiv 2026)

✅ Why this is good

Compares FinBERT, RoBERTa and DeBERTa on financial news sentiment.
Shows how sentiment can improve stock prediction models.
Demonstrates ensemble models can outperform individual sentiment models.
Provides research-backed evidence for using financial sentiment analysis.

❌ Limitations

Focuses mainly on stock price prediction.
Not designed for Shariah screening.
Improvements in prediction are often modest rather than transformative.
Ideas we can use for Sharish
News sentiment scoring (positive/neutral/negative).
Daily company sentiment indicator.
Portfolio sentiment dashboard.
AI alerts when sentiment suddenly deteriorates.
News aggregation and ranking.
2. LSEG Developers - stock insights from news with LLMs

Link: LSEG Developers - stock insights from news with LLMs

✅ Why this is good

Provides a practical implementation pipeline.
Shows how to collect news, analyse sentiment and generate summaries.
Uses financial-specific NLP models.
Demonstrates how financial institutions use news intelligence.

❌ Limitations

Requires access to LSEG/Refinitiv data.
Focuses on general investing rather than Islamic finance.
Sentiment alone cannot determine Shariah compliance.
Ideas we can use for Sharish
News summarisation for investors.
"What happened this week?" company summaries.
Compliance risk alerts from news.
AI-generated weekly reports for mosque endowments.
Monitoring significant company events.
3. Why yfinance broke

Link: Why yfinance broke

✅ Why this is good

Highlights risks of depending on a single free data source.
Introduces Stooq as an alternative.
Useful for rapid prototyping and side projects.
Simple setup for historical price data.

❌ Why this is not very useful for Sharish

Only solves the price-data problem.
No compliance data.
No fundamentals.
No Shariah analysis.
Easily replaceable by other providers.
Ideas we can use for Sharish
Backup data provider.
Historical charts.
Basic performance visualisations.

Priority: Low

4. Four free stock APIs tested

Link: Four free stock APIs tested

✅ Why this is good

Practical comparison of:
Finnhub
Polygon
Alpha Vantage
yFinance
Helps choose data providers.
Discusses rate limits and reliability.
Useful for building a production data pipeline.

❌ Limitations

Focused on infrastructure rather than investment analysis.
Does not discuss Shariah compliance.
Ideas we can use for Sharish
Market price feeds.
Historical stock data.
Watchlists and portfolio performance.
Real-time monitoring.
News API integration (Finnhub).
Which source is MOST useful for Sharish?
🥇 #1 LSEG Developers - stock insights from news with LLMs

Reason: Closest to a real Sharish feature set:

News collection
Summarisation
Sentiment analysis
Investor dashboard
🥈 #2 Four free stock APIs tested

Reason: Helps build the technical infrastructure and data pipeline for the application.

🥉 #3 LLM news sentiment and stock prediction (arXiv 2026)

Reason: Good research support for using sentiment analysis but less practical.

#4 Why yfinance broke

Reason: Useful only as an engineering backup reference.

Most valuable features for our app (Sharish)
High Priority

✅ Shariah screening (AAOIFI / FTSE methodologies)

✅ Revenue source analysis

✅ Interest income detection

✅ Debt ratio calculation

✅ Compliance status (Pass / Fail)

✅ Purification calculations

Medium Priority

✅ News summarisation

✅ AI-generated company summaries

