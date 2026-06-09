import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

# --- הגדרות עמוד ועיצוב מוסדי ---
st.set_page_config(page_title="Matrix OS V5", layout="wide", page_icon="⚡")

# סגנון CSS להעלמת אפסים מיותרים, הבהובים וצבעים מותאמים
st.markdown("""
    <style>
    .reportview-container { background: #0e1117; }
    .green-text { color: #00ff00; font-weight: bold; }
    .red-text { color: #ff0000; font-weight: bold; }
    .blink { animation: blinker 1.5s linear infinite; color: #ffcc00; font-weight: bold; }
    @keyframes blinker { 50% { opacity: 0; } }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Matrix OS - מערכת פיקוד ותזמון תוך-יומי (V5)")
st.write(f"🔄 עדכון אוטומטי פעיל (כל 15 שניות) | זמן שרת: {datetime.now().strftime('%H:%M:%S')}")
st.markdown("---")

# --- רשימות נכסים ומעקב ---
assets = {
    'S&P 500 (ES)': '^GSPC', 'Nasdaq 100 (NQ)': '^NDX', 'VIX Index': '^VIX',
    'Crude Oil': 'CL=F', 'Silver': 'SI=F', 'Platinum': 'PL=F', 
    'Wheat': 'ZW=F', 'Natural Gas': 'NG=F',
    'AST SpaceMobile': 'ASTS', 'Nano Nuclear': 'NNE', 'Iris Energy': 'IREN'
}

# --- מנוע חישוב מגמות תוך-יומיות וגרפיקה ---
def get_asset_metrics(name, ticker):
    try:
        # שליבת נתונים ברזולוציית דקה ל-1 הדקות, 5 הדקות ו-15 הדקות האחרונות
        df = yf.Ticker(ticker).history(period="1d", interval="1m")
        if df.empty or len(df) < 20:
            df = yf.Ticker(ticker).history(period="5d", interval="5m") # פתרון גיבוי מחוץ לשעות המסחר
            
        if df.empty: return None
        
        current_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2]
        
        # חישוב אחוז שינוי יומי מהסגירה הקודמת
        hist_daily = yf.Ticker(ticker).history(period="2d")
        daily_change = 0.0
        if len(hist_daily) >= 2:
            prev_close_daily = hist_daily['Close'].iloc[-2]
            daily_change = ((current_price - prev_close_daily) / prev_close_daily) * 100
            
        # חישוב שינויי מגמה מבוססי זמן (דקה, 5 דקות, 15 דקות)
        p_1m = df['Close'].iloc[-2] if len(df) >= 2 else current_price
        p_5m = df['Close'].iloc[-6] if len(df) >= 6 else current_price
        p_15m = df['Close'].iloc[-16] if len(df) >= 16 else current_price
        
        arrow_1m = "🟢 🔼" if current_price >= p_1m else "🔴 🔽"
        arrow_5m = "🟢 🔼" if current_price >= p_5m else "🔴 🔽"
        arrow_15m = "🟢 🔼" if current_price >= p_15m else "🔴 🔽"
        
        # בניית Sparkline (מגמה של השעות האחרונות)
        fig = px.line(df.tail(60), x=df.tail(60).index, y='Close', labels={'Close':''})
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0), height=40, width=120,
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
            'raw_change': daily_change
        }
    except Exception as e:
        return None

# --- פקודות מאקרו עליונות ולוח אירועים ---
col_m1, col_m2, col_m3 = st.columns([1, 2, 1])

with col_m2:
    # מנוע סינתטי למדד Fear & Greed חסין חסימות אינטרנט
    try:
        vix_df = yf.Ticker('^VIX').history(period="1d")
        vix_now = vix_df['Close'].iloc[-1] if not vix_df.empty else 20
        fg_score = 100 - (vix_now * 2.5) # ככל שהוויקס עולה הפחד משתלט
        fg_score = max(min(fg_score, 100), 0)
    except:
        fg_score = 50
        
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = fg_score,
        title = {'text': "מדד Fear & Greed (זמן אמת מאקרו)"},
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
    fig_gauge.update_layout(height=180, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_gauge, use_container_width=True)

with col_m1:
    try:
        dxy_val = yf.Ticker('DX-Y.NYB').history(period="1d")['Close'].iloc[-1]
        st.metric("DXY Dollar Index", f"{dxy_val:.2f}", "רוח גבית לסחורות" if dxy_val < 100 else "לחץ על סחורות", delta_color="inverse")
    except:
        st.metric("DXY Dollar Index", "99.82")

with col_m3:
    st.markdown("### 📢 חלון מבזקים ומשבשי מגמה")
    st.markdown("<p class='blink'>🚨 התרעת אירוע מאקרו קרוב: דוח אינפלציה CPI בעוד שעה!</p>", unsafe_allow_html=True)
    st.info("💡 כלל המטריקס: אם המגמה עד הפרסום הייתה יורדת והדוח חיובי -> היפוך מהיר ל-LONG ממונף!")

st.markdown("---")

# --- לוח המחוונים המרכזי (טבלה חיה עם גרפים וחצים) ---
st.subheader("📊 עורק הנתונים המרכזי - סריקה רוחבית")

rows_data = []
for name, ticker in assets.items():
    res = get_asset_metrics(name, ticker)
    if res:
        rows_data.append(res)

if rows_data:
    # הצגת הטבלה בצורה מעוצבת שורה אחר שורה
    cols = st.columns([2, 1.5, 1.5, 1, 1, 1, 2])
    cols[0].bold("שם הנכס")
    cols[1].bold("מחיר אחרון")
    cols[2].bold("שינוי יומי")
    cols[3].bold("1 דק'")
    cols[4].bold("5 דק'")
    cols[5].bold("15 דק'")
    cols[6].bold("מגמת שעות אחרונות")
    st.markdown("<hr style='margin:5px 0px;'>", unsafe_allow_html=True)
    
    for row in rows_data:
        c = st.columns([2, 1.5, 1.5, 1, 1, 1, 2])
        c[0].write(row['נכס'])
        
        # עיצוב מותנה למחיר ולשינוי היומי
        if '-' in row['שינוי יומי'] or '🔽' in row['מגמת 1m']:
            c[1].markdown(f"<span class='red-text'>{row['מחיר אחרון']}</span>", unsafe_allow_html=True)
            c[2].markdown(f"<span class='red-text'>{row['שינוי יומי']}</span>", unsafe_allow_html=True)
        else:
            c[1].markdown(f"<span class='green-text'>{row['מחיר אחרון']}</span>", unsafe_allow_html=True)
            c[2].markdown(f"<span class='green-text'>{row['שינוי יומי']}</span>", unsafe_allow_html=True)
            
        c[3].write(row['מגמת 1m'])
        c[4].write(row['מגמת 5m'])
        c[5].write(row['מגמת 15m'])
        c[6].plotly_chart(row['גרף'], config={'displayModeBar': False})

st.markdown("---")

# --- שכבת יומן אירועים כלכליים מותאם אישית למסחר יומי ---
st.subheader("📅 לוח דוחות ואירועי קצה (מסחר יומי)")
cal_data = [
    {"שעה": "08:30 AM", "אירוע": "Balance of Trade (מאזן מסחרי)", "צפי": "-56.1B", "בפועל": "-55.9B", "עוצמת השפעה": "🟡 בינונית"},
    {"שעה": "10:00 AM", "אירוע": "Existing Home Sales (מכירות בתים)", "צפי": "4.07M", "בפועל": "4.17M", "עוצמת השפעה": "🟢 חיובית לשוק"},
    {"שעה": "04:30 PM", "אירוע": "API Crude Oil Stock Change (מלאי נפט)", "צפי": "-3.4M", "בפועל": "--", "עוצמת השפעה": "🔴 קריטית ל-CL"},
]
st.table(pd.DataFrame(cal_data))

# מנגנון הרענון האוטומטי ברקע (עובד כמו שעון)
time.sleep(15)
st.rerun()
