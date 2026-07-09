#!/bin/bash
set -e

APP_PATH="/Applications/TelegramAutoBot.app"

clear

echo "========================================"
echo "  Исправление прав и снятие карантина"
echo "========================================"
echo

echo "Проверяю наличие приложения по пути: $APP_PATH"
if [ ! -d "$APP_PATH" ]; then
    echo "Ошибка: приложение не найдено по пути $APP_PATH"
    echo "Пожалуйста, перенесите TelegramAutoBot.app в папку /Applications и попробуйте ещё раз."
    echo
    read -p "Нажмите Enter для выхода..."
    exit 1
fi

echo "Приложение найдено."
echo

echo "Снимаю метку карантина Gatekeeper..."
sudo xattr -cr "$APP_PATH"

echo "Карантин успешно снят."
echo

echo "Выдаю права на запуск и доступ к файлам..."
sudo chmod -R 755 "$APP_PATH"

echo "Права доступа успешно обновлены."
echo

echo "Готово! Теперь приложение можно запускать."
echo
read -p "Нажмите Enter для выхода..."
