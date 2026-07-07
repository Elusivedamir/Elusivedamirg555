import asyncio
import os
import json
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
    path = os.path.expanduser(f"~/Library/Application Support/{APP_NAME}")
    os.makedirs(path, exist_ok=True)
    return path

def history_file():
    return os.path.join(app_dir(), "processed_posts.json")

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
        self.processed_posts = set()
    
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
            
            session_path = os.path.join(app_dir(), self.session_name)
            
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
    
    async def join_channels(self, channels, progress_cb=None, status_cb=None, time_cb=None):
        total = len(channels)
        for i, ch in enumerate(channels, 1):
            if self.stop_requested:
                return False
            
            try:
                invite_hash = self._extract_invite_hash(ch)
                if invite_hash:
                    await self.client(ImportChatInviteRequest(invite_hash))
                else:
                    entity = await self.get_entity(ch)
                    await self.client(JoinChannelRequest(entity))
                
                if status_cb:
                    status_cb(f"✅ Вступил {ch}")
                    
            except errors.FloodWaitError as e:
                if status_cb:
                    status_cb(f"⏳ FloodWait: ожидание {e.seconds} сек. ({ch})")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                if status_cb:
                    status_cb(f"❌ {ch}: {e}")
                logger.error(f"Ошибка вступления в {ch}: {e}")
            
            if progress_cb:
                progress_cb(i, total)
            
            await asyncio.sleep(utils.random_delay(config.JOIN_DELAY))
        
        return True
    
    async def run_commenting_with_ids(self, channels, pairs, text, progress_cb=None, status_cb=None, time_cb=None):
        self.load_history()
        
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
                status_cb(f"✅ Дневной лимит ({config.DAILY_LIMIT}) достигнут. Ждём полуночи...")
            return True
        
        total = len(pairs)
        current = 0
        
        while config.SENT_TODAY < config.DAILY_LIMIT:
            if self.stop_requested:
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
                    continue
                
                post = messages[0]
                key = f"{source}_{post.id}"
                
                if self.is_post_processed(source, post.id):
                    if status_cb:
                        status_cb(f"⏭ Пост в {source} уже прокомментирован")
                    current += 1
                    continue
                
                if destination and destination.strip():
                    # Режим 1: комментарий к посту в чате обсуждения
                    chat = await self.get_entity(destination)
                    await self.client.send_message(
                        chat,
                        text,
                        reply_to=post.id
                    )
                    if status_cb:
                        status_cb(f"💬 [{config.SENT_TODAY+1}/{config.DAILY_LIMIT}] Ответ на пост в {destination}")
                else:
                    # Режим 2: обычное сообщение в канал
                    await self.client.send_message(
                        channel,
                        text
                    )
                    if status_cb:
                        status_cb(f"💬 [{config.SENT_TODAY+1}/{config.DAILY_LIMIT}] Обычное сообщение в {source}")
                
                self.mark_post_processed(source, post.id)
                config.SENT_TODAY += 1
                config.save_settings()
                
                current += 1
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
                
                await asyncio.sleep(final_delay)
                
            except errors.FloodWaitError as e:
                if status_cb:
                    status_cb(f"⏳ FloodWait: ожидание {e.seconds} сек.")
                await asyncio.sleep(e.seconds)
                continue
            except Exception as e:
                if status_cb:
                    status_cb(f"❌ Ошибка для {source}: {e}")
                logger.error(f"Ошибка отправки комментария для {source}: {e}")
                current += 1
                await asyncio.sleep(random.uniform(
                    config.COMMENT_DELAY_MIN,
                    config.COMMENT_DELAY_MAX
                ))
                continue
        
        if status_cb:
            status_cb(f"✅ Дневной лимит ({config.DAILY_LIMIT}) достигнут! Ждём полуночи...")
        
        now = datetime.now()
        seconds_until_midnight = (
            (24 - now.hour - 1) * 3600 +
            (60 - now.minute - 1) * 60 +
            (60 - now.second)
        )
        await asyncio.sleep(seconds_until_midnight + 10)
        
        if not self.stop_requested:
            if status_cb:
                status_cb("🔄 Новый день! Продолжаем работу...")
            return await self.run_commenting_with_ids(channels, pairs, text, progress_cb, status_cb, time_cb)
        
        return True
