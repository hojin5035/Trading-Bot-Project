import ccxt
import pandas as pd
import pandas_ta as ta
import json
import time
import os
from datetime import datetime
from utils import send_discord_notification

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
        df.to_csv(path, mode='a', header=not os.path.exists(path), index=False, encoding='utf-8-sig')

def monitor_symbol(symbol, config):
    global coin_states
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

    if not state['in_position']:
        if (price > curr['ema9_1h']) and (curr['rsi'] < 70) and is_vol_spike and (price > df.iloc[-2]['close']):
            state.update({"in_position": True, "entry_price": price, "highest_price": price})
            save_data('trade_log.csv', {"timestamp": datetime.now(), "symbol": symbol, "type": "BUY", "price": price, "profit_rate": 0, "reason": "거래량 돌파"}, False)
            send_discord_notification(f"🚀 **[매수]** {symbol} | 가격: {price} | 전략: {setting['vol']}배 돌파")
    else:
        state['highest_price'] = max(state['highest_price'], price)
        profit = (price - state['entry_price']) / state['entry_price']
        if price < (state['highest_price'] * (1 - setting['ts'])) or (price < curr['ema9'] and profit > setting['profit']):
            reason = "TS" if price < (state['highest_price'] * (1 - setting['ts'])) else "EMA"
            save_data('trade_log.csv', {"timestamp": datetime.now(), "symbol": symbol, "type": "SELL", "price": price, "profit_rate": round(profit*100, 2), "reason": reason}, False)
            state.update({"in_position": False, "entry_price": 0})
            send_discord_notification(f"💰 **[매도]** {symbol} | 수익: {profit*100:.2f}% | 사유: {reason}")
    
    save_data('status.json', coin_states)

if __name__ == "__main__":
    if not os.path.exists('data/metadata.json'): save_data('metadata.json', {"start_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
    while True:
        try:
            with open('bot_config.json', 'r') as f: config = json.load(f)
            for sym in symbols:
                monitor_symbol(sym, config)
                time.sleep(1)
            print(f"✅ 스캔 완료 ({datetime.now().strftime('%H:%M:%S')})", end='\r')
            time.sleep(30)
        except Exception as e:
            print(f"❌ 에러: {e}"); time.sleep(10)