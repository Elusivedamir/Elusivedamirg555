import os
import json
import random
import asyncio
from telethon import TelegramClient
from telethon.tl.types import Channel
from datetime import datetime
import config

class TelegramBot:
    def __init__(self, session_name="session_phone"):
        self.session_name = session_name
        self.client = None
        self.stop_requested = False
        self.processed_file = os.path.join(config.get_app_dir(), "processed_posts.json")
        self.processed_posts = self._load_processed_posts()

    def _load_processed_posts(self):
        if os.path.exists(self.processed_file):
            try:
                with open(self.processed_file, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception:
                return set()
        return set()

    def _save_processed_posts(self):
        try:
            with open(self.processed_file, "w", encoding="utf-8") as f:
                json.dump(list(self.processed_posts), f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    def init_client(self, api_id, api_hash, phone):
        proxy_config = None
        if config.PROXY_IP and config.PROXY_PORT:
            import socks
            proxy_type = socks.SOCKS5 if config.PROXY_TYPE == "SOCKS5" else socks.HTTP
            username = config.PROXY_USER if config.PROXY_USER else None
            password = config.PROXY_PASS if config.PROXY_PASS else None
            proxy_config = (proxy_type, config.PROXY_IP, int(config.PROXY_PORT), True, username, password)

        self.client = TelegramClient(self.session_name, int(api_id), api_hash, proxy=proxy_config)

    async def export_channels_to_json(self, status_cb=None):
        if not self.client or not await self.client.is_user_authorized():
            if status_cb: status_cb("❌ Ошибка: Сначала нужно авторизоваться!")
            return False

        extracted_pairs = []
        async for dialog in self.client.iter_dialogs():
            if isinstance(dialog.entity, Channel) and not dialog.entity.megagroup:
                source = dialog.entity.username if dialog.entity.username else f"-100{dialog.entity.id}"
                extracted_pairs.append({"source": source, "destination": ""})

        desktop_path = os.path.expanduser("~/Desktop/channels_database.json")
        with open(desktop_path, "w", encoding="utf-8") as f:
            json.dump(extracted_pairs, f, ensure_ascii=False, indent=4)
        
        if status_cb: status_cb(f"✅ Готово! Файл сохранен на рабочем столе.")
        return True

    # Логика работы (run_commenting_with_ids) остается без изменений, как в прошлом блоке.
