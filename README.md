# 🎮 DayZ Event Notifier — Discord → Telegram

Бот слушает Discord-канал с ивентами и отправляет уведомление в Telegram когда приходит сообщение от бота/системы.

---

## ⚙️ Установка

### 1. Установить Python 3.10+
https://www.python.org/downloads/

### 2. Установить зависимости
```bash
pip install -r requirements.txt
```

### 3. Создать файл `.env`
Скопируйте `.env.example` → `.env` и заполните значения:

```
DISCORD_TOKEN=...
EVENT_CHANNEL_ID=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```

---

## 🔑 Как получить токены

### Discord токен:
1. Зайдите на https://discord.com/developers/applications
2. Создайте новое приложение → раздел **Bot**
3. Нажмите **Reset Token** и скопируйте токен
4. Включите **Message Content Intent** в разделе Bot → Privileged Gateway Intents
5. Пригласите бота на сервер через OAuth2 → URL Generator:
   - Scopes: `bot`
   - Permissions: `Read Messages / View Channels`

### EVENT_CHANNEL_ID — ID канала с ивентами:
1. В Discord: Настройки → Дополнительно → **Режим разработчика** ✅
2. ПКМ на нужный канал → **Копировать ID**

### Telegram Bot Token:
1. Напишите [@BotFather](https://t.me/BotFather) в Telegram
2. `/newbot` → введите имя и username
3. Скопируйте токен

### Telegram Chat ID (ваш личный):
1. Напишите [@userinfobot](https://t.me/userinfobot) → `/start`
2. Скопируйте число из поля **Id**

---

## 🚀 Запуск

```bash
python bot.py
```

Бот напишет в консоль:
```
[Discord] Бот запущен как YourBot#1234
[Discord] Слушаю канал ID: 1234567890123456789
```

---

## 🔄 Автозапуск (опционально)

### Windows — через Task Scheduler или bat-файл:
```bat
@echo off
cd C:\путь\к\папке\dayz-bot
python bot.py
```

### Linux/VPS — через systemd или screen:
```bash
screen -S dayzbot
python bot.py
# Ctrl+A, D — свернуть
```
