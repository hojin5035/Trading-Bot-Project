import ccxt
import pandas as pd
import pandas_ta as ta
import json
import time
from datetime import datetime
from utils import send_discord_notification

# 대상 코인 리스트
symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT']

# 각 코인별 상태(포지션 여부, 진입가 등)를 저장할 딕셔너리
# 4개를 동시에 돌려야 하므로 코인별로 상태 상자가 따로 있어야 합니다.
state = {symbol: {"in_position": False, "entry_price": 0, "highest_price": 0} for symbol in symbols}

def load_config():
    try:
        with open('bot_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# API 객체 생성
exchange = ccxt.binance()

def monitor_symbol(symbol):
    """특정 코인 한 개를 1회 검사하는 함수"""
    global state
    config = load_config()
    # 코인별 설정 가져오기 (없으면 기본값)
    setting = config.get(symbol, {"vol": 3.0, "ts": 0.01, "profit": 0.01})
    
    try:
        # 1. 데이터 수집
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
        vol_ratio = curr['volume'] / avg_vol if avg_vol > 0 else 0

        # 실시간 상태 출력
        pos_status = "보유 중" if state[symbol]["in_position"] else "대기 중"
        print(f"[{now}] {symbol:9} | 가격: {price:10.4f} | 거래량: {vol_ratio:4.1f}배 | {pos_status}")

        # 4. 매수/매도 로직
        if not state[symbol]["in_position"]:
            # [매수 조건 확인]
            if (price > curr['ema9_1h']) and (curr['rsi'] < 70) and (vol_ratio > setting['vol']) and (price > prev['close']):
                send_discord_notification(f"🚀 **[매수 완료]** {symbol}\n💰 가격: {price} USDT\n📈 전략: {setting['vol']}배 거래량 돌파")
                print(f"\n🔔🔔 [{symbol}] 매수 신호 발생! 가격: {price} 🔔🔔\n")
                state[symbol]["entry_price"] = price
                state[symbol]["highest_price"] = price
                state[symbol]["in_position"] = True
        else:
            # [매도 조건 확인]
            if price > state[symbol]["highest_price"]: 
                state[symbol]["highest_price"] = price
            
            current_profit = (price - state[symbol]["entry_price"]) / state[symbol]["entry_price"]
            is_ema_broken = price < curr['ema9']
            is_trailing_stop = price < (state[symbol]["highest_price"] * (1 - setting['ts']))

            if is_trailing_stop or (is_ema_broken and current_profit > setting['profit']):
                reason = "트레일링스탑" if is_trailing_stop else "EMA하향돌파"
                profit_pct = current_profit * 100
                color_emoji = "🟢" if profit_pct > 0 else "🔴"
                send_discord_notification(f"{color_emoji} **[매도 완료]** {symbol}\n💵 수익률: {profit_pct:.2f}%\n사유: {reason}")
                print(f"\n💰💰 [{symbol}] 매도 신호 발생! 사유: {reason}, 수익률: {profit_pct:.2f}% 💰💰\n")
                state[symbol]["in_position"] = False

    except Exception as e:
        print(f"❌ {symbol} 에러: {e}")

if __name__ == "__main__":
    print("🚀 4개 코인 통합 드라이런 모니터링 시작...")
    send_discord_notification("🔔 통합 드라이런 모드 가동: 4개 코인 실시간 감시 중")
    
    while True:
        for sym in symbols:
            monitor_symbol(sym)
            time.sleep(1) # API 과부하 방지용 짧은 휴식
        
        print("-" * 65) # 코인 한 바퀴 돌 때마다 구분선
        time.sleep(30) # 30초마다 전체 다시 스캔