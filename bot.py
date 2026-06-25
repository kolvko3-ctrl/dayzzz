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
POLL_INTERVAL = 30  # секунд между проверками

def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_subscribers(subs: set):
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(list(subs), f)

subscribers = load_subscribers()

intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)

# Храним последнее состояние сообщений {message_id: "текст"}
last_seen = {}


async def tg_request(method: str, payload: dict):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            return await resp.json()


async def send_to_all(text: str):
    if not subscribers:
        print("[TG] Нет подписчиков, пропускаю")
        return
    dead = set()
    for chat_id in list(subscribers):
        result = await tg_request("sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        })
        if not result.get("ok"):
            if result.get("error_code") in (403, 400):
                dead.add(chat_id)
                print(f"[TG] Удаляю мёртвого подписчика: {chat_id}")
    if dead:
        subscribers.difference_update(dead)
        save_subscribers(subscribers)
    print(f"[TG] Отправлено {len(subscribers)} подписчикам")


def extract_text(message: discord.Message) -> str:
    """Извлекаем весь текст из сообщения включая embed поля"""
    parts = []
    if message.content:
        parts.append(message.content)
    for embed in message.embeds:
        if embed.title:
            parts.append(embed.title)
        if embed.description:
            parts.append(embed.description)
        for field in embed.fields:
            parts.append(f"{field.name}: {field.value}")
    return "\n".join(parts)


def build_tg_text(message: discord.Message) -> str:
    server_name = message.guild.name if message.guild else "DayZ"
    channel_name = message.channel.name

    tg_text = f"🎮 <b>Обновление ивентов — {server_name}</b>\n📢 #{channel_name}\n\n"

    for embed in message.embeds:
        if embed.title:
            tg_text += f"<b>{embed.title}</b>\n"
        if embed.description:
            tg_text += f"{embed.description}\n"
        for field in embed.fields:
            tg_text += f"<b>{field.name}:</b> {field.value}\n"
        tg_text += "\n"

    if message.content and not message.embeds:
        tg_text += message.content

    return tg_text.strip()


async def poll_channel():
    """Каждые N секунд читаем канал и проверяем изменения"""
    await discord_client.wait_until_ready()
    print(f"[Poller] Запущен, интервал {POLL_INTERVAL}с")

    channel = discord_client.get_channel(EVENT_CHANNEL_ID)
    if not channel:
        print(f"[Poller] ОШИБКА: канал {EVENT_CHANNEL_ID} не найден!")
        return

    while not discord_client.is_closed():
        try:
            # Читаем последние 10 сообщений от ботов
            async for message in channel.history(limit=10):
                if not message.author.bot:
                    continue

                current_text = extract_text(message)
                prev_text = last_seen.get(message.id)

                if prev_text is None:
                    # Первый запуск — просто запоминаем, не отправляем
                    last_seen[message.id] = current_text
                    print(f"[Poller] Запомнил сообщение {message.id}")

                elif prev_text != current_text:
                    # Текст изменился — отправляем уведомление!
                    print(f"[Poller] Изменение в сообщении {message.id}, отправляю...")
                    last_seen[message.id] = current_text
                    await send_to_all(build_tg_text(message))

        except Exception as e:
            print(f"[Poller ERROR] {e}")

        await asyncio.sleep(POLL_INTERVAL)


async def poll_telegram():
    """Слушаем команды /start и /stop от пользователей"""
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
                            "Когда ивент обновится — я напишу тебе сюда 🎮\n\n"
                            "Чтобы отписаться — напиши /stop"
                        ),
                    })
                    print(f"[TG] Новый подписчик: {chat_id} ({first_name})")

                elif text == "/stop":
                    subscribers.discard(chat_id)
                    save_subscribers(subscribers)
                    await tg_request("sendMessage", {
                        "chat_id": chat_id,
                        "text": "❌ Ты отписан. Напиши /start чтобы подписаться снова.",
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
    asyncio.create_task(poll_channel())
    asyncio.create_task(poll_telegram())


discord_client.run(DISCORD_TOKEN)
