from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import os

app = FastAPI()

# 프론트엔드(React)에서 접근할 수 있도록 허용 (CORS 설정)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/trades")
def get_trades():
    csv_path = r"C:\Users\hojin\IdeaProjects\trading-backend\data" # 봇이 기록하는 경로
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        # 리액트가 읽기 편하게 리스트(JSON) 형태로 변환
        return df.to_dict(orient="records")
    return {"message": "데이터가 아직 없습니다."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)