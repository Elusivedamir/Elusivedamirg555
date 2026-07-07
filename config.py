import os
import json
from datetime import datetime

APP_NAME = "TelegramAutoBot"

def get_app_dir():
    path = os.path.expanduser(f"~/Library/Application Support/{APP_NAME}")
    os.makedirs(path, exist_ok=True)
    return path

CONFIG_FILE = os.path.join(get_app_dir(), "settings.json")

# ==========================
# Настройки по умолчанию
# ==========================

JOIN_DELAY = 30
COMMENT_DELAY_MIN = 15.0
COMMENT_DELAY_MAX = 45.0

# Дневной лимит
DAILY_LIMIT = 40
SENT_TODAY = 0
LAST_RESET_DATE = ""

# Комментарии (5 вариантов)
COMMENT_VARIANTS = [
    "Интересная мысль, спасибо за пост!",
    "Полностью согласен с автором.",
    "А ведь если подумать, тут все не так однозначно.",
    "Отличный разбор ситуации, жду продолжения.",
    "Крутой контент, сохранил себе!"
]

# Прокси
PROXY_TYPE = "SOCKS5"
PROXY_IP = ""
PROXY_PORT = ""
PROXY_USER = ""
PROXY_PASS = ""

def load_settings():
    global JOIN_DELAY, COMMENT_DELAY_MIN, COMMENT_DELAY_MAX
    global DAILY_LIMIT, SENT_TODAY, LAST_RESET_DATE, COMMENT_VARIANTS
    global PROXY_TYPE, PROXY_IP, PROXY_PORT, PROXY_USER, PROXY_PASS
    
    if not os.path.exists(CONFIG_FILE):
        return
    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        JOIN_DELAY = data.get("JOIN_DELAY", JOIN_DELAY)
        COMMENT_DELAY_MIN = data.get("COMMENT_DELAY_MIN", COMMENT_DELAY_MIN)
        COMMENT_DELAY_MAX = data.get("COMMENT_DELAY_MAX", COMMENT_DELAY_MAX)
        
        DAILY_LIMIT = data.get("DAILY_LIMIT", DAILY_LIMIT)
        SENT_TODAY = data.get("SENT_TODAY", SENT_TODAY)
        LAST_RESET_DATE = data.get("LAST_RESET_DATE", LAST_RESET_DATE)
        
        COMMENT_VARIANTS = data.get("COMMENT_VARIANTS", COMMENT_VARIANTS)
        if len(COMMENT_VARIANTS) < 5:
            COMMENT_VARIANTS += [""] * (5 - len(COMMENT_VARIANTS))
        
        PROXY_TYPE = data.get("PROXY_TYPE", PROXY_TYPE)
        PROXY_IP = data.get("PROXY_IP", PROXY_IP)
        PROXY_PORT = data.get("PROXY_PORT", PROXY_PORT)
        PROXY_USER = data.get("PROXY_USER", PROXY_USER)
        PROXY_PASS = data.get("PROXY_PASS", PROXY_PASS)
        
        # Автоматический сброс счётчика при смене дня
        today = datetime.now().strftime("%Y-%m-%d")
        if LAST_RESET_DATE != today:
            SENT_TODAY = 0
            LAST_RESET_DATE = today
            save_settings()
            
    except Exception:
        pass

def save_settings():
    data = {
        "JOIN_DELAY": JOIN_DELAY,
        "COMMENT_DELAY_MIN": COMMENT_DELAY_MIN,
        "COMMENT_DELAY_MAX": COMMENT_DELAY_MAX,
        "DAILY_LIMIT": DAILY_LIMIT,
        "SENT_TODAY": SENT_TODAY,
        "LAST_RESET_DATE": LAST_RESET_DATE,
        "COMMENT_VARIANTS": COMMENT_VARIANTS,
        "PROXY_TYPE": PROXY_TYPE,
        "PROXY_IP": PROXY_IP,
        "PROXY_PORT": PROXY_PORT,
        "PROXY_USER": PROXY_USER,
        "PROXY_PASS": PROXY_PASS
    }
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

def get_remaining_today() -> int:
    return max(0, DAILY_LIMIT - SENT_TODAY)

# Загружаем настройки при импорте
load_settings()
