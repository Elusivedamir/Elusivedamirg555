import os
import sys
import asyncio
import traceback
import csv
import random
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

import config
from telegram_bot import TelegramBot
from utils import setup_logger, format_time

logger = setup_logger()
APP_NAME = "TelegramAutoBot"

def app_dir():
    path = os.path.expanduser(f"~/Library/Application Support/{APP_NAME}")
    os.makedirs(path, exist_ok=True)
    return path

def app_file(name):
    return os.path.join(app_dir(), name)

def beep():
    QApplication.beep()

# ===== СТИЛЬ ДЛЯ macOS =====
STYLE = """
QMainWindow, QWidget {
    background-color:#2b2b2b;
    color:#d4d4d4;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
}
QTabWidget::pane {
    border: 1px solid #3c3c3c;
    background: #2b2b2b;
}
QTabBar::tab {
    background: #3c3c3c;
    color: #d4d4d4;
    padding: 8px 16px;
    margin-right: 2px;
    border: none;
}
QTabBar::tab:selected {
    background: #2b2b2b;
    border-bottom: 2px solid #3390ec;
    color: white;
}
QTabBar::tab:hover {
    background: #4a4a4a;
}
QGroupBox {
    border: 1px solid #3c3c3c;
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 8px;
    background: #2b2b2b;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}
QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QListWidget, QTableWidget {
    background: #3c3c3c;
    border: 1px solid #4a4a4a;
    border-radius: 4px;
    padding: 4px 6px;
    color: white;
    selection-background-color: #3390ec;
}
QPushButton {
    background: #4a4a4a;
    border-radius: 4px;
    padding: 6px 14px;
    font-weight: bold;
    color: white;
    border: none;
    min-height: 20px;
}
QPushButton:hover {
    background: #5a5a5a;
}
QPushButton:pressed {
    background: #3a3a3a;
}
QPushButton:disabled {
    background: #333333;
    color: #777777;
}
QTextEdit {
    background: #1e1e1e;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
}
QLabel#status_label {
    font-size: 14px;
    font-weight: bold;
}
QTableWidget::item {
    background: #2b2b2b;
    color: #d4d4d4;
    padding: 4px;
}
QTableWidget::item:selected {
    background: #3390ec;
}
QHeaderView::section {
    background: #3c3c3c;
    color: #d4d4d4;
    padding: 4px;
    border: none;
    border-right: 1px solid #4a4a4a;
}
QScrollBar:vertical {
    background: #2b2b2b;
    width: 12px;
    border-radius: 6px;
}
QScrollBar::handle:vertical {
    background: #4a4a4a;
    border-radius: 6px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #5a5a5a;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QComboBox {
    background: #3c3c3c;
    border: 1px solid #4a4a4a;
    border-radius: 4px;
    padding: 4px 6px;
    color: white;
    min-height: 20px;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background: #3c3c3c;
    color: white;
    selection-background-color: #3390ec;
}
"""

class MainWindow(QMainWindow):
    code_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        # ===== ОПТИМИЗАЦИЯ ДЛЯ macOS =====
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        self.bot = None
        self.channels = []
        self.pairs = []
        self.is_task_running = False
        self.comment_text = ""
        self._loop = asyncio.get_event_loop()
        self._code_future = None
        self.load_thread = None

        self.code_requested.connect(self._on_code_requested)

        self.setWindowTitle("Telegram AutoBot")
        self.resize(1000, 900)

        self.init_ui()
        self.setStyleSheet(STYLE)

        # Отложенная инициализация
        QTimer.singleShot(100, self._delayed_init)

    def _delayed_init(self):
        """Отложенная инициализация для предотвращения зависаний"""
        self.load_channels_from_file()
        self.load_pairs_from_file()
        self.load_account_from_file()
        self.load_proxy_from_config()
        self.update_status_labels()

    # ===============================
    # UI - ТОЛЬКО 4 ВКЛАДКИ
    # ===============================

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        self.tabs = QTabWidget()

        # ---------- 1. АККАУНТ ----------
        account = QWidget()
        al = QVBoxLayout(account)

        # API настройки
        api_group = QGroupBox("Данные аккаунта Telegram")
        api_layout = QGridLayout()
        api_layout.addWidget(QLabel("API ID:"), 0, 0)
        self.api_id_edit = QLineEdit()
        self.api_id_edit.setPlaceholderText("api_id")
        api_layout.addWidget(self.api_id_edit, 0, 1)

        api_layout.addWidget(QLabel("API Hash:"), 1, 0)
        self.api_hash_edit = QLineEdit()
        self.api_hash_edit.setPlaceholderText("api_hash")
        api_layout.addWidget(self.api_hash_edit, 1, 1)

        api_layout.addWidget(QLabel("Телефон:"), 2, 0)
        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("+71234567890")
        api_layout.addWidget(self.phone_edit, 2, 1)
        api_group.setLayout(api_layout)
        al.addWidget(api_group)

        # Прокси настройки
        proxy_group = QGroupBox("Настройки прокси (опционально)")
        proxy_layout = QGridLayout()

        proxy_layout.addWidget(QLabel("Тип прокси:"), 0, 0)
        self.proxy_type_combo = QComboBox()
        self.proxy_type_combo.addItems(["SOCKS5", "HTTP"])
        self.proxy_type_combo.setCurrentText(config.PROXY_TYPE)
        self.proxy_type_combo.currentTextChanged.connect(self.save_proxy_settings)
        proxy_layout.addWidget(self.proxy_type_combo, 0, 1)

        proxy_layout.addWidget(QLabel("IP адрес:"), 1, 0)
        self.proxy_ip_edit = QLineEdit()
        self.proxy_ip_edit.setText(config.PROXY_IP)
        self.proxy_ip_edit.setPlaceholderText("127.0.0.1")
        self.proxy_ip_edit.textChanged.connect(self.save_proxy_settings)
        proxy_layout.addWidget(self.proxy_ip_edit, 1, 1)

        proxy_layout.addWidget(QLabel("Порт:"), 2, 0)
        self.proxy_port_edit = QLineEdit()
        self.proxy_port_edit.setText(config.PROXY_PORT)
        self.proxy_port_edit.setPlaceholderText("1080")
        self.proxy_port_edit.textChanged.connect(self.save_proxy_settings)
        proxy_layout.addWidget(self.proxy_port_edit, 2, 1)

        proxy_layout.addWidget(QLabel("Логин:"), 3, 0)
        self.proxy_user_edit = QLineEdit()
        self.proxy_user_edit.setText(config.PROXY_USER)
        self.proxy_user_edit.setPlaceholderText("username (опционально)")
        self.proxy_user_edit.textChanged.connect(self.save_proxy_settings)
        proxy_layout.addWidget(self.proxy_user_edit, 3, 1)

        proxy_layout.addWidget(QLabel("Пароль:"), 4, 0)
        self.proxy_pass_edit = QLineEdit()
        self.proxy_pass_edit.setText(config.PROXY_PASS)
        self.proxy_pass_edit.setPlaceholderText("password (опционально)")
        self.proxy_pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.proxy_pass_edit.textChanged.connect(self.save_proxy_settings)
        proxy_layout.addWidget(self.proxy_pass_edit, 4, 1)

        proxy_group.setLayout(proxy_layout)
        al.addWidget(proxy_group)

        # Кнопка авторизации
        self.auth_btn = QPushButton("Авторизоваться")
        self.auth_btn.clicked.connect(self.authorize)
        al.addWidget(self.auth_btn)

        self.auth_status = QLabel("Не авторизован")
        self.auth_status.setObjectName("status_label")
        self.auth_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.auth_status.setStyleSheet("color: #ff6b6b;")
        al.addWidget(self.auth_status)

        # Статистика
        self.stats_label = QLabel()
        self.stats_label.setObjectName("status_label")
        self.stats_label.setStyleSheet("color: #50fa7b;")
        al.addWidget(self.stats_label)
        al.addStretch()

        self.tabs.addTab(account, "Аккаунт")

        # ---------- 2. КАНАЛЫ ----------
        ch_tab = QWidget()
        chl = QVBoxLayout(ch_tab)

        self.channels_list = QListWidget()
        chl.addWidget(QLabel("Список каналов для вступления:"))
        chl.addWidget(self.channels_list)

        row = QHBoxLayout()
        self.add_edit = QLineEdit()
        self.add_edit.setPlaceholderText("@channel, https://t.me/channel или t.me/+invite")
        self.add_btn = QPushButton("Добавить")
        self.add_btn.clicked.connect(self.add_channel)
        row.addWidget(self.add_edit)
        row.addWidget(self.add_btn)
        chl.addLayout(row)

        self.del_ch_btn = QPushButton("Удалить выбранный канал")
        self.del_ch_btn.clicked.connect(self.delete_channel)
        chl.addWidget(self.del_ch_btn)

        self.join_btn = QPushButton("Вступить в каналы из списка")
        self.join_btn.clicked.connect(self.start_joining)
        chl.addWidget(self.join_btn)

        self.tabs.addTab(ch_tab, "Каналы")

        # ---------- 3. СВЯЗКИ ----------
        pair_tab = QWidget()
        pl = QVBoxLayout(pair_tab)

        # Кнопки управления
        controls_layout = QHBoxLayout()

        self.parse_btn = QPushButton("🔍 Парсинг каналов → CSV")
        self.parse_btn.clicked.connect(self.parse_channels_to_csv)
        controls_layout.addWidget(self.parse_btn)

        self.load_csv_btn = QPushButton("📂 Загрузить CSV")
        self.load_csv_btn.clicked.connect(self.load_pairs_from_csv)
        controls_layout.addWidget(self.load_csv_btn)

        pl.addLayout(controls_layout)

        # Таблица связок (только просмотр)
        pl.addWidget(QLabel("📋 Связки (только просмотр):"))

        self.pairs_table = QTableWidget()
        self.pairs_table.setColumnCount(2)
        self.pairs_table.setHorizontalHeaderLabels(["Канал (Source)", "Чат (Destination)"])
        self.pairs_table.horizontalHeader().setStretchLastSection(True)
        self.pairs_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.pairs_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # Только просмотр

        # Оптимизация таблицы
        self.pairs_table.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.pairs_table.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.pairs_table.setAlternatingRowColors(False)
        self.pairs_table.setSortingEnabled(False)
        self.pairs_table.verticalHeader().setVisible(False)
        self.pairs_table.setShowGrid(False)

        pl.addWidget(self.pairs_table)

        # Удаление связки
        self.del_pair_btn = QPushButton("Удалить выбранную связку")
        self.del_pair_btn.clicked.connect(self.delete_pair)
        pl.addWidget(self.del_pair_btn)

        self.tabs.addTab(pair_tab, "Связки")

        # ---------- 4. КОММЕНТИРОВАНИЕ ----------
        comment_tab = QWidget()
        col = QVBoxLayout(comment_tab)

        # Варианты комментариев
        col.addWidget(QLabel("📝 Варианты комментариев (случайный выбор):"))
        self.comment_variants = []
        for i in range(5):
            variant_layout = QHBoxLayout()
            label = QLabel(f"Вариант {i+1}:")
            edit = QTextEdit()
            edit.setMinimumHeight(60)
            edit.setPlaceholderText(f"Вариант комментария #{i+1}")
            if i < len(config.COMMENT_VARIANTS):
                edit.setText(config.COMMENT_VARIANTS[i])
            edit.textChanged.connect(lambda checked, idx=i: self.save_comment_variant(idx))
            self.comment_variants.append(edit)
            variant_layout.addWidget(label)
            variant_layout.addWidget(edit)
            col.addLayout(variant_layout)

        # Кнопки управления (только 2)
        btn_row = QHBoxLayout()
        self.start_comment_btn = QPushButton("▶️ Запустить комментирование")
        self.start_comment_btn.clicked.connect(self.start_commenting)

        self.stop_btn = QPushButton("⏹ Остановить")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_task)

        btn_row.addWidget(self.start_comment_btn)
        btn_row.addWidget(self.stop_btn)
        col.addLayout(btn_row)

        self.tabs.addTab(comment_tab, "Комментирование")

        # ---------- ЛОГ ----------
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)

        # ОПТИМИЗАЦИЯ ЛОГА (ИСПРАВЛЕНО ДЛЯ PyQt6)
        self.log_box.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.log_box.document().setMaximumBlockCount(1000)

        layout.addWidget(self.tabs)
        layout.addWidget(QLabel("Лог работы:"))
        layout.addWidget(self.log_box)

    # ===============================
    # PROXY SETTINGS
    # ===============================

    def save_proxy_settings(self):
        config.PROXY_TYPE = self.proxy_type_combo.currentText()
        config.PROXY_IP = self.proxy_ip_edit.text().strip()
        config.PROXY_PORT = self.proxy_port_edit.text().strip()
        config.PROXY_USER = self.proxy_user_edit.text().strip()
        config.PROXY_PASS = self.proxy_pass_edit.text().strip()
        config.save_settings()

    def load_proxy_from_config(self):
        self.proxy_type_combo.setCurrentText(config.PROXY_TYPE)
        self.proxy_ip_edit.setText(config.PROXY_IP)
        self.proxy_port_edit.setText(config.PROXY_PORT)
        self.proxy_user_edit.setText(config.PROXY_USER)
        self.proxy_pass_edit.setText(config.PROXY_PASS)

    def get_proxy_dict(self):
        if not config.PROXY_IP or not config.PROXY_PORT:
            return None
        return {
            "proxy_type": config.PROXY_TYPE.lower(),
            "addr": config.PROXY_IP,
            "port": config.PROXY_PORT,
            "username": config.PROXY_USER if config.PROXY_USER else "",
            "password": config.PROXY_PASS if config.PROXY_PASS else ""
        }

    # ===============================
    # LOG
    # ===============================

    def log(self, text):
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_box.append(f"{timestamp} | {text}")
        logger.info(text)

        scrollbar = self.log_box.verticalScrollBar()
        is_at_bottom = scrollbar.value() >= scrollbar.maximum() - 10
        if is_at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    # ===============================
    # ASYNC SAFE
    # ===============================

    def run_async_safe(self, coro):
        task = asyncio.create_task(coro)
        def _on_done(t):
            if t.cancelled():
                return
            exc = t.exception()
            if exc is not None:
                self.log(f"❌ Необработанная ошибка: {exc}")
                logger.error("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
        task.add_done_callback(_on_done)
        return task

    # ===============================
    # FILES
    # ===============================

    def load_channels_from_file(self):
        path = app_file("channels.txt")
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                self.channels = [x.strip() for x in f.readlines() if x.strip()]
            self.refresh_channels()
        except Exception as e:
            self.log(f"Ошибка загрузки каналов: {e}")

    def save_channels(self):
        try:
            with open(app_file("channels.txt"), "w", encoding="utf-8") as f:
                for c in self.channels:
                    f.write(c + "\n")
        except Exception as e:
            self.log(f"Ошибка сохранения каналов: {e}")

    def refresh_channels(self):
        self.channels_list.clear()
        self.channels_list.addItems(self.channels)

    def delete_channel(self):
        current_row = self.channels_list.currentRow()
        if current_row >= 0:
            self.channels.pop(current_row)
            self.save_channels()
            self.refresh_channels()

    def load_pairs_from_file(self):
        path = app_file("pairs.txt")
        if not os.path.exists(path):
            return
        try:
            self.pairs = []
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split("|")
                    if len(parts) >= 1:
                        source = parts[0].strip()
                        destination = parts[1].strip() if len(parts) > 1 else ""
                        self.pairs.append((source, destination))
            self.refresh_pairs()
        except Exception as e:
            self.log(f"Ошибка загрузки связок: {e}")

    def save_pairs(self):
        try:
            with open(app_file("pairs.txt"), "w", encoding="utf-8") as f:
                for source, destination in self.pairs:
                    if destination:
                        f.write(f"{source}|{destination}\n")
                    else:
                        f.write(f"{source}\n")
        except Exception as e:
            self.log(f"Ошибка сохранения связок: {e}")

    def refresh_pairs(self):
        self.pairs_table.setUpdatesEnabled(False)
        try:
            self.pairs_table.setRowCount(len(self.pairs))
            for i, (source, destination) in enumerate(self.pairs):
                self.pairs_table.setItem(i, 0, QTableWidgetItem(source))
                dest_text = destination or "❌ ПУСТО (обычный чат)"
                item = QTableWidgetItem(dest_text)
                if not destination:
                    item.setForeground(QColor("#ffa500"))
                self.pairs_table.setItem(i, 1, item)
        finally:
            self.pairs_table.setUpdatesEnabled(True)

    def delete_pair(self):
        current_row = self.pairs_table.currentRow()
        if current_row >= 0:
            self.pairs.pop(current_row)
            self.save_pairs()
            self.refresh_pairs()

    def load_account_from_file(self):
        path = app_file("account.txt")
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = [x.strip() for x in f.readlines()]
            if len(lines) >= 3:
                self.api_id_edit.setText(lines[0])
                self.api_hash_edit.setText(lines[1])
                self.phone_edit.setText(lines[2])
        except Exception as e:
            self.log(f"Ошибка загрузки данных аккаунта: {e}")

    def save_account(self):
        try:
            with open(app_file("account.txt"), "w", encoding="utf-8") as f:
                f.write(self.api_id_edit.text().strip() + "\n")
                f.write(self.api_hash_edit.text().strip() + "\n")
                f.write(self.phone_edit.text().strip() + "\n")
        except Exception as e:
            self.log(f"Ошибка сохранения данных аккаунта: {e}")

    # ===============================
    # ADD ITEMS
    # ===============================

    def add_channel(self):
        value = self.add_edit.text().strip()
        if value:
            self.channels.append(value)
            self.save_channels()
            self.refresh_channels()
            self.add_edit.clear()

    # ===============================
    # PARSE CHANNELS TO CSV
    # ===============================

    def parse_channels_to_csv(self):
        if not self.bot or not self.bot.is_connected:
            self.log("❌ Сначала пройдите авторизацию")
            return

        if not self.channels:
            self.log("❌ Список каналов пуст")
            return

        self.log("🔍 Начинаю парсинг каналов...")
        self.parse_btn.setEnabled(False)
        self.run_async_safe(self._parse_channels_task())

    async def _parse_channels_task(self):
        try:
            results = []
            total = len(self.channels)

            for i, channel in enumerate(self.channels, 1):
                self.log(f"📡 Обработка {i}/{total}: {channel}")

                try:
                    entity = await self.bot.get_entity(channel)

                    channel_id = str(entity.id)
                    if hasattr(entity, 'megagroup') and entity.megagroup:
                        channel_id = f"-100{abs(entity.id)}"
                    elif hasattr(entity, 'broadcast') and entity.broadcast:
                        channel_id = f"-100{abs(entity.id)}"
                    else:
                        channel_id = str(entity.id)

                    username = entity.username if hasattr(entity, 'username') and entity.username else ""
                    title = entity.title if hasattr(entity, 'title') else ""

                    results.append({
                        'number': i,
                        'channel_id': channel_id,
                        'destination': '',
                        'username': username,
                        'title': title
                    })

                    self.log(f"✅ {title} (ID: {channel_id})")

                except Exception as e:
                    self.log(f"❌ Ошибка: {e}")
                    results.append({
                        'number': i,
                        'channel_id': 'ОШИБКА',
                        'destination': '',
                        'username': '',
                        'title': f'ОШИБКА: {channel}'
                    })

                await asyncio.sleep(1)

            # Сохраняем на рабочий стол
            desktop = Path.home() / "Desktop"
            filename = f"channels_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            filepath = desktop / filename

            with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(['№', 'ID КАНАЛА', 'ID ЧАТА (ЕСЛИ ЕСТЬ)', 'USERNAME', 'НАЗВАНИЕ'])
                writer.writerow(['', '← ID канала', '← СЮДА ВСТАВЛЯЙТЕ', '', ''])

                for r in results:
                    writer.writerow([r['number'], r['channel_id'], r['destination'], r['username'], r['title']])

                writer.writerow([])
                writer.writerow(['⚠️ ИНСТРУКЦИЯ:', 'Заполните ID чата и загрузите CSV в бота'])

            self.log(f"✅ Файл сохранён: {filepath}")
            QMessageBox.information(self, "Готово", f"✅ Файл сохранён:\n{filepath}")

        except Exception as e:
            self.log(f"❌ Ошибка: {e}")
            logger.error(traceback.format_exc())
        finally:
            self.parse_btn.setEnabled(True)

    # ===============================
    # LOAD PAIRS FROM CSV
    # ===============================

    def load_pairs_from_csv(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите CSV файл",
            str(Path.home() / "Desktop"),
            "CSV files (*.csv);;All files (*.*)"
        )

        if not filepath:
            return

        self.log("⏳ Загрузка CSV...")
        self.load_csv_btn.setEnabled(False)
        self.run_async_safe(self._load_csv_task(filepath))

    async def _load_csv_task(self, filepath):
        try:
            delimiter = ';'
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                first_line = f.readline()
                if '|' in first_line:
                    delimiter = '|'
                elif '\t' in first_line:
                    delimiter = '\t'
                elif ',' in first_line:
                    delimiter = ','

            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f, delimiter=delimiter)
                rows = [row for row in reader if row and any(cell.strip() for cell in row)]

                if not rows:
                    self.log("❌ Файл пуст")
                    return

                new_pairs = []
                for row in rows[1:]:
                    if len(row) >= 2:
                        source = row[1].strip() if len(row) > 1 else ""
                        if source and source != 'ОШИБКА' and source != 'ID КАНАЛА':
                            dest = row[2].strip() if len(row) > 2 else ""
                            new_pairs.append((source, dest))

                if new_pairs:
                    self.pairs.extend(new_pairs)
                    self.save_pairs()
                    self.refresh_pairs()

                    with_dest = sum(1 for _, d in new_pairs if d)
                    without_dest = len(new_pairs) - with_dest

                    self.log(f"✅ Загружено {len(new_pairs)} связок")
                    self.log(f"📊 С чатом: {with_dest}, без чата: {without_dest}")

                    QMessageBox.information(
                        self,
                        "Готово",
                        f"✅ Загружено {len(new_pairs)} связок\n"
                        f"С чатом: {with_dest}\n"
                        f"Без чата: {without_dest}"
                    )
                else:
                    self.log("❌ Не найдено валидных связок")

        except Exception as e:
            self.log(f"❌ Ошибка: {e}")
            logger.error(traceback.format_exc())
        finally:
            self.load_csv_btn.setEnabled(True)

    # ===============================
    # COMMENT VARIANTS
    # ===============================

    def save_comment_variant(self, index):
        if index < len(self.comment_variants):
            config.COMMENT_VARIANTS[index] = self.comment_variants[index].toPlainText()
            config.save_settings()

    def get_random_comment(self):
        valid = [c for c in config.COMMENT_VARIANTS if c.strip()]
        return random.choice(valid) if valid else ""

    # ===============================
    # STATISTICS
    # ===============================

    def update_status_labels(self):
        today = datetime.now().strftime("%Y-%m-%d")
        if config.LAST_RESET_DATE != today:
            config.SENT_TODAY = 0
            config.LAST_RESET_DATE = today
            config.save_settings()

        remaining = config.get_remaining_today()
        self.stats_label.setText(
            f"📊 Сегодня: {config.SENT_TODAY}/{config.DAILY_LIMIT} "
            f"(осталось: {remaining})"
        )

    # ===============================
    # TELEGRAM AUTH
    # ===============================

    def authorize(self):
        api_id = self.api_id_edit.text().strip()
        api_hash = self.api_hash_edit.text().strip()
        phone = self.phone_edit.text().strip()

        if not api_id or not api_hash or not phone:
            self.log("❌ Заполните все поля")
            return

        try:
            proxy_dict = self.get_proxy_dict()

            self.bot = TelegramBot(
                int(api_id),
                api_hash,
                session_name=f"session_{phone.replace('+', '')}",
                proxy=proxy_dict,
                code_callback=self.ask_code_async
            )
            self.bot.phone = phone
            self.save_account()
            self.auth_btn.setEnabled(False)
            self.run_async_safe(self.connect_bot())
        except ValueError:
            self.log("❌ API ID должен быть числом")

    async def connect_bot(self):
        self.auth_status.setText("⏳ Подключение...")
        self.auth_status.setStyleSheet("color: #ffb86c;")

        try:
            result = await self.bot.connect()
        except Exception as e:
            result = False
            self.log(f"❌ Ошибка: {e}")
            logger.error(traceback.format_exc())

        if result:
            self.auth_status.setText("✅ Авторизован")
            self.auth_status.setStyleSheet("color: #50fa7b;")
            self.log("✅ Telegram подключен")
            if self.get_proxy_dict():
                self.log(f"🌐 Прокси: {config.PROXY_TYPE} {config.PROXY_IP}:{config.PROXY_PORT}")
            beep()
        else:
            self.auth_status.setText("❌ Ошибка")
            self.auth_status.setStyleSheet("color: #ff5555;")

        self.auth_btn.setEnabled(True)
        self.update_status_labels()

    def ask_code_async(self, message):
        self._code_future = self._loop.create_future()
        self.code_requested.emit(message)
        return self._code_future

    @pyqtSlot(str)
    def _on_code_requested(self, message):
        dialog = QDialog(self)
        dialog.setWindowTitle("Telegram Авторизация")
        dialog.setModal(True)
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(message))

        input_edit = QLineEdit()
        if "пароль" in message.lower():
            input_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(input_edit)

        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._code_future.set_result(input_edit.text().strip())
        else:
            self._code_future.set_result("")

    # ===============================
    # JOIN CHANNELS
    # ===============================

    def start_joining(self):
        if not self.bot or not self.bot.is_connected:
            self.log("❌ Сначала авторизуйтесь")
            return

        if not self.channels:
            self.log("❌ Список каналов пуст")
            return

        if self.is_task_running:
            self.log("⚠️ Задача уже выполняется")
            return

        self.is_task_running = True
        self.join_btn.setEnabled(False)
        self.start_comment_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.run_async_safe(self.run_join_task())

    async def run_join_task(self):
        try:
            self.log("🚀 Вступление в каналы...")
            self.bot.stop_requested = False

            result = await self.bot.join_channels(
                self.channels,
                progress_cb=self.progress,
                status_cb=self.log
            )

            if result:
                self.log("✅ Вступление завершено")
            else:
                self.log("⏹ Остановлено")

        except Exception as e:
            self.log(f"❌ Ошибка: {e}")
            logger.error(traceback.format_exc())
        finally:
            self.is_task_running = False
            self.join_btn.setEnabled(True)
            self.start_comment_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    # ===============================
    # COMMENTING
    # ===============================

    def start_commenting(self):
        if not self.bot or not self.bot.is_connected:
            self.log("❌ Сначала авторизуйтесь")
            return

        text = self.get_random_comment()
        if not text:
            self.log("❌ Заполните хотя бы один комментарий")
            return

        if not self.pairs:
            self.log("❌ Список связок пуст")
            return

        if self.is_task_running:
            self.log("⚠️ Задача уже выполняется")
            return

        self.comment_text = text
        self._begin_commenting()

    def _begin_commenting(self):
        self.is_task_running = True
        self.stop_btn.setEnabled(True)
        self.start_comment_btn.setEnabled(False)
        self.join_btn.setEnabled(False)

        self.run_async_safe(self.run_comment_task())

    async def run_comment_task(self):
        try:
            self.log("🚀 Запуск комментирования...")
            self.bot.stop_requested = False

            result = await self.bot.run_commenting_with_ids(
                [],
                self.pairs,
                self.comment_text,
                progress_cb=self.progress,
                status_cb=self.log,
                time_cb=self.log
            )

            if result:
                self.log("✅ Комментирование завершено")
            else:
                self.log("⏹ Остановлено")

        except Exception as e:
            self.log(f"❌ Ошибка: {e}")
            logger.error(traceback.format_exc())
        finally:
            self.is_task_running = False
            self.stop_btn.setEnabled(False)
            self.start_comment_btn.setEnabled(True)
            self.join_btn.setEnabled(True)
            self.update_status_labels()

    def stop_task(self):
        if self.bot:
            self.bot.stop_requested = True
            self.log("🛑 Остановка...")

    def progress(self, current, total):
        self.log(f"📊 Прогресс: {current}/{total}")

    # ===============================
    # CLOSE
    # ===============================

    def closeEvent(self, event):
        try:
            if self.bot:
                self.run_async_safe(self.bot.disconnect())
        except Exception:
            pass
        event.accept()
