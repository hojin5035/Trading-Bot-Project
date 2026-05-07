import pandas as pd
import pandas_ta as ta
import json
import os
import ccxt

# =========================
# 경로
# =========================

current_file_path = os.path.dirname(os.path.abspath(__file__))

ROOT_DIR = os.path.abspath(
    os.path.join(current_file_path, '..', '..')
)

DATA_DIR = os.path.join(ROOT_DIR, "data")

CONFIG_PATH = os.path.join(ROOT_DIR, "bot_config.json")

# =========================
# 데이터 수집
# =========================

def fetch_data(symbol):

    exchange = ccxt.binance()

    since = exchange.milliseconds() - (
        90 * 24 * 60 * 60 * 1000
    )

    all_ohlcv = []

    while True:

        ohlcv = exchange.fetch_ohlcv(
            symbol,
            timeframe='15m',
            since=since,
            limit=1500
        )

        if not ohlcv:
            break

        all_ohlcv.extend(ohlcv)

        since = ohlcv[-1][0] + 1

        if len(ohlcv) < 1500:
            break

    # =========================
    # DataFrame 생성
    # =========================

    df = pd.DataFrame(
        all_ohlcv,
        columns=[
            'timestamp',
            'open',
            'high',
            'low',
            'close',
            'volume'
        ]
    )

    # datetime 컬럼 생성
    df['datetime'] = pd.to_datetime(
        df['timestamp'],
        unit='ms'
    )

    # =========================
    # 지표 생성
    # =========================

    df['ema9'] = ta.ema(
        df['close'],
        length=9
    )

    df['ema36'] = ta.ema(
        df['close'],
        length=36
    )

    df['rsi'] = ta.rsi(
        df['close'],
        length=14
    )

    # =========================
    # 1시간봉 생성
    # =========================

    df_1h = df.resample(
        '1h',
        on='datetime'
    ).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    })

    # 1시간 EMA9
    df_1h['ema9_1h'] = ta.ema(
        df_1h['close'],
        length=9
    )

    # =========================
    # 병합 준비
    # =========================

    df = df.sort_values('datetime')

    df_1h = df_1h.reset_index()

    # merge_asof 병합
    df = pd.merge_asof(
        df,
        df_1h[['datetime', 'ema9_1h']],
        on='datetime',
        direction='backward'
    )

    return df

# =========================
# 백테스트
# =========================

def run_backtest(df, vol, ts, profit):

    if df.empty:
        return -999

    cash = 1000
    stock = 0

    equity_curve = []

    has_pos = False

    entry = 0
    high = 0

    for i in range(36, len(df)):

        curr = df.iloc[i]
        prev = df.iloc[i - 1]

        price = curr['close']

        # 거래량 조건
        avg_vol = df['volume'].iloc[i-5:i].mean()

        vol_spike = (
            curr['volume']
            > avg_vol * vol
        )

        # 상승 캔들
        rising = price > prev['close']

        # =========================
        # BUY
        # =========================

        if not has_pos:

            if (
                price > curr['ema9_1h']
                and price > curr['ema36']
                and curr['rsi'] < 70
                and vol_spike
                and rising
            ):

                stock = cash / price

                cash = 0

                entry = price

                high = price

                has_pos = True

        # =========================
        # SELL
        # =========================

        else:

            high = max(high, price)

            profit_rate = (
                (price - entry)
                / entry
            )

            is_ts = (
                price < high * (1 - ts)
            )

            is_ema_exit = (
                price < curr['ema9']
                and profit_rate > profit
            )

            if is_ts or is_ema_exit:

                cash = stock * price

                stock = 0

                has_pos = False

        # =========================
        # 자산곡선 기록
        # =========================

        equity = (
            cash
            if cash > 0
            else stock * price
        )

        equity_curve.append(equity)

    # =========================
    # 예외 처리
    # =========================

    if len(equity_curve) == 0:
        return -999

    # =========================
    # 최종 수익률
    # =========================

    final = equity_curve[-1]

    final_return = final / 1000

    # =========================
    # MDD 계산
    # =========================

    peak = equity_curve[0]

    mdd = 0

    for x in equity_curve:

        if x > peak:
            peak = x

        dd = (x - peak) / peak

        mdd = min(mdd, dd)

    # =========================
    # 점수
    # =========================

    score = (
        (final_return ** 1.2)
        / (abs(mdd) + 0.001)
    )

    return score

# =========================
# 최적화 대상
# =========================

symbols = [
    'BTC/USDT',
    'ETH/USDT',
    'SOL/USDT',
    'XRP/USDT'
]

vol_list = [
    2.5,
    3.0,
    3.5,
    3.8
]

ts_list = [
    0.007,
    0.01,
    0.015
]

profit_list = [
    0.01,
    0.015,
    0.02
]

# =========================
# 최적화 실행
# =========================

final_config = {}

for sym in symbols:

    print(f"\n{sym} optimizing...")

    df = fetch_data(sym)

    best_score = -999

    best = {}

    for v in vol_list:

        for t in ts_list:

            for p in profit_list:

                score = run_backtest(
                    df.copy(),
                    v,
                    t,
                    p
                )

                if score > best_score:

                    best_score = score

                    best = {
                        "vol": v,
                        "ts": t,
                        "profit": p
                    }

    final_config[sym] = best

    print(
        f"{sym} BEST:",
        best,
        "SCORE:",
        round(best_score, 4)
    )

# =========================
# config 저장
# =========================

if os.path.exists(CONFIG_PATH):

    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)

else:

    config = {}

# 기존 값 유지 + 전략만 갱신
config.update(final_config)

with open(CONFIG_PATH, 'w') as f:

    json.dump(
        config,
        f,
        indent=4
    )

print("\n✅ MDD 기반 최적화 완료")