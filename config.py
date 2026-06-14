from __future__ import annotations
import os
import json
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
BOT_USERNAME = os.environ.get("BOT_USERNAME", "")
ADMIN_CHAT_ID = int(os.environ["ADMIN_CHAT_ID"])
ADMIN_USER_ID = int(os.environ.get("ADMIN_USER_ID", "0"))
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "")
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
GOOGLE_SA_JSON = os.environ.get("GOOGLE_SA_JSON", "")
GOOGLE_SA_PATH = os.environ.get("GOOGLE_SA_PATH", "credentials/google_sa.json")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "15"))

SHOP_URL = os.environ.get("SHOP_URL", "https://example.vercel.app")
GROUP_ID = int(os.environ.get("GROUP_ID", "0"))


def is_admin(user) -> bool:
    if not user:
        return False
    if ADMIN_USER_ID and user.id == ADMIN_USER_ID:
        return True
    if ADMIN_USERNAME and user.username == ADMIN_USERNAME:
        return True
    return False
