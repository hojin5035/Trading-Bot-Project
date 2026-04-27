import ccxt
import pandas as pd
import pandas_ta as ta
import json
import time
import os
from datetime import datetime
from utils import send_discord_notification

# --- [설정] ---
symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT']
exchange = ccxt.binance({'enableRateLimit': True})

# 각 코인별 상태를 추적하기 위한 딕셔너리
coin_states = {
    sym: {"in_position": False, "entry_price": 0, "highest_price": 0} 
    for sym in symbols
}

# --- [데이터 기록 유틸리티] ---
def record_metadata():
    os.makedirs('data', exist_ok=True)
    metadata_path = 'data/metadata.json'
    if not os.path.exists(metadata_path):
        data = {"start_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        with open(metadata_path, 'w') as f:
            json.dump(data, f)

def save_trade_log(symbol, type, price, profit=0, reason="-"):
    log_path = 'data/trade_log.csv'
    new_log = {
        'timestamp': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        'symbol': [symbol],
        'type': [type],
        'price': [price],
        'profit_rate': [round(profit * 100, 2)],
        'reason': [reason]
    }
    df = pd.DataFrame(new_log)
    df.to_csv(log_path, mode='a', header=not os.path.exists(log_path), index=False, encoding='utf-8-sig')

def save_current_status():
    """모든 코인의 현재 상태를 한 번에 저장 (파이차트용)"""
    status_path = 'data/status.json'
    with open(status_path, 'w') as f:
        json.dump(coin_states, f)

def load_config():
    try:
        with open('bot_config.json', 'r') as f: return json.load(f)
    except: return {}

# --- [모니터링 핵심 함수] ---
def monitor_symbol(symbol, config):
    global coin_states
    
    # 1. 데이터 수집
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['ema9'] = ta.ema(df['close'], length=9)
    df['ema9_1h'] = ta.ema(df['close'], length=36)
    df['rsi'] = ta.rsi(df['close'], length=14)
    
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    price = curr['close']
    
    # 2. 설정 로드
    setting = config.get(symbol, {"vol": 3.0, "ts": 0.01, "profit": 0.01})
    state = coin_states[symbol]
    
    # 3. 거래량 지표 계산
    avg_vol = df['volume'].iloc[-6:-1].mean()
    is_vol_spike = curr['volume'] > (avg_vol * setting['vol'])

    # 4. 매매 로직
    if not state['in_position']:
        # [매수 판단]
        if (price > curr['ema9_1h']) and (curr['rsi'] < 70) and is_vol_spike and (price > prev['close']):
            state['in_position'] = True
            state['entry_price'] = price
            state['highest_price'] = price
            
            save_trade_log(symbol, "BUY", price, reason="Vol Spike")
            save_current_status() # 상태 파일 갱신
            send_discord_notification(f"🚀 **[매수 완료]** {symbol}\n💰 가격: {price} USDT\n📈 전략: {setting['vol']}배 거래량 돌파")
    else:
        # [매도 판단]
        if price > state['highest_price']: state['highest_price'] = price
        current_profit = (price - state['entry_price']) / state['entry_price']
        is_ema_broken = price < curr['ema9']
        is_trailing_stop = price < (state['highest_price'] * (1 - setting['ts']))

        if is_trailing_stop or (is_ema_broken and current_profit > setting['profit']):
            reason = "TS" if is_trailing_stop else "EMA"
            save_trade_log(symbol, "SELL", price, profit=current_profit, reason=reason)
            
            state['in_position'] = False
            state['entry_price'] = 0
            save_current_status() # 상태 파일 갱신
            send_discord_notification(f"💰 **[매도 완료]** {symbol}\n📊 수익률: {current_profit*100:.2f}%\n📝 사유: {reason}")

# --- [메인 실행부] ---
if __name__ == "__main__":
    record_metadata()
    print("🚀 4개 코인 통합 드라이런 모니터링 시작...")
    send_discord_notification("🔔 통합 드라이런 모드 가동: 4개 코인 실시간 감시 중")
    
    while True:
        try:
            config = load_config() # 루프마다 설정을 새로 읽어 최적값 변경 시 즉시 반영
            for sym in symbols:
                print(f"🔍 {sym} 분석 중...", end='\r')
                monitor_symbol(sym, config)
                time.sleep(1) # API 과부하 방지
            
            print(f"\n✅ 한 바퀴 완료 ({datetime.now().strftime('%H:%M:%S')}) " + "-"*30)
            time.sleep(30) # 30초 휴식 후 다음 스캔
            
        except Exception as e:
            print(f"\n❌ 루프 에러: {e}")
            time.sleep(10)