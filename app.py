import os
import asyncio
import logging
import time
from aiohttp import web
from bot import main as bot_main

logging.basicConfig(level=logging.INFO)

# === Обработчики веб-запросов ===
async def handle_home(request):
    return web.Response(text="Бот работает!")

async def handle_health(request):
    return web.Response(text="OK", status=200)

# === Самопинг ===
async def ping_self(app):
    """Каждые 10 минут отправляем запрос к /health, чтобы не уснуть."""
    while True:
        await asyncio.sleep(120)  # 10 минут
        try:
            port = os.environ.get('PORT', 5000)
            async with aiohttp.ClientSession() as session:
                await session.get(f"http://localhost:{port}/health")
            logging.info("Self-ping successful")
        except Exception as e:
            logging.warning(f"Self-ping failed: {e}")

# === Запуск бота и веб-сервера в одном цикле ===
async def main():
    # Запускаем веб-сервер
    app = web.Application()
    app.router.add_get('/', handle_home)
    app.router.add_get('/health', handle_health)
    
    # Запускаем самопинг как фоновую задачу
    asyncio.create_task(ping_self(app))
    
    # Запускаем бота в фоновой задаче (но теперь он будет в том же цикле)
    bot_task = asyncio.create_task(bot_main())
    
    # Запускаем веб-сервер
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 5000)))
    await site.start()
    
    logging.info("Flask заменён на aiohttp, бот запущен в том же цикле")
    
    # Ждём, пока бот работает (бесконечно)
    await bot_task

if __name__ == '__main__':
    asyncio.run(main())
