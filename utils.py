import os
import logging
import random
import platform
from logging.handlers import RotatingFileHandler

APP_NAME = "TelegramAutoBot"

def get_app_dir():
    path = os.path.expanduser(f"~/Library/Application Support/{APP_NAME}")
    os.makedirs(path, exist_ok=True)
    return path

def setup_macos_optimizations():
    """Оптимизация для macOS"""
    if platform.system() == 'Darwin':
        os.environ['PYTHONASYNCIODEBUG'] = '0'
        os.environ['QASYNC_DEBUG'] = '0'
        return True
    return False

def setup_logger(name="TelegramAutoBot"):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.DEBUG)
    log_file = os.path.join(get_app_dir(), "bot.log")
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

def random_delay(base, variation=0.2):
    return base * (1 + random.uniform(-variation, variation))

def format_time(seconds):
    if seconds < 0:
        seconds = 0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
