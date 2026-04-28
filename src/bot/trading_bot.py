import ccxt
import pandas as pd
import pandas_ta as ta
import json
import time
import os
from datetime import datetime
from utils import send_discord_notification

# 파일 절대 경로 고정
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT_DIR, "bot_config.json")
SECRETS_PATH = os.path.join(ROOT_DIR, "secrets.json")

# --- [설정 및 상태] ---
symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT']
exchange = ccxt.binance({'enableRateLimit': True})
coin_states = {sym: {"in_position": False, "entry_price": 0, "highest_price": 0, "current_price": 0} for sym in symbols}

def save_data(filename, data, is_json=True):
    os.makedirs('data', exist_ok=True)
    path = f'data/{filename}'
    if is_json:
        with open(path, 'w') as f: json.dump(data, f)
    else: # CSV (Trade Log)
        df = pd.DataFrame([data])
        # [보완] 인코딩 utf-8-sig로 한글 깨짐 방지
        df.to_csv(path, mode='a', header=not os.path.exists(path), index=False, encoding='utf-8-sig')

def monitor_symbol(symbol, config):
    global coin_states
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # 지표 계산
        df['ema9'] = ta.ema(df['close'], length=9)
        df['ema9_1h'] = ta.ema(df['close'], length=36)
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        curr = df.iloc[-1]
        price = curr['close']
        coin_states[symbol]['current_price'] = price # 실시간 가격 업데이트
        
        setting = config.get(symbol, {"vol": 3.0, "ts": 0.01, "profit": 0.01})
        state = coin_states[symbol]
        avg_vol = df['volume'].iloc[-6:-1].mean()
        is_vol_spike = curr['volume'] > (avg_vol * setting['vol'])

        # [수정] 현재 시간 문자열화 (CSV 호환성)
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if not state['in_position']:
            if (price > curr['ema9_1h']) and (curr['rsi'] < 70) and is_vol_spike and (price > df.iloc[-2]['close']):
                state.update({"in_posion": True, "entry_price": price, "highest_price": price})
                save_data('trade_log.csv', {"timestamp": now_str, "symbol": symbol, "type": "BUY", "price": price, "profit_rate": 0, "reason": "거래량 돌파"}, False)
                send_discord_notification(f"🚀 **[매수 완료]** {symbol}\n💰 가격: {price} USDT\n📈 전략: {setting['vol']}배 돌파")
        else:
            state['highest_price'] = max(state['highest_price'], price)
            profit = (price - state['entry_price']) / state['entry_price']
            
            # 매도 조건 (TS 혹은 EMA 이탈)
            is_ts = price < (state['highest_price'] * (1 - setting['ts']))
            is_ema = price < curr['ema9'] and profit > setting['profit']

            if is_ts or is_ema:
                reason = "TS" if is_ts else "EMA"
                save_data('trade_log.csv', {"timestamp": now_str, "symbol": symbol, "type": "SELL", "price": price, "profit_rate": round(profit*100, 2), "reason": reason}, False)
                state.update({"in_position": False, "entry_price": 0})
                send_discord_notification(f"💰 **[매도 완료]** {symbol}\n📊 수익률: {profit*100:.2f}%\n📝 사유: {reason}")
        
        save_data('status.json', coin_states)
    except Exception as e:
        print(f"\n[Error in {symbol}]: {e}")

def load_config():
    try:
        with open(CONFIG_PATH, 'r') as f: return json.load(f)
    except: return {}

if __name__ == "__main__":
    os.makedirs('data', exist_ok=True)
    # 실행 시마다 시작 시간을 현재로 강제 갱신
    save_data('metadata.json', {"start_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
    
    print(f"🚀 퀀트 매매 시스템 가동 및 가동 시간 리셋 완료")
    
    while True:
        try:
            config = load_config()
            current_time = datetime.now().strftime('%H:%M:%S')
            
            for i, sym in enumerate(symbols):
                # 닉네임 없이 깔끔한 진행 로그
                print(f"[{i+1}/{len(symbols)}] {current_time} | 🔍 {sym} 분석 중...          ", end='\r')
                monitor_symbol(sym, config)
                time.sleep(1.5)
            
            print(f"\n✅ {current_time} 스캔 완료! (30초 대기) " + "-"*20)
            time.sleep(30)
            
        except Exception as e:
            print(f"\n❌ 루프 에러: {e}")
            time.sleep(10)