import discord
import aiohttp
import asyncio
import os
import json
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
EVENT_CHANNEL_ID = int(os.getenv("EVENT_CHANNEL_ID"))

SUBSCRIBERS_FILE = "subscribers.json"


def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_subscribers(subs: set):
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(list(subs), f)


subscribers = load_subscribers()

# Discord клиент
intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)


async def tg_request(method: str, payload: dict):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            return await resp.json()


async def send_to_all(text: str):
    dead = set()
    for chat_id in list(subscribers):
        result = await tg_request("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        })
        if not result.get("ok"):
            # Пользователь заблокировал бота — удаляем
            err = result.get("error_code")
            if err in (403, 400):
                dead.add(chat_id)
                print(f"[TG] Удаляю мёртвого подписчика: {chat_id}")
    if dead:
        subscribers.difference_update(dead)
        save_subscribers(subscribers)
    print(f"[TG] Отправлено {len(subscribers)} подписчикам")


async def poll_telegram():
    """Слушаем Telegram через long polling — обрабатываем /start и /stop"""
    offset = None
    print("[TG] Polling запущен...")
    while True:
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset
            result = await tg_request("getUpdates", params)
            updates = result.get("result", [])
            for update in updates:
                offset = update["update_id"] + 1
                msg = update.get("message")
                if not msg:
                    continue
                chat_id = msg["chat"]["id"]
                text = msg.get("text", "")
                first_name = msg["chat"].get("first_name", "друг")

                if text == "/start":
                    subscribers.add(chat_id)
                    save_subscribers(subscribers)
                    await tg_request("sendMessage", {
                        "chat_id": chat_id,
                        "text": (
                            f"✅ Привет, {first_name}!\n\n"
                            "Ты подписан на уведомления об ивентах DayZ.\n"
                            "Когда начнётся ивент — я напишу тебе сюда 🎮\n\n"
                            "Чтобы отписаться — напиши /stop"
                        ),
                    })
                    print(f"[TG] Новый подписчик: {chat_id} ({first_name})")

                elif text == "/stop":
                    subscribers.discard(chat_id)
                    save_subscribers(subscribers)
                    await tg_request("sendMessage", {
                        "chat_id": chat_id,
                        "text": "❌ Ты отписан от уведомлений. Напиши /start чтобы подписаться снова.",
                    })
                    print(f"[TG] Отписался: {chat_id} ({first_name})")

        except Exception as e:
            print(f"[TG ERROR] {e}")
            await asyncio.sleep(5)


@discord_client.event
async def on_ready():
    print(f"[Discord] Бот запущен как {discord_client.user}")
    print(f"[Discord] Слушаю канал ID: {EVENT_CHANNEL_ID}")
    print(f"[TG] Подписчиков: {len(subscribers)}")
    # Запускаем Telegram polling параллельно
    asyncio.create_task(poll_telegram())


@discord_client.event
async def on_message(message: discord.Message):
    if message.channel.id != EVENT_CHANNEL_ID:
        return
    if not message.author.bot:
        return

    print(f"[Discord] Сообщение от бота: {message.author} → {message.content[:80]}")

    channel_name = message.channel.name
    server_name = message.guild.name if message.guild else "DayZ"

    tg_text = (
        f"🎮 <b>Ивент на сервере {server_name}!</b>\n\n"
        f"📢 <b>Канал:</b> #{channel_name}\n"
        f"🤖 <b>От:</b> {message.author.display_name}\n\n"
    )

    if message.content:
        tg_text += f"📝 {message.content}"

    if message.embeds:
        embed = message.embeds[0]
        parts = []
        if embed.title:
            parts.append(f"<b>{embed.title}</b>")
        if embed.description:
            parts.append(embed.description)
        if parts:
            tg_text += "\n".join(parts)

    if not subscribers:
        print("[TG] Нет подписчиков, пропускаю")
        return

    await send_to_all(tg_text)


discord_client.run(DISCORD_TOKEN)
