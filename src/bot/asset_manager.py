import collections
import json
import os

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "..", "..", "bot_config.json")

# 승패 기록 큐
trade_queues = {sym: collections.deque(maxlen=3) for sym in ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT']}

def load_json_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f: return json.load(f)
    return {}

def save_json_config(config):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f: json.dump(config, f, indent=4)

def get_order_config(symbol, total_balance):
    """수익은 나누고 손실은 격리하는 시드 배분 로직"""
    config = load_json_config()
    ind_bal = config.get("individual_balances", {s: 250.0 for s in trade_queues.keys()})
    shared_pool = config.get("shared_profit_pool", 0.0)
    
    q = trade_queues.get(symbol, collections.deque(maxlen=3))
    loss_count = list(q).count('L')
    
    # 1. 레버리지 결정
    if loss_count <= 1: leverage = 2.0
    elif loss_count == 2: leverage = 1.5
    else: leverage = 1.0
    
    # 2. 진입 가능 확인 (직전 'L' 시 Skip)
    active_symbols = [s for s, que in trade_queues.items() if len(que) == 0 or que[-1] != 'L']
    
    if symbol in active_symbols:
        n_active = max(len(active_symbols), 1)
        target_seed = ind_bal.get(symbol, 250.0) + (shared_pool / n_active)
        status = "Active"
    else:
        leverage, target_seed, status = 0, 0, "Skip(Last Failed)"
        
    return leverage, target_seed, status

def update_trade_result(symbol, profit_rate, used_seed):
    """결과에 따라 수익 풀 또는 개별 원금 업데이트"""
    config = load_json_config()
    ind_bal = config.get("individual_balances", {s: 250.0 for s in trade_queues.keys()})
    shared_pool = config.get("shared_profit_pool", 0.0)
    
    profit_amount = used_seed * (profit_rate / 100)
    trade_queues[symbol].append('W' if profit_rate > 0 else 'L')
    
    if profit_amount > 0: shared_pool += profit_amount # 수익 공유
    else: ind_bal[symbol] += profit_amount # 손실 격리
    
    config.update({"individual_balances": ind_bal, "shared_profit_pool": shared_pool, "current_seed": sum(ind_bal.values()) + shared_pool})
    save_json_config(config)

def reset_all_queues():
    for sym in trade_queues:
        trade_queues[sym].clear()
        for _ in range(3): trade_queues[sym].append('W')