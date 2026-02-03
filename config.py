import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
DATA_DIR = os.getenv("DATA_DIR", "./data")
EXPORT_DIR = os.getenv("EXPORT_DIR", "./exports")
TZ = os.getenv("TZ", "Asia/Tashkent")
PROXY_URL = os.getenv("PROXY_URL") # Optional proxy URL (e.g., http://127.0.0.1:1080)

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "stats"), exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

TEACHERS_FILE = os.path.join(DATA_DIR, "teachers.json")
GROUPS_FILE = os.path.join(DATA_DIR, "groups.json")
TEACHER_GROUPS_FILE = os.path.join(DATA_DIR, "teacher_groups.json")
STATS_DIR = os.path.join(DATA_DIR, "stats")
