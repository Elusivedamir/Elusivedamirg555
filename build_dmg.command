#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

APP_NAME="TelegramAutoBot.app"
APP_PATH="$SCRIPT_DIR/dist/$APP_NAME"
OUTPUT_DMG="$SCRIPT_DIR/dist/TelegramAutoBot.dmg"
STAGING_DIR="$SCRIPT_DIR/dist/dmg_staging"
VOL_NAME="TelegramAutoBot"

clear

echo "========================================"
echo "  Создание DMG-установщика"
echo "========================================"
echo

if [ ! -d "$APP_PATH" ]; then
  echo "Ошибка: не найдено приложение по пути: $APP_PATH"
  echo "Сначала соберите .app через install_full.command или build_macos.command."
  exit 1
fi

echo "Найдено приложение: $APP_PATH"
echo

rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"
cp -R "$APP_PATH" "$STAGING_DIR/$APP_NAME"
ln -s /Applications "$STAGING_DIR/Applications"

rm -f "$OUTPUT_DMG"

echo "Создаю DMG..."
hdiutil create -volname "$VOL_NAME" -srcfolder "$STAGING_DIR" -ov -format UDZO "$OUTPUT_DMG"

echo

echo "DMG готов: $OUTPUT_DMG"
echo "Откройте файл и перетащите TelegramAutoBot.app в Applications."
