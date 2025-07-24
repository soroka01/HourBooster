import time
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from ..steam.steam_manager import clients

# Функция для создания главной клавиатуры
def create_main_keyboard(accounts):
    """Создать главную клавиатуру"""
    keyboard = []
    
    for account_name in accounts:
        account_num = account_name[-1]  # Получаем номер аккаунта
        username = accounts[account_name]['username']
        status = "🟢 Активен" if account_name in clients and clients[account_name].logged_on else "🔴 Неактивен"
        keyboard.append([InlineKeyboardButton(
            text=f"Аккаунт {account_num} ({username}) - {status}", 
            callback_data=f"account_{account_name}"
        )])
    
    keyboard.append([InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh")])
    keyboard.append([InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Функция для получения текста главного меню с актуальной информацией
def get_main_menu_text(accounts):
    """Получить текст главного меню с актуальной информацией"""
    text = "🎮 *Steam Hour Booster*\n\n"
    text += "Выберите аккаунт для управления:\n\n"
    
    if not accounts:
        text += "❌ Аккаунты не найдены в config.ini"
    else:
        # Добавляем краткую сводку активных аккаунтов
        active_count = sum(1 for acc in accounts if acc in clients and clients[acc].logged_on)
        text += f"📊 Активных аккаунтов: {active_count}/{len(accounts)}\n"
        text += f"🕐 Обновлено: {time.strftime('%H:%M:%S')}\n\n"
    
    return text

# Функция для создания клавиатуры для управления конкретным аккаунтом
def create_account_keyboard(account_name):
    """Создать клавиатуру для управления конкретным аккаунтом"""
    keyboard = []
    
    if account_name in clients and clients[account_name].logged_on:
        keyboard.append([InlineKeyboardButton(text="⏹️ Остановить", callback_data=f"stop_{account_name}")])
        keyboard.append([InlineKeyboardButton(text="📊 Статистика", callback_data=f"stats_{account_name}")])
    else:
        keyboard.append([InlineKeyboardButton(text="▶️ Запустить", callback_data=f"start_{account_name}")])
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Функция для создания клавиатуры с кнопкой отмены
def create_cancel_keyboard():
    """Создать клавиатуру с кнопкой отмены"""
    keyboard = [
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_code")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
