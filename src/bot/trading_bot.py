import ccxt
import pandas as pd
import pandas_ta as ta
import json
import time
import os
import sys  # <--- 경로 추가를 위해 필요
from datetime import datetime

# --- [경로 설정 및 모듈 로드 해결] ---
# 현재 파일(trading_bot.py)의 위치: src/bot/
current_file_path = os.path.dirname(os.path.abspath(__file__))
# 프로젝트의 루트(TradingBot/) 경로를 잡습니다.
# os.path.join(current_file_path, '..', '..')를 통해 위로 두 번 올라갑니다.
ROOT_DIR = os.path.abspath(os.path.join(current_file_path, '..', '..'))

# src 폴더를 파이썬 탐색 경로에 추가하여 utils를 찾을 수 있게 합니다.
SRC_DIR = os.path.join(ROOT_DIR, 'src')
if SRC_DIR not in sys.path:
    sys.path.append(SRC_DIR)

try:
    from utils import send_discord_notification
except ModuleNotFoundError:
    # 혹시 몰라 한 번 더 예외 처리 (파일 구조가 다를 경우 대비)
    def send_discord_notification(msg): print(f"[Discord Mock]: {msg}")

# 설정 파일들은 최상위(ROOT_DIR)에 있다고 가정합니다.
CONFIG_PATH = os.path.join(ROOT_DIR, "bot_config.json")
SECRETS_PATH = os.path.join(ROOT_DIR, "secrets.json")
# 데이터 저장 폴더도 최상위의 data 폴더로 고정
DATA_DIR = os.path.join(ROOT_DIR, "data")

# --- [설정 및 상태] ---
symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT']
exchange = ccxt.binance({'enableRateLimit': True})
coin_states = {sym: {"in_position": False, "entry_price": 0, "highest_price": 0, "current_price": 0} for sym in symbols}

def save_data(filename, data, is_json=True):
    os.makedirs(DATA_DIR, exist_ok=True) # 최상위 data 폴더 생성
    path = os.path.join(DATA_DIR, filename)
    if is_json:
        with open(path, 'w', encoding='utf-8') as f: 
            json.dump(data, f, indent=4, ensure_ascii=False)
    else: # CSV (Trade Log)
        df = pd.DataFrame([data])
        # 인코딩 utf-8-sig로 한글 깨짐 방지
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
        coin_states[symbol]['current_price'] = price
        
        setting = config.get(symbol, {"vol": 3.0, "ts": 0.01, "profit": 0.01})
        state = coin_states[symbol]
        avg_vol = df['volume'].iloc[-6:-1].mean()
        is_vol_spike = curr['volume'] > (avg_vol * setting['vol'])

        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if not state['in_position']:
            # 롱 진입 로직: 1시간 이평선 위 + RSI 70미만 + 거래량 폭증 + 전봉 대비 상승
            if (price > curr['ema9_1h']) and (curr['rsi'] < 70) and is_vol_spike and (price > df.iloc[-2]['close']):
                state.update({"in_position": True, "entry_price": price, "highest_price": price})
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
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f: 
            return json.load(f)
    except: 
        return {}

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    save_data('metadata.json', {"start_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
    
    print(f"🚀 퀀트 매매 시스템 가동 (루트: {ROOT_DIR})")
    
    while True:
        try:
            config = load_config()
            current_time = datetime.now().strftime('%H:%M:%S')
            
            for i, sym in enumerate(symbols):
                print(f"[{i+1}/{len(symbols)}] {current_time} | 🔍 {sym} 분석 중...          ", end='\r')
                monitor_symbol(sym, config)
                time.sleep(1.5)
            
            print(f"\n✅ {current_time} 스캔 완료! (30초 대기) " + "-"*20)
            time.sleep(30)
            
        except Exception as e:
            print(f"\n❌ 루프 에러: {e}")
            time.sleep(10)