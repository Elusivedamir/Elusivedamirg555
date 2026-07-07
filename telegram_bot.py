import os
import json
import random
import asyncio
import python_socks  
from telethon import TelegramClient
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

        self.client = TelegramClient(
            self.session_name, 
            int(api_id), 
            api_hash,
            proxy=proxy_config,
            connection_retries=5,
            retry_delay=2
        )

    async def run_commenting_with_ids(self, channel_ids, pairs, unused_text=None, status_cb=None):
        self.stop_requested = False
        
        if not pairs:
            if status_cb: status_cb("⚠️ Список связок пуст.")
            return False

        total_pairs = len(pairs)
        if status_cb: 
            status_cb(f"ℹ️ Всего загружено элементов: {total_pairs}. Дневной лимит: {config.DAILY_LIMIT}")

        while config.SENT_TODAY_COUNT < config.DAILY_LIMIT:
            if self.stop_requested:
                if status_cb: status_cb("🛑 Процесс комментирования остановлен.")
                return False

            # Проверка смены суток
            today_str = datetime.now().strftime("%Y-%m-%d")
            if config.LAST_RUN_DATE != today_str:
                config.LAST_RUN_DATE = today_str
                config.SENT_TODAY_COUNT = 0
                config.save_settings()

            # Универсальный индекс (закольцовывает список любой длины)
            real_index = config.CURRENT_INDEX % total_pairs
            pair = pairs[real_index]

            src_channel = pair.get("source", "").strip()
            dest_chat = pair.get("destination", "").strip()

            if not dest_chat:
                config.CURRENT_INDEX += 1
                config.save_settings()
                continue

            # Исключаем ссылки https://t.me/ и оставляем чистые юзернеймы/ID
            if "t.me/" in src_channel: src_channel = src_channel.split("t.me/")[-1].replace("@", "")
            if "t.me/" in dest_chat: dest_chat = dest_chat.split("t.me/")[-1].replace("@", "")

            # Выбираем случайный текст из заполненных окон
            valid_comments = [c for c in config.COMMENT_VARIANTS if c.strip()]
            if not valid_comments:
                if status_cb: status_cb("❌ Ошибка: Все 5 окон комментариев пусты!")
                return False
            chosen_text = random.choice(valid_comments)

            try:
                # Преобразуем строку в сущность Telegram (аккаунт должен быть подписан на чат)
                if dest_chat.startswith("-100") or dest_chat.isdigit():
                    chat_entity = await self.client.get_entity(int(dest_chat))
                else:
                    chat_entity = await self.client.get_entity(dest_chat)

                # РЕЖИМ 1: Поле источника пустое — отправляем обычный пост в чат
                if not src_channel:
                    await self.client.send_message(chat_entity, chosen_text)
                    if status_cb: status_cb(f"💬 [{real_index+1}/{total_pairs}] Отправлен посев в чат {dest_chat}")

                # РЕЖИМ 2: Связка заполнена — комментируем последний пост
                else:
                    if src_channel.startswith("-100") or src_channel.isdigit():
                        entity = await self.client.get_entity(int(src_channel))
                    else:
                        entity = await self.client.get_entity(src_channel)

                    messages = await self.client.get_messages(entity, limit=1)
                    
                    if messages:
                        last_post = messages[0]
                        post_key = f"{entity.id}_{last_post.id}"

                        # Страховка от повторного спама в один пост
                        if post_key not in self.processed_posts:
                            await self.client.send_message(
                                chat_entity,
                                chosen_text,
                                reply_to=last_post.id
                            )
                            self.processed_posts.add(post_key)
                            self._save_processed_posts()
                            if status_cb: status_cb(f"🎯 [{real_index+1}/{total_pairs}] Ответили под постом в чат {dest_chat}")
                        else:
                            if status_cb: status_cb(f"⏭ Пост в {src_channel} уже комментировали на прошлых кругах. Пропуск.")
                    else:
                        if status_cb: status_cb(f"⚠️ В канале {src_channel} нет постов для ответа.")

                # Шагаем дальше по списку
                config.SENT_TODAY_COUNT += 1
                config.CURRENT_INDEX += 1
                config.save_settings()

                # Размазываем лимит на оставшееся время суток
                remaining_comments = config.DAILY_LIMIT - config.SENT_TODAY_COUNT
                if remaining_comments > 0:
                    now = datetime.now()
                    seconds_left_today = ((24 - now.hour - 1) * 3600) + ((60 - now.minute - 1) * 60) + (60 - now.second)
                    
                    base_delay = seconds_left_today / remaining_comments
                    final_delay = base_delay * random.uniform(0.75, 1.25)
                    
                    if final_delay < config.COMMENT_DELAY_MIN:
                        final_delay = random.uniform(config.COMMENT_DELAY_MIN, config.COMMENT_DELAY_MAX)

                    minutes_wait = int(final_delay // 60)
                    if status_cb:
                        status_cb(f"📊 Прогресс суток: {config.SENT_TODAY_COUNT}/{config.DAILY_LIMIT}. Пауза перед следующим действием: ~{minutes_wait} мин.")
                    
                    await asyncio.sleep(final_delay)

            except Exception as e:
                if status_cb: status_cb(f"❌ Ошибка на индексе {real_index} (Чат: {dest_chat}): {str(e)}")
                config.CURRENT_INDEX += 1
                config.save_settings()
                await asyncio.sleep(random.uniform(config.COMMENT_DELAY_MIN, config.COMMENT_DELAY_MAX))
                continue

        if status_cb: status_cb(f"✅ Норма выполнена ({config.SENT_TODAY_COUNT}/{config.DAILY_LIMIT}). Автосон до полуночи...")
        
        now = datetime.now()
        seconds_until_midnight = ((24 - now.hour - 1) * 3600) + ((60 - now.minute - 1) * 60) + (60 - now.second)
        await asyncio.sleep(seconds_until_midnight + 10)
        
        return await self.run_commenting_with_ids(channel_ids, pairs, "", status_cb)
