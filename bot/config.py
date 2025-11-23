import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("❗ Не задан BOT_TOKEN (файл bot/.env или переменная окружения).")
    raise RuntimeError("BOT_TOKEN не задан")

BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_URL = os.getenv("BACKEND_URL", f"http://{BACKEND_HOST}:8000").rstrip("/")