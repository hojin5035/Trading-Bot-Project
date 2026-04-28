import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import plotly.express as px
import streamlit as st
from datetime import datetime
import pytz # 타임존 제어 라이브러리

# 한국 타임존 설정
KST = pytz.timezone('Asia/Seoul')

# ... (기존 코드)

def get_current_time():
    # 서버의 현재 시간이 아닌, 한국의 현재 시간을 가져옵니다.
    return datetime.now(KST)

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

# --- [3. 사이드바 제어판] ---
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

    # dashboard.py 사이드바 내부 수정 제안
    st.divider()
    st.subheader("📊 Portfolio Weight")
    
    # 1. 데이터 로직: 포지션 여부에 따른 비중 계산
    # 보유 중인(in_position=True) 종목들만 필터링
    held_symbols = [sym for sym, stt in status.items() if stt.get('in_position', False)]
    
    allocation_data = []
    if not held_symbols:
        # 매수한 종목이 없으면 'Cash(현금)' 100%
        allocation_data.append({"Asset": "Portfolio", "Type": "Cash", "Weight": 100})
        colors = ["#30363d"] # 현금은 차분한 회색 계열
    else:
        # 매수한 종목이 있으면 해당 종목들 비중 표시 (현재는 균등 배분 가정)
        for sym in held_symbols:
            allocation_data.append({"Asset": "Portfolio", "Type": sym.split('/')[0], "Weight": 100/len(held_symbols)})
        colors = px.colors.qualitative.Pastel # 종목별 화사한 색상
    
    df_bar = pd.DataFrame(allocation_data)
    
    # 2. 아주 얇은 수평 막대 그래프 생성
    fig_bar = px.bar(df_bar, x='Weight', y='Asset', color='Type', orientation='h',
                     color_discrete_sequence=colors,
                     text='Type')

    fig_bar.update_layout(
        barmode='stack',
        height=50,             # 높이를 50으로 줄여 아주 얇게 만듦
        margin=dict(t=0, b=0, l=0, r=0),
        showlegend=False,
        xaxis=dict(visible=False, range=[0, 100]), # 축 제거 및 범위 고정
        yaxis=dict(visible=False),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    
    # 막대 안에 텍스트 표시 설정 (비중이 클 때만 텍스트 노출)
    fig_bar.update_traces(
        texttemplate='%{text} %{x:.0f}%', 
        textposition='inside',
        insidetextanchor='middle',
        marker=dict(line=dict(width=0)) # 테두리 제거로 더 깔끔하게
    )
    
    st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})

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
    # --- [가동 시간 계산 부분 수정] ---
    if meta and 'start_time' in meta:
        # 1. 저장된 시작 시간 문자열을 읽어옴
        start_dt_naive = datetime.strptime(meta['start_time'], '%Y-%m-%d %H:%M:%S')
    
        # 2. 이 시간을 한국 시간(KST)으로 인식하게 만듦
        start_dt = KST.localize(start_dt_naive)
    
        # 3. 현재의 한국 시간과 비교
        now_dt = datetime.now(KST)
        diff = now_dt - start_dt
    
        # (이후 계산 로직은 동일)
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