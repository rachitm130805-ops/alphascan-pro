import concurrent.futures
import time
import pandas as pd
import requests
import streamlit as st
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
    page_title="AlphaScan Pro | Quant Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ADVANCED DESIGN SYSTEM & INJECTED CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* Global CSS Variables & Overrides */
    :root {
        --bg-main: #080A0F;
        --bg-card: #12161F;
        --bg-card-hover: #1A202C;
        --border-color: #212836;
        --border-color-active: #38445D;
        --accent-green: #00E676;
        --accent-cyan: #00E5FF;
        --text-primary: #F0F6FC;
        --text-secondary: #8B949E;
        --font-main: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        --font-mono: 'JetBrains Mono', monospace;
    }

    /* Core Application Background & Fonts */
    .stApp {
        background-color: var(--bg-main) !important;
        font-family: var(--font-main) !important;
        color: var(--text-primary);
    }

    /* Hide Unnecessary Streamlit UI Elements */
    #MainMenu, footer, header {visibility: hidden;}
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
        max-width: 95% !important;
    }

    /* Typography */
    h1, h2, h3, h4, h5, h6 {
        font-family: var(--font-main) !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }

    /* Terminal Navbar & Hero Panels */
    .terminal-navbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1.25rem 1.75rem;
        background: linear-gradient(180deg, rgba(18, 22, 31, 0.8) 0%, rgba(12, 15, 22, 0.9) 100%);
        backdrop-filter: blur(12px);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    }

    .brand-logo {
        font-size: 1.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #00E5FF 0%, #00E676 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.03em;
    }

    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 20px;
        background: rgba(0, 230, 118, 0.1);
        border: 1px solid rgba(0, 230, 118, 0.3);
        color: var(--accent-green);
        font-size: 0.8rem;
        font-weight: 600;
        font-family: var(--font-mono);
    }

    .status-dot {
        width: 8px;
        height: 8px;
        background-color: var(--accent-green);
        border-radius: 50%;
        box-shadow: 0 0 8px var(--accent-green);
    }

    /* Metric Cards Grid */
    .metric-card {
        background: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 10px;
        padding: 1.25rem;
        transition: all 0.2s ease-in-out;
    }
    .metric-card:hover {
        border-color: var(--border-color-active);
        transform: translateY(-2px);
    }
    .metric-label {
        font-size: 0.8rem;
        color: var(--text-secondary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: var(--text-primary);
        font-family: var(--font-mono);
        margin-top: 4px;
    }

    /* Custom Input Fields & Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0C0F16 !important;
        border-right: 1px solid var(--border-color) !important;
    }
    
    .stTextInput>div>div>input, .stSelectbox>div>div>div, .stTextArea>div>div>textarea {
        background-color: #12161F !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
        font-family: var(--font-mono) !important;
    }

    .stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {
        border-color: var(--accent-cyan) !important;
        box-shadow: 0 0 0 1px var(--accent-cyan) !important;
    }

    /* Enterprise Action Buttons */
    .stButton>button {
        background: linear-gradient(180deg, #1A2332 0%, #111722 100%) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-color-active) !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        letter-spacing: 0.02em !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2) !important;
    }
    .stButton>button:hover {
        background: linear-gradient(180deg, #222D40 0%, #161F2E 100%) !important;
        border-color: var(--accent-cyan) !important;
        color: var(--accent-cyan) !important;
        box-shadow: 0 0 12px rgba(0, 229, 255, 0.2) !important;
    }

    /* Styled Form Containers */
    div[data-testid="stForm"] {
        background-color: var(--bg-card);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 2rem;
    }

    /* Dataframe Table Custom Styling */
    div[data-testid="stDataFrame"] {
        border: 1px solid var(--border-color);
        border-radius: 8px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE MANAGEMENT ---
if "user" not in st.session_state:
    st.session_state.user = None
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = None
if "scan_results" not in st.session_state:
    st.session_state.scan_results = None
if "telegram_chat_id" not in st.session_state:
    st.session_state.telegram_chat_id = ""

# --- TELEGRAM UTILS ---
def send_telegram_alert(message, chat_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload, timeout=8)
        return res.status_code == 200
    except Exception:
        return False

# --- LANDING PAGE (UNAUTHENTICATED TERMINAL) ---
if not st.session_state.user:
    # Top Navbar Design
    st.markdown("""
        <div class="terminal-navbar">
            <div class="brand-logo">⚡ ALPHASCAN PRO</div>
            <div class="status-badge"><span class="status-dot"></span> SYSTEM ONLINE</div>
        </div>
    """, unsafe_allow_html=True)

    # Hero Intro
    st.markdown("""
        <div style="text-align: center; margin: 3rem 0;">
            <h1 style="font-size: 3.2rem; margin-bottom: 0.5rem; background: linear-gradient(180deg, #FFFFFF 0%, #8B949E 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                Institutional Market Intelligence
            </h1>
            <p style="color: #8B949E; font-size: 1.15rem; max-width: 700px; margin: 0 auto 2rem auto;">
                High-frequency technical scanner tracking weekly 10 EMA dynamics across 2,000+ NSE equity markets in real-time.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Architectural Highlights
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="metric-card"><div class="metric-label">Universe Coverage</div><div class="metric-value">2000+</div><small style="color:#8B949E">NSE Equities</small></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="metric-card"><div class="metric-label">Algorithm</div><div class="metric-value">10 EMA</div><small style="color:#8B949E">Weekly Support</small></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="metric-card"><div class="metric-label">Execution Engine</div><div class="metric-value">30x</div><small style="color:#8B949E">Thread Pool</small></div>', unsafe_allow_html=True)
    with col4:
        st.markdown('<div class="metric-card"><div class="metric-label">Alert Sync</div><div class="metric-value">&lt; 1s</div><small style="color:#8B949E">Telegram Integration</small></div>', unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Authentication Triggers
    c_btn1, c_btn2, _ = st.columns([1, 1, 2])
    with c_btn1:
        if st.button("🔑 Access Terminal (Sign In)", use_container_width=True):
            st.session_state.auth_mode = "login"
    with c_btn2:
        if st.button("📝 Register Account", use_container_width=True):
            st.session_state.auth_mode = "register"

    # Authentication Form Render
    if st.session_state.auth_mode == "login":
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form("login_form"):
            st.subheader("🔑 Terminal Authentication")
            email = st.text_input("Trader Identification (Email)")
            password = st.text_input("Access Security Token (Password)", type="password")
            submit = st.form_submit_button("Authenticate")
            
            if submit:
                if not email or not password:
                    st.error("Authentication parameters incomplete.")
                else:
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state.user = res.user
                        if res.user and res.user.user_metadata:
                            st.session_state.telegram_chat_id = res.user.user_metadata.get("telegram_chat_id", "")
                        st.success("Session Authorized. Initializing Terminal...")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Authentication Failed: {e}")

    elif st.session_state.auth_mode == "register":
        st.markdown("<br>", unsafe_allow_html=True)
        with st.form("register_form"):
            st.subheader("📝 Request Access Credentials")
            email = st.text_input("Primary Email")
            password = st.text_input("Set Security Token (Min 6 chars)", type="password")
            submit = st.form_submit_button("Create Terminal Profile")
            
            if submit:
                if not email or not password:
                    st.error("Please fill in all parameter fields.")
                else:
                    try:
                        res = supabase.auth.sign_up({"email": email, "password": password})
                        st.success("Profile created! Authenticate above to continue.")
                    except Exception as e:
                        st.error(f"Registration Failed: {e}")

    st.stop()

# --- MAIN QUANT TERMINAL (AUTHENTICATED SESSION) ---
user_email = st.session_state.user.email

# Navbar Header
st.markdown(f"""
    <div class="terminal-navbar">
        <div class="brand-logo">⚡ ALPHASCAN PRO <span style="font-size: 0.8rem; color: #8B949E; font-family: var(--font-mono);">[v2.4 QUANT ENGINE]</span></div>
        <div class="status-badge"><span class="status-dot"></span> LINKED: {user_email}</div>
    </div>
""", unsafe_allow_html=True)

# Sidebar Configuration
st.sidebar.markdown("<h3 style='margin-bottom: 0;'>⚙️ Control Panel</h3>", unsafe_allow_html=True)
st.sidebar.caption("Execution parameters & routing")
st.sidebar.markdown("---")

# Fetch Chat ID from Session or Metadata
if not st.session_state.telegram_chat_id and st.session_state.user and st.session_state.user.user_metadata:
    st.session_state.telegram_chat_id = st.session_state.user.user_metadata.get("telegram_chat_id", "")

# Telegram Setup Component
with st.sidebar.expander("📲 Telegram Routing Configuration", expanded=not bool(st.session_state.telegram_chat_id)):
    current_val = st.session_state.telegram_chat_id
    telegram_id_input = st.text_input("Telegram Chat ID:", value=current_val, key="tg_id")
    
    if st.button("Save Chat ID", use_container_width=True):
        clean_id = telegram_id_input.strip()
        if clean_id:
            try:
                res = supabase.auth.update_user({"data": {"telegram_chat_id": clean_id}})
                if res.user:
                    st.session_state.user = res.user
                st.session_state.telegram_chat_id = clean_id
                st.success("✅ Endpoint Saved!")
                st.rerun()
            except Exception as e:
                st.error(f"Save error: {e}")
        else:
            st.warning("Provide a valid numeric Chat ID.")

    st.caption("Obtain Chat ID from `@userinfobot`. Ensure you trigger `/start` on your dedicated Alert Bot.")

st.sidebar.markdown("---")

# Scanner Core Parameters
scan_mode = st.sidebar.radio("Market Universe:", ["Custom Watchlist", "Nifty 50", "Full NSE (2000+ Stocks)"])
buffer_pct = st.sidebar.slider("10 EMA Buffer Range (%)", 0.5, 3.0, 2.0, 0.1)

symbols_to_scan = []
if scan_mode == "Custom Watchlist":
    custom_input = st.sidebar.text_area("Tickers (Comma Separated):", "RELIANCE, TATASTEEL, INFY, ICICIBANK, LT, ZOMATO")
    symbols_to_scan = [f"{s.strip().upper()}.NS" for s in custom_input.split(",") if s.strip() != ""]
elif scan_mode == "Nifty 50":
    symbols_to_scan = ["ADANIENT.NS", "ADANIPORTS.NS", "ASIANPAINT.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BHARTIARTL.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "ITC.NS", "LT.NS", "RELIANCE.NS", "SBIN.NS", "TCS.NS", "TITAN.NS"]
else:
    def get_all_nse_symbols():
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        headers = {"User-Agent": "Mozilla/5.0"}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                with open("EQUITY_L.csv", "wb") as f:
                    f.write(response.content)
                df = pd.read_csv("EQUITY_L.csv")
                df = df[df[" SERIES"] == "EQ"]
                return [f"{symbol.strip()}.NS" for symbol in df["SYMBOL"]]
        except Exception:
            pass
        return ["RELIANCE.NS", "TATASTEEL.NS", "INFY.NS", "ICICIBANK.NS", "LT.NS"]
    symbols_to_scan = get_all_nse_symbols()

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Terminate Session", use_container_width=True):
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    st.session_state.user = None
    st.session_state.auth_mode = None
    st.session_state.telegram_chat_id = ""
    st.rerun()

# --- SCANNER ALGORITHM ---
def process_single_stock(symbol, buffer_pct):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y", interval="1wk")
        if df.empty or len(df) < 15:
            return None

        df["EMA10"] = ta.trend.ema_indicator(close=df["Close"], window=10)
        current_close = round(df["Close"].iloc[-1], 2)
        current_low = round(df["Low"].iloc[-1], 2)
        ema10 = round(df["EMA10"].iloc[-1], 2)

        if current_close < 5:
            return None

        lower_bound = ema10 * (1 - (buffer_pct / 100))
        upper_bound = ema10 * (1 + (buffer_pct / 100))

        if (lower_bound <= current_low <= upper_bound) or (current_low <= ema10 and current_close >= ema10):
            stock_name = symbol.replace(".NS", "")
            diff_pct = round(((current_close - ema10) / ema10) * 100, 2)
            return {
                "Ticker": stock_name,
                "LTP (₹)": current_close,
                "Weekly Low (₹)": current_low,
                "10 EMA (₹)": ema10,
                "Spread (%)": f"{diff_pct}%",
            }
    except Exception:
        return None
    return None

# Execution Triggers
if st.sidebar.button("🚀 Run Live Scanner Engine", use_container_width=True):
    if not symbols_to_scan:
        st.sidebar.error("Select market parameters.")
    else:
        st.info(f"Executing parallel scan across {len(symbols_to_scan)} market symbols...")
        progress_bar = st.progress(0)
        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            futures = {executor.submit(process_single_stock, sym, buffer_pct): sym for sym in symbols_to_scan}
            completed = 0
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                if res:
                    results.append(res)
                completed += 1
                progress_bar.progress(completed / len(symbols_to_scan))

        st.session_state.scan_results = pd.DataFrame(results) if results else pd.DataFrame()
        st.success("Scan Routine Execution Complete.")

# Terminal Results Render
if st.session_state.scan_results is not None:
    df_res = st.session_state.scan_results
    
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Matches Found</div><div class="metric-value" style="color:var(--accent-green);">{len(df_res)}</div></div>', unsafe_allow_html=True)
    with m2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Selected Strategy</div><div class="metric-value">Weekly EMA</div></div>', unsafe_allow_html=True)
    with m3:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Tolerance Buffer</div><div class="metric-value">±{buffer_pct}%</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if not df_res.empty:
        st.subheader("🎯 Identified Setup Candidates")
        st.dataframe(df_res, use_container_width=True)

        active_chat_id = st.session_state.telegram_chat_id

        if st.button("📲 Push Signals to Telegram Bot"):
            if not active_chat_id:
                st.error("Telegram Chat ID unconfigured. Save your Chat ID in the Control Panel first.")
            else:
                matches_text = [
                    f"• *{row['Ticker']}*: LTP Rs.{row['LTP (₹)']} | 10 EMA Rs.{row['10 EMA (₹)']} ({row['Spread (%)']})"
                    for _, row in df_res.iterrows()
                ]

                total_sent = 0
                for i in range(0, len(matches_text), 15):
                    chunk = matches_text[i : i + 15]
                    msg = f"⚡ *ALPHASCAN QUANT SIGNALS*\n\n" + "\n".join(chunk)
                    if send_telegram_alert(msg, active_chat_id):
                        total_sent += 1
                    time.sleep(0.4)

                if total_sent > 0:
                    st.success(" Signals dispatched successfully to your linked bot endpoint.")
                else:
                    st.error("Delivery failed. Ensure your bot has received a `/start` command.")
    else:
        st.warning("No tickers met the technical criteria during this scan run.")