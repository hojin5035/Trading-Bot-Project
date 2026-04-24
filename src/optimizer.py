import pandas as pd
import pandas_ta as ta
import json

def run_backtest(df, vol_mult, ts_percent, profit_limit):
    cash = 1000.0
    stock = 0.0
    has_position = False
    entry_price = 0.0
    highest_price = 0.0
    fee_rate = 0.001
    
    # 지표 미리 계산
    df['ema9'] = ta.ema(df['close'], length=9)
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['ema9_1h'] = ta.ema(df['close'], length=36)
    
    for i in range(36, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        price = curr['close']
        
        # 5봉 평균 거래량 대비 돌파 확인
        avg_vol = df['volume'].iloc[i-5:i].mean()
        is_vol_spike = curr['volume'] > (avg_vol * vol_mult)
        is_rising = price > prev['close']

        if not has_position:
            # [매수 조건] 1시간 추세 위 + RSI 70미만 + 거래량 폭증 + 상승세
            if (price > curr['ema9_1h']) and (curr['rsi'] < 70) and is_vol_spike and is_rising:
                stock = (cash / price) * (1 - fee_rate)
                cash = 0
                entry_price = price
                highest_price = price
                has_position = True
        else:
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
                
    return cash if cash > 0 else (stock * df.iloc[-1]['close'])

# 최적화 타겟 설정
raw_files = ['BTC_USDT_30d.csv', 'ETH_USDT_30d.csv', 'SOL_USDT_30d.csv', 'XRP_USDT_30d.csv']

# 앞에 'data/'를 싹 다 붙여버리기
target_files = [f"data/{f}" for f in raw_files]
final_config = {}

for file in target_files:
    print(f"🔎 {file} 최적화 중...")
    df_test = pd.read_csv(file)

    symbol = file.replace('data/', '').replace('_30d.csv', '').replace('_', '/')

    best_cash = 0
    best_params = {}

    # 그리드 서치 범위 (거래량, 트레일링스탑, 익절제한)
    for v in [2.0, 2.5, 3.0, 3.5, 3.6, 3.7]:
        for t in [0.005, 0.007, 0.01, 0.015]:
            for p in [0.005, 0.01, 0.015]:
                final_cash = run_backtest(df_test, v, t, p)
                if final_cash > best_cash:
                    best_cash = final_cash
                    best_params = {"vol": v, "ts": t, "profit": p}
    
    final_config[symbol] = best_params
    print(f"✅ {symbol} 완료: {best_cash:.2f} USDT")

# JSON 파일로 내보내기
try:
    # 1. 기존 설정(디스코드 주소 등)을 먼저 읽어옵니다.
    with open('bot_config.json', 'r') as f:
        existing_config = json.load(f)
except FileNotFoundError:
    # 파일이 없으면 빈 딕셔너리로 시작
    existing_config = {}

# 2. 기존 데이터에 이번에 최적화한 final_config 내용을 합칩니다.
# update()를 쓰면 기존 discord_webhook_url은 유지되고 파라미터만 바뀝니다.
existing_config.update(final_config)

# 3. 합쳐진 데이터를 다시 저장합니다.
with open('bot_config.json', 'w') as f:
    json.dump(existing_config, f, indent=4)

print("\n✨ 'bot_config.json' 업데이트 완료! (디스코드 설정 보존)")