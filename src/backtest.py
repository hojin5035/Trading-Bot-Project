import pandas as pd
import pandas_ta as ta
import json

def load_config():
    """최적화된 파라미터 로드"""
    try:
        with open('bot_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ 설정 파일이 없습니다. optimizer.py를 먼저 실행하세요.")
        return None

def run_single_backtest(file_path, symbol, setting):
    """특정 코인 하나에 대한 상세 백테스팅"""
    df = pd.read_csv(file_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # 지표 계산
    df['ema9'] = ta.ema(df['close'], length=9)
    df['rsi'] = ta.rsi(df['close'], length=14)
    df['ema9_1h'] = ta.ema(df['close'], length=36)
    
    # 설정값 적용
    VOL_MULT = setting['vol']
    TS_PERCENT = setting['ts']
    PROFIT_LIMIT = setting['profit']
    
    cash = 1000.0
    stock = 0.0
    has_position = False
    entry_price = 0.0
    highest_price = 0.0
    fee_rate = 0.001
    history = []

    for i in range(36, len(df)):
        curr = df.iloc[i]
        prev = df.iloc[i-1]
        price = curr['close']
        
        # 실시간 평균 거래량 (직전 5봉)
        avg_vol = df['volume'].iloc[i-5:i].mean()
        is_vol_spike = curr['volume'] > (avg_vol * VOL_MULT)

        if not has_position:
            if (price > curr['ema9_1h']) and (curr['rsi'] < 70) and is_vol_spike and (price > prev['close']):
                stock = (cash / price) * (1 - fee_rate)
                cash = 0
                entry_price = price
                highest_price = price
                has_position = True
                history.append(f"  [{curr['timestamp']}] BUY: {price:.4f}")
        else:
            if price > highest_price: highest_price = price
            
            is_ema_broken = price < curr['ema9']
            is_trailing_stop = price < (highest_price * (1 - TS_PERCENT))
            current_profit = (price - entry_price) / entry_price

            if is_trailing_stop or (is_ema_broken and current_profit > PROFIT_LIMIT):
                cash = (stock * price) * (1 - fee_rate)
                reason = "TS" if is_trailing_stop else "EMA"
                profit_pct = current_profit * 100
                history.append(f"  [{curr['timestamp']}] SELL: {price:.4f} ({reason}) | 수익률: {profit_pct:.2f}%")
                stock = 0
                has_position = False

    final_val = cash if cash > 0 else (stock * df.iloc[-1]['close'])
    return final_val, history

# --- 메인 실행부 ---
if __name__ == "__main__":
    config = load_config()
    if config:
        total_initial_cash = 0
        total_final_cash = 0
        
        print("📊 [통합 백테스팅 리포트 시작]")
        print("=" * 60)
        
        for symbol, setting in config.items():
            # 파일명 변환 (BTC/USDT -> BTC_USDT_30d.csv)
            file_name = f"{symbol.replace('/', '_')}_30d.csv"
            
            try:
                final_balance, logs = run_single_backtest(file_name, symbol, setting)
                
                print(f"\n🪙 코인: {symbol}")
                print(f"🛠️ 설정: {setting}")
                # 상위 5개 로그만 출력 (너무 길면 보기 힘드니까요!)
                for log in logs[:5]: print(log) 
                if len(logs) > 5: print(f"  ...외 {len(logs)-5}건의 거래 발생")
                print(f"💰 최종 잔고: {final_balance:.2f} USDT")
                
                total_initial_cash += 1000
                total_final_cash += final_balance
                
            except FileNotFoundError:
                print(f"⚠️ {file_name} 파일을 찾을 수 없어 건너뜁니다.")

        print("\n" + "=" * 60)
        print(f"📈 전체 결과 요약")
        print(f" - 총 투자 원금: {total_initial_cash:.2f} USDT")
        print(f" - 총 최종 잔고: {total_final_cash:.2f} USDT")
        print(f" - 전체 수익률: {((total_final_cash - total_initial_cash) / total_initial_cash) * 100:.2f}%")
        print("=" * 60)