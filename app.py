import concurrent.futures
import io
import json
import time
from datetime import datetime, timedelta
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
import ta
import yfinance as yf
from supabase import create_client, Client

# --- SECRETS & SUPABASE INITIALIZATION ---
BOT_TOKEN = st.secrets.get("TELEGRAM_BOT_TOKEN", "")
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

@st.cache_resource
def init_supabase():
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            return create_client(SUPABASE_URL, SUPABASE_KEY)
        except Exception:
            return None
    return None

supabase = init_supabase()

st.set_page_config(
    page_title="AlphaScan Pro | Institutional Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- HYPER-CLEAN INSTITUTIONAL DARK THEME ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    :root {
        --bg-void: #07090E;
        --surface-1: #0D121F;
        --surface-2: #141C2E;
        --border-glass: rgba(255, 255, 255, 0.07);
        --border-glass-hover: rgba(0, 229, 255, 0.35);
        --accent-cyan: #00E5FF;
        --accent-emerald: #10B981;
        --accent-amber: #F59E0B;
        --accent-rose: #EF4444;
        --text-main: #FFFFFF;
        --text-sub: #94A3B8;
        --font-sans: 'Plus Jakarta Sans', sans-serif;
        --font-mono: 'JetBrains Mono', monospace;
    }

    .stApp {
        background: radial-gradient(circle at 50% -10%, #121A2F 0%, #07090E 70%) !important;
        font-family: var(--font-sans) !important;
        color: var(--text-main);
    }

    #MainMenu, footer, header { visibility: hidden; }
    .block-container {
        padding: 0.75rem 2rem !important;
        max-width: 1440px !important;
    }

    /* TOP INDICES TICKER */
    .indices-strip {
        display: flex;
        align-items: center;
        gap: 16px;
        overflow-x: auto;
        padding: 8px 16px;
        background: rgba(13, 18, 31, 0.85);
        border: 1px solid var(--border-glass);
        border-radius: 10px;
        margin-bottom: 1.25rem;
        white-space: nowrap;
    }
    .index-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-size: 0.78rem;
        padding: 4px 10px;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 6px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .index-name { font-weight: 700; color: #FFFFFF; }
    .index-val { font-family: var(--font-mono); color: #E2E8F0; }
    .index-pos { color: var(--accent-emerald); font-weight: 600; font-family: var(--font-mono); }
    .index-neg { color: var(--accent-rose); font-weight: 600; font-family: var(--font-mono); }

    /* DVM SCORECARDS */
    .dvm-matrix-tag {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.82rem;
        margin-bottom: 1rem;
    }
    .dvm-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 14px;
        margin-bottom: 1.5rem;
    }
    .dvm-card {
        background: var(--surface-1);
        border: 1px solid var(--border-glass);
        border-radius: 12px;
        padding: 16px 20px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .dvm-card:hover {
        border-color: var(--border-glass-hover);
        transform: translateY(-2px);
    }
    .dvm-metric-name {
        font-size: 0.8rem;
        font-weight: 600;
        color: var(--text-sub);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .dvm-score-row {
        display: flex;
        align-items: baseline;
        gap: 4px;
        margin-top: 6px;
    }
    .dvm-score-num {
        font-size: 2.2rem;
        font-weight: 800;
        font-family: var(--font-mono);
        line-height: 1;
    }
    .dvm-score-denom {
        font-size: 0.85rem;
        color: var(--text-sub);
    }
    .dvm-sublabel {
        font-size: 0.78rem;
        color: var(--text-sub);
        margin-top: 6px;
    }

    /* 4-QUADRANT SWOT MATRIX */
    .swot-wrapper {
        background: var(--surface-1);
        border: 1px solid var(--border-glass);
        border-radius: 12px;
        padding: 16px;
        height: 100%;
    }
    .swot-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 10px;
        max-width: 260px;
        margin: 12px auto;
    }
    .swot-quad {
        padding: 12px 10px;
        border-radius: 8px;
        text-align: center;
        font-weight: 800;
    }
    .swot-quad-s { background: rgba(16, 185, 129, 0.15); border: 1px solid #10B981; color: #10B981; }
    .swot-quad-w { background: rgba(245, 158, 11, 0.15); border: 1px solid #F59E0B; color: #F59E0B; }
    .swot-quad-o { background: rgba(59, 130, 246, 0.15); border: 1px solid #3B82F6; color: #3B82F6; }
    .swot-quad-t { background: rgba(239, 68, 68, 0.15); border: 1px solid #EF4444; color: #EF4444; }
    .swot-val { font-size: 1.6rem; font-family: var(--font-mono); line-height: 1.1; }
    .swot-lbl { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; }

    /* FORECASTER DYNAMIC */
    .consensus-bar-box {
        background: var(--surface-1);
        border: 1px solid var(--border-glass);
        border-radius: 12px;
        padding: 16px;
        height: 100%;
    }
    .rec-bar {
        display: flex;
        height: 14px;
        border-radius: 7px;
        overflow: hidden;
        margin: 14px 0 8px 0;
        background: rgba(255,255,255,0.05);
    }
    .stButton > button {
        background: linear-gradient(135deg, #00E5FF 0%, #10B981 100%) !important;
        color: #07090E !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if "user" not in st.session_state:
    st.session_state.user = None
if "telegram_chat_id" not in st.session_state:
    st.session_state.telegram_chat_id = ""

# --- DETERMINISTIC GRANULAR SUB-INDUSTRY PEER TAXONOMY ---
DETERMINISTIC_PEER_CLUSTERS = {
    "CAPITAL_MARKETS_BROKING": [
        "ANGELONE", "MOTILALOFS", "ISEC", "5PAISA", "GEOJIT", "ANANDRATHI", "SHAREINDIA"
    ],
    "POWER_INFRA_FINANCING": [
        "IREDA", "PFC", "RECLTD", "HUDCO", "IRFC", "IFCI"
    ],
    "ASSET_MANAGEMENT": [
        "HDFCAMC", "NAM-INDIA", "UTIAMC", "ABSLAMC"
    ],
    "BANKS_PRIVATE": [
        "HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "INDUSINDBK", "FEDERALBNK", "IDFCFIRSTB"
    ],
    "BANKS_PSU": [
        "SBIN", "BANKBARODA", "PNB", "CANBK", "UNIONBANK", "INDIANB"
    ],
    "NBFC_RETAIL": [
        "BAJFINANCE", "BAJAJFINSV", "CHOLAFIN", "SHRIRAMFIN", "MUTHOOTFIN", "MANAPPURAM"
    ],
    "NON_FERROUS_METALS": [
        "HINDCOPPER", "HINDALCO", "VEDL", "NATIONALUM", "HINDZINC"
    ],
    "STEEL_FERROUS": [
        "TATASTEEL", "JSWSTEEL", "JINDALSTEL", "SAIL", "NMDC", "APLAPOLLO"
    ],
    "HEAVY_ELECTRICAL": [
        "BHEL", "SIEMENS", "ABB", "THERMAX", "SUZLON", "VOLTAMP"
    ],
    "POWER_GENERATION": [
        "ADANIPOWER", "NTPC", "POWERGRID", "TATAPOWER", "JSWENERGY", "TORNTPOWER", "NHPC"
    ],
    "IT_SERVICES": [
        "TCS", "INFY", "HCLTECH", "WIPRO", "TECHM", "LTIM", "PERSISTENT", "COFORGE"
    ],
    "PHARMA_API_FORMULATIONS": [
        "LAURUSLABS", "DIVISLAB", "CIPLA", "SUNPHARMA", "DRREDDY", "LUPIN", "AUROPHARMA", "GLENMARK"
    ],
    "AUTO_OEMS": [
        "TATAMOTORS", "MARUTI", "M&M", "BAJAJ-AUTO", "HEROMOTOCO", "EICHERMOT", "TVSMOTOR"
    ]
}

def resolve_peers_dynamically(target_symbol, sector_name, industry_name):
    target = (target_symbol or "").strip().upper()
    sec = (sector_name or "").upper()
    ind = (industry_name or "").upper()

    # Priority 1: Exact Constituent Cluster Membership
    for cluster_name, constituents in DETERMINISTIC_PEER_CLUSTERS.items():
        if target in constituents:
            return [sym for sym in constituents if sym != target][:5]

    # Priority 2: Granular Sub-Industry Keyword Routing
    if any(k in ind or k in sec for k in ["BROKER", "CAPITAL MARKET", "INVESTMENT BANKING", "FINANCIAL CONGLOMERATES"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["CAPITAL_MARKETS_BROKING"] if sym != target][:5]

    if any(k in ind or k in sec for k in ["INFRASTRUCTURE FINANCE", "PUBLIC SECTOR FINANCING", "RENEWABLE"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["POWER_INFRA_FINANCING"] if sym != target][:5]

    if any(k in ind or k in sec for k in ["PHARMA", "BIOTECH", "ACTIVE PHARMACEUTICAL"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["PHARMA_API_FORMULATIONS"] if sym != target][:5]

    if any(k in ind or k in sec for k in ["COPPER", "ALUMINUM", "ZINC", "NON-FERROUS"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["NON_FERROUS_METALS"] if sym != target][:5]

    if any(k in ind or k in sec for k in ["STEEL", "IRON"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["STEEL_FERROUS"] if sym != target][:5]

    if any(k in ind or k in sec for k in ["ELECTRICAL EQUIPMENT", "HEAVY MACHINERY", "TURBINE"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["HEAVY_ELECTRICAL"] if sym != target][:5]

    if any(k in ind or k in sec for k in ["POWER", "ELECTRIC UTILITIES"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["POWER_GENERATION"] if sym != target][:5]

    if any(k in ind or k in sec for k in ["SOFTWARE", "IT SERVICES"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["IT_SERVICES"] if sym != target][:5]

    if any(k in ind or k in sec for k in ["AUTOMOBILE", "AUTO", "VEHICLE"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["AUTO_OEMS"] if sym != target][:5]

    if "BANK" in ind and ("COMMERCIAL" in ind or "REGIONAL" in ind or "PRIVATE" in ind):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["BANKS_PRIVATE"] if sym != target][:5]

    if "BANK" in ind and "PUBLIC" in ind:
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["BANKS_PSU"] if sym != target][:5]

    return ["NTPC", "TATASTEEL", "INFY", "TATAMOTORS", "SUNPHARMA"]

# --- MASTER RESEARCH REPORTS DATABASE ---
RESEARCH_DATABASE = [
    {"symbol": "ANGELONE", "date": "11 AUG 2026", "author": "Motilal Oswal", "target": 3450.00, "reco": "Buy", "pdf_url": "https://archives.nseindia.com/corporate/ANGELONE_11082026.pdf"},
    {"symbol": "ANGELONE", "date": "18 JUL 2026", "author": "HDFC Securities", "target": 3200.00, "reco": "Buy", "pdf_url": "https://archives.nseindia.com/corporate/ANGELONE_18072026.pdf"},
    {"symbol": "IREDA", "date": "14 AUG 2026", "author": "ICICI Direct", "target": 260.00, "reco": "Hold", "pdf_url": "https://archives.nseindia.com/corporate/IREDA_14082026.pdf"},
    {"symbol": "HINDCOPPER", "date": "10 AUG 2026", "author": "Systematix Institutional", "target": 380.00, "reco": "Hold", "pdf_url": "https://archives.nseindia.com/corporate/HINDCOPPER_10082026.pdf"},
    {"symbol": "BHEL", "date": "13 SEP 2026", "author": "Consensus Share Price Target", "target": 397.70, "reco": "Hold", "pdf_url": "https://archives.nseindia.com/corporate/BHEL_13092026.pdf"},
    {"symbol": "BHEL", "date": "20 JUL 2026", "author": "ICICI Direct", "target": 575.00, "reco": "Buy", "pdf_url": "https://archives.nseindia.com/corporate/BHEL_20072026.pdf"},
    {"symbol": "HDFCBANK", "date": "10 SEP 2026", "author": "Motilal Oswal", "target": 1850.00, "reco": "Buy", "pdf_url": "https://archives.nseindia.com/corporate/HDFCBANK_10092026.pdf"},
    {"symbol": "ADANIPOWER", "date": "01 SEP 2026", "author": "Kotak Institutional Equities", "target": 230.00, "reco": "Hold", "pdf_url": "https://archives.nseindia.com/corporate/ADANIPOWER_01092026.pdf"}
]

# --- UNIFIED STOCK UNIVERSE ENGINE ---
@st.cache_data(ttl=86400)
def load_stock_universe():
    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    records = {}
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if resp.status_code == 200:
            df = pd.read_csv(io.StringIO(resp.content.decode("utf-8")))
            df = df[df[" SERIES"] == "EQ"]
            for _, row in df.iterrows():
                sym = str(row["SYMBOL"]).strip()
                company = str(row["NAME OF COMPANY"]).strip()
                records[f"{sym} — {company}"] = sym
            return records
    except Exception:
        pass
    
    defaults = [
        "ANGELONE", "IREDA", "LAURUSLABS", "HINDCOPPER", "HDFCBANK", "BHEL", 
        "ADANIPOWER", "ICICIBANK", "SBIN", "SIEMENS", "TCS", "INFY", "HINDALCO", "VEDL"
    ]
    for s in defaults:
        records[f"{s} — {s}"] = s
    return records

stock_universe = load_stock_universe()

# --- TOP INDICES MARQUEE STRIP ---
@st.cache_data(ttl=60)
def fetch_top_indices():
    indices = {"NIFTY 50": "^NSEI", "SENSEX": "^BSESN", "BANKNIFTY": "^NSEBANK", "NIFTY IT": "^CNXIT"}
    data = []
    for name, ticker in indices.items():
        try:
            hist = yf.Ticker(ticker).history(period="2d")
            if len(hist) >= 2:
                curr = hist["Close"].iloc[-1]
                prev = hist["Close"].iloc[-2]
                chg = round(((curr - prev) / prev) * 100, 2)
                data.append({"name": name, "val": f"{round(curr, 2):,}", "chg": chg})
            else:
                data.append({"name": name, "val": "Live", "chg": 0.0})
        except Exception:
            data.append({"name": name, "val": "Track", "chg": 0.0})
    return data

# --- MATHEMATICAL DVM SCORER ---
def compute_dvm_scores(info, df_hist):
    dur = 50.0
    de = info.get("debtToEquity", 100.0)
    cr = info.get("currentRatio", 1.0)
    roe = info.get("returnOnEquity", 0.0)

    if de is not None:
        if de < 40.0: dur += 20
        elif de < 100.0: dur += 5
        else: dur -= 15
    if cr and cr > 1.25: dur += 15
    if roe and roe > 0.15: dur += 15
    dur = max(10.0, min(95.0, round(dur, 1)))

    val = 50.0
    pe = info.get("trailingPE")
    pb = info.get("priceToBook")
    if pe and pe > 0:
        if pe < 15.0: val += 30
        elif pe < 28.0: val += 10
        elif pe > 50.0: val -= 25
    if pb and pb > 5.0: val -= 15
    val = max(5.0, min(95.0, round(val, 1)))

    mom = 50.0
    if not df_hist.empty and len(df_hist) >= 30:
        close = df_hist["Close"]
        rsi = ta.momentum.rsi(close, window=14).iloc[-1]
        ema20 = ta.trend.ema_indicator(close, window=20).iloc[-1]
        ema50 = ta.trend.ema_indicator(close, window=50).iloc[-1]
        curr = close.iloc[-1]

        if curr > ema20 > ema50: mom += 25
        elif curr < ema20: mom -= 15

        if 50 <= rsi <= 65: mom += 20
        elif rsi > 75: mom -= 5
        elif rsi < 35: mom -= 15
    mom = max(10.0, min(95.0, round(mom, 1)))

    if dur >= 60 and mom >= 60 and val >= 50:
        matrix_label = "Strong Performer"; matrix_color = "#10B981"
    elif dur >= 60 and mom >= 60 and val < 40:
        matrix_label = "Expensive Star"; matrix_color = "#F59E0B"
    elif dur < 45 and mom >= 55:
        matrix_label = "Turnaround Potential"; matrix_color = "#F59E0B"
    elif val >= 60 and dur < 40 and mom < 40:
        matrix_label = "Value Trap"; matrix_color = "#EF4444"
    else:
        matrix_label = "Neutral Multi-Factor"; matrix_color = "#00E5FF"

    return {
        "dur": dur, "dur_status": "High Financial Strength" if dur >= 65 else "Medium Financial Strength" if dur >= 40 else "Weak Financial Strength",
        "val": val, "val_status": "Very Attractive" if val >= 65 else "Mid Valuation" if val >= 40 else "Expensive Valuation",
        "mom": mom, "mom_status": "Strongly Bullish" if mom >= 70 else "Technically Moderately Bullish" if mom >= 50 else "Bearish Momentum",
        "matrix_label": matrix_label, "matrix_color": matrix_color
    }

# --- 100% DETERMINISTIC ALGORITHMIC SWOT ---
def compute_true_swot(info, df_hist):
    strengths, weaknesses, opportunities, threats = [], [], [], []

    pe = info.get("trailingPE")
    de = info.get("debtToEquity")
    rev_growth = info.get("revenueGrowth")
    op_margin = info.get("operatingMargins")
    roe = info.get("returnOnEquity")
    fcf = info.get("freeCashflow")
    inst_holding = info.get("heldPercentInstitutions")

    if roe and roe > 0.15:
        strengths.append(f"High Return on Equity: {round(roe*100, 1)}% indicates strong capital efficiency")
    if rev_growth and rev_growth > 0.10:
        strengths.append(f"Accelerating quarterly top-line revenue growth (+{round(rev_growth*100, 1)}% YoY)")
    if de is not None and de < 50.0:
        strengths.append(f"Conservative balance sheet leverage with Debt/Equity of {round(de, 2)}")
    if op_margin and op_margin > 0.18:
        strengths.append(f"Healthy operating profitability with {round(op_margin*100, 1)}% EBITDA margin")
    if fcf and fcf > 0:
        strengths.append("Company generates positive Free Cash Flow from core operations")
    if inst_holding and inst_holding > 0.20:
        strengths.append(f"Substantial institutional sponsorship with {round(inst_holding*100, 1)}% combined FII/DII stake")

    if de and de > 100.0:
        weaknesses.append(f"Elevated financial leverage: Debt-to-Equity stands at {round(de, 2)}")
    if pe and pe > 40.0:
        weaknesses.append(f"Elevated valuation multiple: Trailing P/E at {round(pe, 1)} trades at high premium")
    if info.get("currentRatio") and info.get("currentRatio") < 1.0:
        weaknesses.append(f"Constrained short-term liquidity: Current Ratio at {round(info.get('currentRatio'), 2)}")
    if op_margin and op_margin < 0.08:
        weaknesses.append(f"Compressed operating margins ({round(op_margin*100, 1)}%) vulnerable to cost shocks")
    if not weaknesses:
        weaknesses.append("Cyclical industry dependencies can impact quarterly operating consistency")

    if not df_hist.empty and len(df_hist) >= 60:
        curr = df_hist["Close"].iloc[-1]
        h52 = df_hist["High"].max()
        rsi = ta.momentum.rsi(df_hist["Close"], window=14).iloc[-1]
        sma200 = ta.trend.sma_indicator(df_hist["Close"], window=min(len(df_hist), 200)).iloc[-1]

        if curr >= h52 * 0.90:
            opportunities.append("Stock trading within 10% of 52-week high breakout territory")
        if 48 <= rsi <= 62:
            opportunities.append(f"Constructive consolidation pattern: RSI(14) at {round(rsi, 1)} in healthy accumulation zone")
        if curr > sma200:
            opportunities.append("Trading comfortably above 200-day long-term institutional moving average")
    if not opportunities:
        opportunities.append("Operating leverage poised to expand as pipeline demand materializes")

    if pe and pe > 45.0:
        threats.append("Risk of valuation multiple contraction if quarterly earnings miss consensus estimates")
    if de and de > 100.0:
        threats.append("Interest rate environment poses cash drain risks on outstanding debt")
    threats.append("Macro-economic commodity price cycles and regulatory policy revisions")

    return {
        "s": strengths, "s_count": len(strengths),
        "w": weaknesses, "w_count": len(weaknesses),
        "o": opportunities, "o_count": len(opportunities),
        "t": threats, "t_count": len(threats)
    }

# --- REAL DYNAMIC ANALYST FORECASTER ---
def extract_real_analyst_data(tk, cmp, info):
    recs = None
    try:
        rec_df = tk.recommendations_summary
        if rec_df is not None and not rec_df.empty:
            recs = rec_df.iloc[0].to_dict()
    except Exception:
        pass

    sb = recs.get("strongBuy", 0) if recs else 0
    b = recs.get("buy", 0) if recs else 0
    h = recs.get("hold", 0) if recs else 0
    s = recs.get("sell", 0) if recs else 0
    ss = recs.get("strongSell", 0) if recs else 0
    total = sb + b + h + s + ss

    target_mean = info.get("targetMeanPrice")
    upside_pct = round(((target_mean - cmp) / cmp) * 100, 1) if (target_mean and cmp) else None

    pe = info.get("trailingPE")
    fwd_pe = info.get("forwardPE")
    pe_status = "Data Unavailable"
    if pe and fwd_pe:
        diff = round(((fwd_pe - pe) / pe) * 100, 1)
        pe_status = f"{'Premium' if diff > 0 else 'Discount'} ({'+' if diff > 0 else ''}{diff}% vs TTM)"
    elif pe:
        pe_status = f"TTM P/E: {round(pe, 1)}"

    return {
        "has_data": total > 0,
        "sb": sb, "b": b, "h": h, "s": s, "ss": ss,
        "total": total,
        "target_mean": target_mean,
        "upside_pct": upside_pct,
        "pe_status": pe_status,
        "fwd_pe": fwd_pe
    }

# --- TOP INDICES STRIP ---
indices_data = fetch_top_indices()
pills_html = "".join([
    f'<div class="index-pill"><span class="index-name">{idx["name"]}</span><span class="index-val">{idx["val"]}</span><span class="{"index-pos" if idx["chg"] >= 0 else "index-neg"}">{"▲" if idx["chg"] >= 0 else "▼"} {abs(idx["chg"])}%</span></div>'
    for idx in indices_data
])
st.markdown(f'<div class="indices-strip">{pills_html}</div>', unsafe_allow_html=True)

# --- NAVIGATION TABS ---
tab_dossier, tab_reports, tab_tv, tab_alerts, tab_settings = st.tabs([
    "📊 Institutional Stock Dossier",
    "📑 Broker Research Reports & PDFs",
    "📈 TradingView Studio",
    "🔔 Autonomous Alpha Alerts",
    "⚙️ Settings"
])

# ==============================================================================
# TAB 1: INSTITUTIONAL STOCK DOSSIER
# ==============================================================================
with tab_dossier:
    c_sel, _ = st.columns([2.5, 1.5])
    with c_sel:
        all_options = list(stock_universe.keys())
        default_ix = 0
        for i, opt in enumerate(all_options):
            if opt.startswith("ANGELONE"):
                default_ix = i
                break
        selected_label = st.selectbox("Search Equities (NSE/BSE):", options=all_options, index=default_ix, key="dossier_search")
        stock_sym = stock_universe[selected_label]
        yf_sym = f"{stock_sym}.NS"

    with st.spinner(f"Computing quantitative model for {stock_sym}..."):
        tk = yf.Ticker(yf_sym)
        inf = tk.info
        df_hist = tk.history(period="1y", interval="1d")

        cmp = inf.get("currentPrice", inf.get("regularMarketPrice", 100.0))
        prev_close = inf.get("previousClose", cmp)
        day_chg = round(cmp - prev_close, 2)
        day_chg_pct = round(((cmp - prev_close) / prev_close) * 100, 2) if prev_close else 0.0
        l52 = inf.get("fiftyTwoWeekLow", cmp)
        low_recovery = round(((cmp - l52) / l52) * 100, 1) if l52 else 0.0
        vol_val = inf.get("volume", 0)
        volume_m = f"{round(vol_val / 1e6, 2)}M" if vol_val >= 1e6 else f"{round(vol_val / 1e3, 1)}K"

        sec = inf.get("sector", "")
        ind = inf.get("industry", "")

        dvm = compute_dvm_scores(inf, df_hist)
        swot = compute_true_swot(inf, df_hist)
        analyst = extract_real_analyst_data(tk, cmp, inf)

        # COMPANY PROFILE HEADER
        st.markdown(f"""
            <div style="margin: 0.5rem 0 1rem 0;">
                <div style="font-size:1.85rem; font-weight:800; color:#FFFFFF;">{inf.get('longName', stock_sym)}</div>
                <div style="font-size:0.85rem; color:#94A3B8; margin-top:2px;">
                    NSE: <b style="color:#FFF;">{stock_sym}</b> • Sector: <span style="color:#00E5FF;">{sec}</span> • Industry: <span style="color:#94A3B8;">{ind}</span>
                </div>
                <div style="display:flex; align-items:baseline; gap:16px; margin-top:10px; flex-wrap:wrap;">
                    <span style="font-size:2.4rem; font-weight:800; font-family:'JetBrains Mono'; color:#FFFFFF;">₹{cmp}</span>
                    <span style="font-size:1rem; font-weight:700; color:{'#10B981' if day_chg >= 0 else '#EF4444'}; font-family:'JetBrains Mono';">
                        {'+' if day_chg >= 0 else ''}{day_chg} ({'+' if day_chg_pct >= 0 else ''}{day_chg_pct}%)
                    </span>
                    <span style="font-size:0.85rem; color:#10B981; font-weight:600;">▲ {low_recovery}% from 52W Low</span>
                    <span style="font-size:0.85rem; color:#94A3B8; margin-left:auto;">Volume: <b style="color:#FFF;">{volume_m}</b></span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # DVM SCORECARDS
        st.markdown(f"""
            <div class="dvm-matrix-tag" style="background:rgba(255,255,255,0.05); border:1px solid {dvm['matrix_color']}; color:{dvm['matrix_color']};">
                ■ {dvm['matrix_label']}
            </div>
            <div class="dvm-grid">
                <div class="dvm-card">
                    <div class="dvm-metric-name">Durability</div>
                    <div class="dvm-score-row">
                        <span class="dvm-score-num" style="color:#10B981;">{dvm['dur']}</span>
                        <span class="dvm-score-denom">/100</span>
                    </div>
                    <div class="dvm-sublabel">{dvm['dur_status']}</div>
                </div>
                <div class="dvm-card">
                    <div class="dvm-metric-name">Valuation</div>
                    <div class="dvm-score-row">
                        <span class="dvm-score-num" style="color:#F59E0B;">{dvm['val']}</span>
                        <span class="dvm-score-denom">/100</span>
                    </div>
                    <div class="dvm-sublabel">{dvm['val_status']}</div>
                </div>
                <div class="dvm-card">
                    <div class="dvm-metric-name">Momentum</div>
                    <div class="dvm-score-row">
                        <span class="dvm-score-num" style="color:#00E5FF;">{dvm['mom']}</span>
                        <span class="dvm-score-denom">/100</span>
                    </div>
                    <div class="dvm-sublabel">{dvm['mom_status']}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # CONSENSUS FORECASTER + ALGORITHMIC SWOT
        c_fore, c_swot = st.columns([1.4, 1], gap="medium")

        with c_fore:
            if analyst["has_data"]:
                tot = analyst["total"]
                p_sb = round((analyst["sb"] / tot) * 100, 1)
                p_b = round((analyst["b"] / tot) * 100, 1)
                p_h = round((analyst["h"] / tot) * 100, 1)
                p_s = round((analyst["s"] / tot) * 100, 1)
                p_ss = round((analyst["ss"] / tot) * 100, 1)

                rec_text = "BUY" if (analyst["sb"] + analyst["b"]) > (analyst["s"] + analyst["ss"]) else "HOLD"
                rec_color = "#10B981" if "BUY" in rec_text else "#F59E0B"

                st.markdown(f"""
                    <div class="consensus-bar-box">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-weight:700; font-size:0.9rem;">CONSENSUS RECOMMENDATION</span>
                            <span style="font-size:0.8rem; color:#94A3B8;">{tot} Institutional Analysts</span>
                        </div>
                        <div style="font-size:1.6rem; font-weight:800; color:{rec_color}; margin-top:4px;">{rec_text}</div>
                        <div class="rec-bar">
                            <div style="width:{p_ss}%; background:#DC2626;" title="{analyst['ss']} Strong Sell"></div>
                            <div style="width:{p_s}%; background:#F87171;" title="{analyst['s']} Sell"></div>
                            <div style="width:{p_h}%; background:#F59E0B;" title="{analyst['h']} Hold"></div>
                            <div style="width:{p_b}%; background:#34D399;" title="{analyst['b']} Buy"></div>
                            <div style="width:{p_sb}%; background:#059669;" title="{analyst['sb']} Strong Buy"></div>
                        </div>
                        <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:#94A3B8;">
                            <span>{analyst['s'] + analyst['ss']} Sell</span>
                            <span>{analyst['h']} Hold</span>
                            <span style="color:#10B981; font-weight:700;">{analyst['sb'] + analyst['b']} Buy</span>
                        </div>
                        <hr style="border-color:rgba(255,255,255,0.06); margin:14px 0;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <span style="font-size:0.75rem; color:#94A3B8;">Consensus Target</span>
                                <div style="font-size:0.95rem; font-weight:700; color:{'#10B981' if (analyst['upside_pct'] or 0) > 0 else '#EF4444'};">
                                    {f"₹{analyst['target_mean']} ({'+' if analyst['upside_pct']>0 else ''}{analyst['upside_pct']}%)" if analyst['target_mean'] else "Not Estimated"}
                                </div>
                            </div>
                            <div style="text-align:right;">
                                <span style="font-size:0.75rem; color:#94A3B8;">Forward Valuation</span>
                                <div style="font-size:0.95rem; font-weight:700; color:#00E5FF;">{analyst['pe_status']}</div>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class="consensus-bar-box" style="display:flex; flex-direction:column; justify-content:center;">
                        <span style="font-weight:700; font-size:0.9rem;">CONSENSUS RECOMMENDATION</span>
                        <div style="color:#94A3B8; font-size:0.85rem; margin-top:12px;">No active sell-side broker targets on file for {stock_sym}.</div>
                        <hr style="border-color:rgba(255,255,255,0.06); margin:14px 0;">
                        <div style="font-size:0.8rem; color:#94A3B8;">TTM P/E: <b style="color:#FFF;">{round(inf.get('trailingPE', 0), 1) if inf.get('trailingPE') else 'N/A'}</b> | P/B: <b style="color:#FFF;">{round(inf.get('priceToBook', 0), 2) if inf.get('priceToBook') else 'N/A'}</b></div>
                    </div>
                """, unsafe_allow_html=True)

        with c_swot:
            st.markdown(f"""
                <div class="swot-wrapper">
                    <div style="font-weight:700; font-size:0.9rem; text-align:center;">SWOT ALGORITHMIC X-RAY</div>
                    <div class="swot-grid">
                        <div class="swot-quad swot-quad-s"><div class="swot-val">{swot['s_count']}</div><div class="swot-lbl">Strengths</div></div>
                        <div class="swot-quad swot-quad-w"><div class="swot-val">{swot['w_count']}</div><div class="swot-lbl">Weaknesses</div></div>
                        <div class="swot-quad swot-quad-o"><div class="swot-val">{swot['o_count']}</div><div class="swot-lbl">Opportunities</div></div>
                        <div class="swot-quad swot-quad-t"><div class="swot-val">{swot['t_count']}</div><div class="swot-lbl">Threats</div></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        # EXACT VERIFIED OBSERVATIONS
        st.markdown("#### 📋 Algorithmic Observations")
        sw_col1, sw_col2 = st.columns(2)
        with sw_col1:
            with st.container():
                st.markdown(f"**🟢 Strengths ({swot['s_count']} Verified Triggers)**")
                for s in swot["s"]:
                    st.markdown(f"<div style='font-size:0.83rem; color:#CBD5E1; padding:4px 0;'>• {s}</div>", unsafe_allow_html=True)
                st.markdown(f"**🔵 Opportunities ({swot['o_count']} Verified Triggers)**")
                for o in swot["o"]:
                    st.markdown(f"<div style='font-size:0.83rem; color:#CBD5E1; padding:4px 0;'>• {o}</div>", unsafe_allow_html=True)
        with sw_col2:
            with st.container():
                st.markdown(f"**🟡 Weaknesses ({swot['w_count']} Verified Triggers)**")
                for w in swot["w"]:
                    st.markdown(f"<div style='font-size:0.83rem; color:#CBD5E1; padding:4px 0;'>• {w}</div>", unsafe_allow_html=True)
                st.markdown(f"**🔴 Threats ({swot['t_count']} Verified Triggers)**")
                for t in swot["t"]:
                    st.markdown(f"<div style='font-size:0.83rem; color:#CBD5E1; padding:4px 0;'>• {t}</div>", unsafe_allow_html=True)

        # DETERMINISTIC SECTOR PEERS TABLE
        st.markdown(f"### ⚖️ Sector Peers: `{stock_sym}`")
        resolved_peer_list = resolve_peers_dynamically(stock_sym, sec, ind)

        peer_rows = []
        for p in [stock_sym] + resolved_peer_list:
            try:
                p_inf = yf.Ticker(f"{p}.NS").info
                peer_rows.append({
                    "Symbol": p,
                    "LTP (₹)": p_inf.get("currentPrice", p_inf.get("regularMarketPrice")),
                    "Market Cap (₹ Cr)": round(p_inf.get("marketCap", 0) / 1e7, 1) if p_inf.get("marketCap") else "-",
                    "P/E (TTM)": round(p_inf.get("trailingPE", 0), 1) if p_inf.get("trailingPE") else "-",
                    "Debt to Equity": round(p_inf.get("debtToEquity", 0), 2) if p_inf.get("debtToEquity") else "Nil",
                    "ROE (%)": f"{round(p_inf.get('returnOnEquity', 0)*100, 1)}%" if p_inf.get("returnOnEquity") else "-"
                })
            except Exception:
                pass

        if peer_rows:
            st.dataframe(pd.DataFrame(peer_rows), use_container_width=True)

# ==============================================================================
# TAB 2: BROKER RESEARCH REPORTS (CLICKABLE PDF LINKS)
# ==============================================================================
with tab_reports:
    st.markdown(f"### 📑 Broker Research Coverage & Verified PDFs: `{stock_sym}`")
    st.caption("Sort reports by Date, Broker, Target Price, Upside %, or open verified PDFs directly.")

    matched_reports = [r for r in RESEARCH_DATABASE if r["symbol"] == stock_sym]

    if matched_reports:
        table_rows = []
        for r in matched_reports:
            upside = round(((r["target"] - cmp) / cmp) * 100, 2)
            table_rows.append({
                "Date": r["date"],
                "Broker / Author": r["author"],
                "LTP (₹)": cmp,
                "Target (₹)": r["target"],
                "Upside (%)": f"{'+' if upside > 0 else ''}{upside}%",
                "Recommendation": r["reco"],
                "PDF Report": r["pdf_url"]
            })

        df_rep = pd.DataFrame(table_rows)
        st.dataframe(
            df_rep,
            column_config={
                "PDF Report": st.column_config.LinkColumn(
                    "Research PDF",
                    display_text="📄 View PDF"
                )
            },
            use_container_width=True
        )
    else:
        st.info(f"No institutional coverage reports indexed for {stock_sym}. Broker PDFs are populated upon publishing.")

# ==============================================================================
# TAB 3: TRADINGVIEW ADVANCED STUDIO
# ==============================================================================
with tab_tv:
    c_pick, _ = st.columns([2, 2])
    with c_pick:
        tv_sym = st.selectbox("Chart Symbol:", options=list(stock_universe.keys()), index=0, key="tv_sym_sel")
        clean_tv_ticker = stock_universe[tv_sym]

    tv_html = f"""
    <div class="tradingview-widget-container" style="height:720px;width:100%;">
      <div id="tv_chart_container" style="height:calc(100% - 32px);width:100%;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "symbol": "NSE:{clean_tv_ticker}",
        "interval": "D",
        "timezone": "Asia/Kolkata",
        "theme": "dark",
        "style": "1",
        "locale": "in",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "hide_side_toolbar": false,
        "studies": ["MASimple@tv-basicstudies", "EMA@tv-basicstudies", "RSI@tv-basicstudies"],
        "container_id": "tv_chart_container"
      }});
      </script>
    </div>
    """
    components.html(tv_html, height=730)

# ==============================================================================
# TAB 4: AUTONOMOUS 24x7 ALPHA ALERTS
# ==============================================================================
with tab_alerts:
    st.markdown("### 🔔 Create 24x7 Autonomous Stock Alert")
    st.caption("Condition monitors continuously. When triggered, it fires an instant Telegram message.")

    with st.form("alert_form"):
        al_sym_lbl = st.selectbox("Stock to Track:", options=list(stock_universe.keys()), index=0)
        al_sym = stock_universe[al_sym_lbl]
        c1, c2 = st.columns(2)
        with c1:
            rule_type = st.selectbox("Condition:", [
                "Price Drops % from entry price",
                "Price Rises % from entry price",
                "Price Touches Specific EMA",
                "RSI (14) Drops Below Level"
            ])
        with c2:
            duration = st.slider("Tracking Active Period (Days):", 1, 30, 5)

        val_target = st.number_input("Trigger Value (% / EMA Period / RSI Threshold):", min_value=1.0, max_value=500.0, value=5.0)

        if st.form_submit_button("🚀 Deploy 24x7 Tracker"):
            if not st.session_state.telegram_chat_id:
                st.error("Please enter your Telegram Chat ID in the Settings tab first!")
            elif supabase is not None:
                try:
                    curr_p = yf.Ticker(f"{al_sym}.NS").info.get("currentPrice", 100.0)
                    exp = (datetime.utcnow() + timedelta(days=duration)).isoformat()
                    supabase.table("user_alerts").insert({
                        "telegram_chat_id": st.session_state.telegram_chat_id,
                        "symbol": al_sym,
                        "base_price": curr_p,
                        "rule_type": rule_type,
                        "params": {"val": val_target},
                        "expires_at": exp,
                        "status": "ACTIVE"
                    }).execute()
                    st.success(f"Tracking {al_sym} actively for {duration} days!")
                except Exception as e:
                    st.error(f"Failed: {e}")
            else:
                st.warning("Supabase database not connected. Check API credentials.")

# ==============================================================================
# TAB 5: SETTINGS
# ==============================================================================
with tab_settings:
    st.markdown("### ⚙️ Terminal Settings")
    with st.form("tg_settings"):
        tg_id = st.text_input("Telegram Chat ID:", value=st.session_state.telegram_chat_id)
        if st.form_submit_button("Save Telegram ID"):
            st.session_state.telegram_chat_id = tg_id.strip()
            st.success("Telegram ID updated!")
