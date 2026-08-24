import os
import asyncio
import logging
import threading
import time
import requests
from flask import Flask
from bot import main as bot_main

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# === Эндпоинты для пингов ===
@app.route('/')
def home():
    return "Бот работает!"

@app.route('/health')
def health():
    return "OK", 200

# === Функция для запуска Flask ===
def run_flask():
    """Запускает Flask-сервер в фоновом потоке."""
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# === Функция для пинга самого себя ===
def ping_self():
    """
    Каждые 10 минут отправляет запрос к своему же /health,
    чтобы Render не усыпил бота.
    """
    while True:
        time.sleep(120)  # 10 минут
        try:
            port = os.environ.get('PORT', 5000)
            url = f"http://localhost:{port}/health"
            requests.get(url, timeout=5)
            logging.info("Self-ping successful")
        except Exception as e:
            logging.warning(f"Self-ping failed: {e}")

# === Точка входа ===
if __name__ == '__main__':
    # 1. Запускаем Flask в фоновом потоке (чтобы не мешать боту)
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # 2. Запускаем поток для пинга самого себя
    ping_thread = threading.Thread(target=ping_self, daemon=True)
    ping_thread.start()
    
    # 3. Запускаем бота в ОСНОВНОМ потоке (Telethon будет доволен)
    try:
        asyncio.run(bot_main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
    except Exception as e:
        logging.error(f"Ошибка бота: {e}")
        raise
