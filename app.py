"""AMANAT - Shariah stock screening for everyday Muslim investors.  Run:  streamlit run app.py
Two pages: check any listed company (UK first), or build a screened portfolio.
Educational hackathon project. Not financial advice. Not a fatwa."""
import html
import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from shariah import edgar, llm, portfolio, prices, screen, signals, yahoo
from shariah.universe import SUKUK_ETF, UK_UNIVERSE, UNIVERSE

st.set_page_config(page_title="AMANAT · Halal investing", page_icon="☾", layout="wide")

# Look and feel follows the team's "Amanat" mock: Alice-blue page, Baltic-blue accents,
# white rounded cards, DM Sans body + Space Grotesk headings.
BLUES = ["#05668d", "#427aa1", "#77a6c2", "#a8c9df", "#d2e4ef", "#0b3c5d", "#5c95b8", "#8fb8d2",
         "#034b68", "#9fc2d8", "#2f6f95", "#bcd6e6"]
SIGNAL_COLOURS = {"Strong candidate": "#05668d", "Watch": "#77a6c2", "Lower priority": "#a8c9df",
                  "Watch - near Shariah limit": "#c8553d"}
STATUS_LABEL = {"PASS": "✅ Pass", "FAIL": "❌ Fail", "REVIEW": "🔎 Needs review"}
STATUS_CLASS = {"PASS": "pass", "FAIL": "fail", "REVIEW": "review"}
MARKETS = {"UK · London Stock Exchange": {"cur": "£", "universe": UK_UNIVERSE, "label": "UK (FTSE 100)"},
           "US · New York": {"cur": "$", "universe": UNIVERSE, "label": "US"}}
# The investment objective sets the default horizon (years) and suggested risk profile.
GOALS = {"Hajj or Umrah": (3, "Cautious"), "Home purchase": (5, "Cautious"), "Education": (10, "Balanced"),
         "Wealth growth": (15, "Adventurous"), "Charitable endowment": (20, "Balanced")}
RISKS = ["Cautious", "Balanced", "Adventurous"]
STRICTNESS = {"FTSE Shariah · LSEG's index rules": "FTSE Shariah (Yasaar)", "AAOIFI · Islamic finance standard": "AAOIFI"}
# Personal values on top of the Shariah screen, matched against the company's industry.
VALUES = {"🛢️ Fossil fuels": ("oil", "gas", "coal", "petroleum", "crude"),
          "⛏️ Mining": ("mining", "metals", "gold", "silver", "copper", "aluminum")}
# TradingView-style colours for up/down, and the default watchlist per market.
UP, DOWN = "#089981", "#F23645"
DOT = {"PASS": "🟢", "FAIL": "🔴", "REVIEW": "🟡"}
WATCH = {"UK · London Stock Exchange": ["AZN.L", "TSCO.L", "ULVR.L", "REL.L", "RMV.L", "BP.L", "HSBA.L", "DGE.L"],
         "US · New York": ["AAPL", "MSFT", "NVDA", "COST", "JPM", "KO"]}
RANGES = {"1M": 31, "3M": 92, "6M": 183, "1Y": 366, "5Y": 1830}
POPULAR = {"UK · London Stock Exchange": ["Tesco", "AstraZeneca", "Unilever", "HSBC", "Diageo", "BP", "Rightmove"],
           "US · New York": ["Apple", "Microsoft", "Nvidia", "JPMorgan", "Coca-Cola", "Tesla"]}

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
:root {--baltic:#05668d; --cerulean:#427aa1; --alice:#ebf2fa; --ink:#123047; --muted:#6e8799;
       --line:rgba(5,102,141,.12); --pass:#2a9d8f; --fail:#c8553d; --review:#c9971c;}
html, body, [data-testid="stAppViewContainer"] {background:var(--alice); color:var(--ink); font-family:'DM Sans',sans-serif;}
[data-testid="stHeader"] {background:transparent;}
[data-testid="stDecoration"], footer {display:none;}
.block-container {padding-top:1rem; max-width:1240px;}
h1, h2, h3 {font-family:'Space Grotesk',sans-serif !important; letter-spacing:-.04em; color:var(--ink);}


.topbar {display:flex; align-items:center; justify-content:space-between; padding:.6rem 0 0;}
.brand {color:var(--baltic); font-family:'Space Grotesk',sans-serif; font-size:1.25rem; font-weight:700; letter-spacing:-.04em;}
.brand-mark {position:relative; display:inline-block; width:27px; height:27px; margin-right:.45rem; vertical-align:middle;
              background:var(--baltic); clip-path:polygon(50% 0,91% 14%,86% 66%,71% 86%,50% 100%,29% 86%,14% 66%,9% 14%);}
.brand-mark::before {content:""; position:absolute; top:6px; left:6px; width:14px; height:14px; border-radius:50%; background:var(--alice);}
.brand-mark::after {content:""; position:absolute; top:4px; left:11px; width:14px; height:14px; border-radius:50%; background:var(--baltic);}
.brand.word {letter-spacing:.08em;}
.topbar-note {color:var(--muted); font-size:.8rem;}
.hero {margin:1.6rem 0 1.4rem; animation:arrive .9s cubic-bezier(.22,1,.36,1) both;}
.eyebrow {color:var(--cerulean); font-size:.78rem; font-weight:700; letter-spacing:.16em; text-transform:uppercase;}
.hero h1 {max-width:760px; margin:.5rem 0 .7rem; font-size:clamp(2.2rem,4.4vw,3.9rem); letter-spacing:-.06em; line-height:1; padding:0;}
.hero p {max-width:640px; margin:0; color:var(--muted); font-size:1.03rem; line-height:1.6;}
@keyframes arrive {from {opacity:0; transform:translateY(18px);} to {opacity:1; transform:none;}}

.section-heading {display:flex; align-items:end; justify-content:space-between; margin:2rem 0 .8rem;}
.section-title {font-family:'Space Grotesk',sans-serif; font-size:1.4rem; font-weight:600; letter-spacing:-.04em; color:var(--ink);}
.section-heading span {color:var(--muted); font-size:.8rem;}

.stats {display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:1rem;}
@media (min-width:1100px) {.stats.five {grid-template-columns:repeat(5,1fr);}}
.card {padding:1.15rem 1.3rem; border:1px solid var(--line); border-radius:22px; background:rgba(255,255,255,.75);
       box-shadow:0 14px 35px rgba(35,72,99,.055);}
.label {color:var(--muted); font-size:.72rem; letter-spacing:.08em; text-transform:uppercase;}
.big {margin:.3rem 0 .15rem; font-family:'Space Grotesk',sans-serif; font-size:1.8rem; font-weight:600; letter-spacing:-.05em;}
.sub {color:var(--muted); font-size:.8rem; line-height:1.45;}
.good {color:var(--pass);} .bad {color:var(--fail);}

.row {display:grid; grid-template-columns:1fr auto; gap:.15rem 1rem; align-items:center; padding:.85rem 0; border-bottom:1px solid var(--line);}
.row:last-child {border-bottom:0;}
.name {font-size:.95rem; font-weight:700;}
.meta {color:var(--muted); font-size:.78rem;}
.score {color:var(--baltic); font-weight:700;}
.tag {display:inline-block; margin-top:.45rem; padding:.22rem .6rem; border-radius:999px; font-size:.7rem; font-weight:700;
      background:rgba(66,122,161,.12); color:var(--cerulean);}
.tag.warn {background:rgba(200,85,61,.12); color:var(--fail);}

/* company report */
.report-head {display:flex; justify-content:space-between; align-items:flex-start; gap:1.5rem; flex-wrap:wrap;}
.report-name {font-family:'Space Grotesk',sans-serif; font-size:2rem; font-weight:600; letter-spacing:-.05em; line-height:1.1;}
.verdict {padding:.55rem 1.1rem; border-radius:999px; font-weight:700; font-size:1rem; white-space:nowrap;}
.verdict.pass {background:rgba(42,157,143,.14); color:var(--pass);}
.verdict.fail {background:rgba(200,85,61,.13); color:var(--fail);}
.verdict.review {background:rgba(201,151,28,.15); color:#9a7210;}
.why {margin-top:1rem; font-size:1rem; line-height:1.55;}
.ratio {padding:.75rem 0; border-bottom:1px solid var(--line);}
.ratio:last-child {border-bottom:0;}
.ratio-top {display:flex; justify-content:space-between; gap:1rem; font-size:.9rem;}
.ratio-top b {font-weight:700;}
.bar {position:relative; height:9px; margin:.45rem 0 .3rem; border-radius:999px; background:rgba(5,102,141,.09); overflow:hidden;}
.fill {height:100%; border-radius:999px; background:var(--pass);}
.fill.over {background:var(--fail);}
.quote {margin:.6rem 0; padding:.6rem .9rem; border-left:3px solid var(--cerulean); background:rgba(66,122,161,.06); border-radius:0 12px 12px 0;}
.limits li {margin:.25rem 0; color:var(--muted); font-size:.85rem;}

/* Streamlit containers made with key="panel_*" render as cards */
[class*="st-key-panel"] {padding:1.2rem 1.3rem; border:1px solid var(--line); border-radius:22px; background:rgba(255,255,255,.75);
                         box-shadow:0 14px 35px rgba(35,72,99,.055);}

.stTabs [data-baseweb="tab-list"] {gap:.4rem; border-bottom:0;}
.stTabs [data-baseweb="tab"] {padding:.45rem 1rem; border-radius:999px !important; background:rgba(255,255,255,.7); border:1px solid var(--line);}
.stTabs button[role="tab"] {border-radius:999px !important; padding:.45rem 1rem !important;}
.stTabs [aria-selected="true"] {background:var(--baltic); color:#fff !important;}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {display:none;}

.stButton > button {border:1px solid rgba(5,102,141,.18); border-radius:999px; background:var(--cerulean); color:var(--alice) !important; font-weight:700;}
.stButton > button:hover {border-color:var(--baltic); background:var(--baltic);}
[data-testid="stDataFrame"] {border-radius:14px; overflow:hidden;}
.step {margin:1.1rem 0 .2rem; color:var(--cerulean); font-size:.7rem; font-weight:700; letter-spacing:.14em; text-transform:uppercase;}

/* TradingView-style ticker tape */
.tape {overflow:hidden; margin:.7rem 0 .2rem; border-top:1px solid var(--line); border-bottom:1px solid var(--line);
       background:rgba(255,255,255,.6); white-space:nowrap; -webkit-mask-image:linear-gradient(90deg,transparent,#000 4%,#000 96%,transparent);}
.tape-track {display:inline-block; padding:.45rem 0; animation:tape 55s linear infinite;}
.tape:hover .tape-track {animation-play-state:paused;}
.tk {display:inline-block; margin:0 1.4rem; font-size:.82rem; font-variant-numeric:tabular-nums;}
.tk b {margin-right:.35rem;} .up {color:#089981;} .down {color:#F23645;}
@keyframes tape {from {transform:translateX(0);} to {transform:translateX(-50%);}}

/* TradingView-style chart header */
.px-head {display:flex; align-items:baseline; gap:.7rem; flex-wrap:wrap;}
.px-big {font-family:'Space Grotesk',sans-serif; font-size:2rem; font-weight:600; letter-spacing:-.04em; font-variant-numeric:tabular-nums;}
.px-cur {color:var(--muted); font-size:.8rem;}
.px-chg {font-weight:700; font-variant-numeric:tabular-nums;}
.values-note {margin-top:.5rem; color:var(--muted); font-size:.85rem;}
.disclaimer {margin-top:2.5rem; color:var(--muted); font-size:.75rem; text-align:center;}
</style>""", unsafe_allow_html=True)


def card(label: str, value: str, sub: str = "", cls: str = "") -> str:
    return (f'<div class="card"><div class="label">{label}</div><div class="big {cls}">{value}</div>'
            f'<div class="sub">{sub}</div></div>')


def heading(title: str, note: str = "") -> None:
    st.markdown(f'<div class="section-heading"><div class="section-title">{title}</div><span>{note}</span></div>', unsafe_allow_html=True)


def styled(fig, height=340):
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family="DM Sans, sans-serif", color="#123047"), height=height,
                      margin=dict(l=10, r=10, t=10, b=10), legend_title_text="")
    return fig


def big_money(cur: str, x: float) -> str:
    for div, suffix in ((1e12, "tn"), (1e9, "bn"), (1e6, "m")):
        if abs(x) >= div:
            return f"{cur}{x / div:,.1f}{suffix}"
    return f"{cur}{x:,.0f}"


# ---------------- header + the client (no sidebar: everything sits on the page) ----------------
st.markdown("""<div class="topbar"><div class="brand word"><span class="brand-mark" aria-hidden="true"></span>AMANAT</div>
<div class="topbar-note">Educational project · Not financial advice · Not a fatwa</div></div>""", unsafe_allow_html=True)

tape_slot = st.container()  # TradingView-style ticker tape, filled once screening is defined
page = st.segmented_control("Page", ["🔎 Check a company", "📊 Build my portfolio"], default="🔎 Check a company",
                            key="page", label_visibility="collapsed") or "🔎 Check a company"

with st.expander("⚙️ Settings · market, amount, risk profile, Shariah standard"):
    col_obj, col_mkt, col_scr = st.columns(3, gap="large")
    with col_obj:
        st.markdown('<div class="step">Objective</div>', unsafe_allow_html=True)
        goal = st.selectbox("Investment objective", list(GOALS), index=3, key="goal")
        years, suggested = GOALS[goal]
        years = st.slider("Time horizon (years)", 1, 30, years, key=f"years_{goal}")
        risk = st.radio("Risk profile", RISKS, index=RISKS.index(suggested), key=f"risk_{goal}", horizontal=True,
                        help=f"Suggested for {goal.lower()}: {suggested}.")
    with col_mkt:
        st.markdown('<div class="step">Market and amount</div>', unsafe_allow_html=True)
        market = st.radio("Market", list(MARKETS), help="Search covers any listed company; this sets the "
                          "portfolio's stock list and currency.")
        C = MARKETS[market]["cur"]
        amount = st.number_input(f"Amount to invest ({C})", 1_000, 10_000_000, 100_000, step=5_000)
        top_n = st.slider("Number of holdings", 3, 20, 10)
        eq = st.slider("Allocation to Shariah equities", 0.5, 1.0, 1.0, 0.05)
        sk = st.slider("Sukuk (Islamic bonds)", 0.0, 1.0 - eq, 0.0, 0.05) if eq < 1.0 else 0.0
    with col_scr:
        st.markdown('<div class="step">Screening</div>', unsafe_allow_html=True)
        standard = STRICTNESS[st.radio("Shariah standard", list(STRICTNESS),
                                       help="FTSE measures ratios against total assets; AAOIFI against market value.")]
        avoid = st.pills("Also exclude", list(VALUES), selection_mode="multi", key="avoid") or []
        use_llm = st.toggle("Use AI to read US annual reports (10-Ks)", value=llm.available(), disabled=not llm.available(),
                            help="Needs OPENAI_API_KEY in .env. Without it, a rule on the SEC industry code is used.")
        tickers = st.multiselect("Stocks to consider", MARKETS[market]["universe"], default=MARKETS[market]["universe"])


def against_values(r: dict) -> list[str]:
    """Which of the investor's own 'also avoid' values this company's industry hits."""
    industry = (r.get("sic") or "").lower()
    return [v for v in avoid if any(w in industry for w in VALUES[v])]


rules = screen.STANDARDS[standard]


# ---------------- screening (shared by both pages) ----------------
def on_sec(t: str) -> bool:
    """US-listed SEC filers use the filings themselves; everything else (UK etc.) uses Yahoo Finance."""
    try:
        return "." not in t and t.upper() in edgar.ticker_to_cik()
    except Exception:
        return False


@st.cache_data(show_spinner=False)
def screen_one(t: str, std: str, use_ai: bool):
    if not on_sec(t):
        fin = yahoo.company(t)
        p = fin["profile"]
        business = screen.industry_rule(p.get("sector"), p.get("industry"))
        business["source_url"] = fin["source_url"]
        v = screen.verdict(fin, fin["market_cap"], business, std)
        return {"fin": fin, "sic": p.get("industry"), "mcap": fin["market_cap"], "business": business, "verdict": v,
                "source": "Yahoo Finance", "profile": p, "currency": p.get("financialCurrency") or p.get("currency")}
    fin = edgar.financials(t)
    sub = edgar.submissions(t)
    try:
        mcap = (fin["shares_outstanding"] or 0) * prices.last_price(t)
    except Exception:
        mcap = None
    if use_ai:
        item1 = edgar.business_section(t)
        business = llm.business_screen(fin["name"], item1["text"]) if item1["text"] else screen.sic_rule(sub["sicDescription"])
        business["source_url"] = item1.get("url")
    else:
        business = screen.sic_rule(sub["sicDescription"])
        business["source_url"] = (sub.get("latest_10k") or {}).get("url")
    v = screen.verdict(fin, mcap, business, std)
    if fin["name"].isupper():
        fin = {**fin, "name": fin["name"].title()}
    return {"fin": fin, "sic": sub["sicDescription"], "mcap": mcap, "business": business, "verdict": v,
            "source": "SEC EDGAR", "profile": {"industry": sub["sicDescription"], "exchange": "US"}, "currency": "USD"}


@st.cache_data(show_spinner=False, ttl=900)
def quote(t: str):
    """Last close and change on the day before, from cached daily prices."""
    h = prices.history(t)
    return float(h.iloc[-1]), float(h.iloc[-1] / h.iloc[-2] - 1), str(h.index[-1].date())


def status_of(t: str):
    try:
        return screen_one(t, standard, use_llm)["verdict"]["status"]
    except Exception:
        return None


def toggle_watch(symbol: str) -> None:
    wl = st.session_state.setdefault(f"watch_{market}", list(WATCH[market]))
    wl.remove(symbol) if symbol in wl else wl.append(symbol)


watchlist = st.session_state.setdefault(f"watch_{market}", list(WATCH[market]))


# ---------------- ticker tape (drawn in its slot under the header) ----------------
tape = []
for t in dict.fromkeys(watchlist + MARKETS[market]["universe"][:14]):
    try:
        last, chg, _ = quote(t)
    except Exception:
        continue
    tape.append(f'<span class="tk">{DOT.get(status_of(t), "")} <b>{t.removesuffix(".L")}</b>{last:,.2f} '
                f'<span class="{"up" if chg >= 0 else "down"}">{"▲" if chg >= 0 else "▼"} {abs(chg):.2%}</span></span>')
if tape:
    tape_slot.markdown(f'<div class="tape"><div class="tape-track">{"".join(tape) * 2}</div></div>', unsafe_allow_html=True)


# ================= page 1: check any company =================
def ratio_row(label: str, value, limit: float, source: str) -> str:
    if value is None:
        return (f'<div class="ratio"><div class="ratio-top"><b>{label}</b><span>no data · limit {limit:.0%}</span></div>'
                f'<div class="meta">{html.escape(source or "not reported")}</div></div>')
    over = value >= limit
    width = min(value / limit, 1.0) * 100 if limit else 0
    return (f'<div class="ratio"><div class="ratio-top"><b>{label}</b>'
            f'<span class="{"bad" if over else "good"}">{value:.1%} · limit {limit:.0%} {"❌" if over else "✅"}</span></div>'
            f'<div class="bar"><div class="fill{" over" if over else ""}" style="width:{width:.0f}%"></div></div>'
            f'<div class="meta">{html.escape(source or "")}</div></div>')


def company_report(symbol: str, exchange: str) -> None:
    with st.spinner(f"Checking {symbol}..."):
        r = screen_one(symbol, standard, use_llm)
    fin, v, b, p = r["fin"], r["verdict"], r["business"], r["profile"]
    clashes = against_values(r)
    base = v["ratios"].get(rules["denominator"]) or {}
    cur = r["currency"] or ""
    why = {"PASS": f"Passes every {html.escape(standard)} screen we can check.",
           "FAIL": "Fails: " + html.escape("; ".join(v["reasons"]).replace(" >= ", " - over the limit of ")
                                            .replace(" > ", " - over the limit of ")),
           "REVIEW": "Needs a person to check: " + html.escape("; ".join(v["review"]))}[v["status"]]
    meta = " · ".join(html.escape(str(x)) for x in (symbol, exchange or p.get("exchange"), p.get("industry"), p.get("country")) if x)

    with st.container(key="panel_report_head"):
        st.markdown(f'<div class="report-head"><div><div class="label">Shariah screen · {html.escape(standard)}</div>'
                    f'<div class="report-name">{html.escape(fin["name"])}</div><div class="meta">{meta}</div></div>'
                    f'<div class="verdict {STATUS_CLASS[v["status"]]}">{STATUS_LABEL[v["status"]]}</div></div>'
                    f'<div class="why">{why}</div>'
                    + (f'<div class="values-note">Heads up: you asked to also avoid '
                       f'{html.escape(", ".join(c.split(" ", 1)[1].lower() for c in clashes))} - this company is in '
                       f'{html.escape(p.get("industry") or "")}.</div>' if clashes else ""), unsafe_allow_html=True)
        starred = symbol in st.session_state.get(f"watch_{market}", WATCH[market])
        st.button("★ In your watchlist" if starred else "☆ Add to watchlist", key=f"star_{symbol}",
                  on_click=toggle_watch, args=(symbol,))

    left, right = st.columns([1.15, 1], gap="large")
    with left, st.container(key="panel_ratios"):
        denom = rules["denominator"].replace("_", " ")
        st.markdown(f'<div class="label">Financial ratios · share of {denom}</div>', unsafe_allow_html=True)
        rows = [ratio_row(lbl, base.get(k), rules[k], fin["sources"].get(src))
                for k, lbl, src in (("debt", "Debt", "total_debt"),
                                    ("cash", "Cash & interest-bearing items", "cash_and_interest_bearing"),
                                    ("receivables", "Receivables", "receivables"),
                                    ("receivables_plus_cash", "Receivables + cash", "receivables"))
                if rules[k]]
        rows.append(ratio_row("Non-compliant income", v["noncompliant_income_pct"], rules["noncompliant_revenue"],
                              "business activity + interest income"))
        st.markdown("".join(rows), unsafe_allow_html=True)
        st.caption(f"Figures in {cur}, period ending {fin.get('period_end') or 'unknown'}. "
                   + (f"Market value {big_money('', r['mcap'])} {cur}." if r["mcap"] else ""))

    with right, st.container(key="panel_business"):
        st.markdown('<div class="label">Business activity</div>', unsafe_allow_html=True)
        cats = ", ".join(b.get("categories") or []) or "no prohibited activity found"
        st.markdown(f"**{cats[:1].upper() + cats[1:]}**")
        if b.get("evidence"):
            st.markdown(f'<div class="quote">{html.escape(str(b["evidence"]))}</div>', unsafe_allow_html=True)
        st.caption(f"Checked by: {b.get('method')}" + (f" · confidence {b.get('confidence')}" if b.get("method") == "LLM" else ""))
        if p.get("longBusinessSummary"):
            with st.expander("What the company does"):
                st.write(p["longBusinessSummary"])

    try:
        o = prices.ohlc(symbol)
    except Exception:
        o = None
    if o is not None and len(o) > 2:
        with st.container(key="panel_price"):
            listed = o.attrs.get("currency") or ""
            last, prev = o["close"].iloc[-1], o["close"].iloc[-2]
            day = last / prev - 1
            head, pick = st.columns([3, 2], vertical_alignment="center")
            rng = pick.segmented_control("Range", list(RANGES), default="1Y", key=f"rng_{symbol}",
                                         label_visibility="collapsed") or "1Y"
            d = o[o.index >= o.index[-1] - pd.Timedelta(days=RANGES[rng])]
            span = d["close"].iloc[-1] / d["close"].iloc[0] - 1
            head.markdown(f'<div class="px-head"><span class="px-big">{last:,.2f}</span><span class="px-cur">{html.escape(listed)}</span>'
                          f'<span class="px-chg {"up" if day >= 0 else "down"}">{last - prev:+,.2f} ({day:+.2%}) today</span>'
                          f'<span class="px-cur">{span:+.1%} over {rng} · close {o.index[-1]:%d %b %Y}</span></div>',
                          unsafe_allow_html=True)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[.78, .22], vertical_spacing=.03)
            fig.add_trace(go.Candlestick(x=d.index, open=d["open"], high=d["high"], low=d["low"], close=d["close"],
                                         increasing=dict(line_color=UP, fillcolor=UP), decreasing=dict(line_color=DOWN, fillcolor=DOWN),
                                         name=symbol, showlegend=False), row=1, col=1)
            fig.add_trace(go.Bar(x=d.index, y=d["volume"], marker_color=[UP if c >= o_ else DOWN for o_, c in zip(d["open"], d["close"])],
                                 opacity=.45, name="Volume", showlegend=False), row=2, col=1)
            fig.update_layout(xaxis_rangeslider_visible=False, hovermode="x unified")
            fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])], showgrid=False)
            fig.update_yaxes(side="right", gridcolor="rgba(5,102,141,.07)")
            fig.update_yaxes(showticklabels=False, showgrid=False, row=2, col=1)
            st.plotly_chart(styled(fig, 380), width="stretch", config={"displayModeBar": False})

    with st.container(key="panel_ai"):
        st.markdown('<div class="label">AI analyst review</div>', unsafe_allow_html=True)
        # Hook for the team's AI analyser (amanat/ package): read the company's own annual report and
        # return PASS / FAIL / NEEDS REVIEW per screen with quotes. To be wired in here.
        st.write("Coming soon: our AI reads the company's annual report and explains each screen in plain English, "
                 "quoting the report.")

    limits = ["This is research support, not a fatwa - a Shariah scholar makes the ruling."]
    if r["source"] == "Yahoo Finance":
        limits += ["Figures are Yahoo Finance's copy of the accounts, not the filing itself - check the company's annual report.",
                   "\"Debt\" here includes lease liabilities, which can make debt look higher than FTSE's definition.",
                   "Business activity is judged from the industry classification until the AI review is connected."]
    else:
        limits += ["Figures come straight from the company's SEC filings (XBRL)."]
    links = " · ".join(f"[{t}]({u})" for t, u in (("Data source", fin.get("source_url") or b.get("source_url")),
                                                  ("Company website", p.get("website"))) if u)
    with st.expander("Sources and limitations"):
        st.markdown(f"**Source:** {r['source']}" + (f" · {links}" if links else ""))
        st.markdown('<ul class="limits">' + "".join(f"<li>{html.escape(x)}</li>" for x in limits) + "</ul>",
                    unsafe_allow_html=True)


if page.startswith("🔎"):
    st.markdown("""<div class="hero"><div class="eyebrow">Shariah screening for UK investors</div>
<h1>Is it halal to invest in?</h1>
<p>Search any listed company. We check what it does and how it's financed against the Shariah rules,
and show you the evidence behind every answer.</p></div>""", unsafe_allow_html=True)
    q = st.text_input("Search any listed company", placeholder="Company name or ticker - e.g. Tesco, AstraZeneca, Apple",
                      key="query")
    quick = st.pills("Popular", POPULAR[market], key=f"quick_{market}", label_visibility="collapsed")
    q = q.strip() or quick or ""
    if not q:
        st.caption("Try one of the popular companies above, or type any name or ticker.")
    else:
        try:
            matches = yahoo.search(q)
        except Exception as e:
            matches = []
            st.error(f"Search is unavailable right now ({e}). Try a ticker such as TSCO.L.")
        if q.upper() == q and " " not in q and not any(m["symbol"] == q.upper() for m in matches):
            matches.insert(0, {"symbol": q.upper(), "name": q.upper(), "exchange": ""})
        if market.startswith("UK"):  # London listings first for UK investors
            matches.sort(key=lambda m: not m["symbol"].endswith(".L"))
        if not matches:
            st.warning(f"No listed company found for “{q}”.")
        else:
            labels = [f'{m["name"]} · {m["symbol"]}' + (f' · {m["exchange"]}' if m["exchange"] else "") for m in matches]
            i = st.selectbox("Which one?", range(len(matches)), format_func=lambda k: labels[k], key=f"pick_{q}")
            try:
                company_report(matches[i]["symbol"], matches[i]["exchange"])
            except Exception as e:
                st.error(f"Couldn't load the figures for {matches[i]['symbol']}: {e}")


# ================= page 2: build a portfolio =================
else:
    results, errors = {}, []
    with st.spinner("Checking companies against the Shariah screens..."):
        for t in tickers:
            try:
                results[t] = screen_one(t, standard, use_llm)
            except Exception as e:  # keep the demo alive; show what failed
                errors.append(f"{t}: {e}")

    counts = {s: sum(r["verdict"]["status"] == s for r in results.values()) for s in STATUS_LABEL}
    passing = [t for t, r in results.items() if r["verdict"]["status"] == "PASS"]
    removed = [t for t in passing if against_values(results[t])]
    passing = [t for t in passing if t not in removed]
    ranking = signals.rank({t: results[t] for t in passing}, rules, signals.PROFILES[risk]) if passing else pd.DataFrame()
    picks = [] if ranking.empty else ranking[~ranking["signal"].str.startswith("Watch - near")]["ticker"].head(top_n).tolist()

    alloc = portfolio.build(picks or passing, amount, eq, sk, SUKUK_ETF) if (picks or passing) else None
    stt = pur = None
    if alloc is not None:
        try:
            stt = portfolio.stress_test(alloc, amount=amount)
            nc = {t: results[t]["verdict"]["noncompliant_income_pct"] for t in passing}
            pur = portfolio.purification(alloc, {t: results[t]["fin"] for t in passing}, nc)
        except Exception as e:
            errors.append(f"stress test / purification: {e}")

    st.markdown(f"""<div class="hero"><div class="eyebrow">Portfolio · {html.escape(goal)} · {years}-year horizon</div>
<h1>Shariah-screened portfolio</h1>
<p>We check {len(results)} {MARKETS[market]["label"]} companies against the {html.escape(standard)} rules, rank the ones that
pass for a <b>{risk.lower()}</b> risk profile, and show what that means for {C}{amount:,.0f} - with the evidence behind
every verdict.</p></div>""", unsafe_allow_html=True)

    heading("Your plan at a glance", f"{standard} standard · {risk} profile")
    worst = stt.loc[stt["portfolio_return"].idxmin()] if stt is not None and not stt.empty else None
    cards = [
        card("Invested", f"{C}{amount:,.0f}", f"{eq:.0%} Shariah stocks" + (f" · {sk:.0%} sukuk" if sk else "")),
        card("Companies that pass", f"{counts['PASS']} of {len(results)}",
             f"{counts['FAIL']} fail · {counts['REVIEW']} need a person to check"
             + (f" · {len(removed)} left out for your values" if removed else "")),
        card("Stocks in your plan", str(len(picks or passing)), "Top-ranked, max 10% in any one"),
        card(f"In a bad year ({int(worst['year'])})" if worst is not None else "In a bad year",
             f"{C}{worst['value_after']:,.0f}" if worst is not None else "-",
             f"{worst['gain_or_loss']:+,.0f} vs today" if worst is not None else "Not enough price history",
             "bad" if worst is not None and worst["gain_or_loss"] < 0 else ""),
        card("Give to charity this year", f"{C}{pur['to_purify'].sum():,.2f}" if pur is not None and not pur.empty else f"{C}0.00",
             "Purification of dividends"),
    ]
    st.markdown(f'<div class="stats five">{"".join(cards)}</div>', unsafe_allow_html=True)

    if alloc is not None:
        heading("Where your money goes", "Calmer stocks get more")
        left, right = st.columns([1, 1.2], gap="large")
        with left, st.container(key="panel_donut"):
            st.markdown(f'<div class="label">Portfolio value</div><div class="big">{C}{amount:,.0f}</div>', unsafe_allow_html=True)
            names = {r["ticker"]: r["company"] for _, r in ranking.iterrows()} if not ranking.empty else {}
            donut = alloc.assign(label=alloc["holding"].map(lambda h: names.get(h, h)))
            fig = px.pie(donut, names="label", values="amount", hole=.62, color_discrete_sequence=BLUES)
            fig.update_traces(textinfo="none", hovertemplate=f"%{{label}}<br>{C}%{{value:,.0f}} (%{{percent}})<extra></extra>")
            fig.update_layout(legend=dict(orientation="h", y=-0.05, x=0.5, xanchor="center", yanchor="top"))
            st.plotly_chart(styled(fig, 460), width="stretch")
        with right, st.container(key="panel_top"):
            st.markdown(f'<div class="label">Top picks for a {risk.lower()} investor</div>', unsafe_allow_html=True)
            rows = []
            for _, r in ranking.head(5).iterrows():
                share = alloc.set_index("holding")["amount"].get(r["ticker"])
                rows.append(f'<div class="row"><div><div class="name">{html.escape(r["company"])}</div>'
                            f'<div class="meta">{r["ticker"]} · {r["return_1y"]:+.0%} over the past year'
                            + (f" · {C}{share:,.0f} in your plan" if share else "") + '</div>'
                            f'<span class="tag{" warn" if r["signal"].startswith("Watch - near") else ""}">{r["signal"]}</span></div>'
                            f'<div class="score">{r["score"]:.0f}/100</div></div>')
            st.markdown("".join(rows) or '<div class="sub">No compliant stocks to rank yet.</div>', unsafe_allow_html=True)

    # ---------------- details ----------------
    money = st.column_config.NumberColumn  # £ has no built-in format, so label the currency in the header
    money_fmt = "dollar" if C == "$" else "localized"
    heading("Explore the details", "Every number can be traced to its source")
    tab_screen, tab_picks, tab_alloc, tab_stress, tab_ask = st.tabs(
        ["Shariah check", "Stock picks", "Your portfolio", "Bad years & charity", "Ask the analyst"])

    with tab_screen:
        rows = []
        for t, r in results.items():
            v, b = r["verdict"], r["business"]
            base = v["ratios"].get(rules["denominator"], {})
            rows.append({"Ticker": t, "Company": r["fin"]["name"], "Result": STATUS_LABEL[v["status"]],
                         "Debt ratio": base.get("debt"), "Cash ratio": base.get("cash"),
                         "Non-compliant income": v["noncompliant_income_pct"],
                         "Why": "; ".join(v["reasons"] + v["review"]) or "meets all screens",
                         "Evidence": b.get("evidence", ""), "Checked by": b.get("method"), "Data": r["source"]})
        df = pd.DataFrame(rows)
        show = st.segmented_control("Show", ["All"] + list(STATUS_LABEL.values()), default="All", key="screen_filter")
        if show and show != "All" and not df.empty:
            df = df[df["Result"] == show]
        st.dataframe(df, width="stretch", hide_index=True, column_config={
            "Debt ratio": st.column_config.NumberColumn(format="percent"),
            "Cash ratio": st.column_config.NumberColumn(format="percent"),
            "Non-compliant income": st.column_config.NumberColumn(format="percent")})
        st.caption(f"Standard: {standard}. US companies: SEC EDGAR filings. UK companies: Yahoo Finance's copy of the "
                   "accounts. \"Needs review\" means there isn't enough data to decide - we flag it rather than guess.")
        if errors:
            with st.expander(f"{len(errors)} items could not be loaded"):
                st.write(errors)

    with tab_picks:
        if ranking.empty:
            st.info("No compliant stocks to rank yet.")
        else:
            st.plotly_chart(styled(px.bar(ranking, x="ticker", y="score", color="signal",
                                          color_discrete_map=SIGNAL_COLOURS,
                                          labels={"ticker": "", "score": "Score (0-100)"})), width="stretch")
            show = ranking[["ticker", "company", "signal", "score", "price", "return_1y", "momentum_12_1",
                            "volatility", "max_drawdown_1y", "headroom"]]
            st.dataframe(show, width="stretch", hide_index=True, column_config={
                "ticker": "Ticker", "company": "Company", "signal": "Signal",
                "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f"),
                "price": money("Price" if C == "$" else "Price (pence)", format="dollar" if C == "$" else "%.1f"),
                "return_1y": st.column_config.NumberColumn("1-year return", format="percent"),
                "momentum_12_1": st.column_config.NumberColumn("Momentum", format="percent"),
                "volatility": st.column_config.NumberColumn("Volatility", format="percent"),
                "max_drawdown_1y": st.column_config.NumberColumn("Worst fall (1y)", format="percent"),
                "headroom": st.column_config.NumberColumn("Room below Shariah limit", format="percent")})
            st.caption("Score = momentum + steadiness + smaller falls + room below the Shariah limits, weighted for your risk "
                       "appetite. A stock close to a limit may have to be sold if it breaches it. This ranks candidates; "
                       "it does not predict prices.")

            with st.container(key="panel_analyst"):
                st.subheader("Analyst view")
                pick = st.selectbox("Pick a stock", ranking["ticker"].tolist(),
                                    format_func=lambda t: f"{t} · {ranking.set_index('ticker').loc[t, 'company']}")
                row = ranking.set_index("ticker").loc[pick]
                r = results[pick]
                st.markdown(f"**{row['signal']}** · {signals.reasons(row)}")
                st.markdown("**Shariah check:** " + ("; ".join(r["verdict"]["reasons"] + r["verdict"]["review"]) or "meets all screens")
                            + (f" · evidence: “{r['business'].get('evidence')}”" if r["business"].get("evidence") else ""))
                if llm.available() and st.button(f"Write the AI analyst note for {pick}"):
                    facts = {"ticker": pick, "company": row["company"], "signal": row["signal"], "score": round(row["score"]),
                             "metrics": {k: round(float(row[k]), 4) for k in ("return_1y", "momentum_12_1", "volatility",
                                                                               "max_drawdown_1y", "headroom")},
                             "shariah": {"standard": standard, "status": r["verdict"]["status"],
                                         "evidence": r["business"].get("evidence")}}
                    with st.spinner("Writing the note..."):
                        st.markdown(llm.ask(
                            "You are an equity analyst writing for a Shariah-conscious investor. Using ONLY the JSON facts, write: "
                            "1) a two-sentence view, 2) three bullet reasons for, 3) two bullet risks (include Shariah-compliance "
                            "risk if headroom is low), 4) what would change the view. No price targets. No invented numbers. "
                            "End with: Educational project, not financial advice.", json.dumps(facts, default=str)))

    with tab_alloc:
        if alloc is None:
            st.info("No stocks pass yet.")
        else:
            st.plotly_chart(styled(px.sunburst(alloc, path=["sleeve", "holding"], values="amount",
                                               color_discrete_sequence=BLUES), 420), width="stretch")
            st.dataframe(alloc, width="stretch", hide_index=True, column_order=["holding", "sleeve", "weight", "amount"],
                         column_config={"holding": "Holding", "sleeve": "Type",
                                        "weight": st.column_config.NumberColumn("Share", format="percent"),
                                        "amount": money(f"Amount ({C})", format=money_fmt)})
            st.caption("Top-ranked compliant stocks, inverse-volatility weights (calmer stocks get more), max 10% each. "
                       "Deterministic maths - the AI does not choose the numbers.")

    with tab_stress:
        if stt is None:
            st.info("Build a portfolio first.")
        else:
            st.subheader(f"What past years would have done to your {C}{amount:,.0f}")
            year_cards = [card(str(int(y["year"])), f"{C}{y['value_after']:,.0f}",
                               f"{y['gain_or_loss']:+,.0f} ({y['portfolio_return']:+.0%})"
                               + (f"<br>No data for {html.escape(y['no_data_for'])}" if y["no_data_for"] else ""),
                               "good" if y["gain_or_loss"] >= 0 else "bad") for _, y in stt.iterrows()]
            st.markdown(f'<div class="stats">{"".join(year_cards)}</div>', unsafe_allow_html=True)
            st.caption("2008: financial crisis · 2020: Covid crash and recovery · 2022: rate-rise sell-off. "
                       "Holdings that didn't exist yet count as 0%.")
            st.subheader("Purification - the share of your dividends to give to charity")
            if pur is not None and not pur.empty:
                st.markdown(f'<div class="stats">{card("To donate this year", f"{C}{pur["to_purify"].sum():,.2f}", "Dividends × the company’s non-compliant income share")}</div>',
                            unsafe_allow_html=True)
                st.dataframe(pur, width="stretch", hide_index=True, column_config={
                    "holding": "Holding",
                    "dividend_yield": st.column_config.NumberColumn("Dividend yield", format="percent"),
                    "dividend_received": money(f"Dividends you'd receive ({C})", format=money_fmt),
                    "noncompliant_share": st.column_config.NumberColumn("Non-compliant income", format="percent"),
                    "to_purify": money(f"To donate ({C})", format=money_fmt)})
            else:
                st.info("None of your holdings pay dividends that need purifying.")

    with tab_ask:
        if not llm.available():
            st.info("Add OPENAI_API_KEY to .env to enable the AI coach.")
        else:
            context = {"investor": {"type": "individual Muslim investor", "market": market, "currency": C,
                                    "amount": amount, "risk_appetite": risk, "standard": standard},
                       "screen": {t: {"status": r["verdict"]["status"], "reasons": r["verdict"]["reasons"],
                                      "review": r["verdict"]["review"], "evidence": r["business"].get("evidence")}
                                  for t, r in results.items()},
                       "stock_ranking": ranking.drop(columns=[c for c in ranking.columns if c.startswith("s_")]).to_dict("records") if not ranking.empty else [],
                       "allocation": alloc.to_dict("records") if alloc is not None else []}
            system = ("You explain a Shariah-compliant stock recommendation to an everyday Muslim investor. Answer ONLY from "
                      "the JSON context. If the answer is not in it, say so. Plain English, short. Not financial advice.\n"
                      + json.dumps(context, default=str))
            presets = ["Which stocks look strongest and why?", "Why was this split chosen?", "Which companies failed and why?",
                       "What would a bad year do to my money?", "What would make you change this?"]
            st.caption("Try a question, or type your own below. Answers come only from the results on this page.")
            cols = st.columns(len(presets))
            q = None
            for col, p in zip(cols, presets):
                if col.button(p, width="stretch"):
                    q = p
            q = st.chat_input("Ask about this recommendation") or q
            if q:
                st.chat_message("user").write(q)
                with st.spinner("Thinking..."):
                    st.chat_message("assistant").write(llm.ask(system, q))

st.markdown('<div class="disclaimer">Educational hackathon project (Microsoft × LSEG 2026). Not financial advice. '
            'Not a fatwa - this is the evidence a Shariah scholar would review, not a ruling.</div>', unsafe_allow_html=True)
