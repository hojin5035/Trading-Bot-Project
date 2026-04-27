import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import plotly.express as px

# --- [설정 및 스타일] ---
st.set_page_config(page_title="Hojin's Quant Terminal", layout="wide")
st.markdown("""<style>
    html, body, [class*="css"] { font-size: 14px; }
    h1 { font-size: 1.8rem !important; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
</style>""", unsafe_allow_html=True)

# --- [데이터 로드] ---
def get_data():
    try:
        with open('data/status.json', 'r') as f: status = json.load(f)
        with open('data/metadata.json', 'r') as f: meta = json.load(f)
        with open('bot_config.json', 'r') as f: config = json.load(f)
        df = pd.read_csv('data/trade_log.csv')
    except: return {}, {}, {}, pd.DataFrame()
    return status, meta, config, df

status, meta, config, trade_log = get_data()

# --- [사이드바: 자산 & 실시간 시세] ---
with st.sidebar:
    st.header("💰 자산 설정")
    seed = st.number_input("가상 시드 (USDT)", value=1000000)
    st.divider()
    
    st.subheader("📊 실시간 시세")
    for sym, s in status.items():
        st.write(f"{sym.split('/')[0]}: **{s.get('current_price', 0):,.4f}**")
    
    st.divider()
    st.subheader("🍕 현재 비중")
    if status:
        in_pos = [sym for sym, s in status.items() if s['in_position']]
        weights = [100 - len(in_pos)*25] + [25]*len(in_pos)
        labels = ['Cash'] + in_pos
        fig_pie = px.pie(values=weights, names=labels, hole=0.5)
        fig_pie.update_traces(textinfo='percent', textfont_size=12)
        fig_pie.update_layout(showlegend=False, margin=dict(t=0,b=0,l=0,r=0), height=200)
        st.plotly_chart(fig_pie, use_container_width=True)

# --- [메인 상단: 시스템 인디케이터] ---
update_time = datetime.now().strftime('%H:%M:%S')
st.markdown(f"""<div style="background-color: #161b22; padding: 10px; border-radius: 5px; border-left: 5px solid #238636;">
    <span style="color: white;">📡 <b>시스템 가동 중</b> | 업데이트: {update_time} | 모드: Dry-Run</span>
</div>""", unsafe_allow_html=True)

# --- [메인 지표 요약] ---
col1, col2, col3 = st.columns(3)
with col1:
    if meta:
        days = (datetime.now() - datetime.strptime(meta['start_time'], '%Y-%m-%d %H:%M:%S')).days
        st.metric("가동 기간", f"{days+1}일차")
with col2:
    profit = trade_log[trade_log['type'] == 'SELL']['profit_rate'].sum() if not trade_log.empty else 0
    st.metric("누적 수익률", f"{profit:.2f}%")
with col3:
    st.metric("예상 자산", f"{seed * (1 + profit/100):,.0f} USDT")

# --- [탭 구성] ---
tab1, tab2, tab3 = st.tabs(["📈 수익률 분석", "⚙️ 전략 설정", "📰 마켓 뉴스"])

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
            st.code(f"돌파: {cfg['vol']}배 / TS: {cfg['ts']*100}% / 익절기준: {cfg['profit']*100}%")

with tab3:
    st.subheader("실시간 마켓 뉴스")
    st.write("준비 중인 기능입니다.")