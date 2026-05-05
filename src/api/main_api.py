import json
import os
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 리액트 통신 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 경로 설정 (호진님의 경로에 맞게 확인) ---
LOG_PATH = r"C:\Users\hojin\IdeaProjects\trading-backend\data\trade_log.csv"
CONFIG_PATH = r"C:\Users\hojin\OneDrive\Desktop\TradingBot\bot_config.json"

def get_analyzed_data():
    """CSV를 분석하여 승률, 레버리지, 누적 수익/손실을 한 번에 계산합니다."""
    if not os.path.exists(LOG_PATH):
        return {}, {}, {}
    
    try:
        df = pd.read_csv(LOG_PATH)
        if df.empty:
            return {}, {}, {}
        
        df.columns = [c.lower() for c in df.columns] # 컬럼명 소문자 통일
        
        win_rates = {}
        leverages = {}
        cumulative_stats = {}

        for symbol, group in df.groupby('symbol'):
            # 1. 승률 계산
            total_trades = len(group)
            wins = len(group[group['profit_rate'] > 0])
            win_rates[symbol] = f"{(wins / total_trades) * 100:.1f}%"

            # 2. 레버리지 계산 (최근 3경기에 따른 호진님 공식)
            recent_trades = group.tail(3)
            recent_profits = recent_trades['profit_rate'].tolist()
            losses = len([p for p in recent_profits if p <= 0])
            
            if len(recent_profits) < 3:
                base_lev = 1.0
            elif losses <= 1: # 패배 1개 이하 -> 2배
                base_lev = 2.0
            elif losses == 2: # 패배 2개 -> 1.5배
                base_lev = 1.5
            else:             # 패배 3개 -> 1배
                base_lev = 1.0
            leverages[symbol] = f"{base_lev}x"

            # 3. 누적 수익/손실 계산 (막대그래프용)
            # profit_rate가 양수인 것들의 합 / 음수인 것들의 합(절댓값)
            pos_sum = group[group['profit_rate'] > 0]['profit_rate'].sum()
            neg_sum = abs(group[group['profit_rate'] < 0]['profit_rate'].sum())
            
            cumulative_stats[symbol] = {
                "totalProfit": round(pos_sum, 2),
                "totalLoss": round(neg_sum, 2)
            }
            
        return win_rates, leverages, cumulative_stats
    except Exception as e:
        print(f"❌ 분석 오류: {e}")
        return {}, {}, {}

@app.get("/api/status")
def get_bot_status():
    try:
        win_rates, leverages, cum_stats = get_analyzed_data()
        with open(CONFIG_PATH, "r", encoding="utf-8") as f: raw_data = json.load(f)

        ind_bal = raw_data.get("individual_balances", {})
        shared_pool = raw_data.get("shared_profit_pool", 0.0)
        total_assets = sum(ind_bal.values()) + shared_pool

        formatted_stats = []
        for coin_name, params in raw_data.items():
            if "/" in coin_name: 
                # 💡 실시간 비중 표시: (내 원금 / 전체 자산)
                my_weight = (ind_bal.get(coin_name, 250) / total_assets * 100) if total_assets > 0 else 25
                stats = cum_stats.get(coin_name, {"totalProfit": 0, "totalLoss": 0})
                
                formatted_stats.append({
                    "name": coin_name,
                    "status": "분석중",
                    "winRate": win_rates.get(coin_name, "0%"),
                    "lev": leverages.get(coin_name, "1x"),
                    "dist": f"{my_weight:.1f}%", # 0.25 고정 대신 동적 수치 표시
                    "vol": params.get("vol", 0),
                    "ts": params.get("ts", 0),
                    "profit": params.get("profit", 0),
                    "totalProfit": stats["totalProfit"],
                    "totalLoss": stats["totalLoss"]
                })

        return {"botStatus": "실행 중", "currentSeed": round(total_assets, 2), "coinStats": formatted_stats}
    except Exception as e: return {"botStatus": f"오류: {e}", "currentSeed": 0, "coinStats": []}
    
@app.get("/api/trades")
def get_trades():
    try:
        if os.path.exists(LOG_PATH):
            df = pd.read_csv(LOG_PATH)
            return df.to_dict(orient="records")
        return []
    except Exception as e:
        return []

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)