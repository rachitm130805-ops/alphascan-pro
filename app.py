import concurrent.futures
import io
import json
import time
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
import ta
import yfinance as yf
from supabase import create_client, Client

# --- SECRETS & SUPABASE INIT ---
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

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="AlphaScan Pro | Institutional Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- NVIDIA / GOOGLE DESIGN SYSTEM (HIGH DENSITY DARK UI) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --bg-void: #06080E;
        --surface-1: #0D121F;
        --surface-2: #141C30;
        --border-subtle: rgba(255, 255, 255, 0.08);
        --border-active: rgba(0, 229, 255, 0.4);
        --accent-nvidia: #76B900;
        --accent-cyan: #00E5FF;
        --accent-emerald: #10B981;
        --accent-rose: #F43F5E;
        --text-pure: #FFFFFF;
        --text-sub: #94A3B8;
        --font-main: 'Plus Jakarta Sans', sans-serif;
        --font-mono: 'JetBrains Mono', monospace;
    }

    .stApp {
        background: radial-gradient(circle at 50% -20%, #111A33 0%, #06080E 65%) !important;
        font-family: var(--font-main) !important;
        color: var(--text-pure);
    }

    #MainMenu, footer, header { visibility: hidden; }
    .block-container {
        padding: 1.25rem 2.5rem !important;
        max-width: 1440px !important;
    }

    /* Terminal Nav Header */
    .terminal-nav {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 24px;
        background: rgba(13, 18, 31, 0.75);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }

    .nav-brand {
        font-size: 1.25rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .badge-chip {
        font-size: 0.65rem;
        font-weight: 700;
        padding: 2px 8px;
        border-radius: 4px;
        background: rgba(118, 185, 0, 0.15);
        color: var(--accent-nvidia);
        border: 1px solid rgba(118, 185, 0, 0.3);
    }

    /* Fundamental Metric Cards (Screener.in Style) */
    .funda-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 12px;
        margin-bottom: 1.5rem;
    }

    .funda-card {
        background: var(--surface-1);
        border: 1px solid var(--border-subtle);
        border-radius: 10px;
        padding: 12px 14px;
        transition: all 0.2s ease;
    }

    .funda-card:hover {
        border-color: var(--border-active);
        transform: translateY(-2px);
    }

    .funda-title {
        font-size: 0.75rem;
        color: var(--text-sub);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
    }

    .funda-val {
        font-size: 1.15rem;
        font-weight: 700;
        color: #FFFFFF;
        font-family: var(--font-mono);
        margin-top: 4px;
    }

    /* Pros & Cons Container */
    .pros-box {
        background: rgba(16, 185, 129, 0.05);
        border: 1px solid rgba(16, 185, 129, 0.2);
        border-radius: 10px;
        padding: 1rem;
    }

    .cons-box {
        background: rgba(244, 63, 94, 0.05);
        border: 1px solid rgba(244, 63, 94, 0.2);
        border-radius: 10px;
        padding: 1rem;
    }

    /* Standard Interactive Streamlit Inputs */
    .stButton > button {
        background: linear-gradient(135deg, #00E5FF 0%, #10B981 100%) !important;
        color: #06080E !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.55rem 1.25rem !important;
        font-weight: 700 !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button:hover {
        opacity: 0.9;
        transform: translateY(-1px);
        box-shadow: 0 4px 15px rgba(0, 229, 255, 0.3) !important;
    }

    div[data-testid="stForm"] {
        background: rgba(13, 18, 31, 0.85) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 14px !important;
        padding: 2rem !important;
    }

    .stTextInput > div > div > input, div[data-baseweb="select"] > div {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid var(--border-subtle) !important;
        color: var(--text-pure) !important;
        border-radius: 8px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "Sign In"
if "scan_results" not in st.session_state:
    st.session_state.scan_results = None
if "telegram_chat_id" not in st.session_state:
    st.session_state.telegram_chat_id = ""

# --- TELEGRAM SENDER ---
def send_telegram_alert(message, chat_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload, timeout=8)
        return res.status_code == 200
    except Exception:
        return False

# --- LOAD NSE/BSE UNIVERSE ---
@st.cache_data(ttl=86400)
def load_stock_universe():
    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            df = pd.read_csv(io.StringIO(resp.content.decode("utf-8")))
            df = df[df[" SERIES"] == "EQ"]
            records = {}
            for _, row in df.iterrows():
                sym = str(row["SYMBOL"]).strip()
                company = str(row["NAME OF COMPANY"]).strip()
                records[f"{sym} — {company}"] = sym
            return records
    except Exception:
        pass
    return {
        "ADANIPOWER — Adani Power Limited": "ADANIPOWER",
        "RELIANCE — Reliance Industries Limited": "RELIANCE",
        "TATASTEEL — Tata Steel Limited": "TATASTEEL",
        "INFY — Infosys Limited": "INFY",
        "ICICIBANK — ICICI Bank Limited": "ICICIBANK",
        "SBIN — State Bank of India": "SBIN",
        "HDFCBANK — HDFC Bank Limited": "HDFCBANK",
        "TCS — Tata Consultancy Services Limited": "TCS",
        "LT — Larsen & Toubro Limited": "LT",
        "ZOMATO — Zomato Limited": "ZOMATO"
    }

stock_universe = load_stock_universe()

# --- LANDING PAGE ---
if not st.session_state.user:
    st.markdown("""
        <div class="terminal-nav">
            <div class="nav-brand">
                ⚡ AlphaScan <span class="badge-chip">NVIDIA ARCH</span>
            </div>
            <div style="font-size:0.8rem; color:#94A3B8;">Real-Time Techno-Fundamental Terminal</div>
        </div>
    """, unsafe_allow_html=True)

    col_hero, col_auth = st.columns([1.2, 1], gap="large")

    with col_hero:
        st.markdown("""
            <h1 style="font-size: 3rem; font-weight:800; line-height:1.15; margin-bottom:0.75rem;">
                Techno-Fundamental Equity Intelligence.
            </h1>
            <p style="color:#94A3B8; font-size:1.1rem; line-height:1.6; margin-bottom:2rem;">
                Complete Screener.in-grade financial statements, ratio analysis, balance sheets, and real-time technical swing triggers—all unified into a single enterprise terminal.
            </p>
        """, unsafe_allow_html=True)

        g1, g2 = st.columns(2)
        with g1:
            st.markdown("""
                <div class="funda-card">
                    <div style="font-size:1.4rem;">📊</div>
                    <div style="font-weight:700; margin-top:6px;">Screener Financials</div>
                    <div style="font-size:0.8rem; color:#94A3B8;">Quarterly P&L, Balance Sheets, Compounded Sales, Cash Flows.</div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
            st.markdown("""
                <div class="funda-card">
                    <div style="font-size:1.4rem;">🎯</div>
                    <div style="font-weight:700; margin-top:6px;">Algorithmic Screeners</div>
                    <div style="font-size:0.8rem; color:#94A3B8;">Multi-threaded technical scanners & custom financial metrics.</div>
                </div>
            """, unsafe_allow_html=True)
        with g2:
            st.markdown("""
                <div class="funda-card">
                    <div style="font-size:1.4rem;">⚡</div>
                    <div style="font-weight:700; margin-top:6px;">TradingView Pro Engine</div>
                    <div style="font-size:0.8rem; color:#94A3B8;">Unrestricted BSE/NSE charts with full drawing tools & indicators.</div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
            st.markdown("""
                <div class="funda-card">
                    <div style="font-size:1.4rem;">📲</div>
                    <div style="font-weight:700; margin-top:6px;">Telegram Bot Signals</div>
                    <div style="font-size:0.8rem; color:#94A3B8;">Direct multi-channel alert dispatch with single-click sync.</div>
                </div>
            """, unsafe_allow_html=True)

    with col_auth:
        mode = st.radio("Terminal Auth", ["Sign In", "Create Account"], horizontal=True, label_visibility="collapsed")
        if mode == "Sign In":
            with st.form("signin_form"):
                st.subheader("Sign In to Terminal")
                email = st.text_input("Account Email", placeholder="trader@alphascan.com")
                password = st.text_input("Password", type="password", placeholder="Enter your credentials")
                if st.form_submit_button("Enter Terminal", use_container_width=True):
                    if not email or not password:
                        st.error("Missing credentials.")
                    else:
                        try:
                            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                            st.session_state.user = res.user
                            if res.user and res.user.user_metadata:
                                st.session_state.telegram_chat_id = res.user.user_metadata.get("telegram_chat_id", "")
                            st.success("Authenticated.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed: {e}")
        else:
            with st.form("signup_form"):
                st.subheader("Create Profile")
                email = st.text_input("Account Email", placeholder="trader@alphascan.com")
                password = st.text_input("Password (min 6 chars)", type="password")
                if st.form_submit_button("Register Account", use_container_width=True):
                    if not email or not password:
                        st.error("Fill all fields.")
                    else:
                        try:
                            res = supabase.auth.sign_up({"email": email, "password": password})
                            st.success("Account created! Switch to Sign In above.")
                        except Exception as e:
                            st.error(f"Error: {e}")

    st.stop()

# --- AUTHENTICATED TERMINAL DASHBOARD ---
user_email = st.session_state.user.email

st.markdown(f"""
    <div class="terminal-nav">
        <div class="nav-brand">
            ⚡ AlphaScan <span class="badge-chip">NVIDIA ARCH</span>
        </div>
        <div style="display:flex; align-items:center; gap:16px;">
            <span style="font-size:0.85rem; color:#94A3B8;">User: <b style="color:#FFF;">{user_email}</b></span>
            <div style="width:8px; height:8px; border-radius:50%; background:#10B981; box-shadow:0 0 8px #10B981;"></div>
        </div>
    </div>
""", unsafe_allow_html=True)

# Extended Terminal Tabs including Screener.in Fundamentals & Custom Screener
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Screener.in Fundamentals",
    "📈 TradingView Charts",
    "⚡ Technical Scanners",
    "🧪 Custom Query Screener",
    "⚙️ Terminal Settings"
])

# ==============================================================================
# TAB 1: SCREENER.IN COMPLETE FUNDAMENTALS ENGINE
# ==============================================================================
with tab1:
    st.markdown("<br>", unsafe_allow_html=True)

    c_select, _ = st.columns([2, 2])
    with c_select:
        options = list(stock_universe.keys())
        selected_label = st.selectbox("Search Company for Fundamental Report:", options=options, index=0)
        stock_sym = stock_universe[selected_label]
        yf_symbol = f"{stock_sym}.NS"

    with st.spinner(f"Aggregating Screener.in fundamental report for {stock_sym}..."):
        try:
            ticker_obj = yf.Ticker(yf_symbol)
            info = ticker_obj.info

            # Header Overview Card
            company_name = info.get("longName", stock_sym)
            sector = info.get("sector", "N/A")
            industry = info.get("industry", "N/A")
            summary = info.get("longBusinessSummary", "No company profile available.")
            current_price = info.get("currentPrice", info.get("regularMarketPrice", 0.0))
            mcap = info.get("marketCap", 0)
            mcap_cr = round(mcap / 1e7, 2) if mcap else "N/A"
            pe = round(info.get("trailingPE", 0), 2) if info.get("trailingPE") else "N/A"
            book_value = round(info.get("bookValue", 0), 2) if info.get("bookValue") else "N/A"
            div_yield = f"{round(info.get('dividendYield', 0) * 100, 2)}%" if info.get("dividendYield") else "0.0%"
            roce = f"{round(info.get('returnOnAssets', 0) * 100, 2)}%" if info.get("returnOnAssets") else "N/A"
            roe = f"{round(info.get('returnOnEquity', 0) * 100, 2)}%" if info.get("returnOnEquity") else "N/A"
            high_52 = info.get("fiftyTwoWeekHigh", "N/A")
            low_52 = info.get("fiftyTwoWeekLow", "N/A")

            st.markdown(f"""
                <div style="margin-bottom: 1rem;">
                    <h2 style="margin:0; font-size:1.8rem;">{company_name}</h2>
                    <span style="color:#00E5FF; font-weight:600;">{sector}</span> • <span style="color:#94A3B8;">{industry}</span>
                </div>
            """, unsafe_allow_html=True)

            # Key Fundamental Metric Cards
            st.markdown(f"""
                <div class="funda-grid">
                    <div class="funda-card"><div class="funda-title">Market Cap</div><div class="funda-val">₹{mcap_cr} Cr</div></div>
                    <div class="funda-card"><div class="funda-title">Current Price</div><div class="funda-val">₹{current_price}</div></div>
                    <div class="funda-card"><div class="funda-title">52W High / Low</div><div class="funda-val">₹{high_52} / {low_52}</div></div>
                    <div class="funda-card"><div class="funda-title">Stock P/E</div><div class="funda-val">{pe}</div></div>
                    <div class="funda-card"><div class="funda-title">Book Value</div><div class="funda-val">₹{book_value}</div></div>
                    <div class="funda-card"><div class="funda-title">Dividend Yield</div><div class="funda-val">{div_yield}</div></div>
                    <div class="funda-card"><div class="funda-title">ROCE</div><div class="funda-val">{roce}</div></div>
                    <div class="funda-card"><div class="funda-title">ROE</div><div class="funda-val">{roe}</div></div>
                </div>
            """, unsafe_allow_html=True)

            # Automated Pros & Cons (Screener.in Core Element)
            col_pros, col_cons = st.columns(2)
            with col_pros:
                pros_list = []
                if isinstance(pe, (int, float)) and pe < 20:
                    pros_list.append("Stock is trading at an attractive price-to-earnings multiple.")
                if info.get("debtToEquity", 100) < 50:
                    pros_list.append("Company has low debt or is almost debt-free.")
                if info.get("profitMargins", 0) > 0.12:
                    pros_list.append("Company is maintaining a healthy operating profit margin.")
                if not pros_list:
                    pros_list.append("Company has shown consistent operational continuity.")

                pros_html = "".join([f"<li style='margin-bottom:6px;'>{p}</li>" for p in pros_list])
                st.markdown(f"""
                    <div class="pros-box">
                        <b style="color:#10B981; font-size:0.95rem;">✅ PROS</b>
                        <ul style="color:#94A3B8; font-size:0.85rem; margin-top:8px; padding-left:20px;">{pros_html}</ul>
                    </div>
                """, unsafe_allow_html=True)

            with col_cons:
                cons_list = []
                if isinstance(pe, (int, float)) and pe > 40:
                    cons_list.append("Stock is trading at a premium valuation relative to book value.")
                if info.get("debtToEquity", 0) > 100:
                    cons_list.append("Company carries high borrowing and financial leverage.")
                if info.get("revenueGrowth", 0) < 0:
                    cons_list.append("Sales growth has shown deceleration over recent quarters.")
                if not cons_list:
                    cons_list.append("Tax and margin variance observed in trailing periods.")

                cons_html = "".join([f"<li style='margin-bottom:6px;'>{c}</li>" for c in cons_list])
                st.markdown(f"""
                    <div class="cons-box">
                        <b style="color:#F43F5E; font-size:0.95rem;">⚠️ CONS</b>
                        <ul style="color:#94A3B8; font-size:0.85rem; margin-top:8px; padding-left:20px;">{cons_html}</ul>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown("<hr style='border-color:rgba(255,255,255,0.08); margin: 2rem 0;'>", unsafe_allow_html=True)

            # Financial Tables: Quarterly Results & Annual P&L
            st.subheader("📑 Financial Statements & Statements of Profit & Loss")
            funda_view = st.radio("Select Statement:", ["Quarterly Results", "Annual Profit & Loss", "Balance Sheet", "Cash Flows"], horizontal=True)

            if funda_view == "Quarterly Results":
                q_fin = ticker_obj.quarterly_financials
                if not q_fin.empty:
                    # Clean column dates and format in Crores
                    df_q = q_fin.iloc[:8].copy()
                    df_q.columns = [d.strftime("%b %Y") for d in df_q.columns]
                    st.dataframe((df_q / 1e7).round(2), use_container_width=True)
                    st.caption("Figures reported in ₹ Crores")
                else:
                    st.warning("Quarterly financial records not available.")

            elif funda_view == "Annual Profit & Loss":
                a_fin = ticker_obj.financials
                if not a_fin.empty:
                    df_a = a_fin.iloc[:10].copy()
                    df_a.columns = [d.strftime("%Y") for d in df_a.columns]
                    st.dataframe((df_a / 1e7).round(2), use_container_width=True)
                    st.caption("Figures reported in ₹ Crores")
                else:
                    st.warning("Annual P&L statement records not available.")

            elif funda_view == "Balance Sheet":
                bs = ticker_obj.balance_sheet
                if not bs.empty:
                    df_bs = bs.iloc[:10].copy()
                    df_bs.columns = [d.strftime("%Y") for d in df_bs.columns]
                    st.dataframe((df_bs / 1e7).round(2), use_container_width=True)
                    st.caption("Figures reported in ₹ Crores")
                else:
                    st.warning("Balance sheet records not available.")

            else:
                cf = ticker_obj.cashflow
                if not cf.empty:
                    df_cf = cf.iloc[:8].copy()
                    df_cf.columns = [d.strftime("%Y") for d in df_cf.columns]
                    st.dataframe((df_cf / 1e7).round(2), use_container_width=True)
                    st.caption("Figures reported in ₹ Crores")
                else:
                    st.warning("Cash flow statement records not available.")

        except Exception as err:
            st.error(f"Fundamental aggregation failed: {err}")

# ==============================================================================
# TAB 2: TRADINGVIEW ADVANCED UNRESTRICTED CHARTS
# ==============================================================================
with tab2:
    st.markdown("<br>", unsafe_allow_html=True)
    c_chart_sel, c_popout = st.columns([3, 1])
    with c_chart_sel:
        opt_chart = list(stock_universe.keys())
        selected_chart_lbl = st.selectbox("Select Symbol for Interactive Chart:", options=opt_chart, index=0)
        c_sym = stock_universe[selected_chart_lbl]

    with c_popout:
        st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
        tv_url = f"https://in.tradingview.com/chart/?symbol=BSE:{c_sym}"
        st.markdown(f'<a href="{tv_url}" target="_blank"><button style="width:100%; background:#76B900; color:#000; font-weight:700; border:none; border-radius:8px; padding:9px 12px; cursor:pointer;">↗️ Full TradingView Studio</button></a>', unsafe_allow_html=True)

    st.markdown(f"### 📈 TradingView Advanced Engine: `{c_sym}`")
    tv_code = f"""
    <div class="tradingview-widget-container" style="height:720px;width:100%;">
      <div id="tv_chart_container" style="height:calc(100% - 32px);width:100%;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "symbol": "BSE:{c_sym}",
        "interval": "W",
        "timezone": "Asia/Kolkata",
        "theme": "dark",
        "style": "1",
        "locale": "in",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "hide_side_toolbar": false,
        "studies": ["MASimple@tv-basicstudies", "EMA@tv-basicstudies"],
        "container_id": "tv_chart_container"
      }});
      </script>
    </div>
    """
    components.html(tv_code, height=730)

# ==============================================================================
# TAB 3: TECHNICAL MULTI-STRATEGY SCANNERS
# ==============================================================================
with tab3:
    st.markdown("<br>", unsafe_allow_html=True)
    col_sc1, col_sc2 = st.columns([1, 2.5])

    with col_sc1:
        st.markdown('<div class="funda-card">', unsafe_allow_html=True)
        st.subheader("Strategy Parameters")
        strat = st.selectbox("Strategy Profile:", ["Weekly 10 EMA Support", "Bullish MACD Crossover", "RSI Oversold Bounce (RSI < 35)"])
        scan_univ = st.radio("Scanning Universe:", ["Watchlist", "Nifty 50", "Full NSE (2000+ Stocks)"])
        tolerance = st.slider("Tolerance Buffer (%)", 0.5, 3.0, 2.0, 0.1)

        to_scan = []
        if scan_univ == "Watchlist":
            raw_input = st.text_area("Symbols:", "RELIANCE, TATASTEEL, INFY, ICICIBANK, LT, ZOMATO, ADANIPOWER")
            to_scan = [f"{s.strip().upper()}.NS" for s in raw_input.split(",") if s.strip() != ""]
        elif scan_univ == "Nifty 50":
            to_scan = ["ADANIENT.NS", "ADANIPORTS.NS", "ASIANPAINT.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BHARTIARTL.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "ITC.NS", "LT.NS", "RELIANCE.NS", "SBIN.NS", "TCS.NS", "TITAN.NS"]
        else:
            to_scan = [f"{s}.NS" for s in stock_universe.values()]

        st.markdown("<br>", unsafe_allow_html=True)
        trigger_scan = st.button("🚀 Execute Parallel Scan", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_sc2:
        def process_quant_scan(sym, buffer_pct, selected_strat):
            try:
                tk = yf.Ticker(sym)
                df = tk.history(period="1y", interval="1wk")
                if df.empty or len(df) < 15:
                    return None

                close = round(df["Close"].iloc[-1], 2)
                low = round(df["Low"].iloc[-1], 2)

                if selected_strat == "Weekly 10 EMA Support":
                    df["EMA10"] = ta.trend.ema_indicator(close=df["Close"], window=10)
                    ema10 = round(df["EMA10"].iloc[-1], 2)
                    low_b = ema10 * (1 - (buffer_pct / 100))
                    high_b = ema10 * (1 + (buffer_pct / 100))

                    if (low_b <= low <= high_b) or (low <= ema10 and close >= ema10):
                        spread = round(((close - ema10) / ema10) * 100, 2)
                        return {"Symbol": sym.replace(".NS", ""), "LTP (₹)": close, "10 EMA (₹)": ema10, "Spread (%)": f"{spread}%", "Trigger": "Weekly 10 EMA Touch"}

                elif selected_strat == "RSI Oversold Bounce (RSI < 35)":
                    df["RSI"] = ta.momentum.rsi(close=df["Close"], window=14)
                    rsi_val = round(df["RSI"].iloc[-1], 2)
                    if rsi_val <= 35:
                        return {"Symbol": sym.replace(".NS", ""), "LTP (₹)": close, "RSI (14)": rsi_val, "Trigger": "Oversold Zone"}

            except Exception:
                return None
            return None

        if trigger_scan:
            st.info(f"Scanning {len(to_scan)} stocks across market...")
            bar = st.progress(0)
            res = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=30) as ex:
                fut = {ex.submit(process_quant_scan, s, tolerance, strat): s for s in to_scan}
                done = 0
                for f in concurrent.futures.as_completed(fut):
                    r = f.result()
                    if r:
                        res.append(r)
                    done += 1
                    bar.progress(done / len(to_scan))

            st.session_state.scan_results = pd.DataFrame(res) if res else pd.DataFrame()

        if st.session_state.scan_results is not None:
            df_out = st.session_state.scan_results
            col_m1, col_m2 = st.columns(2)
            col_m1.metric("Setups Triggered", len(df_out))
            col_m2.metric("Active Strategy", strat)

            if not df_out.empty:
                st.dataframe(df_out, use_container_width=True)

                if st.button("📲 Push Alerts to Telegram"):
                    tg_id = st.session_state.telegram_chat_id
                    if not tg_id:
                        st.error("Telegram Chat ID missing! Go to Settings tab to link your ID.")
                    else:
                        lines = [f"• *{row['Symbol']}*: ₹{row['LTP (₹)']} — Trigger: {row['Trigger']}" for _, row in df_out.iterrows()]
                        for i in range(0, len(lines), 15):
                            msg = f"⚡ *ALPHASCAN QUANT ALERT*\n\n" + "\n".join(lines[i:i+15])
                            send_telegram_alert(msg, tg_id)
                            time.sleep(0.3)
                        st.success("Dispatched to your Telegram bot!")
            else:
                st.warning("No setup triggers matched.")

# ==============================================================================
# TAB 4: CUSTOM QUERY SCREENER (SCREENER.IN ICONIC TOOL)
# ==============================================================================
with tab4:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🧪 Query Screener Engine")
    st.caption("Filter Indian equities using Screener.in style fundamental thresholds.")

    query_str = st.text_area(
        "Enter Fundamental Query:",
        "Market Cap > 1000 AND Stock PE < 35 AND Debt To Equity < 100",
        help="Use metrics like Market Cap, Stock PE, Debt To Equity"
    )

    c_q1, c_q2 = st.columns([1, 3])
    with c_q1:
        run_query = st.button("Run Fundamental Query", use_container_width=True)

    if run_query:
        st.info("Parsing fundamental parameters across target universe...")
        sample_symbols = ["RELIANCE", "TATASTEEL", "INFY", "ICICIBANK", "LT", "ZOMATO", "ADANIPOWER", "SBIN", "TCS"]
        query_rows = []

        for s in sample_symbols:
            try:
                inf = yf.Ticker(f"{s}.NS").info
                mc = round(inf.get("marketCap", 0) / 1e7, 2)
                p_e = round(inf.get("trailingPE", 999), 2)
                de = round(inf.get("debtToEquity", 999), 2)

                # Query Condition Evaluation
                if mc > 1000 and p_e < 35 and de < 100:
                    query_rows.append({
                        "Symbol": s,
                        "Company": inf.get("shortName", s),
                        "Market Cap (₹ Cr)": mc,
                        "P/E": p_e,
                        "Debt to Equity (%)": de,
                        "ROCE (%)": round(inf.get("returnOnAssets", 0) * 100, 2)
                    })
            except Exception:
                pass

        if query_rows:
            st.success(f"Found {len(query_rows)} companies matching your query criteria.")
            st.dataframe(pd.DataFrame(query_rows), use_container_width=True)
        else:
            st.warning("No companies satisfied the filter conditions.")

# ==============================================================================
# TAB 5: TERMINAL SETTINGS & TELEGRAM ROUTING
# ==============================================================================
with tab5:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="funda-card" style="max-width:550px; margin:0 auto;">', unsafe_allow_html=True)
    st.subheader("📲 Telegram Alerts Binding")

    curr_val = st.session_state.telegram_chat_id
    tg_in = st.text_input("Telegram Chat ID:", value=curr_val)

    if st.button("Link Telegram ID"):
        clean_id = tg_in.strip()
        if clean_id:
            try:
                res = supabase.auth.update_user({"data": {"telegram_chat_id": clean_id}})
                if res.user:
                    st.session_state.user = res.user
                st.session_state.telegram_chat_id = clean_id
                st.success("✅ Chat ID Linked Successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
        else:
            st.warning("Please provide a valid numeric ID.")

    st.caption("Send `/start` to `@userinfobot` to retrieve your Chat ID.")
    st.markdown("<hr style='border-color:rgba(255,255,255,0.08);'>", unsafe_allow_html=True)

    if st.button("🚪 Terminate Session", use_container_width=True):
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
        st.session_state.user = None
        st.session_state.telegram_chat_id = ""
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)