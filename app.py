import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta
import requests

# --- הגדרות עמוד ועיצוב מוסדי ---
st.set_page_config(page_title="Matrix OS V6", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    .reportview-container { background: #0e1117; }
    .green-text { color: #00ff00; font-weight: bold; font-size: 16px; }
    .red-text { color: #ff0000; font-weight: bold; font-size: 16px; }
    .blink { animation: blinker 1.5s linear infinite; color: #ffcc00; font-weight: bold; }
    @keyframes blinker { 50% { opacity: 0; } }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Matrix OS - מערכת פיקוד מוסדית (גרסת נרות יפניים)")
st.write(f"🔄 מתעדכן חי (כל 15 שניות) | זמן מערכת: {datetime.now().strftime('%H:%M:%S')}")
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
        
        # שאיבת מחיר סגירה רשמי מאתמול להתאמה מושלמת מול הכלים החיצוניים
        info = ticker_obj.fast_info
        prev_close_daily = info.previous_close
        current_price = info.last_price
        
        # גיבוי במקרה שהשוק סגור וה-fast_info ריק
        if pd.isna(current_price) or current_price == 0:
            df_fallback = ticker_obj.history(period="1d", interval="1m")
            if df_fallback.empty: return None
            current_price = df_fallback['Close'].iloc[-1]
            
        daily_change = ((current_price - prev_close_daily) / prev_close_daily) * 100
        
        # חלונות זמן לרזולוציה של דקות
        df_1m = ticker_obj.history(period="1d", interval="1m")
        if df_1m.empty or len(df_1m) < 20:
            df_1m = ticker_obj.history(period="5d", interval="1m")
            
        p_1m = df_1m['Close'].iloc[-2] if len(df_1m) >= 2 else current_price
        p_5m = df_1m['Close'].iloc[-6] if len(df_1m) >= 6 else current_price
        p_15m = df_1m['Close'].iloc[-16] if len(df_1m) >= 16 else current_price
        
        # אלגוריתם צביעת חצים מוחלט (ירוק לעלייה, אדום לירידה)
        def get_arrow_html(curr, past):
            return "<span style='color: #00ff00;'>🔼</span>" if curr >= past else "<span style='color: #ff0000;'>🔽</span>"
            
        arrow_1m = get_arrow_html(current_price, p_1m)
        arrow_5m = get_arrow_html(current_price, p_5m)
        arrow_15m = get_arrow_html(current_price, p_15m)
        
        # בניית גרף נרות יפניים מותאם אישית (15 דקות לנר) מהפתיחה
        df_15m = ticker_obj.history(period="1d", interval="15m")
        if df_15m.empty: df_15m = df_1m # גיבוי
        
        fig = go.Figure(data=[go.Candlestick(
            x=df_15m.index,
            open=df_15m['Open'], high=df_15m['High'],
            low=df_15m['Low'], close=df_15m['Close'],
            increasing_line_color='#00ff00', increasing_fillcolor='#00ff00',
            decreasing_line_color='#ff0000', decreasing_fillcolor='#ff0000'
        )])
        
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0), height=60, width=180,
            xaxis_rangeslider_visible=False, xaxis=dict(visible=False), yaxis=dict(visible=False),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
        )
        
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
        mode = "gauge+number",
        value = fg_score,
        title = {'text': "מדד פחד וחמדנות משוקלל (VIX סינתטי)"},
        gauge = {
            'axis': {'range': [0, 100]},
            'bar': {'color': "white"},
            'steps': [
                {'range': [0, 25], 'color': "darkred"},
                {'range': [25, 45], 'color': "red"},
                {'range': [45, 55], 'color': "gray"},
                {'range': [55, 75], 'color': "lightgreen"},
                {'range': [75, 100], 'color': "green"}]
        }
    ))
    # תיקון החיתוך: הגדלנו את t ל-60
    fig_gauge.update_layout(height=180, margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig_gauge, use_container_width=True)

with col_m1:
    # נתון 1: DXY
    try:
        dxy_val = yf.Ticker('DX-Y.NYB').history(period="1d")['Close'].iloc[-1]
        st.metric("DXY Dollar Index", f"{dxy_val:.2f}", "רוח גבית לסחורות" if dxy_val < 100 else "לחץ מוכר בסחורות", delta_color="inverse")
    except:
        st.metric("DXY Dollar Index", "99.82")
        
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
    
    # נתון 2: CNN Fear & Greed (חי)
    import requests
    try:
        url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            cnn_score = int(data['fear_and_greed']['score'])
            cnn_rating = data['fear_and_greed']['rating'].capitalize()
            st.metric("CNN Fear & Greed", f"{cnn_score} / 100", cnn_rating, delta_color="off")
        else:
            st.metric("CNN Fear & Greed", "--", "שגיאת חיבור")
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
    except:
        pass

if sec_data:
    sec_cols = st.columns(3)
    for idx, s in enumerate(sec_data):
        with sec_cols[idx % 3]:
            txt_color = "green-text" if s['pos'] else "red-text"
            st.markdown(f"**{s['name']}**: {s['price']} | <span class='{txt_color}'>{s['chg']}</span>", unsafe_allow_html=True)

st.markdown("---")

# --- לוח אירועים כלכליים דינמי ---
st.subheader("📅 יומן אירועי קצה - מאקרו בזמן אמת")

# 1. ניהול תאריכים דינמי (מתוקן: שימוש נכון במחלקת datetime שייבאנו)
now_dt = datetime.now()
today_date = now_dt.date()
tomorrow_date = today_date + timedelta(days=1)
after_tomorrow_date = today_date + timedelta(days=2)

# 2. מאגר נתונים מרכזי
all_events = [
    {"תאריך": today_date, "שעה": "08:30 AM", "אירוע": "CPI (מדד המחירים לצרכן)", "תקופה": "May", "צפי": "335.11", "קודם": "333.02", "בפועל": "335.12"},
    {"תאריך": today_date, "שעה": "10:30 AM", "אירוע": "EIA Crude Oil Stocks (מלאי נפט)", "תקופה": "Jun 6", "צפי": "-4.0M", "קודם": "-7.974M", "בפועל": "-7.228M"},
    {"תאריך": tomorrow_date, "שעה": "08:30 AM", "אירוע": "Core PPI MoM", "תקופה": "May", "צפי": "0.2%", "קודם": "0.1%", "בפועל": "--"},
    {"תאריך": tomorrow_date, "שעה": "02:30 PM", "אירוע": "Initial Jobless Claims", "תקופה": "Weekly", "צפי": "215K", "קודם": "220K", "בפועל": "--"},
    {"תאריך": after_tomorrow_date, "שעה": "10:00 AM", "אירוע": "אירוע מחרתיים (יוצג רק מחר בחצות)", "תקופה": "Jun", "צפי": "--", "קודם": "--", "בפועל": "--"}
]

# 3. מנגנון סינון והתרעות תוך-יומיות
filtered_events = []

# הגדרת חלון זמן שקט להתרעות חזותיות למניעת הבהובים (משישי בערב עד מוצ"ש)
is_quiet_hours = (now_dt.weekday() == 4 and now_dt.hour >= 18) or (now_dt.weekday() == 5 and now_dt.hour < 21)

for ev in all_events:
    if ev["תאריך"] == today_date:
        day_label = "היום"
    elif ev["תאריך"] == tomorrow_date:
        day_label = "מחר"
    else:
        continue # מתעלם אוטומטית מכל מה שאינו היום או מחר
        
    # בדיקה האם שעת האירוע מתקרבת (טווח של 30 דקות לפני המועד)
    is_approaching = False
    try:
        # המרה של פורמט השעה לבדיקה מתמטית
        time_clean = ev["שעה"].replace(" AM", "").replace(" PM", "")
        ev_hour, ev_min = map(int, time_clean.split(":"))
        if "PM" in ev["שעה"] and ev_hour != 12:
            ev_hour += 12
        elif "AM" in ev["שעה"] and ev_hour == 12:
            ev_hour = 0
            
        # מתוקן: יצירת אובייקט זמן מדויק להשוואה מבלי לקרוא לפונקציות חסרות
        ev_datetime = now_dt.replace(
            year=ev["תאריך"].year, 
            month=ev["תאריך"].month, 
            day=ev["תאריך"].day, 
            hour=ev_hour, 
            minute=ev_min, 
            second=0, 
            microsecond=0
        )
        time_difference = ev_datetime - now_dt
        
        # אם האירוע מתוכנן להיום, טרם עבר, ונותרו פחות מ-30 דקות אליו
        # מתוקן: קריאה ישירה ל-timedelta
        if ev["תאריך"] == today_date and timedelta(minutes=0) <= time_difference <= timedelta(minutes=30):
            if not is_quiet_hours:  # הפעלת ההתראה רק מחוץ לשעות המנוחה
                is_approaching = True
    except:
        pass

    # בניית השורה המעובדת לטבלה
    filtered_events.append({
        "יום": day_label,
        "שעה": ev["שעה"],
        "אירוע": f"🚨 {ev['אירוע']} - מתקרב!" if is_approaching else ev["אירוע"],
        "צפי": ev["צפי"],
        "קודם": ev["קודם"],
        "בפועל": ev["בפועל"],
        "התרעה": is_approaching  # עמודת עזר מוסתרת לעיצוב
    })

# 4. תצוגת הטבלה ועיצוב מותנה
if filtered_events:
    df_cal = pd.DataFrame(filtered_events)
    
    # פונקציה לצביעת שורות של אירועים קרובים בצהוב/כתום בולט
    def style_approaching_events(row):
        if row['התרעה']:
            return ['background-color: rgba(255, 165, 0, 0.3); color: #ffffff; font-weight: bold; border: 1px solid orange;'] * len(row)
        return [''] * len(row)

    # הסרת עמודת העזר הפיקטיבית לפני ההקרנה על המסך
    display_df = df_cal.drop(columns=["התרעה"])
    
    st.dataframe(
        display_df.style.apply(style_approaching_events, axis=1),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("אין אירועי מאקרו מתוכננים להיום או למחר.")

# מנגנון רענון כל 15 שניות
time.sleep(15)
st.rerun()
