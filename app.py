import streamlit as st
import pandas as pd
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import requests
import xml.etree.ElementTree as ET

# הורדת מילון סנטימנט
try:
    nltk.data.find('sentiment/vader_lexicon.zip')
except LookupError:
    nltk.download('vader_lexicon', quiet=True)

# הגדרות עמוד
st.set_page_config(page_title="Matrix OS", layout="wide", page_icon="🖥️")
st.title("🖥️ Matrix OS - דשבורד מוסדי")
st.markdown("---")

assets = {'Silver (SI=F)': 'SI=F', 'Platinum (PL=F)': 'PL=F', 'Crude Oil (CL=F)': 'CL=F', 'Tech (XLK)': 'XLK'}
sia = SentimentIntensityAnalyzer()

def fetch_yahoo_rss(ticker):
    """מנוע עוקף חסימות שואב RSS משרתי Yahoo"""
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            items = root.findall('.//item')
            return [item.find('title').text for item in items[:5]]
    except:
        pass
    return []

def get_sentiment(ticker):
    news_titles = fetch_yahoo_rss(ticker)
    if not news_titles:
        return 0.0, "⚪ אין מידע זמין"
    
    scores = [sia.polarity_scores(title)['compound'] for title in news_titles]
    avg = sum(scores) / len(scores) if scores else 0.0
    
    if avg > 0.1:
        status = "🟢 חיובי (רוח גבית)"
    elif avg < -0.1:
        status = "🔴 שלילי (סכנה)"
    else:
        status = "⚪ ניטרלי"
        
    return round(avg, 2), status

st.subheader("סריקת סנטימנט ופוליגרף מוסדי (RSS)")
data = []
with st.spinner('המטריקס סורק נתונים בזמן אמת...'):
    for name, ticker in assets.items():
        score, status = get_sentiment(ticker)
        data.append({'נכס': name, 'ציון סנטימנט': score, 'סטטוס': status})

st.table(pd.DataFrame(data))

if st.button("רענן נתונים כעת"):
    st.rerun()
