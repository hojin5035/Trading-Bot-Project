import collections
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "..", "..", "bot_config.json")

trade_queues = {sym: collections.deque(maxlen=3) for sym in ['BTC/USDT','ETH/USDT','SOL/USDT','XRP/USDT']}

def load_json_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json_config(config):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4)

def get_total_balance():
    config = load_json_config()
    ind = config.get("individual_balances", {})
    pool = config.get("shared_profit_pool", 0.0)
    return sum(ind.values()) + pool

def get_order_config(symbol, total_balance):
    config = load_json_config()
    ind = config.get("individual_balances", {})
    pool = config.get("shared_profit_pool", 0.0)

    q = trade_queues[symbol]
    loss_count = list(q).count('L')

    leverage = 2.0 if loss_count <= 1 else (1.5 if loss_count == 2 else 1.0)

    active = [s for s,q in trade_queues.items() if len(q)==0 or q[-1] != 'L']

    if symbol in active:
        n = max(len(active),1)
        seed = ind.get(symbol,250) + (pool/n)
        status = "Active"
    else:
        return 0,0,"Skip"

    return leverage, seed, status

def update_trade_result(symbol, profit_rate, used_seed):
    config = load_json_config()
    ind = config.get("individual_balances", {})
    pool = config.get("shared_profit_pool", 0.0)

    profit = used_seed * (profit_rate/100)
    trade_queues[symbol].append('W' if profit_rate>0 else 'L')

    if profit > 0:
        pool += profit
    else:
        ind[symbol] += profit

    config.update({
        "individual_balances": ind,
        "shared_profit_pool": pool,
        "current_seed": sum(ind.values()) + pool
    })

    save_json_config(config)

def reset_all_queues():
    for s in trade_queues:
        trade_queues[s].clear()
        for _ in range(3):
            trade_queues[s].append('W')