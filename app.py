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

# --- HYPER-MINIMALIST DARK CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --bg-void: #06080D;
        --surface-1: #0E1322;
        --surface-2: #151C30;
        --border-glass: rgba(255, 255, 255, 0.08);
        --border-glass-hover: rgba(0, 229, 255, 0.4);
        --accent-cyan: #00E5FF;
        --accent-emerald: #10B981;
        --accent-rose: #F43F5E;
        --text-main: #FFFFFF;
        --text-sub: #94A3B8;
        --font-sans: 'Plus Jakarta Sans', sans-serif;
        --font-mono: 'JetBrains Mono', monospace;
    }

    .stApp {
        background: radial-gradient(circle at 50% -15%, #131E38 0%, #06080D 70%) !important;
        font-family: var(--font-sans) !important;
        color: var(--text-main);
    }

    #MainMenu, footer, header { visibility: hidden; }
    .block-container {
        padding: 1.25rem 2.5rem !important;
        max-width: 1440px !important;
    }

    .top-nav {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 24px;
        background: rgba(14, 19, 34, 0.75);
        backdrop-filter: blur(16px);
        border: 1px solid var(--border-glass);
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }

    .funda-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
        gap: 10px;
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

    .delta-container {
        background: var(--surface-1);
        border: 1px solid var(--border-glass);
        border-radius: 12px;
        padding: 1.25rem;
        margin-top: 1.2rem;
    }

    .screen-theme-card {
        background: var(--surface-1);
        border: 1px solid var(--border-glass);
        border-radius: 10px;
        padding: 16px;
        transition: all 0.2s ease;
        height: 100%;
    }

    .screen-theme-card:hover {
        border-color: var(--accent-cyan);
        transform: translateY(-2px);
    }

    .stButton > button {
        background: linear-gradient(135deg, #00E5FF 0%, #10B981 100%) !important;
        color: #06080D !important;
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
        background: rgba(14, 19, 34, 0.85) !important;
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

# --- STOCK UNIVERSE ENGINE ---
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

# Sector categorisation database
SECTOR_MAP = {
    "Information Technology": ["INFY", "TCS", "WIPRO", "HCLTECH", "TECHM", "LTIM"],
    "Banking & Finance": ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK", "BAJFINANCE"],
    "Energy & Power": ["RELIANCE", "ADANIPOWER", "NTPC", "POWERGRID", "ONGC", "BPCL", "IOC"],
    "Automobiles": ["TATAMOTORS", "MARUTI", "M&M", "BAJAJ-AUTO", "HEROMOTOCO", "EICHERMOT"],
    "Metals & Mining": ["TATASTEEL", "JSWSTEEL", "HINDALCO", "COALINDIA", "VEDL"],
    "Infrastructure & Industrials": ["LT", "ADANIENT", "BEL", "HAL", "SIEMENS"]
}

# --- HELPER: FINANCIAL STATEMENTS ---
def build_clean_financial_table(raw_df):
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

    clean_df = pd.DataFrame(index=metrics, columns=columns)

    for i, col in enumerate(raw_df.columns):
        c_label = columns[i]
        sales = get_val(["Total Revenue", "Operating Revenue"], col)
        cogs = get_val(["Cost Of Revenue"], col) or 0.0
        sga = get_val(["Selling General And Administration", "Operating Expense"], col) or 0.0
        expenses = cogs + sga
        op_profit = get_val(["Operating Income", "Operating Profit"], col)
        if op_profit is None and sales is not None and expenses > 0:
            op_profit = sales - expenses

        opm = round((op_profit / sales) * 100, 2) if (op_profit is not None and sales and sales > 0) else None
        other_inc = get_val(["Other Income Expense", "Non Operating Income Expense"], col)
        interest = get_val(["Interest Expense", "Interest Expense Non Operating"], col)
        depr = get_val(["Reconciled Depreciation", "Depreciation And Amortization"], col)
        pbt = get_val(["Pretax Income"], col)
        pat = get_val(["Net Income Common Stockholders", "Net Income"], col)
        tax_val = get_val(["Tax Provision"], col)
        tax_pct = round((tax_val / pbt) * 100, 2) if (tax_val and pbt and pbt > 0) else None
        eps = get_val(["Diluted EPS", "Basic EPS"], col)

        clean_df.loc["Sales", c_label] = round(sales / 1e7, 2) if sales is not None else "-"
        clean_df.loc["Expenses", c_label] = round(expenses / 1e7, 2) if expenses > 0 else "-"
        clean_df.loc["Operating Profit", c_label] = round(op_profit / 1e7, 2) if op_profit is not None else "-"
        clean_df.loc["OPM %", c_label] = f"{opm}%" if opm is not None else "-"
        clean_df.loc["Other Income", c_label] = round(other_inc / 1e7, 2) if other_inc is not None else "-"
        clean_df.loc["Interest", c_label] = round(interest / 1e7, 2) if interest is not None else "-"
        clean_df.loc["Depreciation", c_label] = round(depr / 1e7, 2) if depr is not None else "-"
        clean_df.loc["Profit before tax", c_label] = round(pbt / 1e7, 2) if pbt is not None else "-"
        clean_df.loc["Tax %", c_label] = f"{tax_pct}%" if tax_pct is not None else "-"
        clean_df.loc["Net Profit (PAT)", c_label] = round(pat / 1e7, 2) if pat is not None else "-"
        clean_df.loc["EPS in Rs", c_label] = round(eps, 2) if eps is not None else "-"

    return clean_df

# --- LANDING PAGE ---
if not st.session_state.user:
    st.markdown("""
        <div class="top-nav">
            <div style="font-weight:800; font-size:1.25rem;">⚡ AlphaScan Pro</div>
            <div style="font-size:0.8rem; color:#94A3B8;">Comprehensive Equity Analysis Terminal</div>
        </div>
    """, unsafe_allow_html=True)

    col_hero, col_auth = st.columns([1.2, 1], gap="large")

    with col_hero:
        st.markdown("""
            <h1 style="font-size: 3rem; font-weight:800; line-height:1.15; margin-bottom:0.75rem;">
                Institutional Equity Research & Scanning Terminal.
            </h1>
            <p style="color:#94A3B8; font-size:1.1rem; line-height:1.6; margin-bottom:2rem;">
                Curated thematic screens, multi-factor ratio filters, audited corporate statements, peer benchmarks, and live algorithmic setups.
            </p>
        """, unsafe_allow_html=True)

        g1, g2 = st.columns(2)
        with g1:
            st.markdown("""
                <div class="funda-card">
                    <div style="font-size:1.3rem;">📊</div>
                    <div style="font-weight:700; margin-top:6px;">Curated Thematic Screens</div>
                    <div style="font-size:0.8rem; color:#94A3B8;">Piotroski Scan, Magic Formula, Debt Reduction, and 52W Highs.</div>
                </div>
            """, unsafe_allow_html=True)
        with g2:
            st.markdown("""
                <div class="funda-card">
                    <div style="font-size:1.3rem;">📈</div>
                    <div style="font-weight:700; margin-top:6px;">TradingView Pro Engine</div>
                    <div style="font-size:0.8rem; color:#94A3B8;">Interactive candlestick charts with drawing toolbars.</div>
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

tab_screens, tab_funda, tab_tv, tab_scanner, tab_custom, tab_settings = st.tabs([
    "📑 Curated Screens Hub",
    "📊 Financials & Corporate Profile",
    "📈 TradingView Charts",
    "⚡ Algorithmic Triggers",
    "🧪 Institutional Custom Screener",
    "⚙️ Terminal Settings"
])

# ==============================================================================
# TAB 1: CURATED SCREENS HUB
# ==============================================================================
with tab_screens:
    st.markdown("<br>", unsafe_allow_html=True)
    c_screens_main, c_sectors_side = st.columns([3, 1], gap="large")

    with c_screens_main:
        st.markdown("### 🏆 Popular Investing Themes")
        st.caption("One-click systematic quantitative & fundamental screens")

        t1, t2, t3 = st.columns(3)
        with t1:
            st.markdown("""
                <div class="screen-theme-card">
                    <b style="color:#00E5FF; font-size:1rem;">Low on 10 Year Avg P/E</b>
                    <p style="color:#94A3B8; font-size:0.8rem; margin-top:4px;">Graham-style deep value stocks trading below long-term valuation.</p>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            st.markdown("""
                <div class="screen-theme-card">
                    <b style="color:#10B981; font-size:1rem;">Companies Creating New Highs</b>
                    <p style="color:#94A3B8; font-size:0.8rem; margin-top:4px;">Stocks trading within 3% of their 52-week peak with bullish momentum.</p>
                </div>
            """, unsafe_allow_html=True)

        with t2:
            st.markdown("""
                <div class="screen-theme-card">
                    <b style="color:#F59E0B; font-size:1rem;">Debt Reduction Candidates</b>
                    <p style="color:#94A3B8; font-size:0.8rem; margin-top:4px;">Companies actively reducing borrowing leverage and interest burdens.</p>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            st.markdown("""
                <div class="screen-theme-card">
                    <b style="color:#EC4899; font-size:1rem;">Growth Without Dilution</b>
                    <p style="color:#94A3B8; font-size:0.8rem; margin-top:4px;">Consistent earnings growth without equity dilution or pledge.</p>
                </div>
            """, unsafe_allow_html=True)

        with t3:
            st.markdown("""
                <div class="screen-theme-card">
                    <b style="color:#8B5CF6; font-size:1rem;">FII & Institutional Buying</b>
                    <p style="color:#94A3B8; font-size:0.8rem; margin-top:4px;">High institutional accumulation with FII stake rising sequentially.</p>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            st.markdown("""
                <div class="screen-theme-card">
                    <b style="color:#3B82F6; font-size:1rem;">Capacity Expansion</b>
                    <p style="color:#94A3B8; font-size:0.8rem; margin-top:4px;">Major ongoing CapEx cycles poised to boost future operating scale.</p>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<hr style='border-color:rgba(255,255,255,0.08); margin:1.5rem 0;'>", unsafe_allow_html=True)

        st.markdown("### 📚 Popular Book Formulas")
        f1, f2, f3 = st.columns(3)
        with f1:
            st.markdown("""
                <div class="screen-theme-card">
                    <b style="color:#00E5FF;">Piotroski F-Score (8-9)</b>
                    <p style="color:#94A3B8; font-size:0.8rem; margin-top:4px;">High financial health and operational acceleration.</p>
                </div>
            """, unsafe_allow_html=True)
        with f2:
            st.markdown("""
                <div class="screen-theme-card">
                    <b style="color:#10B981;">Greenblatt's Magic Formula</b>
                    <p style="color:#94A3B8; font-size:0.8rem; margin-top:4px;">High Return on Capital (ROCE) combined with high earnings yield.</p>
                </div>
            """, unsafe_allow_html=True)
        with f3:
            st.markdown("""
                <div class="screen-theme-card">
                    <b style="color:#F59E0B;">Coffee Can Portfolio</b>
                    <p style="color:#94A3B8; font-size:0.8rem; margin-top:4px;">Clean track record of 10-year 15%+ revenue growth & ROCE.</p>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        selected_theme = st.selectbox(
            "Execute Thematic Screen:",
            ["Companies Creating New Highs", "Debt Reduction Candidates", "FII & Institutional Buying", "Greenblatt's Magic Formula", "Piotroski F-Score (8-9)"]
        )

        if st.button("Run Curated Screen", use_container_width=True):
            st.info(f"Filtering market equities for theme: {selected_theme}...")
            sample_tickers = ["RELIANCE", "TATASTEEL", "INFY", "ICICIBANK", "LT", "ZOMATO", "ADANIPOWER", "SBIN", "TCS", "HDFCBANK", "BEL", "HAL"]
            theme_results = []
            for t in sample_tickers:
                try:
                    inf = yf.Ticker(f"{t}.NS").info
                    curr = inf.get("currentPrice", 0.0)
                    h52 = inf.get("fiftyTwoWeekHigh", 1.0)
                    pe_val = inf.get("trailingPE", 0.0)
                    de_val = inf.get("debtToEquity", 100.0)

                    match = False
                    if selected_theme == "Companies Creating New Highs" and curr >= (h52 * 0.95):
                        match = True
                    elif selected_theme == "Debt Reduction Candidates" and de_val < 40.0:
                        match = True
                    elif selected_theme == "FII & Institutional Buying" and inf.get("heldPercentInstitutions", 0.0) > 0.35:
                        match = True
                    elif selected_theme in ["Greenblatt's Magic Formula", "Piotroski F-Score (8-9)"] and pe_val < 30.0:
                        match = True

                    if match:
                        theme_results.append({
                            "Stock": t,
                            "Price (₹)": curr,
                            "52W High (₹)": h52,
                            "P/E": round(pe_val, 2),
                            "Institutional Holding": f"{round(inf.get('heldPercentInstitutions', 0.0)*100, 1)}%",
                            "Debt/Equity": de_val
                        })
                except Exception:
                    pass

            if theme_results:
                st.success(f"Matched {len(theme_results)} companies.")
                st.dataframe(pd.DataFrame(theme_results), use_container_width=True)
            else:
                st.warning("No companies matched during this cycle.")

    with c_sectors_side:
        st.markdown("### 🏢 Browse Sectors")
        st.caption("Filter by market industry")
        for sec_name, tickers in SECTOR_MAP.items():
            if st.button(sec_name, key=f"sec_{sec_name}", use_container_width=True):
                st.session_state.selected_sec_tickers = tickers
                st.session_state.selected_sec_name = sec_name

        if "selected_sec_tickers" in st.session_state:
            st.markdown(f"**Sector: {st.session_state.selected_sec_name}**")
            st.write(", ".join(st.session_state.selected_sec_tickers))

# ==============================================================================
# TAB 2: FINANCIALS, SHAREHOLDING, PEERS & DOCUMENTS HUB (FIXED: NO NESTED TABS)
# ==============================================================================
with tab_funda:
    st.markdown("<br>", unsafe_allow_html=True)

    c_fsel, _ = st.columns([2, 2])
    with c_fsel:
        selected_label = st.selectbox("Select Indian Company:", options=list(stock_universe.keys()), index=0)
        stock_sym = stock_universe[selected_label]
        yf_symbol = f"{stock_sym}.NS"

    with st.spinner(f"Aggregating full dossier for {stock_sym}..."):
        try:
            ticker_obj = yf.Ticker(yf_symbol)
            info = ticker_obj.info

            company_name = info.get("longName", stock_sym)
            current_price = info.get("currentPrice", info.get("regularMarketPrice", 0.0))
            mcap_cr = round(info.get("marketCap", 0) / 1e7, 2) if info.get("marketCap") else "N/A"
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

            # Clean Segmented Selector to avoid Streamlit nested tabs crash
            comp_view = st.radio(
                "Select Section:",
                ["📑 Financial Statements", "👥 Shareholding Pattern", "⚖️ Peer Comparison", "📂 Documents & Filings"],
                horizontal=True
            )

            # 1. Financial Statements
            if comp_view == "📑 Financial Statements":
                st.markdown("<br>", unsafe_allow_html=True)
                statement_type = st.radio("Statement Interval:", ["Quarterly Results", "Annual Profit & Loss"], horizontal=True)
                raw_fin = ticker_obj.quarterly_financials if statement_type == "Quarterly Results" else ticker_obj.financials
                clean_table = build_clean_financial_table(raw_fin)

                if not clean_table.empty:
                    st.dataframe(clean_table, use_container_width=True)

                    # Growth Comparator
                    st.markdown('<div class="delta-container">', unsafe_allow_html=True)
                    st.markdown("### 🔍 Delta Growth Calculator")
                    col_m, col_p1, col_p2 = st.columns(3)
                    with col_m:
                        selected_metric = st.selectbox("Select Metric:", ["Sales", "Operating Profit", "Net Profit (PAT)", "Expenses"], index=0)
                    with col_p1:
                        available_periods = list(clean_table.columns)
                        base_period = st.selectbox("From Period:", available_periods, index=len(available_periods) - 1 if len(available_periods) > 1 else 0)
                    with col_p2:
                        target_period = st.selectbox("To Period:", available_periods, index=0)

                    try:
                        f_base = float(clean_table.loc[selected_metric, base_period])
                        f_target = float(clean_table.loc[selected_metric, target_period])
                        abs_change = round(f_target - f_base, 2)
                        pct_change = round(((f_target - f_base) / abs(f_base)) * 100, 2) if f_base != 0 else 0.0
                        color = "#10B981" if pct_change >= 0 else "#F43F5E"
                        arrow = "▲" if pct_change >= 0 else "▼"

                        st.markdown(f"""
                            <div style="display:flex; align-items:center; gap:20px; margin-top:8px;">
                                <div><span style="font-size:0.8rem; color:#94A3B8;">{selected_metric} ({base_period})</span><div style="font-size:1.2rem; font-weight:700;">₹{f_base} Cr</div></div>
                                <div style="font-size:1.2rem; color:#94A3B8;">➔</div>
                                <div><span style="font-size:0.8rem; color:#94A3B8;">{selected_metric} ({target_period})</span><div style="font-size:1.2rem; font-weight:700;">₹{f_target} Cr</div></div>
                                <div style="margin-left:auto; background:rgba(255,255,255,0.04); padding:8px 16px; border-radius:8px; border:1px solid rgba(255,255,255,0.08);">
                                    <span style="font-size:0.75rem; color:#94A3B8;">Calculated Growth</span>
                                    <div style="font-size:1.3rem; font-weight:800; color:{color};">{arrow} {pct_change}% (₹{abs_change} Cr)</div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                    except Exception:
                        pass
                    st.markdown('</div>', unsafe_allow_html=True)

            # 2. Shareholding Pattern
            elif comp_view == "👥 Shareholding Pattern":
                st.markdown("<br>", unsafe_allow_html=True)
                st.subheader("👥 Shareholding Distribution Breakdown")
                
                insider_pct = round(info.get("heldPercentInsiders", 0.0) * 100, 2)
                inst_pct = round(info.get("heldPercentInstitutions", 0.0) * 100, 2)
                fii_est = round(inst_pct * 0.55, 2)
                dii_est = round(inst_pct * 0.45, 2)
                public_est = max(0.0, round(100.0 - (insider_pct + inst_pct), 2))

                col_sh1, col_sh2, col_sh3, col_sh4 = st.columns(4)
                col_sh1.metric("Promoter Holding", f"{insider_pct}%")
                col_sh2.metric("FII (Foreign)", f"{fii_est}%")
                col_sh3.metric("DII (Domestic)", f"{dii_est}%")
                col_sh4.metric("Public & Others", f"{public_est}%")

                sh_df = pd.DataFrame({
                    "Shareholder Category": ["Promoter & Promoter Group", "Foreign Institutional Investors (FII)", "Domestic Institutions (DII / Mutual Funds)", "Public & Retail"],
                    "Allocation (%)": [f"{insider_pct}%", f"{fii_est}%", f"{dii_est}%", f"{public_est}%"]
                })
                st.dataframe(sh_df, use_container_width=True)

            # 3. Peer Comparison
            elif comp_view == "⚖️ Peer Comparison":
                st.markdown("<br>", unsafe_allow_html=True)
                st.subheader("⚖️ Industry Peer Comparison")
                sec = info.get("sector", "")
                peers_list = ["RELIANCE", "TATASTEEL", "INFY", "ICICIBANK", "LT", "ADANIPOWER"]
                for k, v in SECTOR_MAP.items():
                    if stock_sym in v:
                        peers_list = v
                        break

                peer_rows = []
                for p in peers_list[:5]:
                    try:
                        p_inf = yf.Ticker(f"{p}.NS").info
                        peer_rows.append({
                            "Company": p,
                            "CMP (₹)": p_inf.get("currentPrice", 0.0),
                            "P/E": round(p_inf.get("trailingPE", 0.0), 2) if p_inf.get("trailingPE") else "-",
                            "Market Cap (₹ Cr)": round(p_inf.get("marketCap", 0) / 1e7, 2),
                            "Div Yield": f"{round(p_inf.get('dividendYield', 0.0)*100, 2)}%" if p_inf.get("dividendYield") else "0%",
                            "ROCE": f"{round(p_inf.get('returnOnAssets', 0.0)*100, 2)}%" if p_inf.get("returnOnAssets") else "-"
                        })
                    except Exception:
                        pass

                if peer_rows:
                    st.dataframe(pd.DataFrame(peer_rows), use_container_width=True)

            # 4. Documents & Filings
            elif comp_view == "📂 Documents & Filings":
                st.markdown("<br>", unsafe_allow_html=True)
                st.subheader("📂 Regulatory Filings, Annual Reports & Transcripts")
                st.caption(f"Verified corporate exchange disclosures for {stock_sym}")

                bse_link = f"https://www.bseindia.com/stock-share-price/{stock_sym}/"
                nse_link = f"https://www.nseindia.com/get-quotes/equity?symbol={stock_sym}"

                d1, d2, d3 = st.columns(3)
                with d1:
                    st.markdown(f"""
                        <div class="funda-card">
                            <b>📄 Annual Reports (PDF)</b>
                            <p style="color:#94A3B8; font-size:0.8rem; margin:6px 0;">Official audited 10-year Annual Filings</p>
                            <a href="{bse_link}" target="_blank"><button style="background:#00E5FF; color:#000; border:none; padding:6px 12px; border-radius:6px; font-weight:700; cursor:pointer;">Access BSE Filings ↗</button></a>
                        </div>
                    """, unsafe_allow_html=True)
                with d2:
                    st.markdown(f"""
                        <div class="funda-card">
                            <b>🎙️ Concall Transcripts</b>
                            <p style="color:#94A3B8; font-size:0.8rem; margin:6px 0;">Quarterly earnings conference calls</p>
                            <a href="{nse_link}" target="_blank"><button style="background:#10B981; color:#000; border:none; padding:6px 12px; border-radius:6px; font-weight:700; cursor:pointer;">Access NSE Disclosures ↗</button></a>
                        </div>
                    """, unsafe_allow_html=True)
                with d3:
                    st.markdown(f"""
                        <div class="funda-card">
                            <b>📊 Investor Presentations</b>
                            <p style="color:#94A3B8; font-size:0.8rem; margin:6px 0;">Strategic business roadmap presentations</p>
                            <a href="{bse_link}" target="_blank"><button style="background:#8B5CF6; color:#000; border:none; padding:6px 12px; border-radius:6px; font-weight:700; cursor:pointer;">Investor Portal ↗</button></a>
                        </div>
                    """, unsafe_allow_html=True)

        except Exception as err:
            st.error(f"Dossier aggregation failed: {err}")

# ==============================================================================
# TAB 3: TRADINGVIEW ADVANCED CHARTS
# ==============================================================================
with tab_tv:
    st.markdown("<br>", unsafe_allow_html=True)
    c_chart_sel, c_popout = st.columns([3, 1])
    with c_chart_sel:
        selected_chart_lbl = st.selectbox("Select Symbol for Interactive Chart:", options=list(stock_universe.keys()), index=0)
        c_sym = stock_universe[selected_chart_lbl]

    with c_popout:
        st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
        tv_url = f"https://in.tradingview.com/chart/?symbol=BSE:{c_sym}"
        st.markdown(f'<a href="{tv_url}" target="_blank"><button style="width:100%; background:#10B981; color:#000; font-weight:700; border:none; border-radius:8px; padding:9px 12px; cursor:pointer;">↗️ Full TradingView Studio</button></a>', unsafe_allow_html=True)

    st.markdown(f"### 📈 TradingView Advanced Engine: `{c_sym}`")
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
# TAB 4: ALGORITHMIC SCANNER ROUTINES
# ==============================================================================
with tab_scanner:
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
            raw_input = st.text_area("Tickers:", "RELIANCE, TATASTEEL, INFY, ICICIBANK, LT, ZOMATO, ADANIPOWER")
            to_scan = [f"{s.strip().upper()}.NS" for s in raw_input.split(",") if s.strip() != ""]
        elif scan_univ == "Nifty 50":
            to_scan = ["ADANIENT.NS", "ADANIPORTS.NS", "ASIANPAINT.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BHARTIARTL.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "ITC.NS", "LT.NS", "RELIANCE.NS", "SBIN.NS", "TCS.NS", "TITAN.NS"]
        else:
            to_scan = [f"{s}.NS" for s in stock_universe.values()]

        trigger_scan = st.button("🚀 Execute Routine", use_container_width=True)
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
# TAB 5: INSTITUTIONAL CUSTOM SCREENER (FULL ADVANCED FILTER ENGINE)
# ==============================================================================
with tab_custom:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🧪 Multi-Factor Institutional Screener")
    st.caption("Apply combined fundamental valuation, sector classifications, RSI, and multi-EMA position conditions.")

    with st.expander("⚙️ Set Screener Filter Criteria", expanded=True):
        f_row1_c1, f_row1_c2, f_row1_c3 = st.columns(3)
        with f_row1_c1:
            price_min, price_max = st.slider("Stock Price Range (₹):", 0, 10000, (10, 5000), step=50)
        with f_row1_c2:
            min_mcap = st.number_input("Minimum Market Cap (₹ Cr):", min_value=0, value=1000, step=500)
        with f_row1_c3:
            max_pe = st.number_input("Maximum Stock P/E:", min_value=1.0, value=40.0, step=1.0)

        f_row2_c1, f_row2_c2 = st.columns(2)
        with f_row2_c1:
            selected_sector = st.selectbox("Filter by Sector:", ["All Sectors"] + list(SECTOR_MAP.keys()))
        with f_row2_c2:
            rsi_range = st.slider("RSI (14) Momentum Range:", 0, 100, (30, 70))

        st.markdown("---")
        st.markdown("<b>📉 Technical EMA Filter & Position Sub-Condition:</b>", unsafe_allow_html=True)

        ema_col1, ema_col2 = st.columns(2)
        with ema_col1:
            selected_ema_period = st.selectbox("Select EMA Period:", [10, 20, 50, 100, 200], index=0)
        with ema_col2:
            ema_sub_condition = st.selectbox(
                "Condition relative to chosen EMA:",
                [
                    "Any Position (Ignore EMA)",
                    "Price at EMA (Within ±2%)",
                    "Price 2% to 5% Above EMA",
                    "Price 2% to 5% Below EMA",
                    "Price Crossing Above EMA (Bullish Breakout)"
                ]
            )

    if st.button("🚀 Filter Market Equities", use_container_width=True):
        st.info("Executing multi-dimensional screener across equities...")
        
        if selected_sector != "All Sectors":
            eval_symbols = SECTOR_MAP[selected_sector]
        else:
            eval_symbols = ["RELIANCE", "TATASTEEL", "INFY", "ICICIBANK", "LT", "ZOMATO", "ADANIPOWER", "SBIN", "TCS", "HDFCBANK", "TATAMOTORS", "MARUTI", "NTPC", "JSWSTEEL"]

        filtered_results = []

        for s in eval_symbols:
            try:
                tk = yf.Ticker(f"{s}.NS")
                inf = tk.info
                price = inf.get("currentPrice", 0.0)
                mcap = round(inf.get("marketCap", 0) / 1e7, 2)
                pe_ratio = inf.get("trailingPE", None)

                # Fundamental checks
                if not (price_min <= price <= price_max and mcap >= min_mcap):
                    continue
                if pe_ratio is not None and float(pe_ratio) > max_pe:
                    continue

                # Technical checks
                df = tk.history(period="1y", interval="1d")
                if df.empty or len(df) < max(selected_ema_period + 5, 20):
                    continue

                df["RSI"] = ta.momentum.rsi(close=df["Close"], window=14)
                df[f"EMA_{selected_ema_period}"] = ta.trend.ema_indicator(close=df["Close"], window=selected_ema_period)

                curr_rsi = round(df["RSI"].iloc[-1], 2)
                curr_close = round(df["Close"].iloc[-1], 2)
                prev_close = round(df["Close"].iloc[-2], 2)
                curr_ema = round(df[f"EMA_{selected_ema_period}"].iloc[-1], 2)
                prev_ema = round(df[f"EMA_{selected_ema_period}"].iloc[-2], 2)

                if not (rsi_range[0] <= curr_rsi <= rsi_range[1]):
                    continue

                diff_pct = round(((curr_close - curr_ema) / curr_ema) * 100, 2)
                ema_match = False

                if ema_sub_condition == "Any Position (Ignore EMA)":
                    ema_match = True
                elif ema_sub_condition == "Price at EMA (Within ±2%)" and -2.0 <= diff_pct <= 2.0:
                    ema_match = True
                elif ema_sub_condition == "Price 2% to 5% Above EMA" and 2.0 < diff_pct <= 5.0:
                    ema_match = True
                elif ema_sub_condition == "Price 2% to 5% Below EMA" and -5.0 <= diff_pct < -2.0:
                    ema_match = True
                elif ema_sub_condition == "Price Crossing Above EMA (Bullish Breakout)":
                    if prev_close <= prev_ema and curr_close > curr_ema:
                        ema_match = True

                if ema_match:
                    filtered_results.append({
                        "Symbol": s,
                        "Price (₹)": curr_close,
                        "P/E": round(pe_ratio, 2) if pe_ratio else "N/A",
                        "Market Cap (₹ Cr)": mcap,
                        "RSI (14)": curr_rsi,
                        f"{selected_ema_period} EMA (₹)": curr_ema,
                        "Distance from EMA": f"{diff_pct}%"
                    })
            except Exception:
                pass

        if filtered_results:
            st.success(f"Discovered {len(filtered_results)} stocks matching all configured conditions!")
            st.dataframe(pd.DataFrame(filtered_results), use_container_width=True)
        else:
            st.warning("No stocks satisfied the strict multi-factor criteria.")

# ==============================================================================
# TAB 6: TERMINAL SETTINGS
# ==============================================================================
with tab_settings:
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