import ccxt
import pandas as pd
import pandas_ta as ta
import json
import time

# 1. 설정 및 API 로드
def load_config():
    with open('bot_config.json', 'r') as f:
        return json.load(f)

# API 키는 보안을 위해 별도 파일이나 환경변수로 관리하는 것이 좋습니다.
exchange = ccxt.binance({
    'apiKey': 'YOUR_API_KEY',
    'secret': 'YOUR_SECRET_KEY',
    'enableRateLimit': True,
})

def fetch_realtime_data(symbol):
    """실시간 데이터 수집 및 지표 계산"""
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=100)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['ema9'] = ta.ema(df['close'], length=9)
    df['ema9_1h'] = ta.ema(df['close'], length=36)
    df['rsi'] = ta.rsi(df['close'], length=14)
    return df

def run_real_trading(symbol):
    config = load_config()
    setting = config.get(symbol, {"vol": 3.0, "ts": 0.01, "profit": 0.01})
    
    print(f"📡 {symbol} 실전 감시 시작... (설정: {setting})")
    
    in_position = False
    entry_price = 0
    highest_price = 0

    while True:
        try:
            df = fetch_realtime_data(symbol)
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            price = curr['close']
            
            # 거래량 돌파 확인
            avg_vol = df['volume'].iloc[-6:-1].mean()
            is_vol_spike = curr['volume'] > (avg_vol * setting['vol'])

            if not in_position:
                # [매수 로직]
                if (price > curr['ema9_1h']) and (curr['rsi'] < 70) and is_vol_spike and (price > prev['close']):
                    # ⚠️ 실제 주문 예시 (주석 해제 시 실제 주문 나감)
                    # exchange.create_market_buy_order(symbol, amount) 
                    print(f"🔥 [{symbol}] 매수 신호 발생! 가격: {price}")
                    entry_price = price
                    highest_price = price
                    in_position = True
            else:
                # [매도 로직]
                if price > highest_price: highest_price = price
                
                current_profit = (price - entry_price) / entry_price
                is_ema_broken = price < curr['ema9']
                is_trailing_stop = price < (highest_price * (1 - setting['ts']))

                if is_trailing_stop or (is_ema_broken and current_profit > setting['profit']):
                    # ⚠️ 실제 주문 예시
                    # exchange.create_market_sell_order(symbol, amount)
                    reason = "TS" if is_trailing_stop else "EMA"
                    print(f"💰 [{symbol}] 매도 실행! 사유: {reason}, 수익률: {current_profit*100:.2f}%")
                    in_position = False
            
            time.sleep(30) # 30초마다 갱신

        except Exception as e:
            print(f"❌ 에러 발생: {e}")
            time.sleep(10)

if __name__ == "__main__":
    # 테스트로 XRP 먼저 감시
    run_real_trading('XRP/USDT')