import collections

# 각 코인별 최근 3거래일 승패 기록 (큐)
trade_queues = {
    'BTC/USDT': collections.deque(maxlen=3),
    'ETH/USDT': collections.deque(maxlen=3),
    'SOL/USDT': collections.deque(maxlen=3),
    'XRP/USDT': collections.deque(maxlen=3)
}

def get_order_config(symbol, total_balance):
    """최근 패배 횟수 기반 레버리지 조절 및 진입 제한"""
    q = trade_queues.get(symbol, collections.deque(maxlen=3))
    loss_count = list(q).count('L')
    
    # 3단계 레버리지 규칙 적용
    if loss_count <= 1: leverage = 2.0
    elif loss_count == 2: leverage = 1.5
    else: leverage = 1.0
    
    seed = total_balance * 0.25 # 25% 균등 분배
    
    # 직전 거래 패배 시 진입 제외 (자산 보호)
    if len(q) > 0 and q[-1] == 'L':
        return 0, 0, "Skip(Last Failed)"
        
    return leverage, seed, "Active"

def update_trade_result(symbol, profit_rate):
    """수익률을 받아 승패 기록 및 큐 업데이트"""
    if symbol in trade_queues:
        result = 'W' if profit_rate > 0 else 'L'
        trade_queues[symbol].append(result)
        print(f"[{symbol}] 결과 기록: {result} | 현재 큐: {list(trade_queues[symbol])}")

def reset_all_queues():
    """새로운 달 시작 시 모든 큐 초기화 (W로 채워 새 시작)"""
    for sym in trade_queues:
        trade_queues[sym].clear()
        for _ in range(3): trade_queues[sym].append('W')
    print("📅 [AssetManager] 모든 종목의 큐가 초기화되었습니다.")