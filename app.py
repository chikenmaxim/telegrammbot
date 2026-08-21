import os
import asyncio
import threading
import logging
from flask import Flask
from bot import bot, dp, main as bot_main

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот работает!"

@app.route('/health')
def health():
    return "OK", 200

def run_bot():
    try:
        asyncio.run(bot_main())
    except Exception as e:
        logging.error(f"Ошибка бота: {e}")

if __name__ == '__main__':
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)