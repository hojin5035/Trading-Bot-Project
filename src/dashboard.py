import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import plotly.express as px

# 1. 페이지 설정 (가장 먼저 실행되어야 함)
st.set_page_config(page_title="Hojin's Quant Terminal", layout="wide")

# 2. CSS 주입: 최상단 여백 제거 및 폰트 조절
st.markdown("""
    <style>
    /* 상단 기본 여백 제거 */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0rem !important;
    }
    html, body, [class*="css"] { font-size: 14px; }
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# --- [데이터 로드 함수] ---
def get_data():
    try:
        with open('data/status.json', 'r') as f: status = json.load(f)
        with open('data/metadata.json', 'r') as f: meta = json.load(f)
        with open('bot_config.json', 'r') as f: config = json.load(f)
        if os.path.exists('data/trade_log.csv'):
            trade_log = pd.read_csv('data/trade_log.csv')
        else:
            trade_log = pd.DataFrame()
    except: return {}, {}, {}, pd.DataFrame()
    return status, meta, config, trade_log

status, meta, config, trade_log = get_data()

# --- [1. 최상단: 시스템 인디케이터 (게임 공지 스타일)] ---
update_time = datetime.now().strftime('%H:%M:%S')
st.markdown(f"""
    <div style="background-color: #161b22; padding: 12px; border-radius: 8px; border-left: 5px solid #238636; margin-bottom: 25px;">
        <span style="color: white; font-size: 15px;">📡 <b>시스템 가동 중</b> | 마지막 스캔: {update_time} | 모드: 통합 드라이런</span>
    </div>
    """, unsafe_allow_html=True)

# --- [2. 핵심 지표 섹션 (수익률 옆에 가동 시간 배치)] ---
col1, col2, col3 = st.columns(3)

with col1:
    # 가동 기간 계산 로직 수정
    if meta and 'start_time' in meta:
        start_dt = datetime.strptime(meta['start_time'], '%Y-%m-%d %H:%M:%S')
        diff = datetime.now() - start_dt
        days = diff.days
        hours = diff.seconds // 3600
        st.metric("🕒 총 가동 시간", f"{days}일 {hours}시간")
    else:
        st.metric("🕒 총 가동 시간", "기록 없음")

with col2:
    profit = trade_log[trade_log['type'] == 'SELL']['profit_rate'].sum() if not trade_log.empty else 0
    st.metric("📈 누적 수익률", f"{profit:+.2f}%")

with col3:
    # 사이드바에서 입력받은 시드를 반영하기 위해 여기서 시드값 호출 (기본값 100만)
    seed = 1000000 
    st.metric("💰 예상 평가 자산", f"{seed * (1 + profit/100):,.0f} USDT")

st.markdown("<br>", unsafe_allow_html=True) # 지표와 탭 사이 간격 추가

# --- [3. 탭 구성 및 나머지 내용] ---
tab1, tab2, tab3 = st.tabs(["📊 매매 분석", "⚙️ 전략 설정", "📰 마켓 뉴스"])
# ... (이후 탭 내부 코드는 동일)