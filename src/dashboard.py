import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import plotly.express as px

# 1. 페이지 설정
st.set_page_config(page_title="Hojin's Quant Terminal", layout="wide")

# CSS 수정: 버튼을 가리지 않도록 상단 여백을 충분히 확보
st.markdown("""
    <style>
    /* 1. 사이드바 아이콘 가시성 확보 */
    button[data-testid="stSidebarCollapseIcon"] {
        background-color: #238636 !important; 
        color: white !important;
        z-index: 999999 !important;
        opacity: 1 !important;
        visibility: visible !important;
    }

    /* 2. 본문 레이아웃 및 날개(여백) */
    .block-container {
        padding-top: 4rem !important; 
        max-width: 1100px !important;
        margin: auto;
    }

    /* 3. 시스템 인디케이터 디자인 */
    .custom-indicator {
        background-color: #161b22;
        padding: 12px 20px;
        border-radius: 8px;
        border-left: 5px solid #238636;
        margin-bottom: 25px;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.4);
    }
    </style>
    """, unsafe_allow_html=True)

# --- [시간 및 데이터 로드] ---
update_time = datetime.now().strftime('%H:%M:%S')

st.markdown(f"""
    <div class="custom-indicator">
        <span style="color: white; font-size: 15px;">📡 <b>Quant Strategy Terminal</b> | 업데이트: {update_time} | 모드: Dry-Run</span>
    </div>
    """, unsafe_allow_html=True)


def get_data():
    try:
        with open('data/status.json', 'r') as f: status = json.load(f)
        with open('data/metadata.json', 'r') as f: meta = json.load(f)
        with open('bot_config.json', 'r') as f: config = json.load(f)
        trade_log = pd.read_csv('data/trade_log.csv') if os.path.exists('data/trade_log.csv') else pd.DataFrame()
    except: return {}, {}, {}, pd.DataFrame()
    return status, meta, config, trade_log

status, meta, config, trade_log = get_data()

# --- [핵심 지표 섹션] ---
col1, col2, col3 = st.columns(3)

with col1:
    if meta and 'start_time' in meta:
        start_dt = datetime.strptime(meta['start_time'], '%Y-%m-%d %H:%M:%S')
        diff = datetime.now() - start_dt
        
        # 정밀 시간 계산 (초 단위까지 고려)
        total_seconds = int(diff.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        
        if days > 0:
            st.metric("🕒 총 가동 시간", f"{days}일 {hours}시간")
        else:
            st.metric("🕒 총 가동 시간", f"{hours}시간 {minutes}분")
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