#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

APP_NAME="TelegramAutoBot.app"
SOURCE_APP="$SCRIPT_DIR/dist/$APP_NAME"
DEST_APP="/Applications/$APP_NAME"

clear

echo "========================================"
echo "  TelegramAutoBot — полная установка"
echo "========================================"
echo

echo "Проверяю Python 3..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "Ошибка: python3 не найден. Установите Python 3.10+ на macOS."
  exit 1
fi

echo "Проверяю и устанавливаю зависимости..."
python3 -m pip install --upgrade pip
python3 -m pip install --upgrade PyQt6 PyQt6-Qt6 PyQt6-sip qasync telethon keyring cryptg pysocks pyinstaller
python3 -m pip install -r requirements.txt

echo

echo "Собираю приложение .app..."
python3 -m PyInstaller --clean --noconfirm build.spec

echo

if [ ! -d "$SOURCE_APP" ]; then
  echo "Ошибка: сборка не создала приложение по пути: $SOURCE_APP"
  exit 1
fi

echo "Найдено приложение: $SOURCE_APP"
echo

echo "Снимаю карантин Gatekeeper..."
sudo xattr -cr "$SOURCE_APP" || true

echo "Выдаю права на запуск..."
sudo chmod -R 755 "$SOURCE_APP"

echo

echo "Копирую приложение в /Applications..."
if [ -d "$DEST_APP" ]; then
  sudo rm -rf "$DEST_APP"
fi
sudo cp -R "$SOURCE_APP" "$DEST_APP"

echo "Проверяю права и карантин в /Applications..."
sudo xattr -cr "$DEST_APP" || true
sudo chmod -R 755 "$DEST_APP"

echo

echo "Открываю приложение..."
open "$DEST_APP"

echo

echo "Установка завершена."
echo "Приложение доступно по пути: $DEST_APP"
