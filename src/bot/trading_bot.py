import ccxt
import pandas as pd
import pandas_ta as ta
import json
import time
import os
from datetime import datetime
import subprocess

# 같은 폴더 내 모듈 임포트
from utils import send_discord
from asset_manager import get_order_config, update_trade_result, reset_all_queues

# --- [1. 경로 및 설정] ---
current_file_path = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(current_file_path, '..', '..'))
DATA_DIR = r"C:\Users\hojin\IdeaProjects\trading-backend\data"
CONFIG_PATH = os.path.join(ROOT_DIR, "bot_config.json")
SECRETS_PATH = os.path.join(ROOT_DIR, "secrets.json")

def load_secrets():
    with open(SECRETS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

secrets = load_secrets()

# --- [2. 거래소 연동 (실거래 모드)] ---
exchange = ccxt.binance({
    'apiKey': secrets.get("binance_api_key"),
    'secret': secrets.get("binance_secret_key"),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})
# 🚨 실거래를 위해 샌드박스 모드를 꺼줍니다 (주석 처리)
exchange.set_sandbox_mode(True) 

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
        # 🔍 터미널 제자리에서 분석 중임을 표시 (\r 사용)
        print(f"🔍 {symbol} 분석 중...          ", end='\r')
        
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
        
        # 데이터 부족 방어
        if not ohlcv or len(ohlcv) < 36:
            return

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df.dropna(inplace=True)
        
        df['ema9'] = ta.ema(df['close'], length=9)
        df['ema9_1h'] = ta.ema(df['close'], length=36)
        df['rsi'] = ta.rsi(df['close'], length=14)
        
        if df['ema9_1h'].iloc[-1] is None or df['rsi'].iloc[-1] is None:
            return
            
        curr, price = df.iloc[-1], df.iloc[-1]['close']
        setting = config.get(symbol, {"vol": 3.0, "ts": 0.01, "profit": 0.01})
        state = coin_states[symbol]
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # --- [매수 로직] ---
        if not state['in_position']:
            avg_vol = df['volume'].iloc[-6:-1].mean()
            if (price > curr['ema9_1h']) and (curr['rsi'] < 70) and (curr['volume'] > avg_vol * setting['vol']):
                
                # 💡 가상 시드 1000달러 기준 동적 배분
                TOTAL_VIRTUAL_SEED = 1000.0
                total_used = sum(s.get('used_seed', 0) for s in coin_states.values() if s['in_position'])
                free_balance = TOTAL_VIRTUAL_SEED - total_used
                
                lev, target_seed, status = get_order_config(symbol, TOTAL_VIRTUAL_SEED)
                
                if lev > 0:
                    actual_seed = min(target_seed, free_balance)
                    
                    if actual_seed < 5.0: # 5달러 미만이면 주문 불가
                        return 
                        
                    amount = (actual_seed * lev) / price
                    
                    try:
                        print(f"\n✨ [{now_str}] {symbol} 매수 진입 시도!")
                        exchange.set_leverage(int(lev), symbol)
                        exchange.create_market_buy_order(symbol, amount)
                        
                        state.update({"in_position": True, "entry_price": price, "highest_price": price, "amount": amount, "used_seed": actual_seed})
                        
                        save_data('trade_log.csv', {"timestamp": now_str, "symbol": symbol, "type": "BUY", "price": price, "profit_rate": 0, "reason": "거래량 돌파"}, False)
                        send_discord(f"🚀 **[매수 완료]** {symbol}\n📊 시장상태: {status}\n💰 진입가: {price} USDT\n📈 레버리지: {lev}x\n💵 투입시드: {actual_seed:.2f} (남은잔고: {free_balance - actual_seed:.2f})")
                        
                    except Exception as order_error:
                        print(f"\n⚠️ [{symbol} 주문 실패] {order_error}")

        # --- [매도 로직] ---
        else:
            state['highest_price'] = max(state['highest_price'], price)
            profit_rate = round(((price - state['entry_price']) / state['entry_price']) * 100, 2)
            
            is_ts = price < (state['highest_price'] * (1 - setting['ts']))
            is_ema = price < curr['ema9'] and (profit_rate/100) > setting['profit']

            if is_ts or is_ema:
                reason = "TS" if is_ts else "EMA"
                
                try:
                    print(f"\n💰 [{now_str}] {symbol} 매도 시도 (수익률: {profit_rate}%)")
                    exchange.create_market_sell_order(symbol, state['amount'])
                    update_trade_result(symbol, profit_rate)
                    save_data('trade_log.csv', {"timestamp": now_str, "symbol": symbol, "type": "SELL", "price": price, "profit_rate": profit_rate, "reason": reason}, False)
                    send_discord(f"💰 **[매도 완료]** {symbol}\n📊 수익률: {profit_rate}%\n📝 사유: {reason}")
                except Exception as sell_error:
                    print(f"\n⚠️ [{symbol} 매도 실패] {sell_error}")
                    
                state.update({"in_position": False, "entry_price": 0, "amount": 0, "used_seed": 0})
                
    except Exception as e:
        print(f"\n❌ Error {symbol}: {e}")

# --- [메인 실행부] ---
if __name__ == "__main__":
    print("========================================")
    print("🚀 시스템 가동 중... (Testnet: 1000 USDT)")
    print("========================================")
    
    last_checked_month = datetime.now().month

    while True:
        try:
            now = datetime.now()
            
            # 매월 1일 전략 최적화 자동화
            if now.month != last_checked_month and now.day == 1:
                print("\n📅 [시스템] 새로운 달 시작! 전략 최적화를 진행합니다...")
                reset_all_queues()
                
                # optimizer.py 실행
                optimizer_path = os.path.join(current_file_path, 'optimizer.py')
                if os.path.exists(optimizer_path):
                    subprocess.run(["python", optimizer_path])
                
                print("✅ [시스템] 최적화 완료. 최신 전략으로 구동을 재개합니다.")
                last_checked_month = now.month

            # 최신 설정값 로드
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {}
                
            for sym in symbols:
                monitor_symbol(sym, config)
                time.sleep(1.5)
                
            time.sleep(30)
            
        except Exception as e:
            print(f"\n[루프 에러] {e}")
            time.sleep(10)