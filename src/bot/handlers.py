import asyncio
import logging
import threading
import time
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from .states import SteamGuardStates
from ..steam.steam_manager import clients, client_threads, pending_logins, run_steam_client, stop_steam_client
from .ui_manager import create_account_keyboard, create_cancel_keyboard

logger = logging.getLogger(__name__)

# Сохраняем ссылку на исходное сообщение для обновления
async def safe_edit_message(callback_query: CallbackQuery, text: str, reply_markup=None, parse_mode=None):
    """Безопасное редактирование сообщения с обработкой ошибки 'message is not modified'"""
    try:
        await callback_query.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Сообщение не изменилось, просто игнорируем ошибку
            logger.debug("Сообщение не изменилось, пропускаем обновление")
            pass
        else:
            # Другая ошибка - пробрасываем дальше
            raise e

# Обработчики команд для управления аккаунтами
async def handle_account_start(account_name, accounts, callback_query: CallbackQuery, state: FSMContext):
    """Запустить аккаунт"""
    user_id = callback_query.from_user.id
    
    if account_name not in accounts:
        await safe_edit_message(callback_query, "❌ Аккаунт не найден в конфигурации")
        return
    
    if account_name in clients and clients[account_name].logged_on:
        text = "⚠️ *Аккаунт уже запущен*\n\n"
        account_data = accounts[account_name]
        text += f"👤 Аккаунт: `{account_data['username']}`\n"
        text += f"📁 Статус: 🟢 Активен\n\n"
        text += "Аккаунт уже работает!"
        keyboard = create_account_keyboard(account_name)
        await safe_edit_message(callback_query, text, keyboard, 'Markdown')
        return
    
    account_data = accounts[account_name]
    
    # Показываем сообщение о запуске
    text = f"🚀 *Запуск аккаунта*\n\n"
    text += f"👤 Аккаунт: `{account_data['username']}`\n"
    text += f"🎮 Игры: {', '.join(map(str, account_data['games']))}\n\n"
    text += "⏳ Подключение к Steam..."
    
    keyboard = create_account_keyboard(account_name)
    await safe_edit_message(callback_query, text, keyboard, 'Markdown')
    
    # Запускаем клиент в отдельном потоке
    thread = threading.Thread(target=run_steam_client, args=(account_name, account_data, user_id))
    thread.daemon = True
    thread.start()
    client_threads[account_name] = thread
    
    # Ждем немного для инициализации
    await asyncio.sleep(5)
    
    # Проверяем результат
    if account_name in clients and clients[account_name].logged_on:
        text = f"🚀 *Аккаунт запущен*\n\n"
        text += f"👤 Аккаунт: `{account_data['username']}`\n"
        text += f"🎮 Игры: {', '.join(map(str, account_data['games']))}\n\n"
        text += "✅ Аккаунт успешно запущен!\n⏰ Накрутка часов активна"
        keyboard = create_account_keyboard(account_name)
        await safe_edit_message(callback_query, text, keyboard, 'Markdown')
    elif user_id in pending_logins:
        # Требуется Steam Guard
        login_data = pending_logins[user_id]
        # Сохраняем ссылку на исходное сообщение для обновления
        pending_logins[user_id]['original_message'] = callback_query
        cancel_keyboard = create_cancel_keyboard()
        
        if login_data['guard_type'] == 'mobile':
            text = f"🔐 *Требуется Steam Guard*\n\n"
            text += f"👤 Аккаунт: `{account_data['username']}`\n\n"
            text += "📱 Введите код из мобильного приложения Steam Guard:\n\n"
            text += "💡 Код состоит из 5 символов (например: ABC12)"
            await state.set_state(SteamGuardStates.waiting_for_guard_code)
        else:  # email
            text = f"📧 *Требуется код с Email*\n\n"
            text += f"👤 Аккаунт: `{account_data['username']}`\n\n"
            text += "📧 Введите код, отправленный на ваш email:\n\n"
            text += "💡 Код состоит из 5 символов"
            await state.set_state(SteamGuardStates.waiting_for_email_code)
        
        # Показываем сообщение с кнопкой отмены
        await safe_edit_message(callback_query, text, cancel_keyboard, 'Markdown')
    else:
        text = f"❌ *Ошибка запуска*\n\n"
        text += f"👤 Аккаунт: `{account_data['username']}`\n"
        text += f"🎮 Игры: {', '.join(map(str, account_data['games']))}\n\n"
        text += "⚠️ Не удалось подключиться к Steam\n"
        text += "Проверьте:\n"
        text += "• Правильность логина и пароля\n"
        text += "• Подключение к интернету\n"
        text += "• Статус серверов Steam"
        keyboard = create_account_keyboard(account_name)
        await safe_edit_message(callback_query, text, keyboard, 'Markdown')

# Обработчики для управления аккаунтами
async def handle_account_stop(account_name, accounts, callback_query: CallbackQuery):
    """Остановить аккаунт"""
    if account_name not in clients:
        account_data = accounts[account_name] if account_name in accounts else None
        
        text = f"⚠️ *Аккаунт не запущен*\n\n"
        if account_data:
            text += f"👤 Аккаунт: `{account_data['username']}`\n"
            text += f"📁 Статус: 🔴 Неактивен\n\n"
        text += "Аккаунт уже остановлен"
        
        keyboard = create_account_keyboard(account_name)
        await safe_edit_message(callback_query, text, keyboard, 'Markdown')
        return
    
    if stop_steam_client(account_name):
        account_data = accounts[account_name]
        
        text = f"⏹️ *Аккаунт остановлен*\n\n"
        text += f"👤 Аккаунт: `{account_data['username']}`\n"
        text += f"📁 Статус: 🔴 Неактивен\n\n"
        text += f"✅ Накрутка часов остановлена"
        
        keyboard = create_account_keyboard(account_name)
        await safe_edit_message(callback_query, text, keyboard, 'Markdown')
    else:
        await safe_edit_message(callback_query, f"❌ Ошибка при остановке аккаунта")

# Обработчик для показа статистики аккаунта
async def handle_account_stats(account_name, accounts, callback_query: CallbackQuery):
    """Показать статистику аккаунта"""
    if account_name not in accounts:
        await safe_edit_message(callback_query, "❌ Аккаунт не найден")
        return
    
    account_data = accounts[account_name]
    is_active = account_name in clients and clients[account_name].logged_on
    
    text = f"📊 *Статистика аккаунта*\n\n"
    text += f"👤 Логин: `{account_data['username']}`\n"
    text += f"📁 Статус: {'🟢 Активен' if is_active else '🔴 Неактивен'}\n"
    text += f"🎮 Количество игр: {len(account_data['games'])}\n"
    text += f"🎯 Игры: {', '.join(map(str, account_data['games']))}\n\n"
    
    if is_active:
        text += "⏰ Накрутка часов активна"
    else:
        text += "💤 Накрутка приостановлена"
    
    text += f"\n🕐 Обновлено: {time.strftime('%H:%M:%S')}"
    
    keyboard = create_account_keyboard(account_name)
    await safe_edit_message(callback_query, text, keyboard, 'Markdown')
