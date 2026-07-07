import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QTabWidget, 
                             QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QGroupBox, 
                             QSpinBox, QDoubleSpinBox, QTextEdit, QScrollArea)
import config
from telegram_bot import TelegramBot

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Telegram Client Manager (July 2026 Ultimate)")
        self.setMinimumSize(700, 650)
        
        self.bot = TelegramBot()
        self.pairs = [] 

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.init_auth_tab()
        self.init_comment_tab()
        self.init_schedule_tab()

    def init_auth_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        auth_group = QGroupBox("Данные аккаунта Telegram")
        auth_layout = QGridLayout()
        auth_layout.addWidget(QLabel("API ID:"), 0, 0)
        self.api_id_input = QLineEdit()
        auth_layout.addWidget(self.api_id_input, 0, 1)
        
        auth_layout.addWidget(QLabel("API Hash:"), 1, 0)
        self.api_hash_input = QLineEdit()
        auth_layout.addWidget(self.api_hash_input, 1, 1)

        auth_layout.addWidget(QLabel("Телефон:"), 2, 0)
        self.phone_input = QLineEdit()
        auth_layout.addWidget(self.phone_input, 2, 1)
        auth_group.setLayout(auth_layout)
        layout.addWidget(auth_group)

        proxy_group = QGroupBox("Настройки приватного прокси (Антифрод)")
        proxy_layout = QGridLayout()

        proxy_layout.addWidget(QLabel("Тип прокси:"), 0, 0)
        self.proxy_type_combo = QComboBox()
        self.proxy_type_combo.addItems(["SOCKS5", "HTTP"])
        self.proxy_type_combo.setCurrentText(config.PROXY_TYPE)
        self.proxy_type_combo.currentTextChanged.connect(self.save_proxy_fields)
        proxy_layout.addWidget(self.proxy_type_combo, 0, 1)

        proxy_layout.addWidget(QLabel("IP Адрес:"), 1, 0)
        self.proxy_ip_input = QLineEdit(config.PROXY_IP)
        self.proxy_ip_input.textChanged.connect(self.save_proxy_fields)
        proxy_layout.addWidget(self.proxy_ip_input, 1, 1)

        proxy_layout.addWidget(QLabel("Порт:"), 2, 0)
        self.proxy_port_input = QLineEdit(config.PROXY_PORT)
        self.proxy_port_input.textChanged.connect(self.save_proxy_fields)
        proxy_layout.addWidget(self.proxy_port_input, 2, 1)

        proxy_layout.addWidget(QLabel("Логин:"), 3, 0)
        self.proxy_user_input = QLineEdit(config.PROXY_USER)
        self.proxy_user_input.textChanged.connect(self.save_proxy_fields)
        proxy_layout.addWidget(self.proxy_user_input, 3, 1)

        proxy_layout.addWidget(QLabel("Пароль:"), 4, 0)
        self.proxy_pass_input = QLineEdit(config.PROXY_PASS)
        self.proxy_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.proxy_pass_input.textChanged.connect(self.save_proxy_fields)
        proxy_layout.addWidget(self.proxy_pass_input, 4, 1)

        proxy_group.setLayout(proxy_layout)
        layout.addWidget(proxy_group)

        self.auth_btn = QPushButton("Авторизоваться")
        layout.addWidget(self.auth_btn)
        self.tabs.addTab(tab, "Авторизация")

    def init_comment_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)

        scroll_layout.addWidget(QLabel("📝 Варианты комментариев для случайной ротации (Рандомный выбор):"))
        
        self.comment_edits = []
        for i in range(5):
            box = QGroupBox(f"Вариант текста №{i+1}")
            box_layout = QVBoxLayout()
            edit = QTextEdit()
            edit.setMinimumHeight(60)
            edit.setText(config.COMMENT_VARIANTS[i])
            edit.textChanged.connect(self.save_comments_from_gui)
            box_layout.addWidget(edit)
            box.setLayout(box_layout)
            scroll_layout.addWidget(box)
            self.comment_edits.append(edit)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        limit_group = QGroupBox("Настройка суточных лимитов и предохранителей")
        limit_layout = QGridLayout()

        limit_layout.addWidget(QLabel("Лимит действий в сутки:"), 0, 0)
        self.daily_limit_spin = QSpinBox()
        self.daily_limit_spin.setRange(1, 500)
        self.daily_limit_spin.setValue(config.DAILY_LIMIT)
        self.daily_limit_spin.valueChanged.connect(self.save_limits_config)
        limit_layout.addWidget(self.daily_limit_spin, 0, 1)

        limit_layout.addWidget(QLabel("Мин. пауза (сек):"), 1, 0)
        self.delay_min_spin = QDoubleSpinBox()
        self.delay_min_spin.setRange(1.0, 300.0)
        self.delay_min_spin.setValue(config.COMMENT_DELAY_MIN)
        self.delay_min_spin.valueChanged.connect(self.save_limits_config)
        limit_layout.addWidget(self.delay_min_spin, 1, 1)

        limit_layout.addWidget(QLabel("Макс. пауза (сек):"), 1, 2)
        self.delay_max_spin = QDoubleSpinBox()
        self.delay_max_spin.setRange(1.0, 300.0)
        self.delay_max_spin.setValue(config.COMMENT_DELAY_MAX)
        self.delay_max_spin.valueChanged.connect(self.save_limits_config)
        limit_layout.addWidget(self.delay_max_spin, 1, 3)

        self.status_limit_label = QLabel(f"Отправлено за сегодня: {config.SENT_TODAY_COUNT} из {config.DAILY_LIMIT}")
        self.status_limit_label.setStyleSheet("font-weight: bold; color: #007AFF;")
        limit_layout.addWidget(self.status_limit_label, 2, 0, 1, 4)

        limit_group.setLayout(limit_layout)
        layout.addWidget(limit_group)

        self.start_comment_btn = QPushButton("Запустить комментирование")
        layout.addWidget(self.start_comment_btn)
        self.tabs.addTab(tab, "Комментирование")

    def init_schedule_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("Здесь настраивается расписание сессий..."))
        self.tabs.addTab(tab, "Расписание")

    def save_proxy_fields(self):
        config.PROXY_TYPE = self.proxy_type_combo.currentText()
        config.PROXY_IP = self.proxy_ip_input.text().strip()
        config.PROXY_PORT = self.proxy_port_input.text().strip()
        config.PROXY_USER = self.proxy_user_input.text().strip()
        config.PROXY_PASS = self.proxy_pass_input.text().strip()
        config.save_settings()

    def save_comments_from_gui(self):
        for i in range(5):
            config.COMMENT_VARIANTS[i] = self.comment_edits[i].toPlainText()
        config.save_settings()

    def save_limits_config(self):
        config.DAILY_LIMIT = self.daily_limit_spin.value()
        config.COMMENT_DELAY_MIN = self.delay_min_spin.value()
        config.COMMENT_DELAY_MAX = self.delay_max_spin.value()
        self.status_limit_label.setText(f"Отправлено за сегодня: {config.SENT_TODAY_COUNT} из {config.DAILY_LIMIT}")
        config.save_settings()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
