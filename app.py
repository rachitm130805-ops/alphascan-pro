import concurrent.futures
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
    page_title="AlphaScan Pro | Stock Scanner",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CLEAN & CLASSY CSS DESIGN SYSTEM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    :root {
        --bg-core: #090D16;
        --surface-card: #111726;
        --surface-card-hover: #172033;
        --border-glass: rgba(255, 255, 255, 0.08);
        --border-glass-hover: rgba(0, 229, 255, 0.4);
        --accent-cyan: #00E5FF;
        --accent-emerald: #10B981;
        --text-primary: #F8FAFC;
        --text-secondary: #94A3B8;
        --font-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
        --font-mono: 'JetBrains Mono', monospace;
    }

    .stApp {
        background: radial-gradient(circle at 50% -10%, #17233D 0%, #090D16 65%) !important;
        font-family: var(--font-sans) !important;
        color: var(--text-primary);
    }

    #MainMenu, footer, header { visibility: hidden; }
    .block-container {
        padding: 1.5rem 2.5rem !important;
        max-width: 1350px !important;
    }

    /* Modern Minimal Navbar */
    .top-nav {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 14px 28px;
        background: rgba(17, 23, 38, 0.7);
        backdrop-filter: blur(14px);
        border: 1px solid var(--border-glass);
        border-radius: 14px;
        margin-bottom: 2.5rem;
    }

    .brand-logo {
        font-size: 1.25rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #FFFFFF;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .brand-tag {
        font-size: 0.7rem;
        font-weight: 700;
        background: rgba(0, 229, 255, 0.12);
        color: var(--accent-cyan);
        border: 1px solid rgba(0, 229, 255, 0.3);
        padding: 2px 7px;
        border-radius: 6px;
    }

    .status-badge {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.8rem;
        color: var(--text-secondary);
        background: rgba(255, 255, 255, 0.04);
        padding: 6px 14px;
        border-radius: 30px;
        border: 1px solid var(--border-glass);
    }

    .pulse-dot {
        width: 7px;
        height: 7px;
        background-color: var(--accent-emerald);
        border-radius: 50%;
        box-shadow: 0 0 10px var(--accent-emerald);
    }

    /* Hero Text Styles */
    .hero-title {
        font-size: 3.2rem;
        font-weight: 800;
        line-height: 1.15;
        letter-spacing: -0.03em;
        color: #FFFFFF;
        margin-bottom: 1rem;
    }

    .hero-subtitle {
        font-size: 1.1rem;
        line-height: 1.6;
        color: var(--text-secondary);
        max-width: 540px;
        margin-bottom: 1.8rem;
    }

    /* Classy Feature Cards */
    .feature-box {
        background: var(--surface-card);
        border: 1px solid var(--border-glass);
        border-radius: 12px;
        padding: 1.4rem;
        transition: all 0.25s ease-in-out;
        height: 100%;
    }

    .feature-box:hover {
        transform: translateY(-3px);
        border-color: var(--border-glass-hover);
        box-shadow: 0 12px 25px rgba(0, 0, 0, 0.3);
    }

    .feature-icon {
        font-size: 1.5rem;
        margin-bottom: 0.75rem;
    }

    .feature-title {
        font-size: 1rem;
        font-weight: 700;
        color: #FFFFFF;
        margin-bottom: 0.35rem;
    }

    .feature-desc {
        font-size: 0.85rem;
        color: var(--text-secondary);
        line-height: 1.5;
        margin: 0;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #00E5FF 0%, #10B981 100%) !important;
        color: #070B14 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.65rem 1.4rem !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        transition: all 0.2s ease !important;
    }

    .stButton > button:hover {
        opacity: 0.92;
        transform: translateY(-1px);
        box-shadow: 0 8px 20px rgba(0, 229, 255, 0.35) !important;
    }

    /* Clean Card Container */
    div[data-testid="stForm"] {
        background: rgba(17, 23, 38, 0.85) !important;
        border: 1px solid var(--border-glass) !important;
        border-radius: 16px !important;
        padding: 2rem !important;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
    }

    .stTextInput > div > div > input, div[data-baseweb="select"] > div {
        background: rgba(255, 255, 255, 0.04) !important;
        border: 1px solid var(--border-glass) !important;
        color: var(--text-primary) !important;
        border-radius: 8px !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: var(--accent-cyan) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = None
if "auth_tab" not in st.session_state:
    st.session_state.auth_tab = "Sign In"
if "scan_results" not in st.session_state:
    st.session_state.scan_results = None
if "telegram_chat_id" not in st.session_state:
    st.session_state.telegram_chat_id = ""

# --- TELEGRAM HELPER ---
def send_telegram_alert(message, chat_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload, timeout=8)
        return res.status_code == 200
    except Exception:
        return False

# --- STOCK UNIVERSE FOR AUTO-SUGGESTION ---
@st.cache_data(ttl=86400)
def load_stock_universe():
    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            import io
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

# --- LANDING PAGE (WHEN LOGGED OUT) ---
if not st.session_state.user:
    # Navbar
    st.markdown("""
        <div class="top-nav">
            <div class="brand-logo">
                ⚡ AlphaScan <span class="brand-tag">PRO</span>
            </div>
            <div class="status-badge">
                <span class="pulse-dot"></span> Live Market Scanning Active
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Hero & Login in Split Columns (Zero Scrolling Needed)
    hero_col, auth_col = st.columns([1.25, 1], gap="large")

    with hero_col:
        st.markdown("""
            <div class="hero-title">Find High-Probability Swing Setups Effortlessly.</div>
            <div class="hero-subtitle">
                AlphaScan scans 2,000+ Indian stocks in seconds to find setups pulling back to the 10 Weekly Moving Average. Get instant alerts delivered straight to your Telegram bot.
            </div>
        """, unsafe_allow_html=True)

        # 4 Clean Feature Cards
        f1, f2 = st.columns(2)
        with f1:
            st.markdown("""
                <div class="feature-box">
                    <div class="feature-icon">🔍</div>
                    <div class="feature-title">2,000+ Stocks Filtered</div>
                    <div class="feature-desc">Scans the full market universe in under 10 seconds without manual effort.</div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
            st.markdown("""
                <div class="feature-box">
                    <div class="feature-icon">📈</div>
                    <div class="feature-title">Weekly 10 EMA Focus</div>
                    <div class="feature-desc">Identifies clean pullbacks to key support zones for high-probability swing trades.</div>
                </div>
            """, unsafe_allow_html=True)
        with f2:
            st.markdown("""
                <div class="feature-box">
                    <div class="feature-icon">📲</div>
                    <div class="feature-title">Instant Telegram Alerts</div>
                    <div class="feature-desc">Send filtered opportunities directly to your private Telegram bot in 1 click.</div>
                </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
            st.markdown("""
                <div class="feature-box">
                    <div class="feature-icon">📊</div>
                    <div class="feature-title">Integrated TradingView</div>
                    <div class="feature-desc">Analyze candles, indicators, and draw support lines directly inside the app.</div>
                </div>
            """, unsafe_allow_html=True)

    with auth_col:
        # Toggle between Sign In and Create Account tabs
        auth_mode = st.radio("Access Terminal", ["Sign In", "Create Account"], horizontal=True, label_visibility="collapsed")

        if auth_mode == "Sign In":
            with st.form("signin_form"):
                st.subheader("Welcome Back")
                st.caption("Sign in to access your scanner and alerts.")
                email = st.text_input("Email Address", placeholder="name@example.com")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submitted = st.form_submit_button("Sign In to Terminal", use_container_width=True)

                if submitted:
                    if not email or not password:
                        st.error("Please enter both email and password.")
                    else:
                        try:
                            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                            st.session_state.user = res.user
                            if res.user and res.user.user_metadata:
                                st.session_state.telegram_chat_id = res.user.user_metadata.get("telegram_chat_id", "")
                            st.success("Signed in successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Sign in failed: {e}")

        else:
            with st.form("signup_form"):
                st.subheader("Create an Account")
                st.caption("Get instant access to real-time market scans.")
                email = st.text_input("Email Address", placeholder="name@example.com")
                password = st.text_input("Choose Password (min 6 chars)", type="password", placeholder="Create a strong password")
                submitted = st.form_submit_button("Create My Account", use_container_width=True)

                if submitted:
                    if not email or not password:
                        st.error("Please fill in all details.")
                    else:
                        try:
                            res = supabase.auth.sign_up({"email": email, "password": password})
                            st.success("Account created successfully! Switch to 'Sign In' above to login.")
                        except Exception as e:
                            st.error(f"Sign up error: {e}")

    st.stop()

# --- MAIN DASHBOARD (WHEN LOGGED IN) ---
user_email = st.session_state.user.email

st.markdown(f"""
    <div class="top-nav">
        <div class="brand-logo">
            ⚡ AlphaScan <span class="brand-tag">PRO</span>
        </div>
        <div style="display:flex; align-items:center; gap:16px;">
            <span style="font-size:0.85rem; color:var(--text-secondary);">Logged in: <b style="color:#FFF;">{user_email}</b></span>
            <div class="pulse-dot"></div>
        </div>
    </div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📊 Stock Scanner", "📲 Alert Settings", "📈 Interactive Chart"])

# --- TAB 1: SCANNER ---
with tab1:
    st.markdown("<br>", unsafe_allow_html=True)
    c_config, c_results = st.columns([1, 2.5])

    with c_config:
        st.markdown('<div class="feature-box">', unsafe_allow_html=True)
        st.subheader("Scanner Settings")
        scan_mode = st.radio("Choose Stocks to Scan:", ["Custom Watchlist", "Nifty 50", "Full NSE (2000+ Stocks)"])
        buffer_pct = st.slider("10 EMA Tolerance Buffer (%)", 0.5, 3.0, 2.0, 0.1)

        symbols_to_scan = []
        if scan_mode == "Custom Watchlist":
            custom_input = st.text_area("Watchlist Tickers (comma separated):", "RELIANCE, TATASTEEL, INFY, ICICIBANK, LT, ZOMATO, ADANIPOWER")
            symbols_to_scan = [f"{s.strip().upper()}.NS" for s in custom_input.split(",") if s.strip() != ""]
        elif scan_mode == "Nifty 50":
            symbols_to_scan = ["ADANIENT.NS", "ADANIPORTS.NS", "ASIANPAINT.NS", "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BHARTIARTL.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "ITC.NS", "LT.NS", "RELIANCE.NS", "SBIN.NS", "TCS.NS", "TITAN.NS"]
        else:
            symbols_to_scan = [f"{s}.NS" for s in stock_universe.values()]

        st.markdown("<br>", unsafe_allow_html=True)
        run_scan = st.button("🚀 Start Scan", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c_results:
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
                        "Distance from EMA": f"{diff_pct}%",
                    }
            except Exception:
                return None
            return None

        if run_scan:
            st.info(f"Scanning {len(symbols_to_scan)} stocks... Please wait.")
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

        if st.session_state.scan_results is not None:
            df_res = st.session_state.scan_results

            r1, r2 = st.columns([1, 1])
            r1.metric("Setups Found", len(df_res))
            r2.metric("Tolerance Buffer", f"±{buffer_pct}%")

            st.markdown("<br>", unsafe_allow_html=True)

            if not df_res.empty:
                st.dataframe(df_res, use_container_width=True)

                if st.button("📲 Send Alerts to My Telegram"):
                    active_chat_id = st.session_state.telegram_chat_id
                    if not active_chat_id:
                        st.error("Telegram Chat ID missing! Please link your Telegram ID in the 'Alert Settings' tab.")
                    else:
                        matches_text = [
                            f"• *{row['Stock']}*: Price Rs.{row['Price (₹)']} | 10 EMA Rs.{row['10 EMA (₹)']} ({row['Distance from EMA']})"
                            for _, row in df_res.iterrows()
                        ]
                        total_sent = 0
                        for i in range(0, len(matches_text), 15):
                            chunk = matches_text[i : i + 15]
                            msg = f"⚡ *ALPHASCAN SWING ALERTS*\n\n" + "\n".join(chunk)
                            if send_telegram_alert(msg, active_chat_id):
                                total_sent += 1
                            time.sleep(0.4)

                        if total_sent > 0:
                            st.success("Alerts dispatched to your Telegram bot!")
                        else:
                            st.error("Could not deliver alerts. Make sure you pressed /start on your bot.")
            else:
                st.warning("No stocks matched the 10 EMA pullback criteria in this scan.")

# --- TAB 2: TELEGRAM SETTINGS ---
with tab2:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="feature-box" style="max-width: 600px; margin: 0 auto;">', unsafe_allow_html=True)
    st.subheader("📲 Telegram Alerts Setup")
    
    current_val = st.session_state.telegram_chat_id
    telegram_id_input = st.text_input("Enter your Telegram Chat ID:", value=current_val)

    if st.button("Save Telegram ID"):
        clean_id = telegram_id_input.strip()
        if clean_id:
            try:
                res = supabase.auth.update_user({"data": {"telegram_chat_id": clean_id}})
                if res.user:
                    st.session_state.user = res.user
                st.session_state.telegram_chat_id = clean_id
                st.success("Chat ID saved successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Save error: {e}")
        else:
            st.warning("Please enter a valid Chat ID.")

    st.markdown("""
    <p style="color:var(--text-secondary); font-size:0.85rem; margin-top:1rem;">
    <b>Quick Setup:</b><br>
    1. Search <code>@userinfobot</code> on Telegram to get your numeric ID.<br>
    2. Paste it here and click Save.<br>
    3. Make sure to open your scanner bot on Telegram and press <b>/start</b> once.
    </p>
    """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color:var(--border-glass);'>", unsafe_allow_html=True)
    if st.button("🚪 Logout", use_container_width=True):
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
        st.session_state.user = None
        st.session_state.telegram_chat_id = ""
        st.rerun()
        
    st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 3: TRADINGVIEW CHART ---
with tab3:
    st.markdown("<br>", unsafe_allow_html=True)

    col_search, col_direct = st.columns([3, 1])

    with col_search:
        options = list(stock_universe.keys())
        default_idx = 0
        for i, opt in enumerate(options):
            if opt.startswith("ADANIPOWER"):
                default_idx = i
                break

        selected_label = st.selectbox(
            "Search Indian Stock (Name or Symbol):",
            options=options,
            index=default_idx
        )
        stock_sym = stock_universe[selected_label]

    with col_direct:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        tv_direct_link = f"https://in.tradingview.com/chart/?symbol=BSE:{stock_sym}"
        st.markdown(
            f'<a href="{tv_direct_link}" target="_blank" style="text-decoration:none;">'
            f'<button style="width:100%; background:linear-gradient(135deg,#00E5FF,#10B981); color:#000; font-weight:700; border:none; border-radius:8px; padding:9px 12px; cursor:pointer;">'
            f'↗️ Open in TradingView'
            f'</button></a>',
            unsafe_allow_html=True
        )

    st.markdown(f"### 📈 Interactive Chart: `{stock_sym}`")

    tv_embed_code = f"""
    <div class="tradingview-widget-container" style="height:720px;width:100%;">
      <div id="tradingview_advanced_engine" style="height:calc(100% - 32px);width:100%;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({{
        "autosize": true,
        "symbol": "BSE:{stock_sym}",
        "interval": "W",
        "timezone": "Asia/Kolkata",
        "theme": "dark",
        "style": "1",
        "locale": "in",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "hide_side_toolbar": false,
        "studies": [
          "MASimple@tv-basicstudies",
          "EMA@tv-basicstudies"
        ],
        "container_id": "tradingview_advanced_engine"
      }});
      </script>
    </div>
    """
    components.html(tv_embed_code, height=730)