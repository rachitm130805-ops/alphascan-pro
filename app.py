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
    page_title="AlphaScan Pro | Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CLEAN ULTRA MODERN CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --bg-void: #07090E;
        --surface-1: #0F1422;
        --surface-2: #161D31;
        --border-glass: rgba(255, 255, 255, 0.08);
        --border-glass-hover: rgba(0, 229, 255, 0.4);
        --accent-cyan: #00E5FF;
        --accent-green: #10B981;
        --accent-red: #F43F5E;
        --text-main: #FFFFFF;
        --text-sub: #94A3B8;
        --font-sans: 'Plus Jakarta Sans', sans-serif;
        --font-mono: 'JetBrains Mono', monospace;
    }

    .stApp {
        background: radial-gradient(circle at 50% -15%, #15213D 0%, #07090E 70%) !important;
        font-family: var(--font-sans) !important;
        color: var(--text-main);
    }

    #MainMenu, footer, header { visibility: hidden; }
    .block-container {
        padding: 1.25rem 2.5rem !important;
        max-width: 1400px !important;
    }

    .top-nav {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 24px;
        background: rgba(15, 20, 34, 0.75);
        backdrop-filter: blur(16px);
        border: 1px solid var(--border-glass);
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }

    .funda-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(135px, 1fr));
        gap: 12px;
        margin-bottom: 1.5rem;
    }

    .funda-card {
        background: var(--surface-1);
        border: 1px solid var(--border-glass);
        border-radius: 10px;
        padding: 12px 14px;
        transition: all 0.2s ease;
    }

    .funda-card:hover {
        border-color: var(--border-glass-hover);
        transform: translateY(-2px);
    }

    .funda-title {
        font-size: 0.72rem;
        color: var(--text-sub);
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.04em;
    }

    .funda-val {
        font-size: 1.15rem;
        font-weight: 700;
        color: #FFFFFF;
        font-family: var(--font-mono);
        margin-top: 4px;
    }

    .pros-box {
        background: rgba(16, 185, 129, 0.05);
        border: 1px solid rgba(16, 185, 129, 0.25);
        border-radius: 10px;
        padding: 1rem;
    }

    .cons-box {
        background: rgba(244, 63, 94, 0.05);
        border: 1px solid rgba(244, 63, 94, 0.25);
        border-radius: 10px;
        padding: 1rem;
    }

    .delta-container {
        background: var(--surface-1);
        border: 1px solid var(--border-glass);
        border-radius: 12px;
        padding: 1.25rem;
        margin-top: 1.2rem;
    }

    .stButton > button {
        background: linear-gradient(135deg, #00E5FF 0%, #10B981 100%) !important;
        color: #07090E !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.55rem 1.25rem !important;
        font-weight: 700 !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button:hover {
        opacity: 0.92;
        transform: translateY(-1px);
        box-shadow: 0 4px 15px rgba(0, 229, 255, 0.3) !important;
    }

    div[data-testid="stForm"] {
        background: rgba(15, 20, 34, 0.85) !important;
        border: 1px solid var(--border-glass) !important;
        border-radius: 14px !important;
        padding: 2rem !important;
    }

    .stTextInput > div > div > input, div[data-baseweb="select"] > div {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid var(--border-glass) !important;
        color: var(--text-main) !important;
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

# --- HELPER: CONVERT RAW YAHOO GAAP TO EXACT SCREENER.IN FORMAT ---
def build_screener_financial_table(raw_df):
    if raw_df is None or raw_df.empty:
        return pd.DataFrame()

    def get_val(labels, col):
        for lbl in labels:
            if lbl in raw_df.index:
                val = raw_df.loc[lbl, col]
                if pd.notna(val):
                    return float(val)
        return None

    columns = [d.strftime("%b %Y") if hasattr(d, "strftime") else str(d)[:7] for d in raw_df.columns]
    metrics = [
        "Sales",
        "Expenses",
        "Operating Profit",
        "OPM %",
        "Other Income",
        "Interest",
        "Depreciation",
        "Profit before tax",
        "Tax %",
        "Net Profit (PAT)",
        "EPS in Rs"
    ]

    screener_df = pd.DataFrame(index=metrics, columns=columns)

    for i, col in enumerate(raw_df.columns):
        c_label = columns[i]
        
        # 1. Sales
        sales = get_val(["Total Revenue", "Operating Revenue"], col)
        
        # 2. Expenses
        cogs = get_val(["Cost Of Revenue"], col) or 0.0
        sga = get_val(["Selling General And Administration", "Operating Expense"], col) or 0.0
        expenses = cogs + sga
        
        # 3. Operating Profit
        op_profit = get_val(["Operating Income", "Operating Profit"], col)
        if op_profit is None and sales is not None and expenses > 0:
            op_profit = sales - expenses

        # 4. OPM %
        opm = round((op_profit / sales) * 100, 2) if (op_profit is not None and sales and sales > 0) else None
        
        # 5. Other Income
        other_inc = get_val(["Other Income Expense", "Non Operating Income Expense"], col)
        
        # 6. Interest
        interest = get_val(["Interest Expense", "Interest Expense Non Operating"], col)
        
        # 7. Depreciation
        depr = get_val(["Reconciled Depreciation", "Depreciation And Amortization"], col)
        
        # 8. PBT
        pbt = get_val(["Pretax Income"], col)
        
        # 9. Net Profit
        pat = get_val(["Net Income Common Stockholders", "Net Income"], col)
        
        # 10. Tax %
        tax_val = get_val(["Tax Provision"], col)
        tax_pct = round((tax_val / pbt) * 100, 2) if (tax_val and pbt and pbt > 0) else None
        
        # 11. EPS
        eps = get_val(["Diluted EPS", "Basic EPS"], col)

        # Scale in ₹ Crores (div by 1e7)
        screener_df.loc["Sales", c_label] = round(sales / 1e7, 2) if sales is not None else "-"
        screener_df.loc["Expenses", c_label] = round(expenses / 1e7, 2) if expenses > 0 else "-"
        screener_df.loc["Operating Profit", c_label] = round(op_profit / 1e7, 2) if op_profit is not None else "-"
        screener_df.loc["OPM %", c_label] = f"{opm}%" if opm is not None else "-"
        screener_df.loc["Other Income", c_label] = round(other_inc / 1e7, 2) if other_inc is not None else "-"
        screener_df.loc["Interest", c_label] = round(interest / 1e7, 2) if interest is not None else "-"
        screener_df.loc["Depreciation", c_label] = round(depr / 1e7, 2) if depr is not None else "-"
        screener_df.loc["Profit before tax", c_label] = round(pbt / 1e7, 2) if pbt is not None else "-"
        screener_df.loc["Tax %", c_label] = f"{tax_pct}%" if tax_pct is not None else "-"
        screener_df.loc["Net Profit (PAT)", c_label] = round(pat / 1e7, 2) if pat is not None else "-"
        screener_df.loc["EPS in Rs", c_label] = round(eps, 2) if eps is not None else "-"

    return screener_df

# --- LANDING PAGE ---
if not st.session_state.user:
    st.markdown("""
        <div class="top-nav">
            <div style="font-weight:800; font-size:1.25rem;">⚡ AlphaScan Pro</div>
            <div style="font-size:0.8rem; color:#94A3B8;">Techno-Fundamental Equity Terminal</div>
        </div>
    """, unsafe_allow_html=True)

    col_hero, col_auth = st.columns([1.2, 1], gap="large")

    with col_hero:
        st.markdown("""
            <h1 style="font-size: 3rem; font-weight:800; line-height:1.15; margin-bottom:0.75rem;">
                Screener.in Financials Meet Algorithmic Precision.
            </h1>
            <p style="color:#94A3B8; font-size:1.1rem; line-height:1.6; margin-bottom:2rem;">
                Standard Indian accounting formats (Sales, OPM, PAT, EPS), visual figure growth calculators, and live multi-threaded scanners.
            </p>
        """, unsafe_allow_html=True)

        g1, g2 = st.columns(2)
        with g1:
            st.markdown("""
                <div class="funda-card">
                    <div style="font-size:1.3rem;">📊</div>
                    <div style="font-weight:700; margin-top:6px;">Clean P&L Reports</div>
                    <div style="font-size:0.8rem; color:#94A3B8;">Sales, Operating Profit, PAT, and EPS in ₹ Crores.</div>
                </div>
            """, unsafe_allow_html=True)
        with g2:
            st.markdown("""
                <div class="funda-card">
                    <div style="font-size:1.3rem;">📈</div>
                    <div style="font-weight:700; margin-top:6px;">TradingView Terminal</div>
                    <div style="font-size:0.8rem; color:#94A3B8;">Unrestricted BSE/NSE charts with full drawing tools.</div>
                </div>
            """, unsafe_allow_html=True)

    with col_auth:
        mode = st.radio("Access", ["Sign In", "Create Account"], horizontal=True, label_visibility="collapsed")
        if mode == "Sign In":
            with st.form("signin_form"):
                st.subheader("Sign In")
                email = st.text_input("Email", placeholder="name@example.com")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Enter Terminal", use_container_width=True):
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state.user = res.user
                        if res.user and res.user.user_metadata:
                            st.session_state.telegram_chat_id = res.user.user_metadata.get("telegram_chat_id", "")
                        st.success("Authenticated.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Sign in failed: {e}")
        else:
            with st.form("signup_form"):
                st.subheader("Create Account")
                email = st.text_input("Email", placeholder="name@example.com")
                password = st.text_input("Password", type="password")
                if st.form_submit_button("Register", use_container_width=True):
                    try:
                        res = supabase.auth.sign_up({"email": email, "password": password})
                        st.success("Account created! Switch to Sign In above.")
                    except Exception as e:
                        st.error(f"Error: {e}")

    st.stop()

# --- AUTHENTICATED TERMINAL DASHBOARD ---
user_email = st.session_state.user.email

st.markdown(f"""
    <div class="top-nav">
        <div style="font-weight:800; font-size:1.25rem;">⚡ AlphaScan Pro</div>
        <div style="display:flex; align-items:center; gap:16px;">
            <span style="font-size:0.85rem; color:#94A3B8;">Logged in: <b style="color:#FFF;">{user_email}</b></span>
            <div style="width:8px; height:8px; border-radius:50%; background:#10B981; box-shadow:0 0 8px #10B981;"></div>
        </div>
    </div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Screener.in Financials",
    "📈 TradingView Charts",
    "⚡ Technical Scanners",
    "🧪 Visual Query Screener",
    "⚙️ Terminal Settings"
])

# ==============================================================================
# TAB 1: EXACT SCREENER.IN FINANCIAL STATEMENTS & GROWTH COMPARATOR
# ==============================================================================
with tab1:
    st.markdown("<br>", unsafe_allow_html=True)

    c_select, _ = st.columns([2, 2])
    with c_select:
        options = list(stock_universe.keys())
        selected_label = st.selectbox("Select Indian Company:", options=options, index=0)
        stock_sym = stock_universe[selected_label]
        yf_symbol = f"{stock_sym}.NS"

    with st.spinner(f"Fetching financial statement for {stock_sym}..."):
        try:
            ticker_obj = yf.Ticker(yf_symbol)
            info = ticker_obj.info

            # Header details
            company_name = info.get("longName", stock_sym)
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
                    <span style="color:#00E5FF; font-weight:600;">{info.get('sector', 'N/A')}</span> • 
                    <span style="color:#94A3B8;">{info.get('industry', 'N/A')}</span>
                </div>
            """, unsafe_allow_html=True)

            # Metric Cards
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

            st.markdown("<hr style='border-color:rgba(255,255,255,0.08); margin: 1.5rem 0;'>", unsafe_allow_html=True)

            # Statement Mode Selector
            statement_type = st.radio("Financial Statement:", ["Quarterly Results", "Annual Profit & Loss"], horizontal=True)

            raw_financials = ticker_obj.quarterly_financials if statement_type == "Quarterly Results" else ticker_obj.financials
            screener_table = build_screener_financial_table(raw_financials)

            if not screener_table.empty:
                st.subheader(f"📑 {statement_type} (Figures in ₹ Crores)")
                st.dataframe(screener_table, use_container_width=True)

                # --- INTERACTIVE FIGURE GROWTH & COMPARISON TOOL (DELTA ENGINE) ---
                st.markdown('<div class="delta-container">', unsafe_allow_html=True)
                st.markdown("### 🔍 Compare Periods & Percentage Growth")
                st.caption("Select any metric (e.g. Sales, Net Profit) and two periods to calculate the exact percentage change.")

                col_m, col_p1, col_p2 = st.columns(3)
                with col_m:
                    selected_metric = st.selectbox("Select Metric to Compare:", ["Sales", "Operating Profit", "Net Profit (PAT)", "Expenses"], index=0)
                with col_p1:
                    available_periods = list(screener_table.columns)
                    base_period = st.selectbox("Base Period (From):", available_periods, index=len(available_periods) - 1 if len(available_periods) > 1 else 0)
                with col_p2:
                    target_period = st.selectbox("Target Period (To):", available_periods, index=0)

                val_base = screener_table.loc[selected_metric, base_period]
                val_target = screener_table.loc[selected_metric, target_period]

                try:
                    f_base = float(val_base)
                    f_target = float(val_target)
                    abs_change = round(f_target - f_base, 2)
                    pct_change = round(((f_target - f_base) / abs(f_base)) * 100, 2) if f_base != 0 else 0.0

                    color = "#10B981" if pct_change >= 0 else "#F43F5E"
                    arrow = "▲" if pct_change >= 0 else "▼"

                    st.markdown(f"""
                        <div style="display:flex; align-items:center; gap:24px; margin-top:12px;">
                            <div>
                                <span style="font-size:0.8rem; color:#94A3B8;">{selected_metric} in {base_period}</span>
                                <div style="font-size:1.3rem; font-weight:700; font-family:var(--font-mono);">₹{f_base} Cr</div>
                            </div>
                            <div style="font-size:1.4rem; color:#94A3B8;">➔</div>
                            <div>
                                <span style="font-size:0.8rem; color:#94A3B8;">{selected_metric} in {target_period}</span>
                                <div style="font-size:1.3rem; font-weight:700; font-family:var(--font-mono);">₹{f_target} Cr</div>
                            </div>
                            <div style="margin-left:auto; background:rgba(255,255,255,0.04); padding:10px 18px; border-radius:10px; border:1px solid rgba(255,255,255,0.08);">
                                <span style="font-size:0.75rem; color:#94A3B8; text-transform:uppercase;">Calculated Growth</span>
                                <div style="font-size:1.4rem; font-weight:800; color:{color}; font-family:var(--font-mono);">
                                    {arrow} {pct_change}% <span style="font-size:0.85rem; color:#94A3B8; font-weight:500;">(₹{abs_change} Cr)</span>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                except Exception:
                    st.info("Select valid numerical periods to calculate percentage changes.")

                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.warning("No financial records found for this ticker.")

        except Exception as e:
            st.error(f"Failed to load financial report: {e}")

# ==============================================================================
# TAB 2: TRADINGVIEW ADVANCED UNRESTRICTED CHARTS
# ==============================================================================
with tab2:
    st.markdown("<br>", unsafe_allow_html=True)
    c_chart_sel, c_popout = st.columns([3, 1])
    with c_chart_sel:
        selected_chart_lbl = st.selectbox("Select Symbol for Chart:", options=list(stock_universe.keys()), index=0)
        c_sym = stock_universe[selected_chart_lbl]

    with c_popout:
        st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
        tv_url = f"https://in.tradingview.com/chart/?symbol=BSE:{c_sym}"
        st.markdown(f'<a href="{tv_url}" target="_blank"><button style="width:100%; background:#10B981; color:#000; font-weight:700; border:none; border-radius:8px; padding:9px 12px; cursor:pointer;">↗️ Full TradingView Studio</button></a>', unsafe_allow_html=True)

    st.markdown(f"### 📈 TradingView Terminal: `{c_sym}`")
    tv_code = f"""
    <div class="tradingview-widget-container" style="height:720px;width:100%;">
      <div id="tv_chart_box" style="height:calc(100% - 32px);width:100%;"></div>
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
        "container_id": "tv_chart_box"
      }});
      </script>
    </div>
    """
    components.html(tv_code, height=730)

# ==============================================================================
# TAB 3: TECHNICAL SCANNERS
# ==============================================================================
with tab3:
    st.markdown("<br>", unsafe_allow_html=True)
    col_sc1, col_sc2 = st.columns([1, 2.5])

    with col_sc1:
        st.markdown('<div class="funda-card">', unsafe_allow_html=True)
        st.subheader("Strategy Config")
        strat = st.selectbox("Strategy:", ["Weekly 10 EMA Support", "RSI Oversold Bounce (RSI < 35)"])
        scan_univ = st.radio("Scan Universe:", ["Watchlist", "Nifty 50", "Full NSE"])
        tolerance = st.slider("Tolerance Buffer (%)", 0.5, 3.0, 2.0, 0.1)

        to_scan = []
        if scan_univ == "Watchlist":
            raw_input = st.text_area("Watchlist Tickers:", "RELIANCE, TATASTEEL, INFY, ICICIBANK, LT, ZOMATO, ADANIPOWER")
            to_scan = [f"{s.strip().upper()}.NS" for s in raw_input.split(",") if s.strip() != ""]
        elif scan_univ == "Nifty 50":
            to_scan = ["ADANIENT.NS", "ADANIPORTS.NS", "ASIANPAINT.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BHARTIARTL.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "ITC.NS", "LT.NS", "RELIANCE.NS", "SBIN.NS", "TCS.NS", "TITAN.NS"]
        else:
            to_scan = [f"{s}.NS" for s in stock_universe.values()]

        trigger_scan = st.button("🚀 Execute Scan", use_container_width=True)
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
            st.info(f"Scanning {len(to_scan)} stocks...")
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
            if not df_out.empty:
                st.metric("Setups Found", len(df_out))
                st.dataframe(df_out, use_container_width=True)

                if st.button("📲 Push Alerts to Telegram"):
                    tg_id = st.session_state.telegram_chat_id
                    if not tg_id:
                        st.error("Telegram Chat ID missing! Configure in Settings tab.")
                    else:
                        lines = [f"• *{row['Symbol']}*: ₹{row['LTP (₹)']} — Trigger: {row['Trigger']}" for _, row in df_out.iterrows()]
                        for i in range(0, len(lines), 15):
                            msg = f"⚡ *ALPHASCAN QUANT ALERT*\n\n" + "\n".join(lines[i:i+15])
                            send_telegram_alert(msg, tg_id)
                            time.sleep(0.3)
                        st.success("Dispatched to Telegram!")
            else:
                st.warning("No setup triggers matched.")

# ==============================================================================
# TAB 4: VISUAL QUERY SCREENER BUILDER (STRICT MATHEMATICAL EVALUATION)
# ==============================================================================
with tab4:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🧪 Screener.in Visual Query Builder")
    st.caption("No manual syntax errors. Select thresholds and the engine strictly computes real values.")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        min_mcap = st.number_input("Minimum Market Cap (₹ Cr):", min_value=0, value=1000, step=500)
    with col_f2:
        max_pe = st.number_input("Maximum Stock P/E:", min_value=1.0, value=30.0, step=1.0)
    with col_f3:
        min_roce = st.number_input("Minimum ROCE (%):", min_value=0.0, value=10.0, step=1.0)

    col_run, _ = st.columns([1, 3])
    with col_run:
        run_query = st.button("Filter Equities", use_container_width=True)

    if run_query:
        st.info("Filtering equities using mathematical checks...")
        universe_symbols = ["RELIANCE", "TATASTEEL", "INFY", "ICICIBANK", "LT", "ZOMATO", "ADANIPOWER", "SBIN", "TCS", "HDFCBANK"]
        matched_rows = []

        for s in universe_symbols:
            try:
                inf = yf.Ticker(f"{s}.NS").info
                
                # Extract strict numerical values
                mcap_cr = round(inf.get("marketCap", 0) / 1e7, 2)
                pe_val = inf.get("trailingPE", None)
                roce_val = round(inf.get("returnOnAssets", 0) * 100, 2) if inf.get("returnOnAssets") else 0.0

                # Strict numerical verification
                if pe_val is not None:
                    pe_float = float(pe_val)
                    if mcap_cr >= min_mcap and pe_float <= max_pe and roce_val >= min_roce:
                        matched_rows.append({
                            "Symbol": s,
                            "Company": inf.get("shortName", s),
                            "Price (₹)": inf.get("currentPrice", 0.0),
                            "Market Cap (₹ Cr)": mcap_cr,
                            "Stock P/E": round(pe_float, 2),
                            "ROCE (%)": f"{roce_val}%",
                            "Debt to Equity": inf.get("debtToEquity", "N/A")
                        })
            except Exception:
                pass

        if matched_rows:
            st.success(f"Matched {len(matched_rows)} stocks strictly satisfying: Market Cap >= ₹{min_mcap} Cr, P/E <= {max_pe}, ROCE >= {min_roce}%")
            st.dataframe(pd.DataFrame(matched_rows), use_container_width=True)
        else:
            st.warning("No stocks matched the exact mathematical criteria.")

# ==============================================================================
# TAB 5: TERMINAL SETTINGS
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

    if st.button("🚪 Logout Account", use_container_width=True):
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
        st.session_state.user = None
        st.session_state.telegram_chat_id = ""
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)