#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="TelegramAutoBot.app"
DEST_APP="/Applications/$APP_NAME"

SOURCE_CANDIDATES=(
  "$SCRIPT_DIR/dist/$APP_NAME"
  "$SCRIPT_DIR/$APP_NAME"
)

clear

echo "========================================"
echo "  Установка TelegramAutoBot"
echo "========================================"
echo

echo "Ищу готовое приложение..."
SOURCE_APP=""
for candidate in "${SOURCE_CANDIDATES[@]}"; do
  if [ -d "$candidate" ]; then
    SOURCE_APP="$candidate"
    break
  fi
done

if [ -z "$SOURCE_APP" ]; then
  echo "Ошибка: не найдено приложение $APP_NAME"
  echo "Пожалуйста, сначала соберите .app в папку dist/ или положите его в корень проекта."
  echo
  read -p "Нажмите Enter для выхода..."
  exit 1
fi

echo "Найдено приложение: $SOURCE_APP"
echo

echo "Копирую приложение в /Applications..."
if [ -d "$DEST_APP" ]; then
  echo "Приложение уже существует. Заменяю его..."
  sudo rm -rf "$DEST_APP"
fi
sudo cp -R "$SOURCE_APP" "$DEST_APP"

echo "Приложение установлено."
echo

echo "Снимаю карантин Gatekeeper..."
sudo xattr -cr "$DEST_APP"

echo "Выдаю права на запуск..."
sudo chmod -R 755 "$DEST_APP"

echo

echo "Открываю приложение..."
open "$DEST_APP"

echo "Готово! TelegramAutoBot запущено."
echo
read -p "Нажмите Enter для выхода..."
