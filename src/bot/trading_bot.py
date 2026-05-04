import ccxt
import pandas as pd
import pandas_ta as ta
import json
import time
import os
import sys # <-- 추가
from datetime import datetime

# --- [경로 및 설정] ---
current_file_path = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(current_file_path, '..', '..'))

# 파이썬이 최상위 폴더(ROOT_DIR)를 인식하게 만듦 (utils import를 위해 필수)
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

# 이제 에러 없이 가져올 수 있습니다.
from utils import send_discord 
from asset_manager import get_order_config, update_trade_result, reset_all_queues

# 하드코딩된 경로 대신 프로젝트 구조에 맞춘 동적 경로 사용
DATA_DIR = os.path.join(ROOT_DIR, "data")
CONFIG_PATH = os.path.join(ROOT_DIR, "bot_config.json")
SECRETS_PATH = os.path.join(ROOT_DIR, "secrets.json")

# 보안 정보 로드 (거래소 객체 생성용)
def load_secrets_for_exchange():
    with open(SECRETS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

secrets = load_secrets_for_exchange()

# 거래소 설정
exchange = ccxt.binance({
    'apiKey': secrets.get("binance_api_key"),
    'secret': secrets.get("binance_secret_key"),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})
exchange.set_sandbox_mode(True) # 연습 모드

symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT']
coin_states = {sym: {"in_position": False, "entry_price": 0, "highest_price": 0, "amount": 0} for sym in symbols}
last_checked_month = datetime.now().month

def save_data(filename, data, is_json=True):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, filename)
    if is_json:
        with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, indent=4)
    else:
        df = pd.DataFrame([data])
        df.to_csv(path, mode='a', header=not os.path.exists(path), index=False, encoding='utf-8-sig')

def monitor_symbol(symbol, config):
    global coin_states
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['ema9'] = ta.ema(df['close'], length=9)
        df['ema9_1h'] = ta.ema(df['close'], length=36)
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        curr, price = df.iloc[-1], df.iloc[-1]['close']
        setting = config.get(symbol, {"vol": 3.0, "ts": 0.01, "profit": 0.01})
        state = coin_states[symbol]
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # [매수 로직]
        if not state['in_position']:
            avg_vol = df['volume'].iloc[-6:-1].mean()
            if (price > curr['ema9_1h']) and (curr['rsi'] < 70) and (curr['volume'] > avg_vol * setting['vol']):
                balance = exchange.fetch_balance()['total'].get('USDT', 0)
                lev, seed, status = get_order_config(symbol, balance)
                
                if lev > 0:
                    amount = (seed * lev) / price
                    exchange.set_leverage(int(lev), symbol)
                    exchange.create_market_buy_order(symbol, amount)
                    
                    state.update({"in_position": True, "entry_price": price, "highest_price": price, "amount": amount})
                    save_data('trade_log.csv', {"timestamp": now_str, "symbol": symbol, "type": "BUY", "price": price, "profit_rate": 0, "reason": "거래량 돌파"}, False)
                    
                    # 호진님의 utils.send_discord 사용
                    send_discord(f"🚀 **[매수 완료]** {symbol}\n💰 가격: {price} USDT\n📈 레버리지: {lev}x\n💵 투입시드: {seed:.2f} USDT")
        
        # [매도 로직]
        else:
            state['highest_price'] = max(state['highest_price'], price)
            profit_rate = round(((price - state['entry_price']) / state['entry_price']) * 100, 2)
            
            is_ts = price < (state['highest_price'] * (1 - setting['ts']))
            is_ema = price < curr['ema9'] and (profit_rate/100) > setting['profit']

            if is_ts or is_ema:
                reason = "TS" if is_ts else "EMA"
                exchange.create_market_sell_order(symbol, state['amount'])
                
                update_trade_result(symbol, profit_rate)
                save_data('trade_log.csv', {"timestamp": now_str, "symbol": symbol, "type": "SELL", "price": price, "profit_rate": profit_rate, "reason": reason}, False)
                
                # 호진님의 utils.send_discord 사용
                send_discord(f"💰 **[매도 완료]** {symbol}\n📊 수익률: {profit_rate}%\n📝 사유: {reason}")
                
                state.update({"in_position": False, "entry_price": 0, "amount": 0})
                
    except Exception as e:
        print(f"Error {symbol}: {e}")

if __name__ == "__main__":
    print(f"🚀 시스템 가동 중... (Testnet: {exchange.get_sandbox_mode()})")
    while True:
        try:
            now = datetime.now()
            if now.month != last_checked_month and now.day == 1:
                reset_all_queues()
                last_checked_month = now.month

            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
                
            for sym in symbols:
                monitor_symbol(sym, config)
                time.sleep(1)
            time.sleep(30)
        except Exception as e:
            print(f"루프 에러: {e}")
            time.sleep(10)