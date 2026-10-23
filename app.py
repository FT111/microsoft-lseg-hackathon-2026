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

from shariah import llm, markets, pipeline, portfolio, prices, signals, yahoo
from shariah.agents import committee, shariah_checker
from shariah.methodology import FAIL, METHODOLOGIES, NEEDS_REVIEW, PASS, STANDARDS
from shariah.universe import UK_UNIVERSE, UNIVERSE

st.set_page_config(page_title="AMANAT · Halal investing", page_icon="☾", layout="wide")

# Look and feel follows the team's "Amanat" mock: Alice-blue page, Baltic-blue accents,
# white rounded cards, DM Sans body + Space Grotesk headings.
BLUES = ["#05668d", "#427aa1", "#77a6c2", "#a8c9df", "#d2e4ef", "#0b3c5d", "#5c95b8", "#8fb8d2",
         "#034b68", "#9fc2d8", "#2f6f95", "#bcd6e6"]
SIGNAL_COLOURS = {"Strong candidate": "#05668d", "Watch": "#77a6c2", "Lower priority": "#a8c9df",
                  "Watch - near Shariah limit": "#c8553d"}
STATUS_LABEL = {PASS: "✅ Pass", FAIL: "❌ Fail", NEEDS_REVIEW: "🔎 Needs review"}
STATUS_CLASS = {PASS: "pass", FAIL: "fail", NEEDS_REVIEW: "review"}
STATUS_ICON = {PASS: "✅", FAIL: "❌", NEEDS_REVIEW: "🔎"}
MARKETS = {"UK · London Stock Exchange": {"cur": "£", "universe": UK_UNIVERSE, "label": "UK (FTSE 100)"},
           "US · New York": {"cur": "$", "universe": UNIVERSE, "label": "US"}}
# The investment objective sets the default horizon (years) and suggested risk profile.
GOALS = {"Hajj or Umrah": (3, "Cautious"), "Home purchase": (5, "Cautious"), "Education": (10, "Balanced"),
         "Wealth growth": (15, "Adventurous"), "Charitable endowment": (20, "Balanced")}
RISKS = ["Cautious", "Balanced", "Adventurous"]
# Display labels for the standards defined in shariah/methodology.py (STANDARDS order: FTSE Yasaar first, AAOIFI second).
STRICTNESS = {"FTSE Shariah · LSEG's index rules": STANDARDS[0], "AAOIFI · Islamic finance standard": STANDARDS[1]}
# Personal values on top of the Shariah screen, matched against the company's industry.
VALUES = {"🛢️ Fossil fuels": ("oil", "gas", "coal", "petroleum", "crude"),
          "⛏️ Mining": ("mining", "metals", "gold", "silver", "copper", "aluminum")}
# TradingView-style colours for up/down, and the default watchlist per market.
UP, DOWN = "#089981", "#F23645"
DOT = {PASS: "🟢", FAIL: "🔴", NEEDS_REVIEW: "🟡"}
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
.good {color:var(--pass);} .bad {color:var(--fail);} .warn-text {color:#9a7210;}

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
.fill.over {background:var(--fail);} .fill.review {background:var(--review);}
.quote {margin:.6rem 0; padding:.6rem .9rem; border-left:3px solid var(--cerulean); background:rgba(66,122,161,.06); border-radius:0 12px 12px 0;}
.limits li {margin:.25rem 0; color:var(--muted); font-size:.85rem;}

/* committee */
.gate {padding:1rem 1.2rem; border-radius:18px; margin:.4rem 0 1rem; border:1px solid var(--line); background:#fff;}
.gate.pass {border-left:6px solid var(--pass);} .gate.fail {border-left:6px solid var(--fail);} .gate.review {border-left:6px solid var(--review);}
.gate .t {font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:1.1rem;}
.fact {display:inline-block; margin:.15rem .25rem 0 0; padding:.1rem .45rem; border-radius:8px; font-size:.7rem;
       background:rgba(66,122,161,.10); color:var(--cerulean);}
.removed {color:var(--muted); text-decoration:line-through; font-size:.85rem;}
.agent-title {font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:1.05rem; margin-bottom:.3rem;}

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


def pct(v) -> str:
    return "-" if v is None else f"{v:.1%}"


def nice(category: str) -> str:
    return category.replace("_", " ")


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
                        help=f"Suggested for {goal.lower()}: {suggested}. Cautious favours steadier stocks; "
                             "Adventurous favours stronger recent momentum.")
    with col_mkt:
        st.markdown('<div class="step">Market and amount</div>', unsafe_allow_html=True)
        market = st.radio("Market", list(MARKETS), help="Search covers any listed company; this sets the "
                          "portfolio's stock list and currency.")
        C = MARKETS[market]["cur"]
        amount = st.number_input(f"Amount to invest ({C})", 1_000, 10_000_000, 100_000, step=5_000)
        top_n = st.slider("Number of holdings", 3, 20, 10)
        eq = st.slider("Allocation to Shariah-screened equities", 0.5, 1.0, 1.0, 0.05,
                       help="The rest is held as non-interest-bearing cash.")
    with col_scr:
        st.markdown('<div class="step">Screening</div>', unsafe_allow_html=True)
        standard = STRICTNESS[st.radio("Shariah standard", list(STRICTNESS),
                                       help="Each standard is applied on its own - their rules are never mixed. FTSE Yasaar "
                                            "measures ratios against total assets; AAOIFI against 12-month average market value.")]
        avoid = st.pills("Also exclude", list(VALUES), selection_mode="multi", key="avoid") or []
        use_llm = st.toggle("Use AI to read US annual reports (10-Ks)", value=llm.available(), disabled=not llm.available(),
                            help="Needs OPENAI_API_KEY in .env. Without it, only the industry code is checked and most "
                                 "companies need a person to review them.")
        tickers = st.multiselect("Stocks to consider", MARKETS[market]["universe"], default=MARKETS[market]["universe"])
meth = METHODOLOGIES[standard]


def against_values(r: dict) -> list[str]:
    """Which of the investor's own 'also avoid' values this company's industry hits.
    A personal preference on top of the Shariah screen - it never changes a screening result."""
    industry = (r.get("sic") or "").lower()
    return [v for v in avoid if any(w in industry for w in VALUES[v])]


# ---------------- screening (shared by both pages) ----------------
@st.cache_data(show_spinner=False)
def screen_one(t: str, std: str, use_ai: bool):
    return pipeline.screen_one(t, std, use_ai)


@st.cache_data(show_spinner=False)
def metrics_for(t: str):
    return signals.price_metrics(t)


def plain_why(v: dict) -> str:
    """One friendly sentence saying what the result means."""
    if v["status"] == PASS:
        return f"Meets every {html.escape(standard)} screen we can check. That is not a religious ruling - it means the " \
               f"numbers and the annual report raise no flag under this standard."
    if v["status"] == FAIL:
        fails = [s for s in v["screens"] if s["status"] == FAIL]
        return "Excluded under this standard because: " + html.escape("; ".join(s["label"].lower() + (f" is {s['value']:.1%}"
                                                                                                        if s.get("value") is not None else "")
                                                                                 + (f" (limit {s['op']} {s['limit']:.1%})" if s.get("limit") else "")
                                                                                 for s in fails)) + "."
    revs = [s for s in v["screens"] if s["status"] == NEEDS_REVIEW]
    return "A person needs to check before this could be held: " + html.escape("; ".join(s["label"].lower() for s in revs)) + "."


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


# ================= the investment committee (used on both pages) =================
def fact_chips(ids, facts) -> str:
    return "".join(f'<span class="fact" title="{html.escape(str(facts.get(i, {}).get("source", "")))}">'
                   f'{html.escape(facts.get(i, {}).get("label", "")[:38])}: '
                   f'{html.escape(str(facts.get(i, {}).get("display", ""))[:30])}</span>' for i in ids)


def show_case(case, title, facts):
    st.markdown(f'<div class="agent-title">{title}</div>', unsafe_allow_html=True)
    if not case or not case.get("available"):
        st.caption("This analyst was unavailable.")
        return
    if case.get("thesis"):
        st.markdown(case["thesis"])
    for p in case.get("points", []):
        st.markdown(f"- {html.escape(p['claim'])}<br>{fact_chips(p['facts'], facts)}", unsafe_allow_html=True)
    if case.get("change"):
        st.caption("What would change this view: " + case["change"])


def render_committee(r: dict, key: str, position=None, rank_row=None, stress=None) -> None:
    """Gate banner (always), then the four-agent discussion on request."""
    t, v = r["ticker"], r["verdict"]
    g = shariah_checker.gate(r)
    cls = STATUS_CLASS[g["status"]]
    items = "".join(f"<li>{html.escape(x)}</li>" for x in (g["reasons"] + g["review"])[:6])
    st.markdown(f'<div class="gate {cls}"><div class="label">Step 1 · Shariah compliance check (decides first, audits last)</div>'
                f'<div class="t">{STATUS_LABEL[g["status"]]} under {html.escape(g["standard"])}</div>'
                f'<div class="sub">{html.escape(g["banner"])}</div><ul class="sub">{items}</ul></div>', unsafe_allow_html=True)
    if g["status"] == FAIL:
        st.caption("Excluded companies are not discussed further - the compliance check has the final word.")
        return
    if not llm.available():
        st.info("Add OPENAI_API_KEY to .env to let the analysts discuss this company.")
        return
    skey = f"committee_{t}_{standard}"
    if st.button("Ask the investment committee", key=f"btn_{key}", help="Two analysts argue for and against, a risk "
                 "reviewer weighs them, and the Shariah checker audits every sentence. About 20 seconds."):
        try:
            m = metrics_for(t)
        except Exception:
            m = None
        with st.spinner("The analysts are reading the evidence..."):
            st.session_state[skey] = committee.run(r, m, rank_row, position, stress)
    res = st.session_state.get(skey)
    if not res or not res.get("ran"):
        return
    facts = res["facts"]
    c1, c2 = st.columns(2, gap="large")
    with c1:
        show_case(res["bull"], "Step 2 · The case for holding it", facts)
    with c2:
        show_case(res["bear"], "Step 3 · The case against", facts)
    rk = res["risk"]
    st.markdown('<div class="agent-title">Step 4 · Risk check</div>', unsafe_allow_html=True)
    if not rk.get("available"):
        st.caption("The risk reviewer was unavailable.")
    else:
        if rk.get("flag"):
            st.markdown(f'<span class="tag warn">Flag: {html.escape(rk["flag"])}</span>', unsafe_allow_html=True)
        if rk.get("summary"):
            st.markdown(rk["summary"])
        for p in rk["key_risks"]:
            st.markdown(f"- {html.escape(p['claim'])}<br>{fact_chips(p['facts'], facts)}", unsafe_allow_html=True)
        if rk.get("unsupported_claims"):
            st.caption("Claims the reviewer found unsupported: " + "; ".join(rk["unsupported_claims"]))
    a = res["audit"]
    if a["approved"]:
        st.success("Step 5 · Shariah audit: every statement above was checked and approved.")
    elif not a["llm_checked"]:
        st.warning("Step 5 · Shariah audit: the rule checks ran, but the AI audit was unavailable. Read the statements with care.")
    if a["removed"]:
        st.warning(f"Step 5 · Shariah audit removed {len(a['removed'])} statement(s) that broke the rules:")
        for sid, why in a["removed"].items():
            st.markdown(f'<div class="removed">{html.escape(a["removed_text"].get(sid, ""))}</div>'
                        f'<div class="sub">{html.escape("; ".join(why))}</div>', unsafe_allow_html=True)
    dropped = res["bull"]["dropped"] + res["bear"]["dropped"] + res["risk"]["dropped"]
    if dropped:
        with st.expander(f"{len(dropped)} claim(s) removed because they cited no evidence or used numbers not in it"):
            for d in dropped:
                st.markdown(f"- {html.escape(d['text'])} - _{html.escape(d['why'])}_")
    with st.expander("The evidence the analysts were allowed to use"):
        st.dataframe(pd.DataFrame([{"Fact": f["label"], "Value": f["display"], "Source": f["source"], "Period": f["period"]}
                                   for f in facts.values()]), width="stretch", hide_index=True)
    st.caption(res["disclaimer"])


# ================= page 1: check any company =================
def ratio_row(s: dict, source: str) -> str:
    label, value, limit = s["label"], s.get("value"), s.get("limit")
    lim_txt = f"limit {s['op']} {limit:.1%}" if limit else ""
    if value is None:
        return (f'<div class="ratio"><div class="ratio-top"><b>{html.escape(label)}</b><span class="warn-text">🔎 no data · {lim_txt}</span></div>'
                f'<div class="meta">{html.escape(s.get("note") or source or "not reported")}</div></div>')
    cls = {PASS: "good", FAIL: "bad", NEEDS_REVIEW: "warn-text"}[s["status"]]
    fill = {PASS: "", FAIL: " over", NEEDS_REVIEW: " review"}[s["status"]]
    width = min(value / limit, 1.0) * 100 if limit else 0
    note = s.get("note") or source or ""
    return (f'<div class="ratio"><div class="ratio-top"><b>{html.escape(label)}</b>'
            f'<span class="{cls}">{value:.1%} · {lim_txt} {STATUS_ICON[s["status"]]}</span></div>'
            f'<div class="bar"><div class="fill{fill}" style="width:{width:.0f}%"></div></div>'
            f'<div class="meta">{html.escape(note[:220])}</div></div>')


def company_report(symbol: str, exchange: str) -> None:
    with st.spinner(f"Checking {symbol}..."):
        r = screen_one(symbol, standard, use_llm)
    fin, v, b, p = r["fin"], r["verdict"], r["business"], r.get("profile") or {}
    clashes = against_values(r)
    cur = r.get("currency") or ""
    meta = " · ".join(html.escape(str(x)) for x in (symbol, exchange or p.get("exchange"), p.get("industry"), p.get("country")) if x)

    with st.container(key="panel_report_head"):
        st.markdown(f'<div class="report-head"><div><div class="label">Shariah screen · {html.escape(standard)}</div>'
                    f'<div class="report-name">{html.escape(fin["name"])}</div><div class="meta">{meta}</div></div>'
                    f'<div class="verdict {STATUS_CLASS[v["status"]]}">{STATUS_LABEL[v["status"]]}</div></div>'
                    f'<div class="why">{plain_why(v)}</div>'
                    + (f'<div class="values-note">Heads up: you asked to also avoid '
                       f'{html.escape(", ".join(c.split(" ", 1)[1].lower() for c in clashes))} - this company is in '
                       f'{html.escape(p.get("industry") or "")}.</div>' if clashes else ""), unsafe_allow_html=True)
        starred = symbol in st.session_state.get(f"watch_{market}", WATCH[market])
        st.button("★ In your watchlist" if starred else "☆ Add to watchlist", key=f"star_{symbol}",
                  on_click=toggle_watch, args=(symbol,))

    left, right = st.columns([1.15, 1], gap="large")
    with left, st.container(key="panel_ratios"):
        denom = meth["ratios"][0]["denominator"].replace("_", " ")
        st.markdown(f'<div class="label">Financial screens · share of {denom}</div>', unsafe_allow_html=True)
        rows = []
        for s in v["screens"]:
            if s["key"] == "activity":
                continue
            if s["key"] == "freshness":
                rows.append(f'<div class="ratio"><div class="ratio-top"><b>Data freshness</b><span class="warn-text">🔎</span></div>'
                            f'<div class="meta">{html.escape(s["note"])}</div></div>')
                continue
            src_key = {"debt": "total_debt", "cash": "cash_and_interest_bearing", "receivables_plus_cash": "receivables",
                       "noncompliant_income": "interest_income"}.get(s["key"], "")
            rows.append(ratio_row(s, fin["sources"].get(src_key, "")))
        st.markdown("".join(rows), unsafe_allow_html=True)
        st.caption(f"Figures in {cur}, balance sheet dated {fin.get('period_end') or 'unknown'}. "
                   + (f"Market value {big_money('', r['mcap']['value'])} {cur} ({r['mcap']['note']})." if r.get("mcap") and
                      meth["ratios"][0]["denominator"] == "market_cap" else ""))

    with right, st.container(key="panel_business"):
        act = next(s for s in v["screens"] if s["key"] == "activity")
        st.markdown(f'<div class="label">Business activity · {STATUS_ICON[act["status"]]} {act["status"].title()}</div>',
                    unsafe_allow_html=True)
        acts = b.get("activities") or []
        if not acts:
            st.markdown("**No excluded activity found**" + (" in the annual report." if b.get("method") == "LLM" else
                                                           " in the industry classification."))
        for a in acts:
            share = (f"~{a['revenue_share_pct']:.0f}% of revenue" if a.get("revenue_share_pct") is not None else
                     f"at least {a['min_revenue_share_pct']:.0f}% of revenue" if a.get("min_revenue_share_pct") else
                     "share of revenue not stated")
            head = f"**{nice(a['category']).capitalize()}** · {share}" + (" · main business" if a.get("primary_business") else "")
            st.markdown(head)
            if a.get("evidence"):
                tick = "✓ quote found in the filing" if a.get("quote_verified") else "✗ quote NOT found in the filing - not used as evidence"
                st.markdown(f'<div class="quote">{html.escape(str(a["evidence"])[:400])}<div class="meta">{tick}</div></div>',
                            unsafe_allow_html=True)
        if act.get("note"):
            st.caption(act["note"])
        st.caption("Checked by: " + {"LLM": "AI reading of the latest annual report, every quote verified in Python",
                                     "SIC rule": "SEC industry code only", "Industry rule": "Yahoo Finance industry only"}
                   .get(b.get("method"), str(b.get("method"))))
        if b.get("main_business") and b.get("method") == "LLM":
            st.caption("What the company does: " + b["main_business"])
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
        st.markdown('<div class="label">AI investment committee</div>', unsafe_allow_html=True)
        st.caption("Four AI agents, in a fixed order. The Shariah compliance check decides first and audits everything "
                   "at the end; the analysts can only explain, never change a result. Every claim must point to a fact "
                   "shown on this page.")
        render_committee(r, key=f"report_{symbol}")

    limits = ["This is research support, not a fatwa - a Shariah scholar makes the ruling.",
              f"Standard applied: {meth['source']} (checked {meth['verified_on']}). {meth['verification_note']}"]
    if fin.get("missing"):
        limits.append("Not reported in the data we have: " + ", ".join(nice(m) for m in fin["missing"]) +
                      " - those screens need a person to check.")
    limits += [n for n in fin.get("notes", [])]
    if r["source"] == "Yahoo Finance":
        limits += ["Figures are Yahoo Finance's copy of the accounts, not the filing itself - check the company's annual report.",
                   "Business activity is judged from the industry classification only: it can exclude a company, but it "
                   "cannot confirm one as clear, so non-US companies need a person to check that screen."]
    else:
        limits += ["Figures come straight from the company's SEC filings (XBRL), all from one balance-sheet date."]
    links = " · ".join(f"[{t}]({u})" for t, u in (("Filing / data source", b.get("source_url") or fin.get("source_url")),
                                                  ("Company website", p.get("website")),
                                                  ("Methodology", meth["url"])) if u)
    with st.expander("Sources and limitations"):
        st.markdown(f"**Source:** {r['source']}" + (f" · {links}" if links else ""))
        st.markdown('<ul class="limits">' + "".join(f"<li>{html.escape(x)}</li>" for x in limits) + "</ul>",
                    unsafe_allow_html=True)
        items = fin.get("items") or {}
        if items:
            st.dataframe(pd.DataFrame([{"Item": nice(k), "Value": (f"{it['value'] / 1e9:,.2f}bn {cur}" if it and k !=
                                        "shares_outstanding" else f"{it['value'] / 1e9:,.3f}bn shares" if it else "not reported"),
                                        "Source row / concept": it["concept"] if it else "-",
                                        "Period end": (it or {}).get("period_end", "-")} for k, it in items.items()]),
                         width="stretch", hide_index=True)


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
                errors.append(f"{t}: {type(e).__name__}: {e}")

    statuses = {t: r["verdict"]["status"] for t, r in results.items()}
    counts = {s: sum(x == s for x in statuses.values()) for s in STATUS_LABEL}
    passing = [t for t, s in statuses.items() if s == PASS]
    removed = [t for t in passing if against_values(results[t])]  # the investor's own values, not the Shariah screen
    passing = [t for t in passing if t not in removed]
    ranking = signals.rank({t: results[t] for t in passing}, signals.PROFILES[risk]) if passing else pd.DataFrame()
    picks = [] if ranking.empty else ranking[~ranking["signal"].str.startswith("Watch - near")]["ticker"].head(top_n).tolist()
    holdings = picks or ([] if ranking.empty else ranking["ticker"].head(top_n).tolist())

    alloc = stt = pur = None
    if holdings:
        try:
            alloc = portfolio.build(holdings, statuses, amount, eq)
            stt = portfolio.stress_test(alloc, amount=amount)
            nc = {t: results[t]["verdict"]["noncompliant_income_pct"] for t in holdings}
            pur = portfolio.purification(alloc, {t: results[t]["fin"] for t in holdings}, nc, standard)
        except portfolio.NotCompliantError as e:
            errors.append(str(e))
            alloc = None
        except Exception as e:
            errors.append(f"portfolio: {e}")

    st.markdown(f"""<div class="hero"><div class="eyebrow">Portfolio · {html.escape(goal)} · {years}-year horizon</div>
<h1>Shariah-screened portfolio</h1>
<p>We check {len(results)} {MARKETS[market]["label"]} companies against the {html.escape(standard)} rules, rank only the ones
that pass every screen for a <b>{risk.lower()}</b> risk profile, and show what that means for {C}{amount:,.0f} - with the
evidence behind every result.</p></div>""", unsafe_allow_html=True)

    if alloc is None:
        st.info("No company in this list passes every screen of this standard, so there is nothing to invest in yet. "
                "Non-US companies always need a person to confirm the business-activity screen - try the US market.")
        if errors:
            with st.expander(f"{len(errors)} items could not be loaded"):
                st.write(errors)
    else:
        names = {r["ticker"]: r["company"] for _, r in ranking.iterrows()}

        # ---- 1. the portfolio ----
        heading("1 · Your portfolio", f"{C}{amount:,.0f} · {len(holdings)} stocks · max 10% in any one")
        with st.container(key="panel_donut"):
            donut = alloc.assign(label=alloc["holding"].map(lambda h: names.get(h, "Non-interest cash" if h == "CASH" else h)))
            fig = px.pie(donut, names="label", values="amount", hole=.55, color_discrete_sequence=BLUES)
            fig.update_traces(textinfo="percent+label", textposition="inside", insidetextorientation="radial",
                              hovertemplate=f"%{{label}}<br>{C}%{{value:,.0f}} (%{{percent}})<extra></extra>")
            fig.update_layout(showlegend=False)
            st.plotly_chart(styled(fig, 520), width="stretch")
            st.caption("Every holding passed every screen of the selected standard. Calmer stocks get a larger share "
                       "(inverse volatility), capped at 10% each; any remainder is non-interest-bearing cash. "
                       "Deterministic maths - the AI does not choose the numbers.")

        # ---- 2. the ten picks ----
        heading("2 · Ten recommended picks", f"{risk} profile · ranked by momentum, steadiness and Shariah headroom")
        with st.container(key="panel_top"):
            rows = []
            for i, (_, r) in enumerate(ranking.head(10).iterrows(), 1):
                share = alloc.set_index("holding")["amount"].get(r["ticker"])
                rows.append(f'<div class="row"><div><div class="name">{i}. {html.escape(r["company"])}</div>'
                            f'<div class="meta">{r["ticker"]} · {r["return_1y"]:+.0%} over the past year · '
                            f'{r["headroom"]:.0%} room below the nearest Shariah limit'
                            + (f" · {C}{share:,.0f} in your plan" if share else " · not in your plan") + '</div>'
                            f'<span class="tag{" warn" if r["signal"].startswith("Watch - near") else ""}">{r["signal"]}</span></div>'
                            f'<div class="score">{r["score"]:.0f}/100</div></div>')
            st.markdown("".join(rows), unsafe_allow_html=True)
            st.caption("Only stocks that pass every screen are ranked. This ranks candidates for holding; it does not "
                       "predict prices. Open any company on the Check a company page for the evidence and the committee.")

        # ---- 3. presence in Muslim-majority markets ----
        heading("3 · Three picks with a footprint in Muslim-majority markets",
                "what their own annual reports say")
        with st.container(key="panel_markets"):
            if market.startswith("UK"):
                st.info("This check reads the company's SEC annual report, which UK-listed companies don't file. "
                        "Switch to the US market to see it.")
            else:
                with st.spinner("Reading the annual reports..."):
                    footprint = markets.rank(ranking["ticker"].tolist(), top=3)
                if not footprint:
                    st.info("None of the passing companies' annual reports name a Muslim-majority country.")
                for i, f in enumerate(footprint, 1):
                    where = ", ".join(f["countries"][:6]) + (f" and {len(f['countries']) - 6} more" if len(f["countries"]) > 6 else "")
                    st.markdown(f'<div class="row"><div><div class="name">{i}. {html.escape(names.get(f["ticker"], f["ticker"]))}</div>'
                                f'<div class="meta">{f["ticker"]} · names {len(f["countries"])} Muslim-majority '
                                f'{"country" if len(f["countries"]) == 1 else "countries"}: {html.escape(where)}'
                                + (f' · also "{html.escape(", ".join(f["regions"]))}"' if f["regions"] else "") + '</div>'
                                + (f'<div class="quote">{html.escape(f["quote"][:360])}<div class="meta">✓ verbatim from the '
                                   f'<a href="{f["url"]}">10-K filed {f["date"]}</a></div></div>' if f["quote"] else "")
                                + '</div></div>', unsafe_allow_html=True)
                st.caption("Chosen from the passing stocks by how many Muslim-majority (OIC) countries their latest 10-K "
                           "names in a business context, with the sentence quoted. This shows where a company operates or "
                           "sells - it is evidence of presence, not an ethics rating, and it says nothing about who runs "
                           "the company. Passing the screens is not a religious ruling.")

st.markdown('<div class="disclaimer">Educational hackathon project (Microsoft × LSEG 2026). Not financial advice. '
            'Not a fatwa - this is the evidence a Shariah scholar would review, not a ruling.</div>', unsafe_allow_html=True)
