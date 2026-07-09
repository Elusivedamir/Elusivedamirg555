import asyncio
import json
import os
import random
import traceback
from datetime import datetime

from telethon import TelegramClient, errors
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

import config
import utils

logger = utils.setup_logger()
APP_NAME = "TelegramAutoBot"


def app_dir():
    return config.get_app_dir()


def history_file():
    return config.get_history_file()


class TelegramBot:
    def __init__(self, api_id, api_hash, session_name="session", proxy=None, code_callback=None):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.proxy = proxy
        self.code_callback = code_callback
        self.client = None
        self.is_connected = False
        self.phone = None
        self.stop_requested = False
        self.stop_event = asyncio.Event()
        self.pause_event = asyncio.Event()
        self.pause_event.set()
        self.processed_posts = set()
        self.dry_run = False
        self.stats = {
            "processed": 0,
            "sent": 0,
            "skipped": 0,
            "errors": 0,
        }

    def request_stop(self):
        self.stop_requested = True
        self.stop_event.set()

    def reset_stop(self):
        self.stop_requested = False
        self.stop_event.clear()

    def pause(self):
        self.pause_event.clear()

    def resume(self):
        self.pause_event.set()

    def set_dry_run(self, enabled: bool):
        self.dry_run = bool(enabled)

    def update_stats(self, processed=0, sent=0, skipped=0, errors=0):
        self.stats["processed"] += processed
        self.stats["sent"] += sent
        self.stats["skipped"] += skipped
        self.stats["errors"] += errors
        self._save_stats_to_file()

    def get_stats(self):
        return dict(self.stats)

    def reset_stats(self):
        self.stats = {"processed": 0, "sent": 0, "skipped": 0, "errors": 0}
        self._save_stats_to_file()

    def _save_stats_to_file(self):
        try:
            payload = {
                "timestamp": datetime.now().isoformat(),
                **self.stats,
            }
            with open(config.get_stats_file(), "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Ошибка сохранения статистики: {e}")

    def load_stats_from_file(self):
        try:
            if not os.path.exists(config.get_stats_file()):
                return self.stats
            with open(config.get_stats_file(), "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for key in self.stats:
                    if key in data:
                        self.stats[key] = int(data[key])
            return self.stats
        except Exception as e:
            logger.error(f"Ошибка чтения статистики: {e}")
            return self.stats

    async def _sleep_interruptible(self, delay, status_cb=None, message=None):
        if delay <= 0:
            return
        try:
            end_time = asyncio.get_running_loop().time() + delay
            while True:
                remaining = end_time - asyncio.get_running_loop().time()
                if remaining <= 0:
                    break
                if self.stop_event.is_set():
                    if status_cb:
                        status_cb(message or "🛑 Остановка...")
                    return
                if self.pause_event.is_set():
                    await asyncio.sleep(min(0.1, remaining))
                    continue
                done, _ = await asyncio.wait(
                    [asyncio.create_task(self.pause_event.wait()), asyncio.create_task(self.stop_event.wait())],
                    timeout=min(0.2, remaining),
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if self.stop_event.is_set():
                    if status_cb:
                        status_cb(message or "🛑 Остановка...")
                    return
                if self.pause_event.is_set():
                    continue
        except Exception:
            pass

    async def _handle_retry(self, exc, attempt, status_cb=None, default_delay=10):
        if isinstance(exc, errors.FloodWaitError):
            delay = max(exc.seconds + 2, default_delay)
            if status_cb:
                status_cb(f"⏳ FloodWait: ожидание {delay} сек.")
            await self._sleep_interruptible(delay, status_cb, "🛑 Остановка после FloodWait")
            return delay

        if isinstance(exc, errors.TooManyRequestsError):
            delay = min(60, default_delay * (2 ** attempt))
            if status_cb:
                status_cb(f"⏳ TooManyRequests: ожидание {delay} сек.")
            await self._sleep_interruptible(delay, status_cb, "🛑 Остановка после TooManyRequests")
            return delay

        if isinstance(exc, errors.SlowModeWaitError):
            delay = max(exc.seconds, default_delay)
            if status_cb:
                status_cb(f"⏳ SlowModeWait: ожидание {delay} сек.")
            await self._sleep_interruptible(delay, status_cb, "🛑 Остановка после SlowModeWait")
            return delay

        if isinstance(exc, (TimeoutError, asyncio.TimeoutError, ConnectionError)):
            delay = min(30, default_delay * (2 ** attempt))
            if status_cb:
                status_cb(f"⏳ Сетевой таймаут/обрыв: повтор через {delay} сек.")
            await self._sleep_interruptible(delay, status_cb, "🛑 Остановка после сетевой ошибки")
            return delay

        delay = min(30, default_delay * (2 ** attempt))
        if status_cb:
            status_cb(f"⏳ Временная ошибка: повтор через {delay} сек.")
        await self._sleep_interruptible(delay, status_cb, "🛑 Остановка после временной ошибки")
        return delay
    
    def load_history(self):
        try:
            with open(history_file(), "r", encoding="utf-8") as f:
                data = json.load(f)
                self.processed_posts = set(data.keys()) if isinstance(data, dict) else set()
                return data
        except Exception:
            return {}
    
    def save_history(self, data):
        try:
            with open(history_file(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Ошибка сохранения истории: {e}")
    
    def is_post_processed(self, channel_id, post_id):
        key = f"{channel_id}_{post_id}"
        return key in self.processed_posts
    
    def mark_post_processed(self, channel_id, post_id):
        key = f"{channel_id}_{post_id}"
        self.processed_posts.add(key)
        history = self.load_history()
        history[key] = True
        self.save_history(history)
    
    async def connect(self):
        credentials = config.load_auth_credentials()
        if self.api_id is None or self.api_id == "":
            self.api_id = int(credentials.get("api_id", "0") or 0)
        if not self.api_hash:
            self.api_hash = credentials.get("api_hash", "") or ""
        if not self.phone:
            self.phone = credentials.get("phone", "") or ""

        try:
            proxy = None
            if self.proxy:
                from socks import PROXY_TYPE_SOCKS5, PROXY_TYPE_SOCKS4
                proxy_type = (
                    PROXY_TYPE_SOCKS5
                    if self.proxy.get("proxy_type", "socks5") == "socks5"
                    else PROXY_TYPE_SOCKS4
                )
                proxy = (
                    proxy_type,
                    self.proxy["addr"],
                    int(self.proxy["port"]),
                    True,
                    self.proxy.get("username", ""),
                    self.proxy.get("password", "")
                )

            session_path = config.get_session_path(self.session_name)

            self.client = TelegramClient(
                session_path,
                self.api_id,
                self.api_hash,
                proxy=proxy
            )

            await self.client.connect()

            if not await self.client.is_user_authorized():
                await self.client.send_code_request(self.phone)

                if asyncio.iscoroutinefunction(self.code_callback):
                    code = await self.code_callback("Введите код из Telegram:")
                else:
                    code = self.code_callback("Введите код из Telegram:")

                if not code:
                    logger.error("Код авторизации не был введен")
                    return False

                await self.client.sign_in(self.phone, code)

            self.is_connected = True
            logger.info("Telegram подключен")
            return True

        except errors.SessionPasswordNeededError:
            if asyncio.iscoroutinefunction(self.code_callback):
                password = await self.code_callback("Введите пароль 2FA:")
            else:
                password = self.code_callback("Введите пароль 2FA:")

            if not password:
                logger.error("Пароль 2FA не был введен")
                return False

            await self.client.sign_in(password=password)
            self.is_connected = True
            return True

        except Exception as e:
            logger.error(f"Ошибка при подключении клиента: {e}")
            logger.error(traceback.format_exc())
            return False
    
    async def disconnect(self):
        if self.client:
            await self.client.disconnect()
            self.is_connected = False
    
    async def get_entity(self, value):
        value = str(value).strip()
        for prefix in ("https://", "http://"):
            if value.startswith(prefix):
                value = value[len(prefix):]
        if value.startswith("t.me/"):
            value = value.replace("t.me/", "")
        return await self.client.get_entity(value)
    
    @staticmethod
    def _extract_invite_hash(value):
        value = str(value).strip()
        for prefix in ("https://", "http://"):
            if value.startswith(prefix):
                value = value[len(prefix):]
        if value.startswith("t.me/"):
            value = value[len("t.me/"):]
        if value.startswith("+"):
            return value[1:]
        if value.startswith("joinchat/"):
            return value[len("joinchat/"):]
        return None
    
    async def join_channels(self, channels, progress_cb=None, status_cb=None, time_cb=None, stats_cb=None):
        total = len(channels)
        self.reset_stop()
        for i, ch in enumerate(channels, 1):
            if self.stop_requested or self.stop_event.is_set():
                return False

            await self.pause_event.wait()
            if self.stop_requested or self.stop_event.is_set():
                return False

            try:
                invite_hash = self._extract_invite_hash(ch)
                if self.dry_run:
                    if status_cb:
                        status_cb(f"🧪 DRY RUN: вступление в {ch} пропущено")
                    self.update_stats(processed=1, sent=0, skipped=1, errors=0)
                    if stats_cb:
                        stats_cb(self.get_stats())
                    if progress_cb:
                        progress_cb(i, total)
                    continue
                if invite_hash:
                    await self.client(ImportChatInviteRequest(invite_hash))
                else:
                    entity = await self.get_entity(ch)
                    await self.client(JoinChannelRequest(entity))

                self.update_stats(processed=1, sent=1, skipped=0, errors=0)
                if stats_cb:
                    stats_cb(self.get_stats())
                if status_cb:
                    status_cb(f"✅ Вступил {ch}")

            except Exception as e:
                if self.stop_requested or self.stop_event.is_set():
                    return False
                self.update_stats(processed=1, sent=0, skipped=0, errors=1)
                if stats_cb:
                    stats_cb(self.get_stats())
                if status_cb:
                    status_cb(f"❌ {ch}: {e}")
                logger.error(f"Ошибка вступления в {ch}: {e}")
                await self._handle_retry(e, attempt=0, status_cb=status_cb, default_delay=5)

            if progress_cb:
                progress_cb(i, total)

            if self.stop_requested or self.stop_event.is_set():
                return False
            await self._sleep_interruptible(utils.random_delay(config.JOIN_DELAY), status_cb=status_cb, message="🛑 Остановка после паузы")

        return True
    
    async def run_commenting_with_ids(self, channels, pairs, text, progress_cb=None, status_cb=None, time_cb=None, stats_cb=None):
        self.load_history()
        self.reset_stop()

        today = datetime.now().strftime("%Y-%m-%d")
        if config.LAST_RESET_DATE != today:
            config.SENT_TODAY = 0
            config.LAST_RESET_DATE = today
            config.save_settings()

        if not pairs:
            if status_cb:
                status_cb("⚠️ Список связок пуст!")
            return False

        if config.SENT_TODAY >= config.DAILY_LIMIT:
            if status_cb:
                status_cb(f"✅ Дневной лимит ({config.DAILY_LIMIT}) достигнут. Завершаем работу.")
            return True

        total = len(pairs)
        current = 0
        attempt = 0

        while config.SENT_TODAY < config.DAILY_LIMIT:
            if self.stop_requested or self.stop_event.is_set():
                if status_cb:
                    status_cb("🛑 Процесс комментирования остановлен")
                return False

            today = datetime.now().strftime("%Y-%m-%d")
            if config.LAST_RESET_DATE != today:
                config.SENT_TODAY = 0
                config.LAST_RESET_DATE = today
                config.save_settings()
                if status_cb:
                    status_cb("🔄 Новый день! Счётчик сброшен.")

            pair = pairs[current % total]
            source, destination = pair

            try:
                channel = await self.get_entity(source)
                messages = await self.client.get_messages(channel, limit=1)

                if not messages:
                    if status_cb:
                        status_cb(f"⚠️ В канале {source} нет постов")
                    current += 1
                    attempt = 0
                    continue

                post = messages[0]

                if self.is_post_processed(source, post.id):
                    self.update_stats(processed=1, sent=0, skipped=1, errors=0)
                    if stats_cb:
                        stats_cb(self.get_stats())
                    if status_cb:
                        status_cb(f"⏭ Пост в {source} уже прокомментирован")
                    current += 1
                    attempt = 0
                    continue

                if self.dry_run:
                    if status_cb:
                        status_cb(f"🧪 DRY RUN: комментарий для {source} не отправлен")
                    self.update_stats(processed=1, sent=0, skipped=1, errors=0)
                    if stats_cb:
                        stats_cb(self.get_stats())
                    current += 1
                    attempt = 0
                    continue

                if destination and destination.strip():
                    await self.client.send_message(channel, text, comment_to=post.id)
                    if status_cb:
                        status_cb(f"💬 [{config.SENT_TODAY+1}/{config.DAILY_LIMIT}] Ответ на пост в {source}")
                else:
                    await self.client.send_message(channel, text)
                    if status_cb:
                        status_cb(f"💬 [{config.SENT_TODAY+1}/{config.DAILY_LIMIT}] Обычное сообщение в {source}")

                self.mark_post_processed(source, post.id)
                config.SENT_TODAY += 1
                config.save_settings()
                self.update_stats(processed=1, sent=1, skipped=0, errors=0)
                if stats_cb:
                    stats_cb(self.get_stats())

                current += 1
                attempt = 0
                if progress_cb:
                    progress_cb(current, total)

                now = datetime.now()
                seconds_left_today = (
                    (24 - now.hour - 1) * 3600 +
                    (60 - now.minute - 1) * 60 +
                    (60 - now.second)
                )
                remaining_comments = config.DAILY_LIMIT - config.SENT_TODAY

                if remaining_comments > 0 and seconds_left_today > 0:
                    base_delay = seconds_left_today / remaining_comments
                    final_delay = base_delay * random.uniform(0.75, 1.25)
                    final_delay = max(
                        config.COMMENT_DELAY_MIN,
                        min(config.COMMENT_DELAY_MAX, final_delay)
                    )
                else:
                    final_delay = random.uniform(
                        config.COMMENT_DELAY_MIN,
                        config.COMMENT_DELAY_MAX
                    )

                if status_cb and time_cb:
                    minutes = int(final_delay // 60)
                    seconds = int(final_delay % 60)
                    time_cb(f"⏳ Следующий комментарий через {minutes} мин {seconds} сек")

                await self._sleep_interruptible(final_delay, status_cb=status_cb, message="🛑 Остановка после паузы")

            except Exception as e:
                if self.stop_requested or self.stop_event.is_set():
                    if status_cb:
                        status_cb("🛑 Процесс комментирования остановлен")
                    return False

                self.update_stats(processed=1, sent=0, skipped=0, errors=1)
                if stats_cb:
                    stats_cb(self.get_stats())
                if status_cb:
                    status_cb(f"❌ Ошибка для {source}: {e}")
                logger.error(f"Ошибка отправки комментария для {source}: {e}")

                current += 1
                attempt += 1
                delay = await self._handle_retry(e, attempt=attempt, status_cb=status_cb, default_delay=5)
                if self.stop_requested or self.stop_event.is_set():
                    return False
                if delay <= 0:
                    await self._sleep_interruptible(random.uniform(config.COMMENT_DELAY_MIN, config.COMMENT_DELAY_MAX), status_cb=status_cb, message="🛑 Остановка после паузы")
                continue

        if status_cb:
            status_cb(f"✅ Дневной лимит ({config.DAILY_LIMIT}) достигнут. Завершаем работу.")
        return True
