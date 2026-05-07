from google import genai
import json

# secrets.json 경로 확인
with open(r"C:\Users\hojin\OneDrive\Desktop\TradingBot\secrets.json", "r") as f:
    secrets = json.load(f)

client = genai.Client(api_key=secrets.get("gemini_api_key"))

# 현재 사용 가능한 모든 모델 출력
print("--- 사용 가능한 모델 목록 ---")
for model in client.models.list():
    print(f"Model Name: {model.name}")