import requests
import json

def send_discord_notification(message):
    with open('secrets.json', 'r') as f:
        config = json.load(f)
    url = config.get('discord_webhook_url')
    if url:
        requests.post(url, json={"content": message})