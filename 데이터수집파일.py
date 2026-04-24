import ccxt
import pandas as pd
import time
from datetime import datetime

exchange = ccxt.binance()

def fetch_historical_data(symbol, timeframe='15m', days=30):
    # 현재 시간 기준 밀리초 계산
    now = exchange.milliseconds()
    since = now - (days * 24 * 60 * 60 * 1000)
    
    all_ohlcv = []
    
    print(f"🚀 {symbol} 수집 시작: {datetime.fromtimestamp(since/1000)} 부터 현재까지")

    while since < now:
        try:
            # 데이터를 가져옴
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since, limit=1000)
            if not ohlcv:
                break
            
            all_ohlcv.extend(ohlcv)
            
            # 진행 상황 출력 (이게 있어야 안 답답합니다!)
            last_date = datetime.fromtimestamp(ohlcv[-1][0]/1000)
            print(f"📊 데이터 수집 중... 마지막 데이터 날짜: {last_date}")
            
            # 다음 데이터를 위해 시간 갱신
            since = ohlcv[-1][0] + 1
            time.sleep(0.2) # 바이낸스 API 호출 제한 방지
            
        except Exception as e:
            print(f"❌ 에러 발생, 5초 후 재시도: {e}")
            time.sleep(5)
            
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# 실행 부분
symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT']

for sym in symbols:
    df = fetch_historical_data(sym, '15m', 30)
    filename = f"{sym.replace('/', '_')}_30d.csv"
    df.to_csv(filename, index=False)
    print(f"✅ {sym} 저장 완료!")