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

# === Эндпоинты ===
@app.route('/')
def home():
    return "Бот работает!"

@app.route('/health')
def health():
    return "OK", 200

# === Функция самопинга (чтобы бот не засыпал) ===
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

# === Функция запуска бота в отдельном потоке ===
def start_bot():
    """Запускает асинхронного бота в фоновом потоке."""
    def run():
        try:
            asyncio.run(bot_main())
        except Exception as e:
            logging.error(f"Ошибка бота: {e}")
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    logging.info("Бот запущен в фоновом потоке")

# === Запускаем бота и самопинг ПРИ ИМПОРТЕ ===
# Это сработает, когда gunicorn загрузит этот файл
start_bot()
ping_thread = threading.Thread(target=ping_self, daemon=True)
ping_thread.start()
