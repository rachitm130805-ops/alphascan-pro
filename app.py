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

# --- PAGE CONFIG & CUSTOM STYLING ---
st.set_page_config(
    page_title="AlphaScan Pro | Quant Terminal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp {
        background-color: #0b0e14;
        color: #e6edf3;
    }
    
    .hero-card {
        background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 30px;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
    }
    
    .feature-card {
        background-color: #161b22;
        border: 1px solid #21262d;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
    }

    .stButton>button {
        background-color: #238636;
        color: #ffffff;
        border-radius: 6px;
        border: 1px solid rgba(240,246,252,0.1);
        padding: 10px 20px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #2ea043;
        border-color: #8b949e;
    }
    
    div[data-testid="stForm"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 20px;
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

# --- LANDING PAGE (UNAUTHENTICATED) ---
if not st.session_state.user:
    st.markdown("""
    <div class="hero-card">
        <h1 style="color: #58a6ff; font-size: 2.8rem; margin-bottom: 5px;">⚡ AlphaScan Pro</h1>
        <p style="font-size: 1.2rem; color: #8b949e;">Automated Technical Swing Scanner & Algorithmic Alert Engine for Indian Markets (NSE)</p>
    </div>
    """, unsafe_allow_html=True)

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        st.markdown("""<div class="feature-card"><h3>📈 2000+</h3><p style="color:#8b949e">NSE Stocks Scanned Realtime</p></div>""", unsafe_allow_html=True)
    with col_f2:
        st.markdown("""<div class="feature-card"><h3>🎯 10 EMA</h3><p style="color:#8b949e">Weekly Support Tracking</p></div>""", unsafe_allow_html=True)
    with col_f3:
        st.markdown("""<div class="feature-card"><h3>⚡ Multi-Threaded</h3><p style="color:#8b949e">High-Speed Execution</p></div>""", unsafe_allow_html=True)
    with col_f4:
        st.markdown("""<div class="feature-card"><h3>📲 Telegram Sync</h3><p style="color:#8b949e">Direct Mobile Alerts</p></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_btn1, col_btn2, _ = st.columns([1, 1, 2])
    with col_btn1:
        if st.button("🔑 Sign In to Terminal", use_container_width=True):
            st.session_state.auth_mode = "login"
    with col_btn2:
        if st.button("📝 Register Account", use_container_width=True):
            st.session_state.auth_mode = "register"

    if st.session_state.auth_mode == "login":
        st.markdown("---")
        with st.form("login_form"):
            st.subheader("🔑 Sign In")
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                if not email or not password:
                    st.error("Please fill in all details.")
                else:
                    try:
                        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state.user = res.user
                        # Load existing metadata Chat ID if present
                        if res.user and res.user.user_metadata:
                            st.session_state.telegram_chat_id = res.user.user_metadata.get("telegram_chat_id", "")
                        st.success("Access Granted! Loading Terminal...")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Authentication Failed: {e}")

    elif st.session_state.auth_mode == "register":
        st.markdown("---")
        with st.form("register_form"):
            st.subheader("📝 Create New Trader Account")
            email = st.text_input("Email")
            password = st.text_input("Password (min 6 chars)", type="password")
            submit = st.form_submit_button("Register")
            
            if submit:
                if not email or not password:
                    st.error("Please fill in all details.")
                else:
                    try:
                        res = supabase.auth.sign_up({"email": email, "password": password})
                        st.success("Account created successfully! Click 'Sign In' above to log in.")
                    except Exception as e:
                        st.error(f"Registration Failed: {e}")

    st.stop()

# --- MAIN TERMINAL (AFTER SUCCESSFUL LOGIN) ---
user_email = st.session_state.user.email

st.sidebar.markdown(f"👤 **Account:** `{user_email}`")

# Fetch current chat id from session
if not st.session_state.telegram_chat_id and st.session_state.user and st.session_state.user.user_metadata:
    st.session_state.telegram_chat_id = st.session_state.user.user_metadata.get("telegram_chat_id", "")

# Telegram Link Management Section in Sidebar
with st.sidebar.expander("📲 Telegram Alerts Setup", expanded=True if not st.session_state.telegram_chat_id else False):
    st.caption("Link your Telegram Chat ID once to receive instant scanner alerts on your Bot.")
    
    current_val = st.session_state.telegram_chat_id
    telegram_id_input = st.text_input("Enter Telegram Chat ID:", value=current_val, key="tg_id")
    
    if st.button("Save Telegram ID"):
        clean_id = telegram_id_input.strip()
        if clean_id:
            try:
                # Save to Supabase User Metadata
                res = supabase.auth.update_user({"data": {"telegram_chat_id": clean_id}})
                if res.user:
                    st.session_state.user = res.user
                st.session_state.telegram_chat_id = clean_id
                st.success("✅ Chat ID Saved & Linked!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to update: {e}")
        else:
            st.warning("Please enter a valid Chat ID.")

    st.markdown("""
    <small><b>How to get your Telegram Chat ID?</b><br>
    1. Telegram par <code>@userinfobot</code> search karo.<br>
    2. Uspe <b>Start</b> dabao - wo aapko aapka numeric <b>Id</b> batayega.<br>
    3. Wo numeric ID yahan paste karke <b>Save</b> kar do.<br><br>
    ⚠️ <i>Important: Apne <b>Scanner Bot</b> par jaakar bhi ek baar <b>/start</b> zaroor dabayein taaki bot aapko alerts bhej sake.</i></small>
    """, unsafe_allow_html=True)

if st.sidebar.button("🚪 Logout", use_container_width=True):
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    st.session_state.user = None
    st.session_state.auth_mode = None
    st.session_state.telegram_chat_id = ""
    st.rerun()

st.sidebar.divider()

# --- SCANNER LOGIC ---
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
                "Stock": stock_name,
                "Price (₹)": current_close,
                "Weekly Low (₹)": current_low,
                "10 EMA (₹)": ema10,
                "Distance (%)": f"{diff_pct}%",
            }
    except Exception:
        return None
    return None

# Terminal UI Header
st.title("⚡ AlphaScan Pro Quantitative Terminal")
st.caption("Weekly 10 EMA Support Scanner & Multi-threaded Parameter Engine")
st.divider()

# Configurations
st.sidebar.header("⚙️ Scanner Settings")
scan_mode = st.sidebar.radio("Market Universe:", ["Custom Watchlist", "Nifty 50", "Full NSE (2000+ Stocks)"])
buffer_pct = st.sidebar.slider("10 EMA Tolerance Buffer (%)", 0.5, 3.0, 2.0, 0.1)

symbols_to_scan = []
if scan_mode == "Custom Watchlist":
    custom_input = st.sidebar.text_area("Tickers (Comma Separated):", "RELIANCE, TATASTEEL, INFY, ICICIBANK, LT, ZOMATO")
    symbols_to_scan = [f"{s.strip().upper()}.NS" for s in custom_input.split(",") if s.strip() != ""]
elif scan_mode == "Nifty 50":
    symbols_to_scan = ["ADANIENT.NS", "ADANIPORTS.NS", "ASIANPAINT.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BHARTIARTL.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "ITC.NS", "LT.NS", "RELIANCE.NS", "SBIN.NS", "TCS.NS", "TITAN.NS"]
else:
    symbols_to_scan = get_all_nse_symbols()

if st.sidebar.button("🚀 Run Live Scan", use_container_width=True):
    if not symbols_to_scan:
        st.sidebar.error("Please add stocks to scan.")
    else:
        st.info(f"Scanning {len(symbols_to_scan)} stocks concurrently...")
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
        st.success("Scan Execution Complete!")

# Results Render
if st.session_state.scan_results is not None and not st.session_state.scan_results.empty:
    df_res = st.session_state.scan_results

    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Setups Identified", len(df_res))
    col_m2.metric("Scan Strategy", "Weekly 10 EMA Support")
    col_m3.metric("Tolerance Buffer", f"±{buffer_pct}%")

    st.subheader("🎯 Active Swing Candidates")
    st.dataframe(df_res, use_container_width=True)

    # Active Linked Chat ID Verification
    active_chat_id = st.session_state.telegram_chat_id

    if st.button("📲 Push Alerts to My Telegram Bot"):
        if not active_chat_id:
            st.error("❌ Telegram Chat ID missing! Please enter and Save your Chat ID in the sidebar settings first.")
        else:
            matches_text = [
                f"• *{row['Stock']}*: Price Rs.{row['Price (₹)']} | 10 EMA Rs.{row['10 EMA (₹)']} ({row['Distance (%)']})"
                for _, row in df_res.iterrows()
            ]

            total_sent = 0
            for i in range(0, len(matches_text), 15):
                chunk = matches_text[i : i + 15]
                msg = f"⚡ *ALPHASCAN PRO ALERTS*\n\n" + "\n".join(chunk)
                if send_telegram_alert(msg, active_chat_id):
                    total_sent += 1
                time.sleep(0.4)

            if total_sent > 0:
                st.success("✅ Setups dispatched successfully to your Bot!")
            else:
                st.error("❌ Alert delivery failed! Make sure you opened your scanner bot in Telegram and clicked /start at least once.")