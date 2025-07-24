@echo off
REM Скрипт для запуска Steam Hour Booster Bot на Windows

echo 🚀 Запуск Steam Hour Booster Bot...

REM Проверяем наличие виртуального окружения
if not exist ".venv" (
    echo ❌ Виртуальное окружение не найдено!
    echo 📋 Выполните: python -m venv .venv
    pause
    exit /b 1
)

REM Проверяем наличие конфигурации
if not exist "config\config.ini" (
    echo ❌ Файл конфигурации не найден!
    echo 📋 Скопируйте config\config.ini.example в config\config.ini и настройте его
    pause
    exit /b 1
)

REM Активируем виртуальное окружение и запускаем бота
call .venv\Scripts\activate
python HourBooster.py
pause
