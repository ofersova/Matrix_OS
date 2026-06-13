import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta
import requests

# --- הגדרות עמוד ---
st.set_page_config(page_title="Matrix OS - Attack Board", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    .reportview-container { background: #0e1117; }
    
    /* עיצוב לאזורי לונג ושורט */
    .long-zone {
        border: 3px solid #00ff00;
        border-radius: 10px;
        padding: 15px;
        background-color: rgba(0, 255, 0, 0.05);
        margin-bottom: 20px;
    }
    .short-zone {
        border: 3px solid #ff0000;
        border-radius: 10px;
        padding: 15px;
        background-color: rgba(255, 0, 0, 0.05);
        margin-bottom: 20px;
    }
    
    /* עיצוב כרטיסיות מידע */
    .card {
        background-color: #1e1e1e;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .card-title { font-size: 14px; color: #888; margin-bottom: 5px; }
    .card-value { font-size: 24px; font-weight: bold; margin-bottom: 5px; }
    .card-target { font-size: 18px; color: #00ff00; font-weight: bold; margin-bottom: 5px; }
    .card-target-short { font-size: 18px; color: #ff0000; font-weight: bold; margin-bottom: 5px; }
    .card-percent { font-size: 16px; color: #aaa; }
    
    /* חצים מיוחדים */
    .arrow-prepare {
        font-size: 30px;
        background: -webkit-linear-gradient(bottom, red, green);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
    }
    .arrow-long { font-size: 30px; color: #00ff00; font-weight: bold; }
    .arrow-short { font-size: 30px; color: #ff0000; font-weight: bold; }
    
    .macro-table th { text-align: center !important; font-size: 18px !important; border-bottom: 2px solid #555 !important; }
    .macro-table td { text-align: center !important; font-size: 24px !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- נתוני בסיס סטטיים ---
sector_perf_history = {
    'XLK': {'qtr': 27.13, 'mo': 2.52},
    'XLF': {'qtr': 11.46, 'mo': 4.60},
    'XLU': {'qtr': -4.30, 'mo': -1.52},
    'XLE': {'qtr': 0.67, 'mo': -1.58},
    'XLRE': {'qtr': 6.94, 'mo': 2.46},
    'XLV': {'qtr': 3.22, 'mo': 3.11},
    'XLI': {'qtr': 9.17, 'mo': 1.64},
    'XLY': {'qtr': 4.66, 'mo': -4.19},
    'XLP': {'qtr': 0.32, 'mo': -0.77},
    'XLB': {'qtr': 4.24, 'mo': -4.96}
}

lev_pairs = {
    'טכנולוגיה': {'base': 'XLK', 'long': 'TQQQ', 'short': 'SQQQ'},
    'שבבים': {'base': 'SOXX', 'long': 'SOXL', 'short': 'SOXS'},
    'פיננסים': {'base': 'XLF', 'long': 'FAS', 'short': 'FAZ'},
    'אנרגיה': {'base': 'XLE', 'long': 'ERX', 'short': 'ERY'},
    'בריאות': {'base': 'XLV', 'long': 'CURE', 'short': 'RXD'},
    'תעשייה': {'base': 'XLI', 'long': 'DUSL', 'short': 'XLI'},
}

# --- פונקציות עזר ---
@st.cache_data(ttl=15)
def fetch_data(tickers, period='5d', interval='5m'):
    return yf.download(tickers, period=period, interval=interval, auto_adjust=True, progress=False)

def calc_volume_profile(prices, vols):
    bins = np.linspace(prices.min(), prices.max(), 50)
    digitized = np.digitize(prices, bins)
    vol_profile = np.zeros(len(bins)-1)
    bin_centers = (bins[:-1] + bins[1:]) / 2
    for i in range(1, len(bins)): vol_profile[i-1] = vols[digitized == i].sum()
    poc_idx = np.argmax(vol_profile)
    va_volume = vol_profile[poc_idx]
    target_volume = vol_profile.sum() * 0.70
    upper_idx, lower_idx = poc_idx, poc_idx
    while va_volume < target_volume:
        can_up, can_down = upper_idx < len(vol_profile)-1, lower_idx > 0
        if not can_up and not can_down: break
        if can_up and (not can_down or vol_profile[upper_idx+1] >= vol_profile[lower_idx-1]):
            upper_idx += 1; va_volume += vol_profile[upper_idx]
        else:
            lower_idx -= 1; va_volume += vol_profile[lower_idx]
    return bin_centers[poc_idx], bin_centers[upper_idx], bin_centers[lower_idx]

def determine_state(price, prev_price, poc, vah, val):
    # לוגיקת מצבים: פריצה מובהקת מול הכנה/איסוף
    trend_up = price > prev_price
    
    if price > vah and trend_up:
        # הרחבה ראשונה מעל אזור הערך
        target = vah + (vah - poc)
        if price > target: target = target + (vah - poc) # יעד מתגלגל
        return "long_confirm", target
    elif val <= price <= vah and trend_up:
        # בתוך האזור, תחילת איסוף ללונג
        return "long_prepare", vah
    elif price < val and not trend_up:
        # הרחבה ראשונה מתחת לאזור הערך
        target = val - (poc - val)
        if price < target: target = target - (poc - val) # יעד מתגלגל
        return "short_confirm", target
    elif val <= price <= vah and not trend_up:
        # בתוך האזור, תחילת פיזור לשורט
        return "short_prepare", val
    else:
        # מצבי ביניים (Whipsaws)
        if trend_up: return "long_prepare", vah
        else: return "short_prepare", val

now_dt = datetime.utcnow() + timedelta(hours=3)
st.title("⚔️ Attack Board - לוח תקיפה מוסדי")
st.write(f"זמן מערכת: {now_dt.strftime('%H:%M:%S')}")

# ==========================================
# 1. RISK ON/OFF (לוח מאקרו עליון עיצוב נקי)
# ==========================================
st.markdown("### 🌍 RISK ON/OFF")

macro_tickers = ['DX-Y.NYB', '^TNX', 'BTC-USD', 'CL=F', 'DIA', 'QQQ', 'SPY']
try:
    macro_data = fetch_data(macro_tickers, period="2d", interval="1h")
    if isinstance(macro_data.columns, pd.MultiIndex):
        macro_data.columns = [f"{col[0]}_{col[1]}" for col in macro_data.columns]
except:
    macro_data = pd.DataFrame()

macro_display = []
names = {'DX-Y.NYB': 'DXY', '^TNX': 'TNX', 'BTC-USD': 'BTC', 'CL=F': 'OIL', 'DIA': 'DOW', 'QQQ': 'NASDAQ', 'SPY': 'S&P500'}

for tick, name in names.items():
    try:
        s = macro_data[f'Close_{tick}'].dropna()
        c_p = float(s.iloc[-1]); p_p = float(s.iloc[0])
        chg = ((c_p - p_p) / p_p) * 100
        
        # לוגיקת חצים מדויקת לפי התמונה שלך
        if tick in ['DX-Y.NYB', '^TNX', 'CL=F']:
            arrow = "<span style='color:red;'>⬆</span>" if chg > 0 else "<span style='color:green;'>⬇</span>"
        else: # BTC, מדדים
            arrow = "<span style='color:green;'>⬆</span>" if chg > 0 else "<span style='color:red;'>⬇</span>"
        
        macro_display.append(f"<td>{name}<br>{arrow}<br><span style='font-size:14px;color:#aaa;'>{chg:+.1f}%</span></td>")
    except:
        macro_display.append(f"<td>{name}<br>--</td>")

html_table = f"""
<table class="macro-table" style="width:100%; margin-bottom: 30px;">
    <tr>{''.join(macro_display)}</tr>
</table>
"""
st.markdown(html_table, unsafe_allow_html=True)


# ==========================================
# 2. מנוע מומנטום וחלוקה לאזורי תקיפה (Long / Short Zones)
# ==========================================
st.markdown("### 🎯 טבלת הנכסים למסחר יומי (סורק חכם)")

# איסוף וחישוב נתונים לכל הסקטורים הממונפים
try:
    all_tickers = [data['base'] for data in lev_pairs.values()] + [data['long'] for data in lev_pairs.values()] + [data['short'] for data in lev_pairs.values()]
    intra_data = fetch_data(all_tickers, period="5d", interval="5m")
    if isinstance(intra_data.columns, pd.MultiIndex):
        intra_data.columns = [f"{col[0]}_{col[1]}" for col in intra_data.columns]
except:
    intra_data = pd.DataFrame()

long_candidates = []
short_candidates = []

for sec_name, data in lev_pairs.items():
    try:
        base_tick = data['base']
        s_base = intra_data[f'Close_{base_tick}'].dropna()
        v_base = intra_data[f'Volume_{base_tick}'].dropna()
        
        c_last = float(s_base.iloc[-1])
        c_prev = float(s_base.iloc[-2])
        intra_chg = ((c_last - float(s_base.iloc[0])) / float(s_base.iloc[0])) * 100
        
        qtr_p = float(sector_perf_history.get(base_tick, {}).get('qtr', 0))
        mo_p = float(sector_perf_history.get(base_tick, {}).get('mo', 0))
        power_score = float((qtr_p * 0.4) + (mo_p * 0.3) + (intra_chg * 0.3))
        
        poc, vah, val = calc_volume_profile(s_base, v_base)
        state, target_price = determine_state(c_last, c_prev, poc, vah, val)
        
        # חישוב המרה לנכס הממונף
        dist_pct = ((target_price - c_last) / c_last)
        
        long_tick, short_tick = data['long'], data['short']
        c_long = float(intra_data[f'Close_{long_tick}'].dropna().iloc[-1])
        c_short = float(intra_data[f'Close_{short_tick}'].dropna().iloc[-1])
        
        targ_long = c_long * (1 + (dist_pct * 3))
        targ_short = c_short * (1 + (-dist_pct * 3)) # מינוף הפוך
        
        pct_long = ((targ_long - c_long) / c_long) * 100
        pct_short = ((targ_short - c_short) / c_short) * 100

        # הכנסה לאזורים לפי כיוון המומנטום המאקרו-אסטרטגי (Power Score)
        if power_score > 0:
            if "long" in state:
                status_html = "הכן פקודה<br><span class='arrow-prepare'>⬆</span>" if "prepare" in state else "אישור מגמה<br><span class='arrow-long'>⬆</span>"
                long_candidates.append({'name': long_tick, 'price': c_long, 'target': targ_long, 'pct': pct_long, 'status': status_html, 'score': power_score})
        else:
            if "short" in state:
                status_html = "הכן פקודה<br><span class='arrow-prepare'>⬇</span>" if "prepare" in state else "אישור מגמה<br><span class='arrow-short'>⬇</span>"
                short_candidates.append({'name': short_tick, 'price': c_short, 'target': targ_short, 'pct': pct_short, 'status': status_html, 'score': power_score})
                
    except Exception as e:
        continue

# מיון לפי עוצמה
long_candidates = sorted(long_candidates, key=lambda x: x['score'], reverse=True)
short_candidates = sorted(short_candidates, key=lambda x: x['score'])

# --- תצוגת האזורים (Heatmap Cards) ---
col_L, col_S = st.columns(2)

with col_L:
    st.markdown("<div class='long-zone'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #00ff00;'>🟢 סקטורים ללונג (זרימת כסף חיובית)</h3>", unsafe_allow_html=True)
    if long_candidates:
        for item in long_candidates:
            st.markdown(f"""
            <div class='card'>
                <div class='card-title'>{item['name']}</div>
                <table style='width:100%;'><tr>
                    <td style='width:33%;'>{item['status']}</td>
                    <td style='width:33%;'>
                        <div class='card-value'>{item['price']:.2f}</div>
                        <div style='font-size:12px;color:#aaa;'>שער נוכחי</div>
                    </td>
                    <td style='width:33%;'>
                        <div class='card-target'>{item['target']:.2f}</div>
                        <div class='card-percent'>({item['pct']:+.1f}%)</div>
                        <div style='font-size:12px;color:#aaa;'>יעד רווח מתגלגל</div>
                    </td>
                </tr></table>
            </div><br>
            """, unsafe_allow_html=True)
    else:
        st.write("אין סקטורים עם מומנטום חיובי ברור כרגע.")
    st.markdown("</div>", unsafe_allow_html=True)

with col_S:
    st.markdown("<div class='short-zone'>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #ff0000;'>🔴 סקטורים לשורט (בריחת הון)</h3>", unsafe_allow_html=True)
    if short_candidates:
        for item in short_candidates:
            st.markdown(f"""
            <div class='card'>
                <div class='card-title'>{item['name']}</div>
                <table style='width:100%;'><tr>
                    <td style='width:33%;'>{item['status']}</td>
                    <td style='width:33%;'>
                        <div class='card-value'>{item['price']:.2f}</div>
                        <div style='font-size:12px;color:#aaa;'>שער נוכחי</div>
                    </td>
                    <td style='width:33%;'>
                        <div class='card-target-short'>{item['target']:.2f}</div>
                        <div class='card-percent'>({item['pct']:+.1f}%)</div>
                        <div style='font-size:12px;color:#aaa;'>יעד רווח מתגלגל</div>
                    </td>
                </tr></table>
            </div><br>
            """, unsafe_allow_html=True)
    else:
        st.write("אין סקטורים עם מומנטום שלילי ברור כרגע.")
    st.markdown("</div>", unsafe_allow_html=True)

time.sleep(15)
st.rerun()
