#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/venv"
VENV_PYTHON="$VENV_DIR/bin/python3"

clear

echo "========================================"
echo "  Запуск TelegramAutoBot"
echo "========================================"
echo

echo "Проверяю наличие Python 3..."
if ! command -v python3 >/dev/null 2>&1; then
    echo "Ошибка: python3 не найден. Установите Python 3.10+ и попробуйте снова."
    exit 1
fi

if [ ! -x "$VENV_PYTHON" ]; then
    echo "Создаю виртуальное окружение..."
    python3 -m venv "$VENV_DIR"
fi

echo "Проверяю и устанавливаю зависимости..."
"$VENV_PYTHON" -m pip install --upgrade pip >/dev/null
"$VENV_PYTHON" -m pip install -r requirements.txt

echo

echo "Запускаю приложение..."
"$VENV_PYTHON" main.py
