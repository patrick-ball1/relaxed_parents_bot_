"""
Конфигурация relaxed_parents_bot.
"""

import os

# ── Telegram ──────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "8814636887:AAGmIx4TOUBdTmz7OJQ45hMR2kLoBZ2uvTc")

# ── Ссылки воронки ────────────────────────────
WEBINAR_URL = os.getenv("WEBINAR_URL", "https://youtu.be/hmeUnKo_twc?si=zlzdR78cqM-gzN6b")
ACADEMY_URL = os.getenv("ACADEMY_URL", "https://t.me/relaxed_parents_bot")
REVIEWS_URL = os.getenv("REVIEWS_URL", "https://t.me/+SNRZMUcm-9M5MzEy")
BOT_LINK    = os.getenv("BOT_LINK",    "https://t.me/relaxed_parents_bot")

# ── Медиафайлы (опционально) ──────────────────
GUIDE_PDF_PATH  = os.getenv("GUIDE_PDF_PATH",  "aptechka_guide.pdf")
VIDEO_DAY1_PATH = os.getenv("VIDEO_DAY1_PATH", "day1_video.mp4")

# ── База данных ───────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:////data/aptechka.db")
