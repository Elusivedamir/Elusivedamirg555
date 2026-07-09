#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

clear

echo "========================================"
echo "  Сборка TelegramAutoBot для macOS"
echo "========================================"
echo

echo "Проверяю Python 3..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "Ошибка: python3 не найден. Установите Python 3.10+ на macOS."
  read -p "Нажмите Enter для выхода..."
  exit 1
fi

echo "Устанавливаю зависимости..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo "Собираю приложение .app..."
python3 -m PyInstaller --clean --noconfirm build.spec

echo

echo "Готово! Артефакт будет в папке dist/"
echo "Ожидаемый путь: $SCRIPT_DIR/dist/TelegramAutoBot.app"
echo
read -p "Нажмите Enter для выхода..."
