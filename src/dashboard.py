import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import plotly.express as px

# 1. 페이지 설정 (레이아웃 및 타이틀)
st.set_page_config(page_title="Quant Strategy Terminal", layout="wide")

# 2. 통합 CSS (버튼 가시성, 날개 여백, 인디케이터 디자인)
st.markdown("""
    <style>
    /* 상단 헤더와 버튼 가시성 확보 */
    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important;
    }
    
    /* 본문 레이아웃: 날개(여백) 복구 및 중앙 정렬 */
    .block-container {
        padding-top: 4rem !important; 
        max-width: 1100px !important;
        margin: auto;
    }

    /* 신호등 인디케이터 디자인 */
    .status-card {
        background-color: #161b22;
        padding: 15px 20px;
        border-radius: 8px;
        border: 1px solid #30363d;
        border-left: 5px solid #238636;
        margin-bottom: 25px;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.4);
        display: flex;
        align-items: center;
    }
    .status-dot {
        color: #238636;
        font-size: 22px;
        margin-right: 12px;
        animation: blink 2s infinite; /* 깜빡이는 효과 */
    }
    @keyframes blink {
        0% { opacity: 0.4; }
        50% { opacity: 1; }
        100% { opacity: 0.4; }
    }
    
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# --- [데이터 로드 함수] ---
def get_data():
    try:
        # 파일 로드 시 경로 체크
        status = {}
        if os.path.exists('data/status.json'):
            with open('data/status.json', 'r') as f: status = json.load(f)
        
        meta = {}
        if os.path.exists('data/metadata.json'):
            with open('data/metadata.json', 'r') as f: meta = json.load(f)
            
        config = {}
        if os.path.exists('bot_config.json'):
            with open('bot_config.json', 'r') as f: config = json.load(f)
            
        trade_log = pd.DataFrame()
        if os.path.exists('data/trade_log.csv'):
            trade_log = pd.read_csv('data/trade_log.csv')
            
    except Exception as e:
        return {}, {}, {}, pd.DataFrame()
    return status, meta, config, trade_log

status, meta, config, trade_log = get_data()
update_time = datetime.now().strftime('%H:%M:%S')

# --- [3. 사이드바 제어판 (날개 버튼의 정체)] ---
with st.sidebar:
    st.header("⚙️ System Control")
    st.markdown("전략 실행 및 자산 설정")
    
    # 가상 시드 설정
    seed_input = st.number_input("초기 자본 (USDT)", min_value=100, value=1000000, step=100000)
    
    st.divider()
    st.subheader("📡 Real-time Quotes")
    for sym in ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT']:
        p = status.get(sym, {}).get('current_price', 0)
        st.write(f"{sym}: **{p:,.2f}**")

# --- [4. 메인 화면: 신호등 인디케이터] ---
st.markdown(f"""
    <div class="status-card">
        <span class="status-dot">●</span>
        <span style="color: white; font-size: 16px;">
            <b>Quant Strategy Terminal Active</b> | 업데이트: {update_time} | 모드: Dry-Run
        </span>
    </div>
    """, unsafe_allow_html=True)

# --- [5. 핵심 지표 섹션] ---
col1, col2, col3 = st.columns(3)

with col1:
    if meta and 'start_time' in meta:
        start_dt = datetime.strptime(meta['start_time'], '%Y-%m-%d %H:%M:%S')
        diff = datetime.now() - start_dt
        total_sec = int(diff.total_seconds())
        days, hours, minutes = total_sec // 86400, (total_sec % 86400) // 3600, (total_sec % 3600) // 60
        time_str = f"{days}일 {hours}시간" if days > 0 else f"{hours}시간 {minutes}분"
        st.metric("🕒 총 가동 시간", time_str)
    else:
        st.metric("🕒 총 가동 시간", "기록 없음")

with col2:
    profit = trade_log[trade_log['type'] == 'SELL']['profit_rate'].sum() if not trade_log.empty else 0
    st.metric("📈 누적 수익률", f"{profit:+.2f}%")

with col3:
    st.metric("💰 예상 평가 자산", f"{seed_input * (1 + profit/100):,.0f} USDT")

st.markdown("<br>", unsafe_allow_html=True)

st.markdown("---") # 구분선 추가

# --- [5.1 자산 배분 현황 (파이 차트)] ---
st.subheader("📊 Portfolio Allocation")
col_chart, col_info = st.columns([2, 1]) # 차트를 크게, 설명을 작게

with col_chart:
    # 파이 차트용 데이터 준비 (예시: 설정된 심볼별로 균등 배분 가정 또는 실제 보유량)
    # 실제 보유량 데이터가 status.json에 있다면 그 데이터를 사용하면 됩니다.
    allocation_data = []
    for sym in config.keys():
        # 여기서는 간단히 전략에 포함된 코인들 이름을 가져옵니다.
        allocation_data.append({"Symbol": sym, "Value": 1}) # 예시 비중
    
    if allocation_data:
        df_pie = pd.DataFrame(allocation_data)
        fig_pie = px.pie(df_pie, values='Value', names='Symbol', 
                         hole=0.4, # 도넛 모양으로 만들어 더 세련되게 표시
                         color_discrete_sequence=px.colors.sequential.Greens_r)
        fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=300)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("설정된 전략이 없어 차트를 표시할 수 없습니다.")

with col_info:
    st.write("**포트폴리오 요약**")
    st.caption("현재 전략이 적용된 심볼들의 배분 상태입니다. 각 코인별로 동일한 가중치의 리스크 파라미터가 적용되어 있습니다.")
    # 추가적인 통계치나 안내 문구를 여기에 넣을 수 있습니다.

# --- [6. 상세 데이터 분석 탭] ---
tab1, tab2, tab3 = st.tabs(["📊 Trade Analysis", "⚙️ Strategy Config", "📰 Market News"])

with tab1:
    if not trade_log.empty:
        # 수익률 차트
        fig = px.bar(trade_log[trade_log['type']=='SELL'], x='timestamp', y='profit_rate', 
                     color='profit_rate', color_continuous_scale='RdYlGn', title="Trade Performance")
        st.plotly_chart(fig, use_container_width=True)
        # 전체 로그
        st.dataframe(trade_log.sort_values('timestamp', ascending=False), use_container_width=True)
    else:
        st.info("데이터 수집 중입니다. 첫 매매가 발생하면 여기에 표시됩니다.")

with tab2:
    st.subheader("Active Strategy Parameters")
    for sym, cfg in config.items():
        if isinstance(cfg, dict):
            st.markdown(f"**{sym}**")
            st.code(f"돌파: {cfg['vol']:.1f}배 / TS: {cfg['ts']*100:.2f}% / 익절: {cfg['profit']*100:.1f}%")

with tab3:
    st.write("실시간 마켓 뉴스를 통합할 예정입니다.")