import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px

# 1. 페이지 설정
st.set_page_config(layout="wide")

# 2. 전용 CSS 주입 (글씨 크기 및 간격 조절)
st.markdown(
    """
    <style>
    /* 전체 기본 폰트 크기 조절 */
    html, body, [class*="css"] {
        font-size: 14px; /* 대화창과 비슷한 적당한 크기 */
    }
    
    /* 제목(Title) 크기 줄이기 */
    h1 {
        font-size: 1.8rem !important;
        font-weight: 700;
    }
    
    /* 부제목(Subheader) 크기 줄이기 */
    h2, h3 {
        font-size: 1.2rem !important;
        margin-top: 1rem !important;
    }
    
    /* 사이드바 글씨 크기 */
    .sidebar .sidebar-content {
        font-size: 13px;
    }

    /* 표(Dataframe) 글씨 크기 */
    .stDataFrame, .stTable {
        font-size: 12px;
    }

    /* 메트릭(Metric) 라벨 크기 조절 */
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
    }
    
    /* 메트릭 숫자 크기 조절 */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- [데이터 로드 함수들] ---
def load_metadata():
    try:
        with open('data/metadata.json', 'r') as f:
            return json.load(f)
    except: return None

def load_status():
    try:
        with open('data/status.json', 'r') as f:
            return json.load(f)
    except: return {}

def load_trade_log():
    try:
        df = pd.read_csv('data/trade_log.csv')
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except: return pd.DataFrame()

def load_bot_config():
    try:
        with open('bot_config.json', 'r') as f:
            return json.load(f)
    except: return {}

# --- [사이드바: 자산 설정 및 전략 확인] ---
st.sidebar.header("💰 자산 설정")
virtual_seed = st.sidebar.number_input("가상 시드 입력 (USDT)", value=1000000)

st.sidebar.divider()
st.sidebar.header("⚙️ 현재 적용 전략 (JSON)")
config_data = load_bot_config()

if config_data:
    for sym, cfg in config_data.items():
        if isinstance(cfg, dict):
            st.sidebar.subheader(f"📍 {sym} 전략")
            
            # 수치를 한글로 풀어서 설명
            vol_desc = f"📊 거래량 돌파: {cfg.get('vol')}배"
            ts_desc = f"🛡️ 익절 보존(TS): {cfg.get('ts')*100:.1f}%"
            profit_desc = f"🎯 최소 익절 기준: {cfg.get('profit')*100:.1f}%"
            
            st.sidebar.write(vol_desc)
            st.sidebar.write(ts_desc)
            st.sidebar.write(profit_desc)
            st.sidebar.divider()

# --- [메인 레이아웃] ---
st.title("📈 실시간 트레이딩 분석 대시보드")

# 1. 상단 지표 (Metric)
metadata = load_metadata()
trade_log = load_trade_log()
status = load_status()

col1, col2, col3 = st.columns(3)

with col1:
    if metadata:
        start_time = datetime.strptime(metadata['start_time'], '%Y-%m-%d %H:%M:%S')
        duration = datetime.now() - start_time
        days = duration.days
        hours = duration.seconds // 3600
        st.metric("운영 기간", f"{days}일 {hours}시간", delta=f"{days+1}일차")
    else:
        st.metric("운영 기간", "기록 없음")

with col2:
    total_profit_rate = trade_log[trade_log['type'] == 'SELL']['profit_rate'].sum() if not trade_log.empty else 0.0
    st.metric("누적 수익률", f"{total_profit_rate:.2f}%", delta=f"{total_profit_rate:.2f}%")

with col3:
    current_asset = virtual_seed * (1 + total_profit_rate / 100)
    st.metric("현재 총 자산", f"{current_asset:,.0f} USDT")

st.divider()

# 2. 중간 섹션: 파이차트 & 수익률 차트
left_col, right_col = st.columns([1, 2])

with left_col:
    st.subheader("🍕 자산 배분 (현금 vs 코인)")
    # 파이차트 데이터 생성
    in_pos_coins = [sym for sym, state in status.items() if state['in_position']]
    cash_weight = 100 - (len(in_pos_coins) * 25) # 4개 코인 기준, 각각 25%씩 할당 가정
    
    labels = ['Cash'] + in_pos_coins
    values = [cash_weight] + [25] * len(in_pos_coins)
    
    # 파이차트 생성 부분 수정
    fig_pie = px.pie(values=values, names=labels, hole=0.4, 
                 color_discrete_sequence=px.colors.sequential.RdBu)

    # 차트 안의 글씨 크기만 명시적으로 키우기
    fig_pie.update_traces(textinfo='percent+label', textfont_size=14) 
    fig_pie.update_layout(legend=dict(font=dict(size=13))) # 범례 글씨

    st.plotly_chart(fig_pie, use_container_width=True)

with right_col:
    st.subheader("📊 날짜별 수익률 추이")
    if not trade_log.empty and 'SELL' in trade_log['type'].values:
        sell_logs = trade_log[trade_log['type'] == 'SELL'].copy()
        # 마우스 오버 시 정보를 위한 차트
        fig_bar = px.bar(sell_logs, x='timestamp', y='profit_rate', 
                         color='profit_rate', color_continuous_scale='RdYlGn',
                         hover_data=['symbol', 'reason', 'price'])
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("아직 매도 기록이 없습니다. 봇이 첫 수익을 낼 때까지 기다려주세요!")

# 3. 하단 섹션: 전체 매매 로그 표
st.divider()
st.subheader("📜 상세 매매 히스토리")
if not trade_log.empty:
    st.dataframe(trade_log.sort_values(by='timestamp', ascending=False), use_container_width=True)
else:
    st.write("기록된 매매 데이터가 없습니다.")