import json
import os
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai

app = FastAPI()

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 경로 (기존 그대로 유지) ---
LOG_PATH = r"C:\Users\hojin\IdeaProjects\trading-backend\data\trade_log.csv"
CONFIG_PATH = r"C:\Users\hojin\OneDrive\Desktop\TradingBot\bot_config.json"
SECRETS_PATH = r"C:\Users\hojin\OneDrive\Desktop\TradingBot\secrets.json"
DATA_DIR = r"C:\Users\hojin\IdeaProjects\trading-backend\data"

# --- Gemini ---
def load_secrets():
    try:
        with open(SECRETS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

secrets = load_secrets()
gemini_key = secrets.get("gemini_api_key")

if gemini_key:
    ai_model = genai.Client(api_key=gemini_key)
    MODEL_ID = 'gemini-2.0-flash'
else:
    ai_model = None

# --- 핵심 분석 함수 (🔥 완전 수정됨) ---
def get_analyzed_data():
    if not os.path.exists(LOG_PATH):
        return {}, {}, {}

    try:
        df = pd.read_csv(LOG_PATH)

        if df.empty:
            return {}, {}, {}

        df.columns = [c.lower() for c in df.columns]

        # 🔥 정렬 (안정성)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values(by="timestamp")

        win_rates = {}
        leverages = {}
        cumulative_stats = {}

        for symbol, group in df.groupby('symbol'):

            # 🔥 SELL만 사용
            sell_group = group[group['type'] == 'SELL']

            if sell_group.empty:
                continue

            total = len(sell_group)
            wins = len(sell_group[sell_group['profit_rate'] > 0])

            win_rate = (wins / total) * 100 if total > 0 else 0
            win_rates[symbol] = f"{win_rate:.1f}%"

            # 🔥 최근 3개도 SELL 기준
            recent = sell_group.tail(3)
            losses = len([p for p in recent['profit_rate'] if p <= 0])

            base_lev = 2.0 if losses <= 1 else (1.5 if losses == 2 else 1.0)
            leverages[symbol] = f"{base_lev}x"

            cumulative_stats[symbol] = {
                "totalProfit": round(sell_group[sell_group['profit_rate'] > 0]['profit_rate'].sum(), 2),
                "totalLoss": round(abs(sell_group[sell_group['profit_rate'] < 0]['profit_rate'].sum()), 2)
            }

        return win_rates, leverages, cumulative_stats

    except Exception as e:
        print(f"❌ 분석 오류: {e}")
        return {}, {}, {}

# --- 상태 API ---
@app.get("/api/status")
def get_bot_status():
    try:
        win_rates, leverages, cum_stats = get_analyzed_data()

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        ind_bal = raw_data.get("individual_balances", {})
        shared_pool = raw_data.get("shared_profit_pool", 0.0)
        total_assets = sum(ind_bal.values()) + shared_pool

        formatted_stats = []

        for coin_name, params in raw_data.items():
            if isinstance(params, dict) and "/" in coin_name:

                stats = cum_stats.get(coin_name, {"totalProfit": 0, "totalLoss": 0})

                formatted_stats.append({
                    "name": coin_name,
                    "status": "분석중",
                    "winRate": win_rates.get(coin_name, "0%"),
                    "lev": leverages.get(coin_name, "1x"),
                    "dist": f"{(ind_bal.get(coin_name, 0)/total_assets*100):.1f}%" if total_assets > 0 else "0%",
                    "vol": params.get("vol", "-"),
                    "ts": params.get("ts", "-"),
                    "profit": params.get("profit", "-"),
                    "totalProfit": stats["totalProfit"],
                    "totalLoss": stats["totalLoss"]
                })

        return {
            "botStatus": "실행 중",
            "currentSeed": round(total_assets, 2),
            "coinStats": formatted_stats
        }

    except Exception as e:
        return {"botStatus": f"오류: {e}", "coinStats": []}

# --- 거래 로그 ---
@app.get("/api/trades")
def get_trades():
    try:
        if os.path.exists(LOG_PATH):
            df = pd.read_csv(LOG_PATH)
            return df.to_dict(orient="records")
        return []
    except Exception as e:
        print(f"❌ 매매 기록 로드 오류: {e}")
        return []

@app.get("/api/equity")
def get_equity():

    path = os.path.join(DATA_DIR, "equity_log.csv")

    if not os.path.exists(path):
        return []

    df = pd.read_csv(path)

    if df.empty:
        return []

    df = df.tail(300)

    return [
        {
            "timestamp": row["timestamp"],
            "equity": float(row["equity"]),
            "mdd": float(row["mdd"])
        }
        for _, row in df.iterrows()
    ]

# --- AI ---
@app.get("/api/ai/{mode}")
def get_ai_analysis(mode: str):
    if not ai_model:
        raise HTTPException(status_code=500, detail="Gemini 미설정")

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        prompt = (
            f"트레이딩 분석: {raw_data.get('individual_balances')}"
            if mode == "strategy"
            else "시장 조언을 해줘."
        )

        response = ai_model.models.generate_content(
            model=MODEL_ID,
            contents=prompt
        )

        return {"result": response.text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 실행 ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)