import streamlit as st
import yfinance as yf
import pandas as pd
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# הורדת מילון סנטימנט (מונע שגיאות בענן)
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

def get_sentiment(ticker):
    try:
        news = yf.Ticker(ticker).news
        if not news: return 0.0, "⚪"
        scores = [sia.polarity_scores(n['title'])['compound'] for n in news[:3]]
        avg = sum(scores)/len(scores)
        status = "🟢 חיובי (רוח גבית)" if avg > 0.1 else ("🔴 שלילי (סכנה)" if avg < -0.1 else "⚪ ניטרלי")
        return round(avg, 2), status
    except:
        return 0.0, "⚪ שגיאה"

st.subheader("סריקת סנטימנט ופוליגרף מוסדי")
data = []
with st.spinner('המטריקס סורק נתונים בזמן אמת...'):
    for name, ticker in assets.items():
        score, status = get_sentiment(ticker)
        data.append({'נכס': name, 'ציון סנטימנט': score, 'סטטוס': status})

st.table(pd.DataFrame(data))

if st.button("רענן נתונים כעת"):
    st.rerun()
