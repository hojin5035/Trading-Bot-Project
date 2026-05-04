import requests
import json
import os

def load_secrets():
    """보안 정보 로드"""
    try:
        with open('secrets.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def send_discord(message):
    """디스코드 알림 전송"""
    secrets = load_secrets()
    url = secrets.get('discord_webhook_url')
    if url:
        try:
            requests.post(url, json={"content": message}, timeout=5)
        except Exception as e:
            print(f"디스코드 전송 에러: {e}")