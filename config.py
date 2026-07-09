import json
from datetime import datetime
from pathlib import Path

try:
    import keyring
except Exception:  # pragma: no cover - optional dependency
    keyring = None

APP_NAME = "TelegramAutoBot"
APP_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
CONFIG_FILE = APP_DIR / "settings.json"
SERVICE_NAME = APP_NAME


def get_app_dir() -> str:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    return str(APP_DIR)


def get_config_file() -> str:
    return str(CONFIG_FILE)


def get_log_file() -> str:
    return str(APP_DIR / "bot.log")


def get_history_file() -> str:
    return str(APP_DIR / "processed_posts.json")


def get_stats_file() -> str:
    return str(APP_DIR / "stats.json")


def get_session_path(session_name: str) -> str:
    return str(APP_DIR / f"{session_name}.session")


def _get_keyring_backend():
    if keyring is None:
        raise RuntimeError("python-keyring is required for secure storage")
    return keyring


def set_secret(name: str, value: str) -> None:
    if not value:
        return
    _get_keyring_backend().set_password(SERVICE_NAME, name, value)


def get_secret(name: str, default: str | None = None) -> str | None:
    try:
        value = _get_keyring_backend().get_password(SERVICE_NAME, name)
        return value if value is not None else default
    except Exception:
        return default


def delete_secret(name: str) -> None:
    try:
        _get_keyring_backend().delete_password(SERVICE_NAME, name)
    except Exception:
        pass


def save_auth_credentials(api_id: str, api_hash: str, phone: str) -> None:
    set_secret("api_id", str(api_id))
    set_secret("api_hash", str(api_hash))
    set_secret("phone", str(phone))


def load_auth_credentials() -> dict:
    return {
        "api_id": get_secret("api_id", ""),
        "api_hash": get_secret("api_hash", ""),
        "phone": get_secret("phone", ""),
    }


def save_proxy_settings(proxy_type: str, proxy_ip: str, proxy_port: str, proxy_user: str, proxy_pass: str) -> None:
    set_secret("proxy_type", proxy_type)
    set_secret("proxy_ip", proxy_ip)
    set_secret("proxy_port", proxy_port)
    set_secret("proxy_user", proxy_user)
    set_secret("proxy_pass", proxy_pass)


def load_proxy_settings() -> dict:
    return {
        "proxy_type": get_secret("proxy_type", "SOCKS5") or "SOCKS5",
        "proxy_ip": get_secret("proxy_ip", "") or "",
        "proxy_port": get_secret("proxy_port", "") or "",
        "proxy_user": get_secret("proxy_user", "") or "",
        "proxy_pass": get_secret("proxy_pass", "") or "",
    }


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

# Прокси (в памяти; безопасно хранится в keyring)
PROXY_TYPE = "SOCKS5"
PROXY_IP = ""
PROXY_PORT = ""
PROXY_USER = ""
PROXY_PASS = ""


def load_settings():
    global JOIN_DELAY, COMMENT_DELAY_MIN, COMMENT_DELAY_MAX
    global DAILY_LIMIT, SENT_TODAY, LAST_RESET_DATE, COMMENT_VARIANTS
    global PROXY_TYPE, PROXY_IP, PROXY_PORT, PROXY_USER, PROXY_PASS

    get_app_dir()

    if not CONFIG_FILE.exists():
        proxy_settings = load_proxy_settings()
        PROXY_TYPE = proxy_settings["proxy_type"]
        PROXY_IP = proxy_settings["proxy_ip"]
        PROXY_PORT = proxy_settings["proxy_port"]
        PROXY_USER = proxy_settings["proxy_user"]
        PROXY_PASS = proxy_settings["proxy_pass"]
        return

    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as f:
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

        proxy_settings = load_proxy_settings()
        PROXY_TYPE = proxy_settings["proxy_type"]
        PROXY_IP = proxy_settings["proxy_ip"]
        PROXY_PORT = proxy_settings["proxy_port"]
        PROXY_USER = proxy_settings["proxy_user"]
        PROXY_PASS = proxy_settings["proxy_pass"]

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
    }
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with CONFIG_FILE.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception:
        pass


def get_remaining_today() -> int:
    return max(0, DAILY_LIMIT - SENT_TODAY)


load_settings()
