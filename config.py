from __future__ import annotations
import os
import json
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN     = os.environ["BOT_TOKEN"]
ADMIN_CHAT_ID = int(os.environ["ADMIN_CHAT_ID"])
ADMIN_USERNAME = os.environ["ADMIN_USERNAME"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
GOOGLE_SA_JSON  = os.environ.get("GOOGLE_SA_JSON", "")
GOOGLE_SA_PATH  = os.environ.get("GOOGLE_SA_PATH", "credentials/google_sa.json")
POLL_INTERVAL   = int(os.environ.get("POLL_INTERVAL", 15))  # секунды

SHOP_URL  = os.environ.get("SHOP_URL", "https://твой-сайт.vercel.app")
GROUP_ID  = int(os.environ.get("GROUP_ID", "-1001003321871117"))
