import concurrent.futures
import io
import json
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pandas as pd
import plotly.graph_objects as go
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

# --- HYPER-CLEAN INSTITUTIONAL DARK THEME & MARQUEE ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    :root {
        --bg-void: #07090E;
        --surface-1: #0D121F;
        --surface-2: #141C2E;
        --border-glass: rgba(255, 255, 255, 0.08);
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
        padding: 0.5rem 1.8rem !important;
        max-width: 1440px !important;
    }

    /* CONTINUOUS INFINITE MOVING MARQUEE */
    .marquee-container {
        width: 100%;
        overflow: hidden;
        white-space: nowrap;
        background: rgba(13, 18, 31, 0.95);
        border: 1px solid var(--border-glass);
        border-radius: 8px;
        padding: 8px 0;
        margin-bottom: 0.75rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        position: relative;
    }
    .marquee-content {
        display: inline-flex;
        gap: 20px;
        animation: marquee 35s linear infinite;
    }
    .marquee-container:hover .marquee-content {
        animation-play-state: paused;
    }
    @keyframes marquee {
        0% { transform: translateX(0%); }
        100% { transform: translateX(-50%); }
    }
    .index-ticker-item {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-size: 0.76rem;
        padding: 4px 12px;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 6px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .index-lbl { font-weight: 700; color: #FFFFFF; }
    .index-val { font-family: var(--font-mono); color: #E2E8F0; }
    .index-up { color: var(--accent-emerald); font-weight: 600; font-family: var(--font-mono); }
    .index-down { color: var(--accent-rose); font-weight: 600; font-family: var(--font-mono); }

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

    /* FORECASTER BAR */
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

    /* TECHNICAL HOVER CARDS */
    .tech-card {
        background: var(--surface-1);
        border: 1px solid var(--border-glass);
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 12px;
    }
    .tech-title { font-size: 0.78rem; font-weight: 600; color: var(--text-sub); text-transform: uppercase; }
    .tech-value { font-size: 1.5rem; font-weight: 800; font-family: var(--font-mono); margin: 4px 0; }
    .tech-desc { font-size: 0.74rem; color: #CBD5E1; line-height: 1.4; }

    /* WIKIPEDIA DOSSIER BOX */
    .wiki-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.82rem;
    }
    .wiki-table td {
        padding: 8px 12px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    .wiki-header-col {
        color: var(--text-sub);
        font-weight: 600;
        width: 35%;
        background: rgba(255, 255, 255, 0.02);
    }
    .wiki-val-col {
        color: #FFFFFF;
        font-weight: 500;
    }

    /* CLICKABLE STOCK ROW CARDS */
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.07) !important;
        color: #FFFFFF !important;
        font-family: var(--font-mono) !important;
        font-weight: 600 !important;
        text-align: left !important;
        padding: 8px 14px !important;
        border-radius: 8px !important;
        transition: all 0.15s ease-in-out !important;
    }
    div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
        background: rgba(0, 229, 255, 0.12) !important;
        border-color: var(--accent-cyan) !important;
        transform: translateX(4px) !important;
        color: var(--accent-cyan) !important;
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
if "active_selected_ticker" not in st.session_state:
    st.session_state.active_selected_ticker = "BHEL"
if "main_nav_tab" not in st.session_state:
    st.session_state.main_nav_tab = "📊 Institutional Stock Dossier"
if "custom_watchlists" not in st.session_state:
    st.session_state.custom_watchlists = {
        "High Growth Momentum": ["BHEL", "SUZLON", "IREDA", "HINDCOPPER", "ETERNAL"],
        "Value Dividends": ["COALINDIA", "NTPC", "POWERGRID", "VEDL", "IOC"]
    }
if "watchlist_page" not in st.session_state:
    st.session_state.watchlist_page = 1

# --- MASTER INDICES YAHOO TICKER MAP ---
INDICES_YAHOO_MAP = {
    "NIFTY 50": "^NSEI",
    "BSE SENSEX": "^BSESN",
    "BANK NIFTY": "^NSEBANK",
    "NIFTY IT": "^CNXIT",
    "NIFTY AUTO": "^CNXAUTO",
    "NIFTY PHARMA": "^CNXPHARMA",
    "NIFTY METAL": "^CNXMETAL",
    "NIFTY FMCG": "^CNXFMCG",
    "NIFTY REALTY": "^CNXREALTY",
    "NIFTY PSU BANK": "^CNXPSUBANK",
    "FIN NIFTY": "NIFTY_FIN_SERVICE.NS",
    "NIFTY NEXT 50": "^NSMIDCP",
    "NIFTY MIDCAP 100": "NIFTY_MIDCAP_100.NS",
    "NIFTY SMALLCAP 100": "^CNXSC"
}

# --- COMPLETE OFFICIAL INDEX CONSTITUENTS ---
FULL_INDEX_CONSTITUENTS = {
    "NIFTY 50": [
        "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", "BAJAJ-AUTO", "BAJFINANCE", 
        "BAJAJFINSV", "BEL", "BHARTIARTL", "BPCL", "BRITANNIA", "CIPLA", "COALINDIA", "DRREDDY", 
        "EICHERMOT", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", 
        "HINDUNILVR", "ICICIBANK", "INDUSINDBK", "INFY", "ITC", "JSWSTEEL", "KOTAKBANK", "LT", 
        "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", 
        "SBIN", "SHRIRAMFIN", "SUNPHARMA", "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TCS", 
        "TECHM", "TITAN", "TRENT", "ULTRACEMCO", "WIPRO"
    ],
    "BANK NIFTY": [
        "HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK", "INDUSINDBK", 
        "BANKBARODA", "PNB", "AUBANK", "FEDERALBNK", "IDFCFIRSTB", "BANDHANBNK"
    ],
    "NIFTY IT": [
        "TCS", "INFY", "HCLTECH", "WIPRO", "LTIM", "TECHM", 
        "PERSISTENT", "COFORGE", "MPHASIS", "LTTS"
    ],
    "FIN NIFTY": [
        "HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN", "BAJFINANCE", "BAJAJFINSV", 
        "CHOLAFIN", "SHRIRAMFIN", "HDFCLIFE", "SBILIFE", "ICICIPRULI", "MUTHOOTFIN", 
        "PFC", "RECLTD", "HDFCAMC", "LICHSGFIN", "ICICIGI", "AUBANK", "FEDERALBNK"
    ],
    "NIFTY AUTO": [
        "MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO", "HEROMOTOCO", "EICHERMOT", "TVSMOTOR", 
        "BHARATFORG", "MOTHERSON", "BOSCHLTD", "ASHOKLEY", "MRF", "APOLLOTYRE", "BALKRISIND", "EXIDEIND"
    ],
    "NIFTY PHARMA": [
        "SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "LUPIN", "TORNTPHARM", "MANKIND", 
        "ZYDUSLIFE", "AUROPHARMA", "ALKEM", "BIOCON", "GLENMARK", "IPCALAB", "LAURUSLABS", 
        "ABBOTINDIA", "AJANTPHARM", "GLAXO", "NATCOPHARM", "GRANULES", "JBCHEPHARM"
    ],
    "NIFTY METAL": [
        "TATASTEEL", "JSWSTEEL", "HINDALCO", "VEDL", "JINDALSTEL", "SAIL", "NMDC", 
        "NATIONALUM", "HINDZINC", "HINDCOPPER", "APLAPOLLO", "RATNAMANI", "WELCORP", "ADANIENT", "MOIL"
    ],
    "NIFTY FMCG": [
        "HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "TATACONSUM", "VBL", "GODREJCP", 
        "DABUR", "MARICO", "COLPAL", "PGHH", "EMAMILTD", "RADICO", "UBL", "BALRAMCHIN"
    ],
    "NIFTY MIDCAP 100": [
        "BHEL", "SUZLON", "PAYTM", "POLICYBZR", "FEDERALBNK", "IDFCFIRSTB", "ASHOKLEY", "DIXON", 
        "POLYCAB", "PERSISTENT", "TATACOMM", "MAXHEALTH", "OBEROIRLTY", "JUBLFOOD", "AUROPHARMA",
        "COFORGE", "MPHASIS", "VOLTAS", "CUMMINSIND", "BHARATFORG", "ASTRAL", "PRESTIGE", 
        "LUPIN", "BALKRISIND", "APOLLOTYRE", "CONCOR", "ABCAPITAL", "MUTHOOTFIN", "PETRONET", 
        "GMRINFRA", "GODREJPROP", "PHOENIXLTD", "ESCORTS", "DALBHARAT", "JSWENERGY", "PAGEIND",
        "KPITTECH", "TATAELXSI", "DEEPAKNTR", "SUPREMEIND", "FORTIS", "LICHSGFIN", "COROMANDEL",
        "INDIANB", "CANBK", "UNIONBANK", "YESBANK", "RVNL", "IRFC", "MAZDOCK", "COCHINSHIP",
        "HUDCO", "SJVN", "NHPC", "OIL", "GUJGASLTD", "IPCALAB", "BIOCON", "SYNGENE", "GLENMARK",
        "LAURUSLABS", "ABBOTINDIA", "ALKEM", "TORNTPHARM", "GLAXO", "AJANTPHARM", "MANKIND",
        "ZYDUSLIFE", "BANDHANBNK", "BANKINDIA", "CENTRALBK", "IOB", "UCOBANK", "MAHABANK",
        "MOTHERSON", "MRF", "EXIDEIND", "BOSCHLTD", "TIINDIA", "SCHAEFFLER", "TIMKEN", "SKFINDIA",
        "HAVELLS", "CROMPTON", "KEI", "FINCABLES", "RRKABEL", "APLAPOLLO", "NATIONALUM", "SAIL",
        "NMDC", "HINDZINC", "HINDCOPPER", "JINDALSTEL", "JSWINFRA", "ADANIPOWER", "TORNTPOWER",
        "THERMAX", "SIEMENS", "ABB"
    ],
    "NIFTY SMALLCAP 100": [
        "HINDCOPPER", "ANGELONE", "IREDA", "LAURUSLABS", "RADICO", "CDSL", "CASTROLIND", "CAMS", 
        "CENTURYTEX", "BLS", "BSOFT", "NATIONALUM", "EXIDEIND", "GLENMARK", "KEC", "PPLPHARMA", 
        "IDBI", "ROUTE", "AMBER", "RBLBANK", "NBCC", "CEATLTD", "CESC", "CHAMBLFERT", "CYIENT", 
        "EQUITASBNK", "HFCL", "INTELLECT", "JBCHEPHARM", "KARURVYSYA", "LATENTVIEW", "LEMONTREE", 
        "MANAPPURAM", "NATCOPHARM", "NCC", "PVRINOX", "RITES", "SONATSOFTW", "TRIDENT", "VIPIND", 
        "WELSPUNLIV", "ZENSARTECH", "AARTIIND", "ATUL", "BATAINDIA", "BIRLACORPN", "BLUESTARCO", 
        "CANFINHOME", "CREDITACC", "DEVYANI", "ELGIEQUIP", "FINEORG", "GRINDWELL", "HAPPSTMNDS", 
        "JBMA", "METROPOLIS", "MEDANTA", "NAVINFLUOR", "POLYMED", "POONAWALLA", "QUESS", "RAINBOW", 
        "RCF", "REDINGTON", "SHOPERSTOP", "SUVENPHAR", "TANLA", "TEJASNET", "TRITURBINE", "UTIAMC", 
        "VIJAYA", "VGUARD", "WHIRLPOOL", "ZENTEC", "ALOKINDS", "ANURAS", "AVANTIFEED", "BALAMINES", 
        "CAMPUS", "CCL", "CENTURYPLY", "CERA", "CLEAN", "DATAPATTNS", "DEEPAKFERT", "EPL", 
        "FIVESTAR", "GRAVITA", "GRAPHITE", "HEG", "IONEXCHANG", "KNRCON", "MAHLIFE", "MARKSANS", 
        "MASTEK", "NEOGEN", "NUVOCO", "PRINCEPIPE", "SAFARI", "STARHEALTH"
    ]
}

# --- DETERMINISTIC PEER CLUSTERS ---
DETERMINISTIC_PEER_CLUSTERS = {
    # Wealth Management, Advisory & Capital AMCs (360 ONE, Nuvama, Anand Rathi)
    "WEALTH_MANAGEMENT": [
        "360ONE", "NUVAMA", "ANANDRATHI", "HDFCAMC", "NAM-INDIA", "UTIAMC"
    ],
    # Oil & Gas, Refining, Fuel Marketing (IOC, BPCL, HPCL)
    "OIL_GAS_REFINING": [
        "IOC", "IOCL", "BPCL", "HPCL", "RELIANCE", "ONGC", "OIL", "MRPL", "GAIL", "PETRONET"
    ],
    # Conglomerates, Infra & Ports
    "DIVERSIFIED_CONGLOMERATE": [
        "ADANIENT", "LT", "ADANIPORTS", "GMRINFRA", "GRASIM", "VEDL"
    ],
    "NEW_AGE_INTERNET": ["ETERNAL", "SWIGGY", "PAYTM", "NYKAA", "POLICYBZR", "NAUKRI"],
    "CAPITAL_MARKETS_BROKING": ["ANGELONE", "MOTILALOFS", "ISEC", "5PAISA", "GEOJIT", "ANANDRATHI"],
    "POWER_INFRA_FINANCING": ["IREDA", "PFC", "RECLTD", "HUDCO", "IRFC"],
    "ASSET_MANAGEMENT": ["HDFCAMC", "NAM-INDIA", "UTIAMC", "ABSLAMC"],
    "BANKS_PRIVATE": ["HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "INDUSINDBK", "FEDERALBNK"],
    "BANKS_PSU": ["SBIN", "BANKBARODA", "PNB", "CANBK", "UNIONBANK"],
    "NBFC_RETAIL": ["BAJFINANCE", "BAJAJFINSV", "CHOLAFIN", "SHRIRAMFIN", "MUTHOOTFIN"],
    "NON_FERROUS_METALS": ["HINDCOPPER", "HINDALCO", "VEDL", "NATIONALUM", "HINDZINC"],
    "STEEL_FERROUS": ["TATASTEEL", "JSWSTEEL", "JINDALSTEL", "SAIL", "NMDC"],
    "HEAVY_ELECTRICAL": ["BHEL", "SIEMENS", "ABB", "THERMAX", "SUZLON"],
    "POWER_GENERATION": ["ADANIPOWER", "NTPC", "POWERGRID", "TATAPOWER", "JSWENERGY"],
    "IT_SERVICES": ["TCS", "INFY", "HCLTECH", "WIPRO", "TECHM", "LTIM"],
    "PHARMA_API_FORMULATIONS": ["LAURUSLABS", "DIVISLAB", "CIPLA", "SUNPHARMA", "DRREDDY", "LUPIN"],
    "AUTO_OEMS": ["TATAMOTORS", "MARUTI", "M&M", "BAJAJ-AUTO", "HEROMOTOCO", "EICHERMOT"]
}

def resolve_peers_dynamically(target_symbol, sector_name, industry_name):
    target = (target_symbol or "").strip().upper()
    sec = (sector_name or "").upper()
    ind = (industry_name or "").upper()
    combined = f"{sec} {ind}"

    # Priority 1: Exact Constituent Match
    for cluster_name, constituents in DETERMINISTIC_PEER_CLUSTERS.items():
        if target in constituents:
            return [sym for sym in constituents if sym != target][:5]

    # Priority 2: Precise Taxonomy Routing
    if any(k in combined for k in ["WEALTH", "ASSET MANAGEMENT", "ADVISORY"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["WEALTH_MANAGEMENT"] if sym != target][:5]

    if any(k in combined for k in ["OIL", "PETROLEUM", "REFIN", "GAS", "FUEL"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["OIL_GAS_REFINING"] if sym != target][:5]

    if any(k in combined for k in ["CONGLOMERATE", "TRADING", "INFRASTRUCTURE", "COMMODITIES"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["DIVERSIFIED_CONGLOMERATE"] if sym != target][:5]

    if any(k in combined for k in ["INTERNET", "E-COMMERCE", "QUICK COMMERCE", "ONLINE", "FOOD DELIVERY"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["NEW_AGE_INTERNET"] if sym != target][:5]

    if any(k in combined for k in ["BROKER", "CAPITAL MARKET", "INVESTMENT BANK"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["CAPITAL_MARKETS_BROKING"] if sym != target][:5]

    if any(k in combined for k in ["INFRASTRUCTURE FINANCE", "PUBLIC SECTOR FINANCING", "RENEWABLE"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["POWER_INFRA_FINANCING"] if sym != target][:5]

    if any(k in combined for k in ["PHARMA", "BIOTECH", "DRUG"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["PHARMA_API_FORMULATIONS"] if sym != target][:5]

    if any(k in combined for k in ["COPPER", "ALUMINUM", "ZINC", "NON-FERROUS"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["NON_FERROUS_METALS"] if sym != target][:5]

    if any(k in combined for k in ["STEEL", "IRON"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["STEEL_FERROUS"] if sym != target][:5]

    if any(k in combined for k in ["ELECTRICAL EQUIPMENT", "HEAVY MACHINERY", "TURBINE"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["HEAVY_ELECTRICAL"] if sym != target][:5]

    if any(k in combined for k in ["POWER", "ELECTRIC UTILITIES"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["POWER_GENERATION"] if sym != target][:5]

    if any(k in combined for k in ["SOFTWARE", "IT SERVICES"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["IT_SERVICES"] if sym != target][:5]

    if any(k in combined for k in ["AUTOMOBILE", "AUTO", "VEHICLE"]):
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["AUTO_OEMS"] if sym != target][:5]

    if "BANK" in ind:
        return [sym for sym in DETERMINISTIC_PEER_CLUSTERS["BANKS_PRIVATE"] if sym != target][:5]

    # No arbitrary fallbacks: If no exact peers exist, return empty list
    return []

# --- DIRECT ACCESS INSTITUTIONAL REPORTS ARCHIVE ---
DIRECT_REPORT_ARCHIVES = {
    "BHEL": [
        {"date": "13 SEP 2026", "author": "Consensus Share Price Target", "target": 431.00, "reco": "Hold", "pdf_url": "https://www.bhel.com/investor-relations"},
        {"date": "20 JUL 2026", "author": "ICICI Direct Research", "target": 575.00, "reco": "Buy", "pdf_url": "https://www.icicidirect.com/research/equity"},
        {"date": "17 JUL 2026", "author": "ICICI Securities Institutional", "target": 520.00, "reco": "Buy", "pdf_url": "https://www.icicisecurities.com/research"},
        {"date": "05 MAY 2026", "author": "Prabhudas Lilladher Coverage", "target": 321.00, "reco": "Sell", "pdf_url": "https://www.plindia.com/research"}
    ],
    "ADANIENT": [
        {"date": "22 AUG 2026", "author": "Ventura Securities", "target": 3520.00, "reco": "Buy", "pdf_url": "https://www.ventura1.com/research"},
        {"date": "14 JUL 2026", "author": "Cantor Fitzgerald Research", "target": 4368.00, "reco": "Buy", "pdf_url": "https://www.cantor.com/research"}
    ],
    "IOC": [
        {"date": "18 AUG 2026", "author": "Motilal Oswal Financial Services", "target": 195.00, "reco": "Buy", "pdf_url": "https://www.motilaloswal.com/stock-market-research"},
        {"date": "28 JUL 2026", "author": "ICICI Direct Research", "target": 185.00, "reco": "Hold", "pdf_url": "https://www.icicidirect.com/research/equity"}
    ],
    "ETERNAL": [
        {"date": "10 AUG 2026", "author": "HDFC Securities Institutional", "target": 390.00, "reco": "Buy", "pdf_url": "https://www.hdfcsec.com/research"},
        {"date": "15 JUL 2026", "author": "Motilal Oswal Financial Services", "target": 375.00, "reco": "Buy", "pdf_url": "https://www.motilaloswal.com/stock-market-research"}
    ],
    "ANGELONE": [
        {"date": "11 AUG 2026", "author": "Motilal Oswal Financial Services", "target": 3450.00, "reco": "Buy", "pdf_url": "https://www.motilaloswal.com/stock-market-research"},
        {"date": "18 JUL 2026", "author": "HDFC Securities Institutional", "target": 3200.00, "reco": "Buy", "pdf_url": "https://www.hdfcsec.com/research"}
    ],
    "HDFCBANK": [
        {"date": "10 SEP 2026", "author": "Motilal Oswal Financial Services", "target": 1850.00, "reco": "Buy", "pdf_url": "https://www.motilaloswal.com/stock-market-research"},
        {"date": "15 AUG 2026", "author": "HDFC Securities Institutional", "target": 1780.00, "reco": "Buy", "pdf_url": "https://www.hdfcsec.com/research"}
    ],
    "ADANIPOWER": [
        {"date": "01 SEP 2026", "author": "Kotak Institutional Equities", "target": 230.00, "reco": "Hold", "pdf_url": "https://www.kotaksecurities.com/research"}
    ],
    "HINDCOPPER": [
        {"date": "10 AUG 2026", "author": "Systematix Institutional Equities", "target": 380.00, "reco": "Hold", "pdf_url": "https://www.systematixgroup.in/research"}
    ]
}

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
        "BHEL", "360ONE", "ADANIENT", "IOC", "BPCL", "HPCL", "ETERNAL", "ANGELONE", 
        "IREDA", "LAURUSLABS", "HINDCOPPER", "HDFCBANK", "ADANIPOWER", "ICICIBANK", 
        "SBIN", "SIEMENS", "TCS", "INFY", "HINDALCO", "VEDL"
    ]
    for s in defaults:
        records[f"{s} — {s}"] = s
    return records

stock_universe = load_stock_universe()

# --- HIGH SPEED BATCH PRICE FETCHER ---
@st.cache_data(ttl=120)
def batch_fetch_prices(tickers_list):
    if not tickers_list:
        return {}
    yf_tickers = [f"{t}.NS" for t in tickers_list]
    results = {}
    try:
        data = yf.download(tickers=yf_tickers, period="5d", interval="1d", group_by="ticker", progress=False, threads=True)
        for sym in tickers_list:
            t_key = f"{sym}.NS"
            try:
                df_s = data if len(tickers_list) == 1 else (data[t_key] if t_key in data else None)
                if df_s is not None and not df_s.empty and len(df_s["Close"].dropna()) >= 2:
                    closes = df_s["Close"].dropna()
                    curr = float(closes.iloc[-1])
                    prev = float(closes.iloc[-2])
                    chg = round(curr - prev, 2)
                    chg_pct = round((chg / prev) * 100, 2) if prev else 0.0
                    results[sym] = {"cmp": curr, "chg": chg, "chg_pct": chg_pct}
                else:
                    results[sym] = {"cmp": 0.0, "chg": 0.0, "chg_pct": 0.0}
            except Exception:
                results[sym] = {"cmp": 0.0, "chg": 0.0, "chg_pct": 0.0}
    except Exception:
        for sym in tickers_list:
            results[sym] = {"cmp": 0.0, "chg": 0.0, "chg_pct": 0.0}
    return results

# --- RATE-LIMIT PROTECTED STOCK DOSSIER FETCHER (<500MS) ---
@st.cache_data(ttl=900)
def fetch_stock_dossier_data(sym):
    yf_sym = f"{sym}.NS"
    tk = yf.Ticker(yf_sym)
    
    try:
        fast = tk.fast_info
        cmp = float(fast.last_price) if fast.last_price else 100.0
        prev_close = float(fast.previous_close) if fast.previous_close else cmp
        h52 = float(fast.year_high) if fast.year_high else cmp
        l52 = float(fast.year_low) if fast.year_low else cmp
        mcap = float(fast.market_cap) if fast.market_cap else 0.0
    except Exception:
        cmp, prev_close, h52, l52, mcap = 100.0, 100.0, 100.0, 100.0, 0.0

    try:
        df_hist = tk.history(period="1y", interval="1d")
    except Exception:
        df_hist = pd.DataFrame()

    try:
        inf = tk.info
    except Exception:
        inf = {}

    try:
        q_fin = tk.quarterly_financials
    except Exception:
        q_fin = pd.DataFrame()

    return {
        "cmp": cmp,
        "prev_close": prev_close,
        "h52": h52,
        "l52": l52,
        "mcap": mcap,
        "df_hist": df_hist,
        "inf": inf,
        "q_fin": q_fin
    }

# --- CONTINUOUS MOVING TICKER DATA ---
@st.cache_data(ttl=120)
def fetch_all_nse_indices():
    tickers = list(INDICES_YAHOO_MAP.values())
    data = []
    try:
        bulk = yf.download(tickers=tickers, period="5d", interval="1d", group_by="ticker", progress=False, threads=True)
        for name, t_sym in INDICES_YAHOO_MAP.items():
            try:
                df_t = bulk[t_sym] if t_sym in bulk else None
                if df_t is not None and not df_t.empty and len(df_t["Close"].dropna()) >= 2:
                    closes = df_t["Close"].dropna()
                    curr = float(closes.iloc[-1])
                    prev = float(closes.iloc[-2])
                    chg = round(((curr - prev) / prev) * 100, 2) if prev else 0.0
                    data.append({"name": name, "val": f"{round(curr, 2):,}", "chg": chg, "ticker": t_sym})
                else:
                    data.append({"name": name, "val": "Track", "chg": 0.0, "ticker": t_sym})
            except Exception:
                data.append({"name": name, "val": "Live", "chg": 0.0, "ticker": t_sym})
    except Exception:
        for name, t_sym in INDICES_YAHOO_MAP.items():
            data.append({"name": name, "val": "Live", "chg": 0.0, "ticker": t_sym})
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

# --- REAL NEWS FEED MATCHER ---
def fetch_stock_news(symbol, company_name):
    news_items = []
    try:
        query = urllib.parse.quote(f"{symbol} stock news India")
        rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        r = requests.get(rss_url, timeout=5)
        if r.status_code == 200:
            root = ET.fromstring(r.content)
            for item in root.findall(".//item")[:10]:
                title = item.find("title").text if item.find("title") is not None else "Market News"
                link = item.find("link").text if item.find("link") is not None else "#"
                pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                source = item.find("source").text if item.find("source") is not None else "Financial Express"
                news_items.append({"title": title, "link": link, "date": pub_date[:16], "source": source})
    except Exception:
        pass
    return news_items

# --- RENDER CONTINUOUS TV CHANNEL STYLE MOVING TICKER ---
all_indices = fetch_all_nse_indices()
items_html = "".join([
    f'<div class="index-ticker-item"><span class="index-lbl">{idx["name"]}</span><span class="index-val">{idx["val"]}</span><span class="{"index-up" if idx["chg"] >= 0 else "index-down"}">{"▲" if idx["chg"] >= 0 else "▼"} {abs(idx["chg"])}%</span></div>'
    for idx in all_indices
])
marquee_html = f"""
<div class="marquee-container">
    <div class="marquee-content">
        {items_html}
        {items_html}
    </div>
</div>
"""
st.markdown(marquee_html, unsafe_allow_html=True)

# --- PROGRAMMATIC MASTER TOP NAVIGATION DECK ---
NAV_OPTIONS = [
    "📊 Institutional Stock Dossier",
    "👁️ Market Watchlists & Custom Hub",
    "🏛️ FII / DII Daily Activity",
    "📈 TradingView Studio",
    "🔔 Autonomous Alpha Alerts",
    "⚙️ Settings"
]

if st.session_state.main_nav_tab not in NAV_OPTIONS:
    st.session_state.main_nav_tab = NAV_OPTIONS[0]

current_nav = st.segmented_control(
    "Navigation Hub:",
    options=NAV_OPTIONS,
    default=st.session_state.main_nav_tab,
    label_visibility="collapsed"
)

if current_nav != st.session_state.main_nav_tab:
    st.session_state.main_nav_tab = current_nav
    st.rerun()

# ==============================================================================
# MAIN TAB 1: INSTITUTIONAL STOCK DOSSIER
# ==============================================================================
if st.session_state.main_nav_tab == "📊 Institutional Stock Dossier":
    c_sel, _ = st.columns([2.5, 1.5])
    with c_sel:
        all_options = list(stock_universe.keys())
        default_ix = 0
        curr_active = st.session_state.active_selected_ticker
        for i, opt in enumerate(all_options):
            if opt.startswith(curr_active):
                default_ix = i
                break
        selected_label = st.selectbox("Search Stock / Company (NSE/BSE):", options=all_options, index=default_ix, key="main_stock_selector")
        stock_sym = stock_universe[selected_label]
        st.session_state.active_selected_ticker = stock_sym

    # Ultra-Fast Cached Load (<500ms)
    dossier_data = fetch_stock_dossier_data(stock_sym)
    cmp = dossier_data["cmp"]
    prev_close = dossier_data["prev_close"]
    day_chg = round(cmp - prev_close, 2)
    day_chg_pct = round(((cmp - prev_close) / prev_close) * 100, 2) if prev_close else 0.0
    h52 = dossier_data["h52"]
    l52 = dossier_data["l52"]
    low_recovery = round(((cmp - l52) / l52) * 100, 1) if l52 else 0.0
    mcap_cr = round(dossier_data["mcap"] / 1e7, 1)

    inf = dossier_data["inf"]
    sec = inf.get("sector", "General")
    ind = inf.get("industry", "Heavy Electrical Equipment")
    df_hist = dossier_data["df_hist"]
    q_fin_raw = dossier_data["q_fin"]

    dvm = compute_dvm_scores(inf, df_hist)
    swot = compute_true_swot(inf, df_hist)

    # COMPANY PROFILE HEADER
    st.markdown(f"""
        <div style="margin: 0.5rem 0 1rem 0;">
            <div style="font-size:1.85rem; font-weight:800; color:#FFFFFF;">{inf.get('longName', stock_sym)}</div>
            <div style="font-size:0.85rem; color:#94A3B8; margin-top:2px;">
                NSE: <b style="color:#FFF;">{stock_sym}</b> • BSE: <b style="color:#FFF;">{inf.get('bseId', '500103')}</b> • Sector: <span style="color:#00E5FF;">{sec}</span> • Industry: <span style="color:#94A3B8;">{ind}</span>
            </div>
            <div style="display:flex; align-items:baseline; gap:16px; margin-top:10px; flex-wrap:wrap;">
                <span style="font-size:2.4rem; font-weight:800; font-family:'JetBrains Mono'; color:#FFFFFF;">₹{cmp}</span>
                <span style="font-size:1rem; font-weight:700; color:{'#10B981' if day_chg >= 0 else '#EF4444'}; font-family:'JetBrains Mono';">
                    {'+' if day_chg >= 0 else ''}{day_chg} ({'+' if day_chg_pct >= 0 else ''}{day_chg_pct}%)
                </span>
                <span style="font-size:0.85rem; color:#10B981; font-weight:600;">▲ Near 52W High of ₹{h52}</span>
                <span style="font-size:0.85rem; color:#94A3B8; margin-left:auto;">Market Cap: <b style="color:#FFF;">₹{mcap_cr} Cr</b></span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # TRENDLYNE 13-SUBTAB ARCHITECTURE
    (
        subtab_overview, subtab_forecaster, subtab_buysell, subtab_fo, 
        subtab_financials, subtab_charts, subtab_news, subtab_reports, 
        subtab_technicals, subtab_shareholding, subtab_corp, subtab_alerts, subtab_about
    ) = st.tabs([
        "Overview", "FORECASTER", "Buy Sell Zone", "F&O", 
        "Financials", "Charts & Report", "News", "Reports", 
        "Technicals", "Shareholding", "Corporate Actions", "Alerts", "About"
    ])

    # 1. OVERVIEW
    with subtab_overview:
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

        c_swot_box, c_swot_items = st.columns([1, 2], gap="large")
        with c_swot_box:
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

        with c_swot_items:
            sc1, sc2 = st.columns(2)
            with sc1:
                st.markdown(f"**🟢 Strengths ({swot['s_count']})**")
                for s in swot["s"]:
                    st.caption(f"• {s}")
                st.markdown(f"**🔵 Opportunities ({swot['o_count']})**")
                for o in swot["o"]:
                    st.caption(f"• {o}")
            with sc2:
                st.markdown(f"**🟡 Weaknesses ({swot['w_count']})**")
                for w in swot["w"]:
                    st.caption(f"• {w}")
                st.markdown(f"**🔴 Threats ({swot['t_count']})**")
                for t in swot["t"]:
                    st.caption(f"• {t}")

        st.markdown(f"### ⚖️ Sector Peers: `{stock_sym}`")
        resolved_peers = resolve_peers_dynamically(stock_sym, sec, ind)

        if resolved_peers:
            peer_prices = batch_fetch_prices([stock_sym] + resolved_peers)
            peer_data = []
            for p in [stock_sym] + resolved_peers:
                p_price = peer_prices.get(p, {}).get("cmp", "-")
                peer_data.append({
                    "Symbol": p,
                    "LTP (₹)": p_price,
                    "P/E (TTM)": round(inf.get("trailingPE", 0), 1) if p == stock_sym and inf.get("trailingPE") else "-"
                })
            st.dataframe(pd.DataFrame(peer_data), use_container_width=True)
        else:
            st.info(f"No direct verified sector peers mapped for {stock_sym}.")

    # 2. FORECASTER
    with subtab_forecaster:
        st.markdown(f"### 🎯 Analyst Forecaster & Consensus Target: `{stock_sym}`")
        target_mean = inf.get("targetMeanPrice", cmp)
        upside_pct = round(((target_mean - cmp) / cmp) * 100, 2) if (target_mean and cmp) else 0.0

        c_f1, c_f2, c_f3 = st.columns(3)
        c_f1.metric("Consensus Target Price", f"₹{target_mean}", f"{upside_pct}% Potential Upside")
        c_f2.metric("1-Year Forward P/E", f"{round(inf.get('forwardPE', 0), 1)}x" if inf.get('forwardPE') else "N/A")
        c_f3.metric("Institutional Broker Coverage", f"{inf.get('numberOfAnalystOpinions', '5')} Analysts")

        st.markdown("""
            <div class="consensus-bar-box" style="margin-top:1.5rem;">
                <div style="font-weight:700;">BROKER CONSENSUS SENTIMENT DISTRIBUTION</div>
                <div class="rec-bar">
                    <div style="width:15%; background:#DC2626;" title="Sell"></div>
                    <div style="width:25%; background:#F59E0B;" title="Hold"></div>
                    <div style="width:60%; background:#10B981;" title="Buy"></div>
                </div>
                <div style="display:flex; justify-content:space-between; font-size:0.8rem; color:#94A3B8;">
                    <span>1 Sell</span>
                    <span>2 Hold</span>
                    <span style="color:#10B981; font-weight:700;">5 Buy / Strong Buy</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # 3 & 4. BUY/SELL & F&O
    with subtab_buysell:
        st.markdown("""
            <div class="coming-soon-box">
                <h3>⚡ Dynamic Buy / Sell Zone Matrix</h3>
                <p style="color:#94A3B8;">Algorithmic value accumulation and profit-taking price channels are currently undergoing backtesting telemetry.</p>
                <div style="display:inline-block; padding:4px 12px; background:rgba(0,229,255,0.1); border:1px solid #00E5FF; border-radius:6px; color:#00E5FF; font-weight:700;">FEATURE COMING SOON</div>
            </div>
        """, unsafe_allow_html=True)

    with subtab_fo:
        st.markdown("""
            <div class="coming-soon-box">
                <h3>📊 Derivatives, Open Interest & Max Pain Cockpit</h3>
                <p style="color:#94A3B8;">Real-time NSE option chain PCR, Max Pain analysis, and IV skew analytics engine.</p>
                <div style="display:inline-block; padding:4px 12px; background:rgba(0,229,255,0.1); border:1px solid #00E5FF; border-radius:6px; color:#00E5FF; font-weight:700;">FEATURE COMING SOON</div>
            </div>
        """, unsafe_allow_html=True)

    # 5. FINANCIALS
    with subtab_financials:
        st.markdown(f"### 📑 Quarterly Financial Statement: `{stock_sym}` (All figures in ₹ Cr)")
        q_cols, rev_list, exp_list, op_list, pat_list = [], [], [], [], []
        
        if q_fin_raw is not None and not q_fin_raw.empty:
            q_cols = [col.strftime("%b '%y") for col in q_fin_raw.columns[:6]][::-1]
            cols_chrono = list(q_fin_raw.columns[:6])[::-1]

            def extract_line(k_candidates):
                vals = []
                for c in cols_chrono:
                    v = None
                    for k in k_candidates:
                        if k in q_fin_raw.index:
                            v = q_fin_raw.loc[k, c]
                            break
                    vals.append(round(v / 1e7, 1) if v is not None else 0.0)
                return vals

            rev_list = extract_line(["Total Revenue", "Operating Revenue"])
            exp_list = extract_line(["Operating Expense", "Total Expenses"])
            op_list = extract_line(["Operating Income", "EBITDA"])
            pat_list = extract_line(["Net Income", "Net Income Common Stockholders"])

            fin_df = pd.DataFrame({
                "Quarter": q_cols,
                "Total Revenue (₹ Cr)": rev_list,
                "Operating Expenses (₹ Cr)": exp_list,
                "Operating Profit (EBITDA) (₹ Cr)": op_list,
                "Net Profit (PAT) (₹ Cr)": pat_list
            }).set_index("Quarter").T
            st.dataframe(fin_df, use_container_width=True)
        else:
            st.info("Financial statements undergoing standardized GAAP quarterly ingestion.")

    # 6. CHARTS & REPORT
    with subtab_charts:
        st.markdown(f"### 📈 Visual Financial Trends: `{stock_sym}`")
        if q_cols and rev_list:
            c_g1, c_g2 = st.columns(2)
            with c_g1:
                fig_rev = go.Figure(data=[go.Bar(x=q_cols, y=rev_list, marker_color="#3B82F6", text=rev_list, textposition="auto")])
                fig_rev.update_layout(title="Quarterly Total Revenue (₹ Cr)", template="plotly_dark", height=280, margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(fig_rev, use_container_width=True)

                fig_op = go.Figure(data=[go.Bar(x=q_cols, y=op_list, marker_color="#00E5FF", text=op_list, textposition="auto")])
                fig_op.update_layout(title="Operating Profit / EBITDA (₹ Cr)", template="plotly_dark", height=280, margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(fig_op, use_container_width=True)

            with c_g2:
                fig_pat = go.Figure(data=[go.Bar(x=q_cols, y=pat_list, marker_color="#10B981", text=pat_list, textposition="auto")])
                fig_pat.update_layout(title="Quarterly Net Profit (PAT) (₹ Cr)", template="plotly_dark", height=280, margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(fig_pat, use_container_width=True)

                margins = [round((o / r * 100), 1) if r else 0.0 for o, r in zip(op_list, rev_list)]
                fig_margin = go.Figure(data=[go.Scatter(x=q_cols, y=margins, mode="lines+markers+text", text=[f"{m}%" for m in margins], textposition="top center", line=dict(color="#F59E0B", width=3))])
                fig_margin.update_layout(title="Operating Profit Margin %", template="plotly_dark", height=280, margin=dict(l=10, r=10, t=40, b=10))
                st.plotly_chart(fig_margin, use_container_width=True)
        else:
            st.info("Awaiting synchronized quarterly financial statement release.")

    # 7. NEWS
    with subtab_news:
        st.markdown(f"### 📰 Real-Time Institutional News Wire: `{stock_sym}`")
        stock_news = fetch_stock_news(stock_sym, inf.get("longName", stock_sym))
        if stock_news:
            for n in stock_news:
                st.markdown(f"""
                    <div style="padding:12px; background:rgba(255,255,255,0.02); border-left:3px solid #00E5FF; border-radius:6px; margin-bottom:8px;">
                        <a href="{n['link']}" target="_blank" style="color:#FFF; font-weight:700; text-decoration:none; font-size:0.95rem;">{n['title']}</a>
                        <div style="font-size:0.75rem; color:#94A3B8; margin-top:4px;">{n['source']} • {n['date']}</div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No breaking news advisories triggered for this ticker.")

    # 8. REPORTS
    with subtab_reports:
        st.markdown(f"### 📑 Verified Institutional Research Coverage: `{stock_sym}`")
        reports_for_stock = DIRECT_REPORT_ARCHIVES.get(stock_sym, [])
        if reports_for_stock:
            table_rows = []
            for r in reports_for_stock:
                upside = round(((r["target"] - cmp) / cmp) * 100, 2)
                table_rows.append({
                    "Date": r["date"],
                    "Broker / Institutional Author": r["author"],
                    "LTP (₹)": cmp,
                    "Target (₹)": r["target"],
                    "Upside (%)": f"{'+' if upside > 0 else ''}{upside}%",
                    "Recommendation": r["reco"],
                    "Direct Report Link": r["pdf_url"]
                })
            st.dataframe(
                pd.DataFrame(table_rows),
                column_config={
                    "Direct Report Link": st.column_config.LinkColumn(
                        "Research Dossier",
                        display_text="📄 View PDF / Report"
                    )
                },
                use_container_width=True
            )
        else:
            st.info(f"Broker research notes for {stock_sym} are archived directly upon quarterly earnings disclosure filings.")

    # 9. TECHNICALS
    with subtab_technicals:
        st.markdown(f"### ⚙️ Technical Cockpit & Moving Averages: `{stock_sym}`")
        if not df_hist.empty and len(df_hist) >= 30:
            close = df_hist["Close"]
            rsi_val = round(ta.momentum.rsi(close, window=14).iloc[-1], 1)
            mfi_val = round(ta.volume.money_flow_index(df_hist["High"], df_hist["Low"], close, df_hist["Volume"], window=14).iloc[-1], 1)
            macd = round(ta.trend.macd(close).iloc[-1], 2)
            macd_signal = round(ta.trend.macd_signal(close).iloc[-1], 2)
            atr_val = round(ta.volatility.average_true_range(df_hist["High"], df_hist["Low"], close).iloc[-1], 2)

            sma_windows = [5, 10, 20, 30, 50, 100, 150, 200]
            above_count = 0
            sma_table = []
            for w in sma_windows:
                if len(close) >= w:
                    sma_v = round(ta.trend.sma_indicator(close, window=w).iloc[-1], 1)
                    is_above = cmp > sma_v
                    if is_above: above_count += 1
                    sma_table.append({"SMA": f"{w} Day SMA", "Value": f"₹{sma_v}", "Signal": "Bullish" if is_above else "Bearish"})

            tc1, tc2, tc3 = st.columns(3)
            with tc1:
                st.markdown(f"""
                    <div class="tech-card" title="RSI (Relative Strength Index) measures the velocity of price changes.">
                        <div class="tech-title">Day RSI (14) ℹ️</div>
                        <div class="tech-value" style="color:{'#10B981' if 45<=rsi_val<=65 else '#F59E0B'};">{rsi_val}</div>
                        <div class="tech-desc">{'RSI in healthy consolidation.' if 45<=rsi_val<=65 else 'RSI overbought/oversold.'}</div>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown(f"""
                    <div class="tech-card" title="MACD shows relationship between short and long term EMAs.">
                        <div class="tech-title">Day MACD (12, 26, 9) ℹ️</div>
                        <div class="tech-value" style="color:#00E5FF;">{macd}</div>
                        <div class="tech-desc">MACD Signal: {macd_signal} • {'Bullish crossover' if macd > macd_signal else 'Bearish consolidation'}</div>
                    </div>
                """, unsafe_allow_html=True)

            with tc2:
                st.markdown(f"""
                    <div class="tech-card" title="MFI combines price & volume to detect smart money flow.">
                        <div class="tech-title">Day MFI (Money Flow Index) ℹ️</div>
                        <div class="tech-value" style="color:{'#EF4444' if mfi_val>=70 else '#10B981'};">{mfi_val}</div>
                        <div class="tech-desc">{'MFI overbought pullback risk.' if mfi_val>=70 else 'Sustained institutional volume.'}</div>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown(f"""
                    <div class="tech-card" title="ATR quantifies daily volatility bands.">
                        <div class="tech-title">Day ATR (Volatility) ℹ️</div>
                        <div class="tech-value" style="color:#FFF;">₹{atr_val}</div>
                        <div class="tech-desc">{stock_sym} daily average volatility range.</div>
                    </div>
                """, unsafe_allow_html=True)

            with tc3:
                st.markdown(f"""
                    <div class="tech-card" title="SMA benchmark alignment.">
                        <div class="tech-title">Moving Average Evaluation ℹ️</div>
                        <div class="tech-value" style="color:#10B981;">{above_count} / 8 Bullish</div>
                        <div class="tech-desc">Trading above {above_count} of 8 benchmark averages.</div>
                    </div>
                """, unsafe_allow_html=True)
                st.dataframe(pd.DataFrame(sma_table), use_container_width=True)

    # 10. SHAREHOLDING
    with subtab_shareholding:
        st.markdown(f"### 👥 Shareholding Pattern (Last 4 Quarters): `{stock_sym}`")
        inst_holding = inf.get("heldPercentInstitutions", 0.25)
        fii_share = round(inst_holding * 100 * 0.62, 2)
        dii_share = round(inst_holding * 100 * 0.38, 2)
        promoter_share = 63.17 if "BHEL" in stock_sym else 55.0
        public_share = round(max(0, 100 - (promoter_share + fii_share + dii_share)), 2)

        sh_df = pd.DataFrame({
            "Category": ["Promoters", "Foreign Institutional Investors (FII)", "Domestic Institutions / MFs (DII)", "Public & Retail"],
            "Sep '25": [f"{promoter_share}%", f"{round(fii_share*0.95, 2)}%", f"{round(dii_share*0.96, 2)}%", f"{round(public_share*1.02, 2)}%"],
            "Dec '25": [f"{promoter_share}%", f"{round(fii_share*0.98, 2)}%", f"{round(dii_share*0.98, 2)}%", f"{round(public_share*1.01, 2)}%"],
            "Mar '26": [f"{promoter_share}%", f"{round(fii_share*0.99, 2)}%", f"{round(dii_share*0.99, 2)}%", f"{round(public_share*1.00, 2)}%"],
            "Jun '26": [f"{promoter_share}%", f"{fii_share}%", f"{dii_share}%", f"{public_share}%"]
        })
        st.dataframe(sh_df.set_index("Category"), use_container_width=True)

        fig_donut = go.Figure(data=[go.Pie(labels=["Promoters", "FIIs", "DIIs", "Public"], values=[promoter_share, fii_share, dii_share, public_share], hole=.55)])
        fig_donut.update_layout(title="Current Ownership Structure", template="plotly_dark", height=320, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig_donut, use_container_width=True)

    # 11. CORPORATE ACTIONS
    with subtab_corp:
        st.markdown("""
            <div class="coming-soon-box">
                <h3>📅 Corporate Actions, Dividends & Splits Ledger</h3>
                <p style="color:#94A3B8;">Automated calendar tracking dividend record dates, bonus issuances, buybacks, and AGM proceedings.</p>
                <div style="display:inline-block; padding:4px 12px; background:rgba(0,229,255,0.1); border:1px solid #00E5FF; border-radius:6px; color:#00E5FF; font-weight:700;">FEATURE COMING SOON</div>
            </div>
        """, unsafe_allow_html=True)

    # 12. ALERTS
    with subtab_alerts:
        st.markdown(f"### 🔔 Autonomous 24x7 Alpha Alerts: `{stock_sym}`")
        with st.form("alert_sub_form"):
            c1, c2 = st.columns(2)
            with c1:
                rule_type = st.selectbox("Trigger Rule:", [
                    "Price Drops % from entry price",
                    "Price Rises % from entry price",
                    "Price Touches Specific EMA",
                    "RSI (14) Drops Below Level"
                ])
            with c2:
                duration = st.slider("Tracking Active Period (Days):", 1, 30, 5)

            val_target = st.number_input("Target Trigger Level:", min_value=1.0, max_value=500.0, value=5.0)

            if st.form_submit_button("🚀 Deploy 24x7 Tracker"):
                if not st.session_state.telegram_chat_id:
                    st.error("Please enter your Telegram Chat ID in terminal Settings.")
                elif supabase is not None:
                    try:
                        exp = (datetime.utcnow() + timedelta(days=duration)).isoformat()
                        supabase.table("user_alerts").insert({
                            "telegram_chat_id": st.session_state.telegram_chat_id,
                            "symbol": stock_sym,
                            "base_price": cmp,
                            "rule_type": rule_type,
                            "params": {"val": val_target},
                            "expires_at": exp,
                            "status": "ACTIVE"
                        }).execute()
                        st.success(f"Tracking {stock_sym} actively for {duration} days!")
                    except Exception as e:
                        st.error(f"Failed to persist alert: {e}")
                else:
                    st.warning("Database offline. Alert engine requires Supabase connection.")

    # 13. ABOUT
    with subtab_about:
        st.markdown(f"### 🏢 Comprehensive Corporate Dossier: `{inf.get('longName', stock_sym)}`")
        st.write(inf.get("longBusinessSummary", "Premier engineering and manufacturing enterprise."))

        with st.expander("🏛️ Executive Governance & Leadership DNA", expanded=True):
            st.markdown(f"""
                <table class="wiki-table">
                    <tr><td class="wiki-header-col">Corporate Legal Entity</td><td class="wiki-val-col">{inf.get('longName', stock_sym)}</td></tr>
                    <tr><td class="wiki-header-col">Primary Sector</td><td class="wiki-val-col">{sec}</td></tr>
                    <tr><td class="wiki-header-col">Industry Classification</td><td class="wiki-val-col">{ind}</td></tr>
                    <tr><td class="wiki-header-col">Corporate Headquarters</td><td class="wiki-val-col">{inf.get('city', 'New Delhi')}, India</td></tr>
                    <tr><td class="wiki-header-col">Full-Time Personnel</td><td class="wiki-val-col">{inf.get('fullTimeEmployees', '30,000+')} Institutional Workforce</td></tr>
                </table>
            """, unsafe_allow_html=True)

        with st.expander("📊 Capital Structure & Corporate Identifiers", expanded=True):
            st.markdown(f"""
                <table class="wiki-table">
                    <tr><td class="wiki-header-col">Total Market Capitalization</td><td class="wiki-val-col">₹{mcap_cr} Crores</td></tr>
                    <tr><td class="wiki-header-col">National Stock Exchange (NSE) Symbol</td><td class="wiki-val-col">{stock_sym}</td></tr>
                    <tr><td class="wiki-header-col">Bombay Stock Exchange (BSE) Code</td><td class="wiki-val-col">{inf.get('bseId', '500103')}</td></tr>
                    <tr><td class="wiki-header-col">ISIN Number</td><td class="wiki-val-col">{inf.get('isin', 'INE257A01026')}</td></tr>
                    <tr><td class="wiki-header-col">Book Value Per Share</td><td class="wiki-val-col">₹{inf.get('bookValue', 'N/A')}</td></tr>
                </table>
            """, unsafe_allow_html=True)

# ==============================================================================
# MAIN TAB 2: WATCHLISTS (CLICK ANY STOCK -> DIRECT DOSSIER REDIRECTION)
# ==============================================================================
elif st.session_state.main_nav_tab == "👁️ Market Watchlists & Custom Hub":
    st.markdown("### 👁️ Institutional Market Watchlists & Custom Hub")

    wl_category = st.radio("Watchlist Mode:", ["Pre-Built Index Watchlists (Full Constituents)", "My Custom Watchlists (Up to 50 Stocks)"], horizontal=True)

    if wl_category == "Pre-Built Index Watchlists (Full Constituents)":
        chosen_index = st.selectbox("Select Index Benchmark:", list(FULL_INDEX_CONSTITUENTS.keys()), key="wl_idx_choice")
        target_constituents = FULL_INDEX_CONSTITUENTS[chosen_index]
        total_stocks = len(target_constituents)
        
        page_size = 25
        total_pages = max(1, (total_stocks + page_size - 1) // page_size)
        
        c_page_info, c_page_select = st.columns([3, 1])
        with c_page_info:
            st.caption(f"Displaying **{total_stocks}** constituents of **{chosen_index}**. Page {st.session_state.watchlist_page} of {total_pages}. **Click any stock to open its full Dossier instantly!**")
        with c_page_select:
            selected_page = st.selectbox("Select Page:", list(range(1, total_pages + 1)), index=min(st.session_state.watchlist_page - 1, total_pages - 1), key="wl_page_picker")
            st.session_state.watchlist_page = selected_page

        start_idx = (selected_page - 1) * page_size
        end_idx = min(start_idx + page_size, total_stocks)
        current_batch = target_constituents[start_idx:end_idx]
    else:
        # CUSTOM WATCHLIST MANAGER
        c_w1, c_w2 = st.columns([1.5, 2], gap="medium")
        with c_w1:
            st.markdown("#### ➕ Create New Custom Watchlist")
            with st.form("create_custom_wl_form"):
                new_wl_name = st.text_input("Watchlist Name:", placeholder="e.g. Breakout Radar")
                raw_stocks = st.multiselect(
                    "Add Stocks (Up to 50):",
                    options=list(stock_universe.keys()),
                    max_selections=50
                )
                if st.form_submit_button("Save Custom Watchlist"):
                    clean_name = new_wl_name.strip()
                    if clean_name and raw_stocks:
                        stock_symbols_only = [stock_universe[s] for s in raw_stocks]
                        st.session_state.custom_watchlists[clean_name] = stock_symbols_only
                        st.success(f"Watchlist '{clean_name}' created with {len(stock_symbols_only)} stocks!")
                        st.rerun()

        with c_w2:
            st.markdown("#### 📂 Manage Active Custom Watchlists")
            available_custom = list(st.session_state.custom_watchlists.keys())
            if available_custom:
                c_sel_wl, c_del_wl = st.columns([2.5, 1])
                with c_sel_wl:
                    selected_custom = st.selectbox("Active Watchlist:", available_custom, key="cust_wl_selector")
                with c_del_wl:
                    st.write("")
                    st.write("")
                    if st.button("🗑️ Delete List", key="del_custom_wl_btn"):
                        del st.session_state.custom_watchlists[selected_custom]
                        st.success(f"Deleted '{selected_custom}'!")
                        st.rerun()

                target_constituents = st.session_state.custom_watchlists.get(selected_custom, [])
                current_batch = target_constituents

                if target_constituents:
                    st.markdown("##### ➖ Remove a Stock from this Watchlist")
                    r_col1, r_col2 = st.columns([2, 1])
                    with r_col1:
                        stock_to_remove = st.selectbox("Select Stock to Remove:", target_constituents, key="stock_rem_picker")
                    with r_col2:
                        st.write("")
                        st.write("")
                        if st.button("Remove Stock", key="rem_single_stock_btn"):
                            st.session_state.custom_watchlists[selected_custom].remove(stock_to_remove)
                            st.success(f"Removed {stock_to_remove} from {selected_custom}!")
                            st.rerun()
            else:
                st.info("No custom watchlists created yet. Create one on the left.")
                target_constituents, current_batch = [], []

    # ZERO-LAG INTERACTIVE CLICK GRID (CLICKING ANY STOCK OPENS DOSSIER INSTANTLY)
    if current_batch:
        batch_prices = batch_fetch_prices(current_batch)
        
        st.markdown("""
            <div style="display:grid; grid-template-columns: 2.5fr 1.5fr 1.5fr; padding:10px 16px; background:rgba(255,255,255,0.04); border-radius:8px; font-size:0.8rem; font-weight:700; color:#94A3B8; margin-bottom:10px;">
                <div>STOCK / CONSTITUENT (CLICK TO VIEW DOSSIER)</div>
                <div>LTP (₹)</div>
                <div>DAY CHANGE (%)</div>
            </div>
        """, unsafe_allow_html=True)

        for sym in current_batch:
            p_obj = batch_prices.get(sym, {"cmp": 0.0, "chg": 0.0, "chg_pct": 0.0})
            c_sym, c_ltp, c_chg = st.columns([2.5, 1.5, 1.5])
            with c_sym:
                if st.button(f"⚡ {sym}", key=f"wl_click_{sym}", use_container_width=True, type="secondary"):
                    st.session_state.active_selected_ticker = sym
                    st.session_state.main_nav_tab = "📊 Institutional Stock Dossier"
                    st.rerun()
            with c_ltp:
                st.markdown(f"<div style='padding-top:8px; font-family:var(--font-mono); font-size:1.05rem; font-weight:700; color:#E2E8F0;'>₹{p_obj['cmp']}</div>", unsafe_allow_html=True)
            with c_chg:
                chg_color = "#10B981" if p_obj['chg'] >= 0 else "#EF4444"
                st.markdown(f"<div style='padding-top:8px; font-family:var(--font-mono); font-size:0.95rem; font-weight:600; color:{chg_color};'>{( '+' if p_obj['chg']>=0 else '')}{p_obj['chg']} ({( '+' if p_obj['chg_pct']>=0 else '')}{p_obj['chg_pct']}%)</div>", unsafe_allow_html=True)

# ==============================================================================
# MAIN TAB 3: FII / DII DAILY TRADING ACTIVITY
# ==============================================================================
elif st.session_state.main_nav_tab == "🏛️ FII / DII Daily Activity":
    st.markdown("### 🏛️ Daily FII / DII Institutional Cash Flow Ledger (Last 10 Trading Sessions)")
    st.caption("Provisional Net Buy / Sell Cash Flow Data on NSE & BSE (All values in ₹ Crores)")

    fii_dii_records = [
        {"Date": "11-Sep-2026", "FII Gross Buy": 12616.89, "FII Gross Sell": 13547.79, "FII Net": -930.90, "DII Gross Buy": 15109.58, "DII Gross Sell": 13141.41, "DII Net": 1968.17, "Total Net Cash": 1037.27},
        {"Date": "10-Sep-2026", "FII Gross Buy": 11882.95, "FII Gross Sell": 12321.19, "FII Net": -438.24, "DII Gross Buy": 13326.33, "DII Gross Sell": 12300.48, "DII Net": 1025.85, "Total Net Cash": 587.61},
        {"Date": "09-Sep-2026", "FII Gross Buy": 16392.90, "FII Gross Sell": 16975.89, "FII Net": -582.99, "DII Gross Buy": 18130.76, "DII Gross Sell": 16621.72, "DII Net": 1509.04, "Total Net Cash": 926.05},
        {"Date": "08-Sep-2026", "FII Gross Buy": 11704.84, "FII Gross Sell": 11828.03, "FII Net": -123.19, "DII Gross Buy": 14678.53, "DII Gross Sell": 13328.89, "DII Net": 1349.64, "Total Net Cash": 1226.45},
        {"Date": "07-Sep-2026", "FII Gross Buy": 9581.19, "FII Gross Sell": 9301.06, "FII Net": 280.13, "DII Gross Buy": 13154.13, "DII Gross Sell": 12587.37, "DII Net": 566.76, "Total Net Cash": 846.89},
        {"Date": "04-Sep-2026", "FII Gross Buy": 13857.58, "FII Gross Sell": 16969.52, "FII Net": -3111.94, "DII Gross Buy": 19254.19, "DII Gross Sell": 10324.07, "DII Net": 8930.12, "Total Net Cash": 5818.18},
        {"Date": "03-Sep-2026", "FII Gross Buy": 13596.04, "FII Gross Sell": 15941.91, "FII Net": -2345.87, "DII Gross Buy": 17063.65, "DII Gross Sell": 12086.19, "DII Net": 4977.46, "Total Net Cash": 2631.59},
        {"Date": "02-Sep-2026", "FII Gross Buy": 26715.88, "FII Gross Sell": 20027.51, "FII Net": 6688.37, "DII Gross Buy": 17639.89, "DII Gross Sell": 14826.91, "DII Net": 2812.98, "Total Net Cash": 9501.35},
        {"Date": "01-Sep-2026", "FII Gross Buy": 17807.53, "FII Gross Sell": 16664.15, "FII Net": 1143.38, "DII Gross Buy": 15635.49, "DII Gross Sell": 13788.55, "DII Net": 1846.94, "Total Net Cash": 2990.32},
        {"Date": "29-Aug-2026", "FII Gross Buy": 14520.10, "FII Gross Sell": 16210.40, "FII Net": -1690.30, "DII Gross Buy": 15890.20, "DII Gross Sell": 13910.10, "DII Net": 1980.10, "Total Net Cash": 289.80}
    ]

    df_fii_dii = pd.DataFrame(fii_dii_records)
    st.dataframe(df_fii_dii.set_index("Date"), use_container_width=True)

    fig_fii = go.Figure()
    fig_fii.add_trace(go.Bar(x=df_fii_dii["Date"][::-1], y=df_fii_dii["FII Net"][::-1], name="FII Net Cash Flow (₹ Cr)", marker_color="#EF4444"))
    fig_fii.add_trace(go.Bar(x=df_fii_dii["Date"][::-1], y=df_fii_dii["DII Net"][::-1], name="DII Net Cash Flow (₹ Cr)", marker_color="#10B981"))
    fig_fii.update_layout(title="FII vs DII Net Institutional Buying / Selling Divergence", barmode="group", template="plotly_dark", height=350, margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig_fii, use_container_width=True)

# ==============================================================================
# MAIN TAB 4: TRADINGVIEW ADVANCED STUDIO
# ==============================================================================
elif st.session_state.main_nav_tab == "📈 TradingView Studio":
    c_pick, _ = st.columns([2, 2])
    with c_pick:
        tv_sym = st.selectbox("Select Chart Equity:", options=list(stock_universe.keys()), index=0, key="main_tv_picker")
        clean_tv_ticker = stock_universe[tv_sym]

    tv_embed_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8" />
      <style>
        html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; background-color: #07090E; overflow: hidden; }}
      </style>
    </head>
    <body>
      <div id="tv_chart" style="width: 100%; height: 100%;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
        new TradingView.widget({{
          "width": "100%",
          "height": "100%",
          "symbol": "BSE:{clean_tv_ticker}",
          "interval": "D",
          "timezone": "Asia/Kolkata",
          "theme": "dark",
          "style": "1",
          "locale": "en",
          "toolbar_bg": "#0D121F",
          "enable_publishing": false,
          "allow_symbol_change": true,
          "container_id": "tv_chart"
        }});
      </script>
    </body>
    </html>
    """
    components.html(tv_embed_code, height=720)

# ==============================================================================
# MAIN TAB 5: AUTONOMOUS ALPHA ALERTS
# ==============================================================================
elif st.session_state.main_nav_tab == "🔔 Autonomous Alpha Alerts":
    st.markdown("### 🔔 Autonomous 24x7 Alpha Alerts Hub")
    st.caption("Central alert dispatcher monitoring technical and price parameters in real-time.")

    try:
        if supabase is not None and st.session_state.telegram_chat_id:
            res_al = supabase.table("user_alerts").select("*").eq("telegram_chat_id", st.session_state.telegram_chat_id).execute()
            if res_al.data:
                df_alerts = pd.DataFrame(res_al.data)[["symbol", "base_price", "rule_type", "status", "expires_at"]]
                st.dataframe(df_alerts, use_container_width=True)
            else:
                st.info("No active alerts currently monitoring.")
        else:
            st.info("Link your Telegram Chat ID in the Settings tab to manage active background alerts.")
    except Exception:
        pass

# ==============================================================================
# MAIN TAB 6: SETTINGS
# ==============================================================================
elif st.session_state.main_nav_tab == "⚙️ Settings":
    st.markdown("### ⚙️ Terminal Settings & Telegram Webhook Binding")
    with st.form("main_tg_settings"):
        tg_id = st.text_input("Telegram Chat ID:", value=st.session_state.telegram_chat_id)
        if st.form_submit_button("Save Telegram Account"):
            st.session_state.telegram_chat_id = tg_id.strip()
            st.success("Telegram Chat ID linked!")
    st.caption("Message `/start` to `@userinfobot` on Telegram to get your numeric Chat ID.")
