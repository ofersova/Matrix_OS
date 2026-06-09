import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
from datetime import datetime

# --- הגדרות עמוד ועיצוב מוסדי ---
st.set_page_config(page_title="Matrix OS V5.1", layout="wide", page_icon="⚡")

# הגדרת סגנונות צבע קבועים ומניעת הבהובים מיותרים
st.markdown("""
    <style>
    .reportview-container { background: #0e1117; }
    .green-text { color: #00ff00; font-weight: bold; font-size: 16px; }
    .red-text { color: #ff0000; font-weight: bold; font-size: 16px; }
    .blink { animation: blinker 1.5s linear infinite; color: #ffcc00; font-weight: bold; }
    @keyframes blinker { 50% { opacity: 0; } }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Matrix OS - מערכת פיקוד ותזמון תוך-יומי")
st.write(f"🔄 עדכון אוטומטי פעיל (כל 15 שניות) | זמן מערכת: {datetime.now().strftime('%H:%M:%S')}")
st.markdown("---")

# --- רשימות נכסים ומעקב ---
assets = {
    'S&P 500 (ES)': '^GSPC', 'Nasdaq 100 (NQ)': '^NDX', 'VIX Index': '^VIX',
    'Crude Oil': 'CL=F', 'Silver': 'SI=F', 'Platinum': 'PL=F', 
    'Wheat': 'ZW=F', 'Natural Gas': 'NG=F',
    'AST SpaceMobile': 'ASTS', 'Nano Nuclear': 'NNE', 'Iris Energy': 'IREN'
}

sectors = {
    'Tech (XLK)': 'XLK', 'Energy (XLE)': 'XLE', 'Financials (XLF)': 'XLF', 
    'Utilities (XLU)': 'XLU', 'Materials (XLB)': 'XLB', 'Staples (XLP)': 'XLP', 
    'Real Estate (XLRE)': 'XLRE', 'Nuclear (URA)': 'URA', 'Quantum (QTUM)': 'QTUM'
}

# --- מנוע חישוב מגמות תוך-יומיות וגרפיקה ---
def get_asset_metrics(name, ticker):
    try:
        # שליפת נתונים ברזולוציית דקה למגמה תוך-יומית
        df = yf.Ticker(ticker).history(period="1d", interval="1m")
        if df.empty or len(df) < 20:
            df = yf.Ticker(ticker).history(period="5d", interval="5m")
            
        if df.empty: return None
        
        current_price = df['Close'].iloc[-1]
        
        # חישוב אחוז שינוי יומי מדויק לעד 2 ספרות
        hist_daily = yf.Ticker(ticker).history(period="2d")
        daily_change = 0.0
        if len(hist_daily) >= 2:
            prev_close_daily = hist_daily['Close'].iloc[-2]
            daily_change = ((current_price - prev_close_daily) / prev_close_daily) * 100
            
        # מומנטום של חלונות זמן (דקה, 5 דקות, 15 דקות)
        p_1m = df['Close'].iloc[-2] if len(df) >= 2 else current_price
        p_5m = df['Close'].iloc[-6] if len(df) >= 6 else current_price
        p_15m = df['Close'].iloc[-16] if len(df) >= 16 else current_price
        
        arrow_1m = "🔼" if current_price >= p_1m else "🔽"
        arrow_5m = "🔼" if current_price >= p_5m else "🔽"
        arrow_15m = "🔼" if current_price >= p_15m else "🔽"
        
        # בניית קו מגמה גרפי נקי (Sparkline) ללא רעש ויזואלי
        fig = px.line(df.tail(45), x=df.tail(45).index, y='Close')
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0), height=35, width=110,
            xaxis=dict(visible=False), yaxis=dict(visible=False),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
        )
        fig.update_traces(line_color='#00ff00' if current_price >= df['Close'].iloc[0] else '#ff0000', line_width=1.5)
        
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
    fig_gauge.update_layout(height=160, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_gauge, use_container_width=True)

with col_m1:
    try:
        dxy_val = yf.Ticker('DX-Y.NYB').history(period="1d")['Close'].iloc[-1]
        st.metric("DXY Dollar Index", f"{dxy_val:.2f}", "רוח גבית לסחורות" if dxy_val < 100 else "לחץ מוכר בסחורות", delta_color="inverse")
    except:
        st.metric("DXY Dollar Index", "99.82")

with col_m3:
    st.markdown("### 📢 משבשי מגמה ומבזקים")
    st.markdown("<p class='blink'>🚨 אירוע קרוב: דוח מדד המחירים לצרכן (CPI) ישנה את משטר השוק!</p>", unsafe_allow_html=True)
    st.info("💡 חוק היפוך מומנטום: אם השוק ירד לקראת ההודעה והנתון יצא חיובי -> חפש פריצת לונג ב-TQQQ.")

st.markdown("---")

# --- עורק הנתונים המרכזי ---
st.subheader("📊 סריקה רוחבית תוך-יומית (מאקרו ומיקרו)")

rows_data = []
for name, ticker in assets.items():
    res = get_asset_metrics(name, ticker)
    if res: rows_data.append(res)

if rows_data:
    cols = st.columns([2.5, 1.5, 1.5, 1, 1, 1, 2.5])
    cols[0].markdown("**שם הנכס**")
    cols[1].markdown("**מחיר**")
    cols[2].markdown("**שינוי יומי**")
    cols[3].markdown("**1 דק'**")
    cols[4].markdown("**5 דק'**")
    cols[5].markdown("**15 דק'**")
    cols[6].markdown("**מגמה בשעות האחרונות**")
    st.markdown("<hr style='margin:4px 0px;'>", unsafe_allow_html=True)
    
    for row in rows_data:
        c = st.columns([2.5, 1.5, 1.5, 1, 1, 1, 2.5])
        c[0].write(row['נכס'])
        
        # התאמת צבעים מלאה ומניעת אפסים מיותרים
        color_class = "green-text" if row['is_positive'] else "red-text"
        
        c[1].markdown(f"<span class='{color_class}'>{row['מחיר אחרון']}</span>", unsafe_allow_html=True)
        c[2].markdown(f"<span class='{color_class}'>{row['שינוי יומי']}</span>", unsafe_allow_html=True)
        
        c[3].markdown(f"<span class='{color_class}'>{row['מגמת 1m']}</span>", unsafe_allow_html=True)
        c[4].markdown(f"<span class='{color_class}'>{row['מגמת 5m']}</span>", unsafe_allow_html=True)
        c[5].markdown(f"<span class='{color_class}'>{row['מגמת 15m']}</span>", unsafe_allow_html=True)
        c[6].plotly_chart(row['גרף'], config={'displayModeBar': False})

st.markdown("---")

# --- רוטציית סקטורים חסינת תקלות ---
st.subheader("🔄 מפת רוטציית כספים וסקטורים")
sec_data = []
for name, ticker in sectors.items():
    try:
        hist = yf.Ticker(ticker).history(period="2d")
        if len(hist) >= 2:
            c_p = hist['Close'].iloc[-1]
            p_p = hist['Close'].iloc[-2]
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

# --- לוח אירועים כלכליים ---
st.subheader("📅 לוח זמנים לפרסום נתונים משבשי מגמה")
cal_data = [
    {"שעה": "08:30 AM", "אירוע": "Balance of Trade (מאזן מסחרי)", "צפי": "-56.1B", "בפועל": "-55.9B", "עוצמה": "🟡 בינונית"},
    {"שעה": "10:00 AM", "אירוע": "Existing Home Sales (מכירות בתים)", "צפי": "4.07M", "בפועל": "4.17M", "עוצמה": "🟢 חיובית"},
    {"שעה": "04:30 PM", "אירוע": "API Crude Oil Stock Change (מלאי נפט)", "צפי": "-3.4M", "בפועל": "--", "עוצמה": "🔴 קריטית ל-CL"},
]
st.table(pd.DataFrame(cal_data))

# מנגנון שינה והרצה מחדש ברקע (15 שניות)
time.sleep(15)
st.rerun()
