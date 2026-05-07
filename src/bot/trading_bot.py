import ccxt
import pandas as pd
import pandas_ta as ta
import json
import time
import os
from datetime import datetime
import platform

from utils import send_discord
from asset_manager import get_order_config, update_trade_result, reset_all_queues

import subprocess

# --- 경로 (기존 유지) ---
current_file_path = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(current_file_path, '..', '..'))
DATA_DIR = r"C:\Users\hojin\IdeaProjects\trading-backend\data"
CONFIG_PATH = os.path.join(ROOT_DIR, "bot_config.json")
STATE_PATH = os.path.join(ROOT_DIR, "state.json")

last_checked_month = datetime.now().month
optimizer_path = os.path.join(current_file_path, 'optimizer.py')

os.makedirs(DATA_DIR, exist_ok=True)

# --- 거래소 ---
exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})
exchange.set_sandbox_mode(True)

symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT']

# --- 상태 ---
def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH, 'r', encoding='utf-8') as f:
            state = json.load(f)
    else:
        state = {}

    for sym in symbols:
        if sym not in state:
            state[sym] = {
                "in_position": False,
                "entry_price": 0,
                "highest_price": 0,
                "amount": 0,
                "used_seed": 0
            }

    if "global" not in state:
        state["global"] = {}

    state["global"].setdefault("peak", 1000.0)
    state["global"].setdefault("mdd", 0.0)
    state["global"].setdefault("trading_enabled", True)

    return state

def save_state(state):
    with open(STATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4)

coin_states = load_state()
live_monitor = {}

# --- 로그 ---
def save_log(data):
    path = os.path.join(DATA_DIR, "trade_log.csv")
    df = pd.DataFrame([data])
    df.to_csv(path, mode='a', header=not os.path.exists(path), index=False, encoding='utf-8-sig')

# --- 추가 ---
def save_equity():
    path = os.path.join(DATA_DIR, "equity_log.csv")

    balance = get_current_balance()
    mdd = coin_states["global"]["mdd"]

    df = pd.DataFrame([{
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "equity": balance,
        "mdd": round(mdd * 100, 2)
    }])

    df.to_csv(
        path,
        mode='a',
        header=not os.path.exists(path),
        index=False,
        encoding='utf-8-sig'
    )

def update_mdd():
    global coin_states

    balance = get_current_balance()

    peak = coin_states["global"]["peak"]

    if balance > peak:
        peak = balance

    mdd = (balance - peak) / peak

    coin_states["global"]["peak"] = peak
    coin_states["global"]["mdd"] = round(mdd, 4)

    # 🔥 계좌 보호
    if mdd <= -0.15:
        coin_states["global"]["trading_enabled"] = False
    else:
        coin_states["global"]["trading_enabled"] = True

    return mdd

def calculate_mdd(current, peak):
    if peak == 0:
        return 0
    return (current - peak) / peak  # 음수 값

def get_current_balance():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            config = json.load(f)

        return config.get("current_seed", 1000.0)

    return 1000.0

# --- 파라미터 미세조정 ---
def adjust_params(symbol):
    import pandas as pd

    LOG_PATH = r"C:\Users\hojin\IdeaProjects\trading-backend\data\trade_log.csv"

    if not os.path.exists(LOG_PATH):
        return

    df = pd.read_csv(LOG_PATH)
    df = df[df['symbol'] == symbol]
    df = df[df['type'] == 'SELL'].tail(10)

    if len(df) < 5:
        return

    winrate = (df['profit_rate'] > 0).mean()
    avg_profit = df['profit_rate'].mean()

    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)

    p = config[symbol]

    # 🔥 핵심 로직
    if winrate < 0.4:
        p['ts'] *= 1.1
        p['profit'] *= 1.1

    elif winrate > 0.7 and avg_profit < 0.5:
        p['profit'] *= 1.1

    # 범위 제한 (중요)
    p['ts'] = min(max(p['ts'], 0.005), 0.03)
    p['profit'] = min(max(p['profit'], 0.005), 0.05)

    config[symbol] = p

    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)

    print(f"⚙️ {symbol} 파라미터 자동 조정: {p}")

# --- 핵심 ---
def monitor_symbol(symbol, config):
    global coin_states, live_monitor
    if not coin_states["global"]["trading_enabled"]:
        return

    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=200)
        if len(ohlcv) < 50:
            return

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        df['ema9'] = ta.ema(df['close'], length=9)
        df['ema36'] = ta.ema(df['close'], length=36)
        df['rsi'] = ta.rsi(df['close'], length=14)

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        price = curr['close']
        avg_vol = df['volume'].iloc[-6:-1].mean()

        setting = config.get(symbol, {"vol": 3.0, "ts": 0.01, "profit": 0.01})
        state = coin_states[symbol]

        status_text = "보유중" if state['in_position'] else "대기"

        live_monitor[symbol] = {
            "price": round(price, 2),
            "rsi": round(curr['rsi'], 2),
            "ema36": round(curr['ema36'], 2),
            "status": status_text
        }

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        is_rising = price > prev['close']
        is_vol_spike = curr['volume'] > avg_vol * setting['vol']

        current_mdd = abs(coin_states["global"]["mdd"])

        # =====================
        # BUY
        # =====================
        if not state['in_position']:

            if price > curr['ema36'] and curr['rsi'] < 70 and is_vol_spike and is_rising:

                total_balance = config.get("current_seed", 1000)

                lev, seed, status = get_order_config(symbol, total_balance)

                # 🔥 MDD 기반 자동 리스크 감소
                if current_mdd > 0.05:
                    lev *= 0.7

                if current_mdd > 0.10:
                    lev *= 0.5

                lev = max(1.0, round(lev, 2))

                if lev > 0 and seed > 5:

                    entry_price = price * 1.0005
                    amount = (seed * lev) / entry_price

                    state.update({
                        "in_position": True,
                        "entry_price": entry_price,
                        "highest_price": entry_price,
                        "amount": amount,
                        "used_seed": seed
                    })

                    save_log({
                        "timestamp": now,
                        "symbol": symbol,
                        "type": "BUY",
                        "price": entry_price,
                        "reason": "volume_spike"
                    })

                    send_discord(
                        f"🚀 [매수]\n"
                        f"{symbol}\n"
                        f"가격: {entry_price:.2f}\n"
                        f"레버리지: {lev}x\n"
                        f"시드: {seed:.2f}\n"
                        f"상태: {status}"
                    )

                    print(f"🚀 BUY {symbol}")

        # =====================
        # SELL
        # =====================
        else:
            state['highest_price'] = max(state['highest_price'], price)

            entry = state['entry_price']
            highest = state['highest_price']

            profit_rate = (price - entry) / entry

            ts_active = highest > entry * 1.003

            is_ts = ts_active and price < highest * (1 - setting['ts'])
            is_ema = price < curr['ema9'] and profit_rate > setting['profit']

            if is_ts or is_ema:
                exit_price = price * 0.9995
                profit_percent = round(profit_rate * 100, 2)

                update_trade_result(symbol, profit_percent, state['used_seed'])

                adjust_params(symbol)

                save_log({
                    "timestamp": now,
                    "symbol": symbol,
                    "type": "SELL",
                    "price": exit_price,
                    "profit_rate": profit_percent,
                    "reason": "TS" if is_ts else "EMA"
                })

                send_discord(
                    f"💰 [매도]\n"
                    f"{symbol}\n"
                    f"수익률: {profit_percent}%\n"
                    f"사유: {'TS' if is_ts else 'EMA'}"
                )

                print(f"💰 SELL {symbol} {profit_percent}%")

                state.update({
                    "in_position": False,
                    "entry_price": 0,
                    "amount": 0,
                    "used_seed": 0
                })

        coin_states[symbol] = state

    except Exception as e:
        print(f"❌ {symbol} error:", e)

def clear_console():
    os.system('cls' if platform.system() == 'Windows' else 'clear')

# --- 실행 ---
if __name__ == "__main__":
    print("🚀 시뮬레이션 시작")
    
    coin_states = load_state()
    save_state(coin_states)

    while True:
        try:
            now = datetime.now()

            # ✅ 월 변경 감지 + 1일일 때 실행
            if now.month != last_checked_month and now.day == 1:
                print("\n📅 [시스템] 월간 리셋 + 옵티마이저 실행")

                # 1. 큐 리셋
                reset_all_queues()

                # 2. 옵티마이저 실행
                if os.path.exists(optimizer_path):
                    subprocess.run(["python", optimizer_path])

                # 3. 디스코드 알림
                send_discord("📅 월간 전략 업데이트 완료")

                last_checked_month = now.month

            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {}

            for sym in symbols:
                monitor_symbol(sym, config)
                time.sleep(1)

            # MDD 갱신
            update_mdd()

            # 자산 로그 저장
            save_equity()

            # 상태 저장
            save_state(coin_states)

            # =========================
            # 실시간 콘솔 모니터
            # =========================
            clear_console()

            current_balance = get_current_balance()
            current_mdd = coin_states["global"]["mdd"] * 100

            print("=" * 60)
            print(f"🚀 Hojin Trading Bot")
            print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"💰 현재 자산: ${current_balance:.2f}")
            print(f"📉 현재 MDD: {current_mdd:.2f}%")
            print("=" * 60)

            for sym in symbols:
                data = live_monitor.get(sym, {})

                print(
                    f"[{sym}] "
                    f"가격:{data.get('price', 0)} | "
                    f"RSI:{data.get('rsi', 0)} | "
                    f"EMA36:{data.get('ema36', 0)} | "
                    f"상태:{data.get('status', '대기')}"
                )

            print("=" * 60)

            time.sleep(30)

        except Exception as e:
            print("루프 에러:", e)
            time.sleep(5)