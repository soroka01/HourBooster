#!/bin/bash
# Скрипт для запуска Steam Hour Booster Bot

echo "🚀 Запуск Steam Hour Booster Bot..."

# Проверяем наличие виртуального окружения
if [ ! -d ".venv" ]; then
    echo "❌ Виртуальное окружение не найдено!"
    echo "📋 Выполните: python -m venv .venv"
    exit 1
fi

# Проверяем наличие конфигурации
if [ ! -f "config/config.ini" ]; then
    echo "❌ Файл конфигурации не найден!"
    echo "📋 Скопируйте config/config.ini.example в config/config.ini и настройте его"
    exit 1
fi

# Активируем виртуальное окружение и запускаем бота
source .venv/bin/activate
python HourBooster.py
