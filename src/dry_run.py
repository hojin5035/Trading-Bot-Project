import ccxt
import pandas as pd
import pandas_ta as ta
import json
import time
from datetime import datetime

def load_config():
    with open('bot_config.json', 'r') as f:
        return json.load(f)

# API 키 없이 공용(public) 데이터만 가져오기
exchange = ccxt.binance()

def run_simulation_mode(symbol):
    config = load_config()
    setting = config.get(symbol, {"vol": 3.0, "ts": 0.01, "profit": 0.01})
    
    print(f"📡 {symbol} 실시간 가상 모드 가동 중...")
    print(f"⚙️ 설정: 거래량 {setting['vol']}배 / TS {setting['ts']*100}% / 익절제한 {setting['profit']*100}%")
    print("-" * 50)
    
    in_position = False
    entry_price = 0
    highest_price = 0

    while True:
        try:
            # 1. 15분봉 데이터 수집 (API 키 필요 없음)
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # 2. 지표 계산
            df['ema9'] = ta.ema(df['close'], length=9)
            df['ema9_1h'] = ta.ema(df['close'], length=36)
            df['rsi'] = ta.rsi(df['close'], length=14)
            
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            price = curr['close']
            now = datetime.now().strftime('%H:%M:%S')
            
            # 3. 거래량 체크
            avg_vol = df['volume'].iloc[-6:-1].mean()
            vol_ratio = curr['volume'] / avg_vol

            # 실시간 상태 출력 (로그)
            status = "보유 중" if in_position else "대기 중"
            print(f"[{now}] 가격: {price:.4f} | RSI: {curr['rsi']:.1f} | 거래량: {vol_ratio:.1f}배 | 상태: {status}")

            if not in_position:
                # 매수 조건 확인
                if (price > curr['ema9_1h']) and (curr['rsi'] < 70) and (vol_ratio > setting['vol']) and (price > prev['close']):
                    print(f"\n🔔🔔 [매수 신호 발생!] 가격: {price} 🔔🔔\n")
                    entry_price = price
                    highest_price = price
                    in_position = True
            else:
                # 매도 조건 확인 (트레일링 스탑)
                if price > highest_price: highest_price = price
                
                current_profit = (price - entry_price) / entry_price
                is_ema_broken = price < curr['ema9']
                is_trailing_stop = price < (highest_price * (1 - setting['ts']))

                if is_trailing_stop or (is_ema_broken and current_profit > setting['profit']):
                    reason = "트레일링스탑" if is_trailing_stop else "EMA하향돌파"
                    print(f"\n💰💰 [매도 신호 발생!] 사유: {reason}, 수익률: {current_profit*100:.2f}% 💰💰\n")
                    in_position = False
            
            # 15분 봉이지만 실시간 느낌을 위해 30초마다 갱신
            time.sleep(30) 

        except Exception as e:
            print(f"❌ 에러: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_simulation_mode('XRP/USDT')