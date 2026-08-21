import os
import asyncio
import logging
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

async def run_bot_and_flask():
    """Запускает бота и Flask-сервер в одном потоке."""
    # Запускаем бота как задачу
    bot_task = asyncio.create_task(bot_main())
    
    # Запускаем Flask-сервер в отдельном потоке, но управляем им из asyncio
    from werkzeug.serving import make_server
    server = make_server('0.0.0.0', int(os.environ.get('PORT', 5000)), app)
    server.serve_forever()  # Это блокирует, но мы запустим в потоке
    
    # Ожидаем завершения бота (он никогда не завершится)
    await bot_task

if __name__ == '__main__':
    # Запускаем Flask в отдельном потоке, но основной цикл asyncio остаётся свободным
    import threading
    def run_flask():
        app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False, use_reloader=False)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # В основном потоке запускаем бота
    try:
        asyncio.run(bot_main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
