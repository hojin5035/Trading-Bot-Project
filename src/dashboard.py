import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import plotly.express as px

# 1. 페이지 설정 (가장 먼저 실행되어야 함)
st.set_page_config(page_title="Hojin's Quant Terminal", layout="wide")

# dashboard.py 상단 CSS 부분 수정
st.markdown("""
    <style>
    /* 1. 스트림릿 기본 헤더 제거 (잘림 현상 근본 해결) */
    header[data-testid="stHeader"] {
        visibility: hidden;
        height: 0%;
    }
    
    /* 2. 상단 여백 최소화 */
    .block-container {
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        max-width: 95%; /* 화면을 더 넓게 쓰려면 조절 */
    }

    /* 3. 인디케이터 바 디자인 (상단 고정 느낌) */
    .custom-indicator {
        background-color: #161b22;
        padding: 12px 20px;
        border-radius: 0px 0px 8px 8px; /* 위쪽은 붙이고 아래만 둥글게 */
        border-left: 5px solid #238636;
        margin-bottom: 20px;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.2);
    }
    
    html, body, [class*="css"] { font-size: 14px; }
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

update_time = datetime.now().strftime('%H:%M:%S')

# 인디케이터 출력부 (클래스 추가)
st.markdown(f"""
    <div class="custom-indicator">
        <span style="color: white; font-size: 15px;">📡 <b>시스템 가동 중</b> | 마지막 스캔: {update_time} | 모드: 통합 드라이런</span>
    </div>
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

with tab1:
    if not trade_log.empty:
        fig_bar = px.bar(trade_log[trade_log['type']=='SELL'], x='timestamp', y='profit_rate', color='profit_rate', 
                         hover_data=['symbol', 'reason'], color_continuous_scale='RdYlGn')
        st.plotly_chart(fig_bar, use_container_width=True)
        st.dataframe(trade_log.sort_values('timestamp', ascending=False), use_container_width=True)
    else: st.info("매매 기록을 기다리는 중입니다...")

with tab2:
    st.subheader("현재 적용 중인 전략 파라미터")
    for sym, cfg in config.items():
        if isinstance(cfg, dict):
            st.write(f"**{sym}**")
            # :.2f 또는 :.1f를 사용해서 소수점 자릿수를 고정합니다.
            vol = cfg['vol']
            ts_percent = cfg['ts'] * 100
            profit_percent = cfg['profit'] * 100
            
            st.code(f"돌파: {vol:.1f}배 / TS: {ts_percent:.2f}% / 익절기준: {profit_percent:.1f}%")

with tab3:
    st.subheader("실시간 마켓 뉴스")
    st.write("준비 중인 기능입니다.")