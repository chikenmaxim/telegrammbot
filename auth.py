# auth.py
import asyncio
from telethon import TelegramClient

API_ID = 36452258  # Ваш api_id
API_HASH = "d583e25f462f72b255a648defa0421cb"  # Ваш api_hash


async def main():
    client = TelegramClient("my_account", API_ID, API_HASH)
    await client.start()
    print("✅ Аккаунт авторизован. Сессия сохранена.")
    await client.disconnect()

asyncio.run(main())