import os
import json

APP_NAME = "TelegramAutoBot"

def get_app_dir():
    path = os.path.expanduser(f"~/Library/Application Support/{APP_NAME}")
    os.makedirs(path, exist_ok=True)
    return path

CONFIG_FILE = os.path.join(get_app_dir(), "settings.json")

# Настройки по умолчанию
JOIN_DELAY = 30
COMMENT_DELAY_MIN = 15.0
COMMENT_DELAY_MAX = 45.0

COMMENT_SCHEDULE = [(9, 0), (15, 0), (21, 0)]

# Пять комментариев для рандомной ротации (улучшенный антифрод)
COMMENT_VARIANTS = [
    "Интересная мысль, спасибо за пост!",
    "Полностью согласен с автором.",
    "А ведь если подумать, тут все не так однозначно.",
    "Отличный разбор ситуации, жду продолжения.",
    "Крутой контент, сохранил себе!"
]

PROXY_TYPE = "SOCKS5"
PROXY_IP = ""
PROXY_PORT = ""
PROXY_USER = ""
PROXY_PASS = ""

DAILY_LIMIT = 40       
LAST_RUN_DATE = ""     
SENT_TODAY_COUNT = 0   
CURRENT_INDEX = 0      # Сквозной указатель для вечного кругового обхода списка

def load_settings():
    global JOIN_DELAY, COMMENT_DELAY_MIN, COMMENT_DELAY_MAX, COMMENT_SCHEDULE
    global PROXY_TYPE, PROXY_IP, PROXY_PORT, PROXY_USER, PROXY_PASS
    global DAILY_LIMIT, LAST_RUN_DATE, SENT_TODAY_COUNT, CURRENT_INDEX, COMMENT_VARIANTS

    if not os.path.exists(CONFIG_FILE):
        return

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        JOIN_DELAY = data.get("JOIN_DELAY", JOIN_DELAY)
        COMMENT_DELAY_MIN = data.get("COMMENT_DELAY_MIN", COMMENT_DELAY_MIN)
        COMMENT_DELAY_MAX = data.get("COMMENT_DELAY_MAX", COMMENT_DELAY_MAX)
        COMMENT_SCHEDULE = [tuple(item) for item in data.get("COMMENT_SCHEDULE", COMMENT_SCHEDULE)]
        
        COMMENT_VARIANTS = data.get("COMMENT_VARIANTS", COMMENT_VARIANTS)
        if len(COMMENT_VARIANTS) < 5:
            COMMENT_VARIANTS += [""] * (5 - len(COMMENT_VARIANTS))

        PROXY_TYPE = data.get("PROXY_TYPE", PROXY_TYPE)
        PROXY_IP = data.get("PROXY_IP", PROXY_IP)
        PROXY_PORT = data.get("PROXY_PORT", PROXY_PORT)
        PROXY_USER = data.get("PROXY_USER", PROXY_USER)
        PROXY_PASS = data.get("PROXY_PASS", PROXY_PASS)
        
        DAILY_LIMIT = data.get("DAILY_LIMIT", DAILY_LIMIT)
        LAST_RUN_DATE = data.get("LAST_RUN_DATE", LAST_RUN_DATE)
        SENT_TODAY_COUNT = data.get("SENT_TODAY_COUNT", SENT_TODAY_COUNT)
        CURRENT_INDEX = data.get("CURRENT_INDEX", CURRENT_INDEX)
    except Exception:
        pass

def save_settings():
    data = {
        "JOIN_DELAY": JOIN_DELAY,
        "COMMENT_DELAY_MIN": COMMENT_DELAY_MIN,
        "COMMENT_DELAY_MAX": COMMENT_DELAY_MAX,
        "COMMENT_SCHEDULE": COMMENT_SCHEDULE,
        "COMMENT_VARIANTS": COMMENT_VARIANTS,
        "PROXY_TYPE": PROXY_TYPE,
        "PROXY_IP": PROXY_IP,
        "PROXY_PORT": PROXY_PORT,
        "PROXY_USER": PROXY_USER,
        "PROXY_PASS": PROXY_PASS,
        "DAILY_LIMIT": DAILY_LIMIT,
        "LAST_RUN_DATE": LAST_RUN_DATE,
        "SENT_TODAY_COUNT": SENT_TODAY_COUNT,
        "CURRENT_INDEX": CURRENT_INDEX
    }
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

load_settings()
