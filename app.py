import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta
import requests
import pandas_market_calendars as mcal

# --- פונקציות מתמטיות של צינור הנתונים המוסדי ---
@st.cache_data(ttl=3600)
def calculate_hurst(series):
    if len(series) < 30: return 0.5
    lags = range(2, 15)
    tau = [np.sqrt(np.std(np.subtract(series[lag:], series[:-lag]))) for lag in lags]
    poly = np.polyfit(np.log(lags), np.log(tau), 1)
    return poly[0] * 2.0

def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_atr(data, window=14):
    high_low = data['High'] - data['Low']
    high_close = np.abs(data['High'] - data['Close'].shift())
    low_close = np.abs(data['Low'] - data['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    atr = true_range.rolling(window=window).mean()
    return atr

# --- פונקציות זיכרון מטמון למניעת הבהובים ---
@st.cache_data(ttl=15)
def fetch_macro_data():
    return yf.download(['SPY', '^VIX', '^TNX', 'CL=F'], period='45d', interval='1d', auto_adjust=True, progress=False)

@st.cache_data(ttl=15)
def fetch_sector_data(ticker):
    return yf.download(ticker, period='5d', interval='15m', auto_adjust=True, progress=False)

# --- הגדרות עמוד ועיצוב מוסדי ---
st.set_page_config(page_title="Matrix OS V6", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    .reportview-container { background: #0e1117; }
    .green-text { color: #00ff00; font-weight: bold; font-size: 16px; }
    .red-text { color: #ff0000; font-weight: bold; font-size: 16px; }
    .blink { animation: blinker 1.5s linear infinite; color: #ffcc00; font-weight: bold; }
    @keyframes blinker { 50% { opacity: 0; } }
    
    /* מניעת שקיפות נתונים בלבד מבלי לפגוע ברקע השחור המקורי */
    .stApp *:not(.blink) {
        opacity: 1 !important;
        transition: none !important;
    }
    div[data-testid="stStatusWidget"] {
        opacity: 0 !important;
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

now_dt = datetime.now()

st.title("⚡ Matrix OS - מערכת פיקוד מוסדית (גרסת נרות יפניים)")
st.write(f"🔄 מתעדכן חי | זמן מערכת: {now_dt.strftime('%H:%M:%S')}")
st.markdown("---")

# --- רשימות נכסים ומעקב (מותאם ל-Finviz) ---
assets = {
    'S&P 500 (SPY)': 'SPY', 'Nasdaq 100 (QQQ)': 'QQQ', 'VIX Index': '^VIX',
    'Crude Oil': 'CL=F', 'Silver': 'SI=F', 'Platinum': 'PL=F', 
    'Wheat': 'ZW=F', 'Natural Gas': 'NG=F',
    'AST SpaceMobile': 'ASTS', 'Nano Nuclear': 'NNE', 'Iris Energy': 'IREN'
}

sectors = {
    'Tech (XLK)': 'XLK', 'Energy (XLE)': 'XLE', 'Financials (XLF)': 'XLF', 
    'Utilities (XLU)': 'XLU', 'Materials (XLB)': 'XLB', 'Staples (XLP)': 'XLP', 
    'Real Estate (XLRE)': 'XLRE', 'Nuclear (URA)': 'URA', 'Quantum (QTUM)': 'QTUM'
}

# --- מנוע נרות יפניים תוך-יומיים וחישוב מגמות ---
def get_asset_metrics(name, ticker):
    try:
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.fast_info
        prev_close_daily = info.previous_close
        current_price = info.last_price
        
        if pd.isna(current_price) or current_price == 0:
            df_fallback = ticker_obj.history(period="1d", interval="1m")
            if df_fallback.empty: return None
            current_price = df_fallback['Close'].iloc[-1]
            
        daily_change = ((current_price - prev_close_daily) / prev_close_daily) * 100
        df_1m = ticker_obj.history(period="1d", interval="1m")
        if df_1m.empty or len(df_1m) < 20: df_1m = ticker_obj.history(period="5d", interval="1m")
            
        p_1m = df_1m['Close'].iloc[-2] if len(df_1m) >= 2 else current_price
        p_5m = df_1m['Close'].iloc[-6] if len(df_1m) >= 6 else current_price
        p_15m = df_1m['Close'].iloc[-16] if len(df_1m) >= 16 else current_price
        
        def get_arrow_html(curr, past):
            return "<span style='color: #00ff00;'>🔼</span>" if curr >= past else "<span style='color: #ff0000;'>🔽</span>"
            
        arrow_1m = get_arrow_html(current_price, p_1m)
        arrow_5m = get_arrow_html(current_price, p_5m)
        arrow_15m = get_arrow_html(current_price, p_15m)
        
        df_15m = ticker_obj.history(period="1d", interval="15m")
        if df_15m.empty: df_15m = df_1m 
        
        fig = go.Figure(data=[go.Candlestick(
            x=df_15m.index, open=df_15m['Open'], high=df_15m['High'],
            low=df_15m['Low'], close=df_15m['Close'],
            increasing_line_color='#00ff00', increasing_fillcolor='#00ff00',
            decreasing_line_color='#ff0000', decreasing_fillcolor='#ff0000'
        )])
        
        fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=60, width=180,
            xaxis_rangeslider_visible=False, xaxis=dict(visible=False), yaxis=dict(visible=False),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        
        return {
            'נכס': name,
            'מחיר אחרון': f"{current_price:.2f}" if current_price > 1 else f"{current_price:.4f}",
            'שינוי יומי': f"{daily_change:.2f}%",
            'מגמת 1m': arrow_1m,
            'מגמת 5m': arrow_5m,
            'מגמת 15m': arrow_15m,
            'גרף': fig,
            'is_positive': daily_change >= 0
        }
    except:
        return None

# --- קומת המאקרו העליונה ---
col_m1, col_m2, col_m3 = st.columns([1, 2, 1])

with col_m2:
    try:
        vix_df = yf.Ticker('^VIX').history(period="1d")
        vix_now = vix_df['Close'].iloc[-1] if not vix_df.empty else 20
        fg_score = 100 - (vix_now * 2.5)
        fg_score = max(min(fg_score, 100), 0)
    except:
        fg_score = 50
        
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number", value = fg_score,
        title = {'text': "מדד פחד וחמדנות משוקלל (VIX סינתטי)"},
        gauge = {'axis': {'range': [0, 100]}, 'bar': {'color': "white"},
            'steps': [{'range': [0, 25], 'color': "darkred"}, {'range': [25, 45], 'color': "red"},
                {'range': [45, 55], 'color': "gray"}, {'range': [55, 75], 'color': "lightgreen"}, {'range': [75, 100], 'color': "green"}]}
    ))
    fig_gauge.update_layout(height=180, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig_gauge, use_container_width=True)

with col_m1:
    try:
        dxy_val = yf.Ticker('DX-Y.NYB').history(period="1d")['Close'].iloc[-1]
        st.metric("DXY Dollar Index", f"{dxy_val:.2f}", "רוח גבית לסחורות" if dxy_val < 100 else "לחץ מוכר בסחורות", delta_color="inverse")
    except:
        st.metric("DXY Dollar Index", "99.82")
        
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
    
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            cnn_score = int(data['fear_and_greed']['score'])
            cnn_rating = data['fear_and_greed']['rating'].capitalize()
            st.metric("CNN Fear & Greed", f"{cnn_score} / 100", cnn_rating, delta_color="off")
        else:
            st.metric("CNN Fear & Greed", "--", "שגיאת חיבור (חסום)")
    except:
        st.metric("CNN Fear & Greed", "--", "שגיאת רשת")

with col_m3:
    st.markdown("### 📢 משבשי מגמה ומבזקים")
    st.markdown("<p class='blink'>🚨 התראת מאקרו: שים לב לפרסום נתוני נפט/אינפלציה בלוח!</p>", unsafe_allow_html=True)
    st.info("💡 שים לב: פריצה של נר 15 דק' אחרון בגרף מלווה בחצים ירוקים מעידה על כניסת מוסדיים.")

st.markdown("---")

# --- עורק הנתונים המרכזי ---
st.subheader("📊 סריקה רוחבית (מומנטום ונרות יפניים מהפתיחה)")
rows_data = []
for name, ticker in assets.items():
    res = get_asset_metrics(name, ticker)
    if res: rows_data.append(res)

if rows_data:
    cols = st.columns([2, 1.5, 1.5, 1, 1, 1, 3])
    cols[0].markdown("**שם הנכס**")
    cols[1].markdown("**מחיר**")
    cols[2].markdown("**שינוי יומי**")
    cols[3].markdown("**1 דק'**")
    cols[4].markdown("**5 דק'**")
    cols[5].markdown("**15 דק'**")
    cols[6].markdown("**גרף תוך-יומי (נר = 15 דק')**")
    st.markdown("<hr style='margin:4px 0px;'>", unsafe_allow_html=True)
    
    for row in rows_data:
        c = st.columns([2, 1.5, 1.5, 1, 1, 1, 3])
        c[0].write(row['נכס'])
        color_class = "green-text" if row['is_positive'] else "red-text"
        c[1].markdown(f"<span class='{color_class}'>{row['מחיר אחרון']}</span>", unsafe_allow_html=True)
        c[2].markdown(f"<span class='{color_class}'>{row['שינוי יומי']}</span>", unsafe_allow_html=True)
        c[3].markdown(row['מגמת 1m'], unsafe_allow_html=True)
        c[4].markdown(row['מגמת 5m'], unsafe_allow_html=True)
        c[5].markdown(row['מגמת 15m'], unsafe_allow_html=True)
        c[6].plotly_chart(row['גרף'], config={'displayModeBar': False})

st.markdown("---")

# --- רוטציית סקטורים ---
st.subheader("🔄 מפת רוטציית כספים וסקטורים")
sec_data = []
for name, ticker in sectors.items():
    try:
        t_obj = yf.Ticker(ticker)
        i = t_obj.fast_info
        c_p = i.last_price
        p_p = i.previous_close
        chg = ((c_p - p_p) / p_p) * 100
        sec_data.append({'name': name, 'price': f"{c_p:.2f}", 'chg': f"{chg:.2f}%", 'pos': chg >= 0})
    except: pass

if sec_data:
    sec_cols = st.columns(3)
    for idx, s in enumerate(sec_data):
        with sec_cols[idx % 3]:
            txt_color = "green-text" if s['pos'] else "red-text"
            st.markdown(f"**{s['name']}**: {s['price']} | <span class='{txt_color}'>{s['chg']}</span>", unsafe_allow_html=True)

st.markdown("---")

# --- לוח אירועים כלכליים דינמי ---
st.subheader("📅 יומן אירועי קצה - מאקרו בזמן אמת")
today_date = now_dt.date()
tomorrow_date = today_date + timedelta(days=1)

all_events = [
    {"תאריך": today_date, "שעה": "08:30 AM", "עוצמה": "🔴", "אירוע": "CPI מדד המחירים לצרכן", "תקופה": "May", "בפועל": "335.12", "צפי": "335.11", "קודם": "333.02", "is_lower_better": True},
    {"תאריך": today_date, "שעה": "10:30 AM", "עוצמה": "🟠", "אירוע": "EIA Crude Oil Stocks Change", "תקופה": "Jun 6", "בפועל": "-7.228M", "צפי": "-4.0M", "קודם": "-7.974M", "is_lower_better": False},
    {"תאריך": tomorrow_date, "שעה": "08:30 AM", "עוצמה": "🔴", "אירוע": "Core PPI MoM", "תקופה": "May", "בפועל": "--", "צפי": "0.2%", "קודם": "0.1%", "is_lower_better": True},
    {"תאריך": tomorrow_date, "שעה": "02:30 PM", "עוצמה": "🟠", "אירוע": "Initial Jobless Claims", "תקופה": "Weekly", "בפועל": "--", "צפי": "215K", "קודם": "220K", "is_lower_better": True}
]

filtered_events = []
is_quiet_hours = (now_dt.weekday() == 4 and now_dt.hour >= 18) or (now_dt.weekday() == 5 and now_dt.hour < 21)

for ev in all_events:
    if ev["תאריך"] == today_date: day_label = "Today"
    elif ev["תאריך"] == tomorrow_date: day_label = "Tomorrow"
    else: continue 
        
    is_approaching = False
    try:
        time_clean = ev["שעה"].replace(" AM", "").replace(" PM", "")
        ev_hour, ev_min = map(int, time_clean.split(":"))
        if "PM" in ev["שעה"] and ev_hour != 12: ev_hour += 12
        elif "AM" in ev["שעה"] and ev_hour == 12: ev_hour = 0
            
        ev_datetime = now_dt.replace(year=ev["תאריך"].year, month=ev["תאריך"].month, day=ev["תאריך"].day, hour=ev_hour, minute=ev_min, second=0, microsecond=0)
        time_difference = ev_datetime - now_dt
        if ev["תאריך"] == today_date and timedelta(minutes=0) <= time_difference <= timedelta(minutes=30):
            if not is_quiet_hours: is_approaching = True
    except: pass

    filtered_events.append({
        "Date": day_label, "Time": ev["שעה"], "Impact": ev["עוצמה"],
        "Event": f"🚨 {ev['אירוע']}" if is_approaching else ev["אירוע"],
        "For": ev["תקופה"], "Actual": ev["בפועל"], "Expected": ev["צפי"], "Prior": ev["קודם"],
        "התרעה": is_approaching, "is_lower_better": ev["is_lower_better"]
    })

if filtered_events:
    df_cal = pd.DataFrame(filtered_events)
    def style_table(row):
        styles = [''] * len(row)
        idx_actual = row.index.get_loc('Actual')
        if row['התרעה']: styles = ['background-color: rgba(255, 165, 0, 0.2); border-bottom: 1px solid orange;'] * len(row)
        try:
            if row['Actual'] != '--' and row['Expected'] != '--':
                val_actual = float(str(row['Actual']).replace('%', '').replace('M', '').replace('K', '').strip())
                val_expected = float(str(row['Expected']).replace('%', '').replace('M', '').replace('K', '').strip())
                if val_actual != val_expected:
                    is_green = (val_actual < val_expected) if row['is_lower_better'] else (val_actual > val_expected)
                    color = '#00ff00' if is_green else '#ff4b4b'
                    styles[idx_actual] = styles[idx_actual] + f'color: {color}; font-weight: bold;'
        except: pass
        return styles

    st.dataframe(df_cal.style.apply(style_table, axis=1), use_container_width=True, hide_index=True, column_config={"התרעה": None, "is_lower_better": None})
else:
    st.info("אין אירועי מאקרו מתוכננים להיום או למחר.")

st.markdown("---")

# --- מנוע החישוב האמיתי (Data Pipeline לפרק 8 ו-12) ---
st.subheader("🌍 קומת מאקרו: סביבת שוק וזרימת הון")

# הצבת ערכי ברירת מחדל בטוחים (מונע שגיאות חילוץ)
hurst_spy = 0.5
erp_stress = 0.20
tnx_val = 4.0
oil_price = 75.0
term_structure = "ניטרלי"

try:
    hist_market = fetch_macro_data()
    if isinstance(hist_market.columns, pd.MultiIndex):
        hist_market.columns = [f"{col[0]}_{col[1]}" for col in hist_market.columns]
    
    spy_closes = hist_market['Close_SPY'].dropna().values
    vix_val = float(hist_market['Close_^VIX'].dropna().iloc[-1])
    tnx_val = float(hist_market['Close_^TNX'].dropna().iloc[-1])
    oil_price = float(hist_market['Close_CL=F'].dropna().iloc[-1])
    
    hurst_spy = calculate_hurst(spy_closes)
    erp_stress = (vix_val / 100.0) + (tnx_val / 100.0)
    term_structure = "Backwardation" if oil_price > 80 else "Contango"
except Exception as e:
    pass # במקרה של תקלת רשת, המערכת תשתמש בערכי ברירת המחדל שהוגדרו מראש למעלה

current_day = now_dt.day
current_month = now_dt.month

is_tom_active = True if current_day >= 26 or current_day <= 4 else False
is_pre_tom_active = True if 15 <= current_day <= 22 else False 
is_gann_window = True if (20 <= current_day <= 23) and (current_month in [3, 6, 9, 12]) else False

tom_color = "normal" if is_tom_active else "off"

col_mac1, col_mac2, col_mac3, col_mac4 = st.columns(4)
col_mac1.metric("📉 משטר שוק (Hurst)", f"{hurst_spy:.2f}", "מגמתי שורי (H > 0.5)" if hurst_spy > 0.5 else "שוק דשדוש", delta_color="normal" if hurst_spy > 0.5 else "inverse")
col_mac2.metric("🛢️ עקום הנפט (WTI)", f"{oil_price:.2f}$", f"{term_structure} (הגנת לונג)", delta_color="normal" if "Backwardation" in term_structure else "inverse")
col_mac3.metric("🚨 ערוץ לחץ (ERP Stress)", f"{erp_stress:.2f}", "שוק רגוע (Risk-On)" if erp_stress < 0.25 else "שוק בסיכון", delta_color="inverse")

if is_tom_active:
    cal_status = "TOM פעיל"
elif is_pre_tom_active:
    cal_status = "Pre-TOM משיכות"
else:
    cal_status = "שגרה"
col_mac4.metric("📅 סטטוס קלנדרי", cal_status, "חלון מוסדי פעיל" if cal_status != "שגרה" else "", delta_color=tom_color)

st.markdown("<hr style='border: 1px solid #333;'>", unsafe_allow_html=True)
st.subheader("📊 טבלת צלפים: סנכרון רב-ממדי (The 6-Pillar Confluence)")

matrix_sectors = {
    'QQQ': {'name': 'טכנולוגיה', 'long_3x': 'TQQQ', 'short_3x': 'SQQQ', 'base_weight': -10 if erp_stress > 0.25 else 0},
    'SOXX': {'name': 'שבבים (SOXX)', 'long_3x': 'SOXL', 'short_3x': 'SOXS', 'base_weight': -15 if erp_stress > 0.25 else 0},
    'XLF': {'name': 'פיננסים (XLF)', 'long_3x': 'FAS', 'short_3x': 'FAZ', 'base_weight': 10 if tnx_val > 4.2 else 0},
    'IWM': {'name': 'ראסל 2000 (IWM)', 'long_3x': 'TNA', 'short_3x': 'TZA', 'base_weight': -15 if tnx_val > 4.2 else 0},
    'XLE': {'name': 'אנרגיה (XLE)', 'long_3x': 'ERX', 'short_3x': 'ERY', 'base_weight': 15 if "Backwardation" in term_structure else 0},
    'XLRE': {'name': 'נדלן (XLRE)', 'long_3x': 'DRN', 'short_3x': 'DRV', 'base_weight': -20 if tnx_val > 4.2 else 0},
    'XBI': {'name': 'ביוטק (XBI)', 'long_3x': 'LABU', 'short_3x': 'LABD', 'base_weight': 0},
    'XLV': {'name': 'בריאות (XLV)', 'long_3x': 'CURE', 'short_3x': 'RXD', 'base_weight': 10 if erp_stress > 0.25 else 0},
    'XLU': {'name': 'תשתיות (XLU)', 'long_3x': 'UTSL', 'short_3x': 'XLU', 'base_weight': 15 if erp_stress > 0.25 else 0},
    'XLI': {'name': 'תעשייה (XLI)', 'long_3x': 'DUSL', 'short_3x': 'XLI', 'base_weight': -10 if erp_stress > 0.25 else 0},
    'XLY': {'name': 'צריכה מחזורית (XLY)', 'long_3x': 'WANT', 'short_3x': 'XLY', 'base_weight': -10 if erp_stress > 0.25 else 0},
    'XLP': {'name': 'צריכה בסיסית (XLP)', 'long_3x': 'NEED', 'short_3x': 'XLP', 'base_weight': 10 if erp_stress > 0.25 else 0},
    'XLB': {'name': 'חומרי גלם (XLB)', 'long_3x': 'XLB', 'short_3x': 'XLB', 'base_weight': 0},
    'URA': {'name': 'גרעין (URA)', 'long_3x': 'URA', 'short_3x': 'URA', 'base_weight': 10 if "Backwardation" in term_structure else 0},
    'QTUM': {'name': 'קוואנטום (QTUM)', 'long_3x': 'QTUM', 'short_3x': 'QTUM', 'base_weight': -5 if erp_stress > 0.25 else 0},
    'ARKX': {'name': 'חלל (ARKX)', 'long_3x': 'ARKX', 'short_3x': 'ARKX', 'base_weight': -5 if erp_stress > 0.25 else 0}
}

matrix_table_data = []

for ticker, info in matrix_sectors.items():
    try:
        df_sector = fetch_sector_data(ticker)
        if not df_sector.empty:
            if isinstance(df_sector.columns, pd.MultiIndex):
                df_sector.columns = [col[0] for col in df_sector.columns]
                
            df_sector['RSI'] = calculate_rsi(df_sector)
            last_row = df_sector.iloc[-1]
            rsi = float(last_row['RSI'])
            
            base_w = info['base_weight']
            rsi_w = 50.0 - rsi
            
            cal_w = 0
            if is_tom_active: cal_w = 25
            elif is_pre_tom_active: cal_w = -25
            
            confluence_score = base_w + rsi_w + cal_w
            
            hurst_mult_str = "x1.5" if hurst_spy < 0.5 else "x1.0"
            gann_mult_str = "x1.2" if is_gann_window else "x1.0"
            
            if hurst_spy < 0.5: confluence_score *= 1.5 
            if is_gann_window: confluence_score *= 1.2
            
            lead_reason = ""
            is_macro_aligned = False
            
            if ticker in ['XLF'] and tnx_val > 4.2: 
                lead_reason, is_macro_aligned = "TNX זינוק", (confluence_score > 0)
            elif ticker in ['IWM', 'XLRE'] and tnx_val > 4.2: 
                lead_reason, is_macro_aligned = "TNX לחץ", (confluence_score < 0)
            elif ticker in ['XLE', 'URA'] and "Backwardation" in term_structure: 
                lead_reason, is_macro_aligned = "נפט/אנרגיה", (confluence_score > 0)
            elif ticker in ['QQQ', 'SOXX', 'XLY', 'XLI', 'QTUM', 'ARKX'] and erp_stress < 0.25: 
                lead_reason, is_macro_aligned = "Risk-On (שוק)", (confluence_score > 0)
            elif ticker in ['QQQ', 'SOXX', 'XLY', 'XLI', 'QTUM', 'ARKX'] and erp_stress > 0.25: 
                lead_reason, is_macro_aligned = "Risk-Off (לחץ)", (confluence_score < 0)
            elif ticker in ['XLU', 'XLP', 'XLV'] and erp_stress > 0.25:
                lead_reason, is_macro_aligned = "הגנה מוסדית", (confluence_score > 0)
            elif ticker in ['XLU', 'XLP', 'XLV'] and erp_stress < 0.25:
                lead_reason, is_macro_aligned = "נטישת הגנות", (confluence_score < 0)
            else: 
                lead_reason, is_macro_aligned = "זרימה פנימית", False

            sym_rsi = "🔥" if abs(rsi_w) > 10 else "➖"
            sym_hurst = "📉" if hurst_spy < 0.5 else "➖"
            sym_gann = "⏳" if is_gann_window else "➖"
            sym_tom = "📅" if cal_w != 0 else "➖"
            sym_lead = "🧭" if is_macro_aligned else "➖"
            sym_macro = "🌍" if base_w != 0 else "➖"
            
            sym_panel = f"\u200E{sym_rsi} {sym_hurst} {sym_gann} {sym_tom} {sym_lead} {sym_macro}"
            
            if confluence_score > 25:
                status_text = f"🟢 +{confluence_score:.1f} (לונג)"
                trigger_text = f"{info['long_3x']}"
            elif confluence_score < -25:
                status_text = f"🔴 {confluence_score:.1f} (שורט)"
                trigger_text = f"{info['short_3x']}"
            elif confluence_score > 10:
                status_text = f"⚪ +{confluence_score:.1f}"
                trigger_text = "--"
            elif confluence_score < -10:
                status_text = f"⚪ {confluence_score:.1f}"
                trigger_text = "--"
            else:
                status_text = f"⚪ {confluence_score:.1f}"
                trigger_text = "--"

            matrix_table_data.append({
                "פאנל חיווי": sym_panel,
                "הדק\n(ביצוע)": trigger_text,
                "סקטור\n(בסיס)": info['name'],
                "קפיץ\nמשוקלל": status_text,
                "🔥 (RSI)\nמתיחת מיקרו": f"{rsi_w:+.1f}",
                "📉 (Hurst)\nמכפיל הגנה": hurst_mult_str,
                "⏳ (Gann)\nתזמון": gann_mult_str,
                "📅 (TOM)\nעונתיות": f"{cal_w:+d}",
                "🧭 (Lead)\nאיתות": lead_reason,
                "🌍 (Macro)\nמשקל": f"{base_w:+d}",
                "score": confluence_score
            })
    except: pass

if matrix_table_data:
    df_matrix = pd.DataFrame(matrix_table_data)
    df_matrix['abs_score'] = df_matrix['score'].abs()
    df_matrix = df_matrix.sort_values(by='abs_score', ascending=False).drop(columns=['abs_score', 'score'])
    
    df_matrix = df_matrix[[
        'פאנל חיווי',
        'הדק\n(ביצוע)',
        'סקטור\n(בסיס)',
        'קפיץ\nמשוקלל',
        '🔥 (RSI)\nמתיחת מיקרו',
        '📉 (Hurst)\nמכפיל הגנה',
        '⏳ (Gann)\nתזמון',
        '📅 (TOM)\nעונתיות',
        '🧭 (Lead)\nאיתות',
        '🌍 (Macro)\nמשקל'
    ]]

    def style_matrix(row):
        styles = [''] * len(row)
        score_val = str(row['קפיץ\nמשוקלל'])
        sym_panel = str(row['פאנל חיווי'])
        
        active_symbols = len([s for s in sym_panel if s not in ["➖", "\u200E", " "]])
        
        if active_symbols >= 3:
            if "לונג" in score_val: 
                return ['background-color: rgba(0, 255, 0, 0.1); border-bottom: 1px solid #00ff00;'] * len(row)
            elif "שורט" in score_val: 
                return ['background-color: rgba(255, 0, 0, 0.1); border-bottom: 1px solid #ff0000;'] * len(row)
        return styles

    st.dataframe(df_matrix.style.apply(style_matrix, axis=1), use_container_width=True, hide_index=True)

st.markdown("---")

# ==========================================
# --- תוסף זירת צלפים מוסדית PRO (Volume Profile + Camarilla) ---
# ==========================================
st.subheader("🎯 זירת צלפים PRO (Liquidity, Order Blocks & POC)")

@st.cache_data(ttl=120)  # רענון כל שתי דקות
def get_pro_reversal_targets():
    pairs = [('SOXX', 'SOXS'), ('QQQ', 'SQQQ')]
    results = []
    
    for base, lev in pairs:
        try:
            daily = yf.download(base, period="5d", interval="1d", progress=False)
            if isinstance(daily.columns, pd.MultiIndex):
                daily.columns = [col[0] for col in daily.columns]
            yest = daily.iloc[-2] if len(daily) > 1 else daily.iloc[0]
            H, L, C = float(yest['High']), float(yest['Low']), float(yest['Close'])
            R4 = C + (H - L) * 1.1 / 2
            
            intra = yf.download(base, period="5d", interval="5m", progress=False)
            if isinstance(intra.columns, pd.MultiIndex):
                intra.columns = [col[0] for col in intra.columns]
            prices, vols = intra['Close'], intra['Volume']
            
            bins = np.linspace(prices.min(), prices.max(), 50)
            digitized = np.digitize(prices, bins)
            vol_profile = np.zeros(len(bins)-1)
            bin_centers = (bins[:-1] + bins[1:]) / 2
            
            for i in range(1, len(bins)):
                vol_profile[i-1] = vols[digitized == i].sum()
                
            poc_idx = np.argmax(vol_profile)
            poc_price = bin_centers[poc_idx]
            
            va_volume = vol_profile[poc_idx]
            target_volume = vol_profile.sum() * 0.70
            upper_idx, lower_idx = poc_idx, poc_idx
            
            while va_volume < target_volume:
                can_up = upper_idx < len(vol_profile) - 1
                can_down = lower_idx > 0
                if not can_up and not can_down: break
                
                vol_up = vol_profile[upper_idx + 1] if can_up else 0
                vol_down = vol_profile[lower_idx - 1] if can_down else 0
                
                if vol_up >= vol_down and can_up:
                    upper_idx += 1
                    va_volume += vol_up
                elif can_down:
                    lower_idx -= 1
                    va_volume += vol_down
                else: break
                    
            VAH = bin_centers[upper_idx]
            VAL = bin_centers[lower_idx]
            
            curr_base = float(yf.Ticker(base).fast_info.last_price)
            curr_lev = float(yf.Ticker(lev).fast_info.last_price)
            
            def get_target(res):
                dist = (res - curr_base) / curr_base
                return dist, curr_lev * (1 + (dist * -3))
                
            dist_vah, lev_vah = get_target(VAH)
            dist_poc, lev_poc = get_target(poc_price)
            
            state_color = "white"
            status_text = "ממתין לתנועה"
            
            if curr_base > VAH:
                state_color = "#ff4b4b" 
                status_text = "⚠️ המחיר מעל לאזור הערך (FOMO / נפרץ)"
            elif curr_base < VAL:
                state_color = "#ff4b4b" 
                status_text = "⚠️ המחיר מתחת לאזור הערך (נפרץ מטה)"
            else:
                if abs(dist_vah) <= 0.006: 
                    state_color = "#00ff00" 
                    status_text = "✅ איתות שורט: המחיר נבלם בתקרת ה-VAH"
                elif abs(dist_poc) <= 0.005:
                    state_color = "#ffcc00" 
                    status_text = "⚖️ המחיר על ליבת ה-POC (מגנט מסחר)"
                else:
                    state_color = "#ffffff"
                    status_text = "המחיר בתוך אזור הערך (תנועת דשדוש)"
            
            results.append({
                'lev': lev, 'base': base, 'curr_lev': curr_lev, 'curr_base': curr_base,
                'poc': poc_price, 'vah': VAH, 'val': VAL, 'r4': R4,
                'lev_poc': lev_poc, 'lev_vah': lev_vah,
                'dist_vah': dist_vah, 'color': state_color, 'status': status_text
            })
        except Exception as e:
            continue
    return results

pro_data = get_pro_reversal_targets()

if pro_data:
    cols_pro = st.columns(len(pro_data))
    for idx, data in enumerate(pro_data):
        with cols_pro[idx]:
            bc = data['color'] if data['color'] != 'white' else '#444'
            st.markdown(f"<div style='border:2px solid {bc}; padding:10px; border-radius:5px;'>", unsafe_allow_html=True)
            st.markdown(f"#### {data['lev']} | נוכחי: **{data['curr_lev']:.2f}$**", unsafe_allow_html=True)
            
            st.markdown(f"<span style='color:#00ff00; font-size:15px;'>🎯 יעד כניסה 1 (VAH): <b>[{data['lev_vah']:.2f}$]</b></span><br>", unsafe_allow_html=True)
            st.markdown(f"<span style='color:#00ffff; font-size:15px;'>🎯 יעד כניסה 2 (POC): <b>[{data['lev_poc']:.2f}$]</b></span>", unsafe_allow_html=True)
            
            st.markdown("<hr style='margin: 8px 0; border-color: #555;'>", unsafe_allow_html=True)
            st.markdown(f"<small><b>נתוני {data['base']} מוסדיים (נוכחי: {data['curr_base']:.2f}$):</b></small><br>", unsafe_allow_html=True)
            st.markdown(f"<small>🔼 תקרת אזור (VAH): {data['vah']:.2f}$</small><br>", unsafe_allow_html=True)
            st.markdown(f"<b><small>🎯 ליבת כוח (POC): {data['poc']:.2f}$</small></b><br>", unsafe_allow_html=True)
            st.markdown(f"<small>🔽 רצפת אזור (VAL): {data['val']:.2f}$</small>", unsafe_allow_html=True)
            
            st.markdown(f"<br><span style='color:{data['color']}; font-weight:bold;'>{data['status']}</span>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("ממתין לנתוני מסחר לחילוץ רמות PRO...")

# ==========================================
# פקודות רענון סיום הקובץ
# ==========================================
time.sleep(15)
st.rerun()
