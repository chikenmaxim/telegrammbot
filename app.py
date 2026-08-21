import os
import asyncio
import logging
from flask import Flask
import threading

# Импортируем функцию main() из bot.py
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
    """Запускает Flask-сервер в отдельном потоке (чтобы не мешать боту)"""
    port = int(os.environ.get('PORT', 5000))
    # use_reloader=False — обязательно, иначе Flask попытается запустить второй процесс
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

if __name__ == '__main__':
    # 1. Запускаем Flask в фоновом потоке (daemon=True — завершится вместе с главным)
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # 2. Запускаем бота в ОСНОВНОМ потоке (Telethon будет доволен)
    try:
        asyncio.run(bot_main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
    except Exception as e:
        logging.error(f"Ошибка бота: {e}")
        raise
