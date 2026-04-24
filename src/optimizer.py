import pandas as pd
import pandas_ta as ta
import json
import os
import sys
import ccxt # 혹시 설치 안 되어 있다면: pip install ccxt

def fetch_historical_data(symbol, timeframe='15m', days=90):
    """
    바이낸스에서 과거 데이터를 가져오는 함수
    """
    # 바이낸스 객체 생성 (로그인 없이 공용 API 사용)
    exchange = ccxt.binance()
    
    # 가져올 시작 시간 계산 (현재로부터 90일 전)
    since = exchange.milliseconds() - (days * 24 * 60 * 60 * 1000)
    all_ohlcv = []
    
    print(f"📡 바이낸스에서 {symbol} 데이터 불러오는 중...")
    
    # 바이낸스는 한 번에 500~1000개만 주므로 루프를 돌며 다 가져옵니다.
    while since < exchange.milliseconds():
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since)
        if not ohlcv:
            break
        all_ohlcv.extend(ohlcv)
        # 마지막 데이터의 다음 시간부터 다시 가져오기
        since = ohlcv[-1][0] + 1 
        
    # 데이터프레임 변환
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # 중복 제거 및 인덱스 설정
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    
    return df

def run_backtest(df, vol_mult, ts_percent, profit_limit):
    # 초기 설정
    cash = 1000.0
    stock = 0.0
    has_position = False
    entry_price = 0.0
    highest_price = 0.0
    fee_rate = 0.001  # 바이낸스 기본 수수료 0.1%
    
    # 지표 계산 (이미 밖에서 계산해서 넘겨줄 수도 있지만, 안전하게 내부에서 한 번 더 체크)
    if 'ema9' not in df.columns:
        df['ema9'] = ta.ema(df['close'], length=9)
    if 'rsi' not in df.columns:
        df['rsi'] = ta.rsi(df['close'], length=14)
    if 'ema9_1h' not in df.columns:
        df['ema9_1h'] = ta.ema(df['close'], length=36) # 15분봉 기준 9시간(9*4) 정도의 흐름

    # 백테스트 루프
    # 지표 계산을 위해 앞부분 일부(36봉)는 건너뜁니다.
    for i in range(36, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        price = curr['close']
        
        # 5봉 평균 거래량 대비 돌파 확인
        avg_vol = df['volume'].iloc[i-5:i].mean()
        vol_ratio = curr['volume'] / avg_vol if avg_vol > 0 else 0
        is_vol_spike = vol_ratio > vol_mult
        is_rising = price > prev['close']

        if not has_position:
            # [매수 조건] 추세 위 + RSI 70미만 + 거래량 폭증 + 상승세
            if (price > curr['ema9_1h']) and (curr['rsi'] < 70) and is_vol_spike and is_rising:
                stock = (cash / price) * (1 - fee_rate)
                cash = 0
                entry_price = price
                highest_price = price
                has_position = True
        else:
            # 고점 갱신 (트레일링 스탑용)
            if price > highest_price: 
                highest_price = price
            
            is_ema_broken = price < curr['ema9']
            is_trailing_stop = price < (highest_price * (1 - ts_percent))
            current_profit = (price - entry_price) / entry_price

            # [매도 조건] 트레일링 스탑 혹은 (수익권일 때만) EMA9 하향 돌파
            if is_trailing_stop or (is_ema_broken and current_profit > profit_limit):
                cash = (stock * price) * (1 - fee_rate)
                stock = 0
                has_position = False
                
    # 최종 자산 가치 반환 (현금 + 남은 주식의 현재가치)
    final_value = cash if cash > 0 else (stock * df.iloc[-1]['close'])
    return final_value

# 1. 프로그래스 바 함수 (전공자 느낌 물씬!)
def draw_progress_bar(current, total, bar_length=30):
    percent = float(current) * 100 / total
    arrow = '-' * int(percent / 100 * bar_length - 1) + '>'
    spaces = ' ' * (bar_length - len(arrow))
    sys.stdout.write(f'\r 진행도: [{arrow}{spaces}] {percent:.1f}% 완료')
    sys.stdout.flush()

# 2. 데이터 수집 함수 (90일치)
def get_90d_data(symbol):
    print(f"\n📥 {symbol} 데이터 수집 중...")
    
    df = fetch_historical_data(symbol, '15m', 90)
    
    # data 폴더가 없으면 생성
    if not os.path.exists('data'):
        os.makedirs('data')
        
    filename = f"data/{symbol.replace('/', '_')}_90d.csv"
    df.to_csv(filename, index=False)
    return df

# 3. 메인 하이브리드 옵티마이저
symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT']
final_config = {}

vol_list = [2.0, 2.5, 3.0, 3.5, 3.6]
ts_list = [0.007, 0.01, 0.015]
profit_list = [0.01, 0.015, 0.02]

# 전체 루프 횟수 (코인 수 * 파라미터 조합 수)
total_steps = len(symbols) * len(vol_list) * len(ts_list) * len(profit_list)
current_step = 0

for sym in symbols:
    df_total = get_90d_data(sym)
    
    # 30일 단위 슬라이싱 (15분봉 기준)
    df_recent = df_total.iloc[-2880:]
    df_mid = df_total.iloc[-5760:-2880]
    df_old = df_total.iloc[-8640:-5760]
    
    best_score = -999999
    best_params = {}

    print(f"🔎 {sym} 하이브리드 최적화 분석 시작...")
    
    for v in vol_list:
        for t in ts_list:
            for p in profit_list:
                # 가중치 4:6 및 5:3:2 로직 적용
                res_all = run_backtest(df_total, v, t, p)
                res_recent = run_backtest(df_recent, v, t, p)
                res_mid = run_backtest(df_mid, v, t, p)
                res_old = run_backtest(df_old, v, t, p)

                weighted_score = (res_recent * 0.5) + (res_mid * 0.3) + (res_old * 0.2)
                final_score = (res_all * 0.4) + (weighted_score * 0.6)

                if final_score > best_score:
                    best_score = final_score
                    best_params = {"vol": v, "ts": t, "profit": p}
                
                # 게이지 바 업데이트
                current_step += 1
                draw_progress_bar(current_step, total_steps)
    
    final_config[sym] = best_params
    print(f"\n✅ {sym} 최적화 완료! (Best Score: {best_score:.2f})")

# 4. JSON 파일 업데이트 (디스코드 정보 유지)
try:
    with open('bot_config.json', 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    config = {}

config.update(final_config)
with open('bot_config.json', 'w') as f:
    json.dump(config, f, indent=4)

print("\n✨ 모든 작업이 완료되었습니다! 'bot_config.json'이 최신화되었습니다.")