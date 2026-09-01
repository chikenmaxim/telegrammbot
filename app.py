import os
import asyncio
import logging
import threading
import time
import requests  # <-- вместо aiohttp
from flask import Flask
from bot import main as bot_main

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def ping_self():
    while True:
        time.sleep(120)  # 10 минут
        try:
            port = os.environ.get('PORT', 5000)
            url = f"http://localhost:{port}/health"
            requests.get(url, timeout=5)
            logging.info("Self-ping successful")
        except Exception as e:
            logging.warning(f"Self-ping failed: {e}")

if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Опционально: если хотите оставить самопинг
    ping_thread = threading.Thread(target=ping_self, daemon=True)
    ping_thread.start()
    
    try:
        asyncio.run(bot_main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
    except Exception as e:
        logging.error(f"Ошибка бота: {e}")
        raise
