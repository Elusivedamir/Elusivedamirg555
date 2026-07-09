# Инструкция по проверке проекта на macOS

## 1. Подготовка окружения

### Проверка версии Python
```bash
python3 --version
```
Требуется Python 3.10+

### Установка Xcode Command Line Tools (если не установлены)
```bash
xcode-select --install
```

### Создание виртуального окружения
```bash
cd /path/to/Elusivedamirg555-main
python3 -m venv venv
source venv/bin/activate
```

### Установка зависимостей
```bash
pip install --upgrade pip
pip install --upgrade PyQt6 PyQt6-Qt6 PyQt6-sip qasync telethon keyring cryptg pysocks pyinstaller
pip install -r requirements.txt
```

### Проверка конфликтов зависимостей
```bash
pip check
```

## 2. Проверка синтаксиса

```bash
python3 -m py_compile main.py config.py utils.py telegram_bot.py gui.py gui_styles.py gui_auth.py gui_channels.py gui_pairs.py gui_commenting.py
```

## 3. Запуск smoke-тестов

```bash
python3 test_smoke.py
```

Ожидаемый результат: 6/6 тестов пройдено

## 4. Проверка импортов

```bash
python3 -c "import config; print('config.py: OK')"
python3 -c "import utils; print('utils.py: OK')"
python3 -c "import telegram_bot; print('telegram_bot.py: OK')"
python3 -c "import gui; print('gui.py: OK')"
```

## 5. Запуск GUI (тест отображения)

```bash
python3 main.py
```

Ожидаемое поведение:
- Окно приложения должно открыться
- Должны быть видны 4 вкладки: Аккаунт, Каналы, Связки, Комментирование
- Стиль должен быть тёмным (macOS dark theme)
- Шрифт должен быть SF Pro Display

Закрыть окно: Cmd+Q или через меню приложения

## 6. Проверка путей к файлам

Проект использует macOS-специфичные пути:
- `~/Library/Application Support/TelegramAutoBot/` - для настроек и сессий
- `~/Desktop/` - для сохранения CSV файлов (через диалог)

Проверить создание директории:
```bash
ls -la ~/Library/Application\ Support/TelegramAutoBot/
```

## 7. Потенциальные проблемы на macOS

### PyQt6 на macOS
- Убедитесь, что установлены последние версии PyQt6
- Если возникают проблемы с отображением, проверьте переменные окружения в main.py (строки 8-13)

### Шрифт SF Pro Display
- Шрифт должен быть доступен в системе (стандартный для macOS)
- Если шрифт не отображается, можно заменить на системный в main.py (строка 58)

### Права доступа (TCC)
- При первом запуске macOS может запросить права доступа к файлам
- Разрешите доступ при появлении диалога

## 8. Troubleshooting

### Ошибка импорта PyQt6
```bash
pip install --upgrade PyQt6 PyQt6-Qt6 PyQt6-sip
```

### Ошибка с qasync
```bash
pip install --upgrade qasync
```

### Проблемы с отображением GUI
Проверьте переменные окружения в main.py:
```python
os.environ['QT_MAC_WANTS_LAYER'] = '1'
os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '1'
os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
```

### Проблемы с путями к файлам
Убедитесь, что директория существует:
```bash
mkdir -p ~/Library/Application\ Support/TelegramAutoBot/
```

## 9. Логирование

Логи работы бота выводятся в GUI-окно в разделе "Лог работы"
Дополнительные логи можно найти в системном логе macOS:
```bash
log stream --predicate 'process == "Python"' --level debug
```

## 10. Тестирование функциональности

### Тест авторизации
1. Заполните API ID, API Hash и телефон
2. Нажмите "Авторизоваться"
3. Введите код из Telegram

### Тест работы с каналами
1. Добавьте тестовый канал
2. Попробуйте вступить (если авторизованы)

### Тест парсинга в CSV
1. Добавьте каналы в список
2. Авторизуйтесь
3. Нажмите "Парсинг каналов → CSV"
4. Выберите место сохранения

## Итоговая проверка

После выполнения всех шагов:
- ✅ Python 3.10+ установлен
- ✅ Все зависимости установлены без конфликтов
- ✅ Синтаксис всех файлов корректен
- ✅ Smoke-тесты пройдены (6/6)
- ✅ GUI открывается и отображается корректно
- ✅ Пути к файлам работают
- ✅ macOS-оптимизации применены
