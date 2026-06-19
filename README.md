# 🤖 Бот «Аптечка» — @Aptechka_umay_bot

Telegram-бот с 7-дневной прогревающей воронкой по ТЗ доктора Эламана Усупбекова.
Блок оплаты **не включён** — добавляется отдельно.

---

## 📁 Структура проекта

```
aptechka_bot/
├── bot.py             # Основной файл бота (хендлеры, воронка)
├── config.py          # Все настройки (токен, пути, URL)
├── database.py        # SQLite через SQLAlchemy async
├── analytics.py       # Запись событий воронки
├── requirements.txt   # Зависимости Python
├── aptechka_guide.pdf # ← положите PDF-гайд сюда
└── day1_video.mp4     # ← положите видео Дня 1 сюда
```

---

## 🚀 Шаг 1 — Установка окружения

### Требования
- Python 3.11+
- pip

### Установка

```bash
# Клонируйте / распакуйте папку
cd aptechka_bot

# Создайте виртуальное окружение
python -m venv venv
source venv/bin/activate      # Linux / Mac
venv\Scripts\activate         # Windows

# Установите зависимости
pip install -r requirements.txt
```

---

## ⚙️ Шаг 2 — Настройка config.py

Откройте `config.py` и укажите:

| Переменная | Что вписать |
|---|---|
| `BOT_TOKEN` | Токен из @BotFather (уже вставлен) |
| `ACADEMY_URL` | Ссылка на лендинг / страницу подписки академии |
| `GUIDE_PDF_PATH` | Путь к PDF-гайду (по умолчанию `aptechka_guide.pdf` рядом с bot.py) |
| `VIDEO_DAY1_PATH` | Путь к видео для Дня 1 (по умолчанию `day1_video.mp4`) |

Либо задайте через переменные окружения:

```bash
export BOT_TOKEN="ваш_токен"
export ACADEMY_URL="https://ваша-ссылка.com"
export GUIDE_PDF_PATH="/путь/к/файлу.pdf"
export VIDEO_DAY1_PATH="/путь/к/видео.mp4"
```

---

## 📄 Шаг 3 — Добавьте медиафайлы

1. Положите PDF-гайд в папку бота и назовите его `aptechka_guide.pdf`
   (или укажите другое имя в `config.py`).
2. Положите видеофайл для Дня 1 и назовите его `day1_video.mp4`.

Если файлов нет — бот отправит текстовую заглушку и продолжит работу.

---

## ▶️ Шаг 4 — Запуск

```bash
python bot.py
```

Вы увидите в консоли:
```
2024-xx-xx INFO Bot started
```

---

## 🌐 Шаг 5 — Деплой на сервер (продакшен)

### Вариант A — systemd (Linux VPS)

Создайте файл `/etc/systemd/system/aptechka_bot.service`:

```ini
[Unit]
Description=Aptechka Telegram Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/aptechka_bot
ExecStart=/home/ubuntu/aptechka_bot/venv/bin/python bot.py
Restart=always
RestartSec=5
Environment=BOT_TOKEN=ваш_токен
Environment=ACADEMY_URL=https://ваша-ссылка.com

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable aptechka_bot
sudo systemctl start aptechka_bot
sudo systemctl status aptechka_bot
```

### Вариант B — Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "bot.py"]
```

```bash
docker build -t aptechka_bot .
docker run -d \
  -e BOT_TOKEN="ваш_токен" \
  -e ACADEMY_URL="https://ваша-ссылка.com" \
  -v $(pwd)/aptechka.db:/app/aptechka.db \
  --name aptechka aptechka_bot
```

---

## 📊 Шаг 6 — Аналитика

Все события пишутся в таблицу `analytics` в файле `aptechka.db`.

Просмотр через SQLite:
```bash
sqlite3 aptechka.db "SELECT event, count(*) FROM analytics GROUP BY event;"
```

### Ключевые события воронки

| Событие | Когда |
|---|---|
| `bot_started` | Пользователь нажал /start |
| `name_collected` | Ввёл имя |
| `age_segmented` | Выбрал возрастной сегмент |
| `guide_delivered` | PDF отправлен |
| `guide_opened_button` | Нажал «Я открыла гайд» |
| `day1_engaged` | Согласился смотреть видео |
| `day2_read` | Прочитал историю с приёма |
| `day3_interest_clicked` | Нажал «Хочу узнать про академию» (🔥 горячий лид) |
| `day4_offer_sent` | Получил анонс академии |

---

## 💳 Шаг 7 — Блок оплаты (не включён)

Для добавления оплаты подключите одно из:

- **Telegram Payments** (встроенный провайдер): `bot.send_invoice()`
- **Stripe / CloudPayments / Robokassa**: вебхук → выдача доступа после `payment.success`
- **ЮKassa, Kaspi**: callback URL → обновление `users.stage = 'paid'` в БД

После оплаты нужно:
1. Пометить пользователя в БД (`stage = 'paid'`)
2. Остановить дальнейшую воронку (убрать запланированные задания из APScheduler)
3. Отправить ссылку/доступ в академию

---

## ❓ Частые вопросы

**Бот не отправляет PDF**
→ Проверьте путь в `GUIDE_PDF_PATH`. Файл должен существовать до запуска бота.

**Воронка не отправляется через 24 часа**
→ APScheduler работает в памяти. При перезапуске бота задания **теряются**.
Для продакшена переведите планировщик на постоянное хранилище:
```python
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
jobstores = {"default": SQLAlchemyJobStore(url="sqlite:///jobs.db")}
scheduler = AsyncIOScheduler(jobstores=jobstores)
```

**Как добавить нового пользователя в базу вручную?**
```bash
sqlite3 aptechka.db "INSERT INTO users(user_id, name) VALUES(123456789, 'Тест');"
```
