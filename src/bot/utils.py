import requests
import json
import os

def load_secrets():
    # 현재 파일(src/bot/utils.py) 기준 -> 최상위 루트 탐색
    current_file_path = os.path.dirname(os.path.abspath(__file__))
    root_path = os.path.abspath(os.path.join(current_file_path, '..', '..'))
    secrets_path = os.path.join(root_path, 'secrets.json')
    
    try:
        with open(secrets_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ secrets.json 파일을 찾을 수 없습니다.")
        return {}
    except Exception as e:
        print(f"❌ secrets.json 로드 에러: {e}")
        return {}

def send_discord(message):
    secrets = load_secrets()
    url = secrets.get('discord_webhook_url')
    
    if url:
        try:
            requests.post(url, json={"content": message}, timeout=5)
        except Exception as e:
            print(f"❌ 디스코드 전송 에러: {e}")
    else:
        print(f"📢 [Discord 알림 대기중]: {message}")