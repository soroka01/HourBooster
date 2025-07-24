import asyncio
import logging
import threading
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

# Импорты наших модулей
from src.config_manager import ConfigManager
from src.bot.states import SteamGuardStates
from src.steam.steam_manager import clients, client_threads, pending_logins, run_steam_client
from src.bot.ui_manager import create_main_keyboard, get_main_menu_text, create_account_keyboard, create_cancel_keyboard
from src.bot.handlers import safe_edit_message, handle_account_start, handle_account_stop, handle_account_stats
from src.bot.access_middleware import AccessMiddleware

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализируем менеджер конфигурации
config_manager = ConfigManager()

# Создаем экземпляры бота и диспетчера
bot = Bot(token=config_manager.get_bot_token())
dp = Dispatcher()

# Подключаем middleware для проверки доступа
dp.message.middleware(AccessMiddleware(config_manager))
dp.callback_query.middleware(AccessMiddleware(config_manager))

# Регистрация хэндлеров
# Команда /start для отображения главного меню
@dp.message(Command("start"))
async def start_command(message: Message):
    """Главное меню бота"""
    accounts = config_manager.get_accounts_from_config()
    text = get_main_menu_text(accounts)
    
    if not accounts:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]])
    else:
        keyboard = create_main_keyboard(accounts)
    
    await message.answer(text, reply_markup=keyboard, parse_mode='Markdown')

# Команда /help для отображения информации о боте
@dp.message(Command("help"))
async def help_command(message: Message):
    """Показать помощь"""
    text = "📖 *Помощь*\n\n"
    text += "🎯 *Как использовать:*\n"
    text += "1. Выберите аккаунт из списка\n"
    text += "2. Нажмите 'Запустить' для начала накрутки часов\n"
    text += "3. При необходимости введите Steam Guard код\n"
    text += "4. Используйте 'Остановить' для завершения\n\n"
    text += "⚙️ *Настройка:*\n"
    text += "Аккаунты настраиваются в файле `config.ini`\n\n"
    text += "📊 *Функции:*\n"
    text += "• Управление тремя аккаунтами\n"
    text += "• Автоматическая Steam Guard поддержка\n"
    text += "• Статистика работы\n"
    text += "• Удобное управление кнопками\n\n"
    text += "🔧 *Команды:*\n"
    text += "/start - Главное меню\n"
    text += "/help - Помощь\n"
    text += "/cancel - Отменить ввод кода"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]])
    
    await message.answer(text, reply_markup=keyboard, parse_mode='Markdown')

# Команда /cancel для отмены текущей операции
@dp.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    """Отменить текущую операцию"""
    current_state = await state.get_state()
    user_id = message.from_user.id
    
    if current_state in [SteamGuardStates.waiting_for_guard_code, SteamGuardStates.waiting_for_email_code]:
        # Очищаем данные входа
        if user_id in pending_logins:
            del pending_logins[user_id]
        
        await state.clear()
        await message.answer("❌ Ввод кода отменен. Используйте /start для возврата в меню.")
    else:
        await message.answer("ℹ️ Нет активных операций для отмены. Используйте /start для начала работы.")

# Обработчик callback запросов (нажатий на кнопки)
@dp.callback_query()
async def handle_callback_query(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    data = callback_query.data
    accounts = config_manager.get_accounts_from_config()
    
    # Обработка отмены ввода кода
    if data == "cancel_code":
        user_id = callback_query.from_user.id
        if user_id in pending_logins:
            del pending_logins[user_id]
        
        await state.clear()
        
        text = get_main_menu_text(accounts)
        if not accounts:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]])
        else:
            keyboard = create_main_keyboard(accounts)
        
        await safe_edit_message(callback_query, text, keyboard, 'Markdown')
        return
    
    # Сбрасываем состояние при любом callback (кроме самого процесса входа)
    if not data.startswith("start_"):
        await state.clear()
    
    if data == "refresh" or data == "back":
        text = get_main_menu_text(accounts)
        
        if not accounts:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]])
        else:
            keyboard = create_main_keyboard(accounts)
        
        await safe_edit_message(callback_query, text, keyboard, 'Markdown')
        
    elif data == "help":
        text = "📖 *Помощь*\n\n"
        text += "🎯 *Как использовать:*\n"
        text += "1. Выберите аккаунт из списка\n"
        text += "2. Нажмите 'Запустить' для начала накрутки часов\n"
        text += "3. При необходимости введите Steam Guard код\n"
        text += "4. Используйте 'Остановить' для завершения\n\n"
        text += "⚙️ *Настройка:*\n"
        text += "Аккаунты настраиваются в файле `config.ini`\n\n"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]])
        await safe_edit_message(callback_query, text, keyboard, 'Markdown')
        
    elif data.startswith("account_"):
        account_name = data.replace("account_", "")
        
        if account_name not in accounts:
            await safe_edit_message(callback_query, "❌ Аккаунт не найден")
            return
        
        account_data = accounts[account_name]
        is_active = account_name in clients and clients[account_name].logged_on
        
        text = f"⚙️ *Управление аккаунтом*\n\n"
        text += f"👤 Логин: `{account_data['username']}`\n"
        text += f"📁 Статус: {'🟢 Активен' if is_active else '🔴 Неактивен'}\n"
        text += f"🎮 Игры: {', '.join(map(str, account_data['games']))}\n\n"
        text += "Выберите действие:"
        
        keyboard = create_account_keyboard(account_name)
        await safe_edit_message(callback_query, text, keyboard, 'Markdown')
        
    elif data.startswith("start_"):
        account_name = data.replace("start_", "")
        await handle_account_start(account_name, accounts, callback_query, state)
        
    elif data.startswith("stop_"):
        account_name = data.replace("stop_", "")
        await handle_account_stop(account_name, accounts, callback_query)
        
    elif data.startswith("stats_"):
        account_name = data.replace("stats_", "")
        await handle_account_stats(account_name, accounts, callback_query)

# Обработчик для ввода Steam Guard кода
@dp.message(SteamGuardStates.waiting_for_guard_code)
async def process_guard_code(message: Message, state: FSMContext):
    """Обработка Steam Guard кода"""
    user_id = message.from_user.id
    guard_code = message.text.strip()
    
    if user_id not in pending_logins:
        await message.answer("❌ Сессия истекла. Попробуйте запустить аккаунт заново.")
        await state.clear()
        return
    
    login_data = pending_logins[user_id]
    account_name = login_data['account_name']
    account_data = login_data['account_data']
    original_message = login_data.get('original_message')
    
    # Обновляем исходное сообщение
    if original_message:
        text = f"🔐 *Требуется Steam Guard*\n\n"
        text += f"👤 Аккаунт: `{account_data['username']}`\n\n"
        text += "⏳ Проверяем Steam Guard код..."
        cancel_keyboard = create_cancel_keyboard()
        await safe_edit_message(original_message, text, cancel_keyboard, 'Markdown')
    
    # Запускаем вход с кодом
    thread = threading.Thread(
        target=run_steam_client, 
        args=(account_name, account_data, user_id, guard_code, None)
    )
    thread.daemon = True
    thread.start()
    client_threads[account_name] = thread
    
    await asyncio.sleep(3)
    
    if account_name in clients and clients[account_name].logged_on:
        # Успешный вход - обновляем исходное сообщение
        if original_message:
            text = f"✅ *Успешный вход!*\n\n"
            text += f"👤 Аккаунт: `{account_data['username']}`\n"
            text += f"🎮 Игры: {', '.join(map(str, account_data['games']))}\n\n"
            text += "🚀 Аккаунт запущен!\n⏰ Накрутка часов активна"
            
            keyboard = create_account_keyboard(account_name)
            await safe_edit_message(original_message, text, keyboard, 'Markdown')
        
        # Удаляем сообщение пользователя с кодом
        try:
            await message.delete()
        except Exception:
            pass  # Игнорируем ошибки удаления
        
        await state.clear()
    else:
        # Неверный код - обновляем исходное сообщение
        if original_message:
            text = f"🔐 *Требуется Steam Guard*\n\n"
            text += f"👤 Аккаунт: `{account_data['username']}`\n\n"
            text += "📱 Введите код из мобильного приложения Steam Guard:\n\n"
            text += "💡 Код состоит из 5 символов (например: ABC12)\n"
            text += "❌ Неверный код. Попробуйте еще раз"
            cancel_keyboard = create_cancel_keyboard()
            await safe_edit_message(original_message, text, cancel_keyboard, 'Markdown')
        
        # Удаляем неверное сообщение пользователя
        try:
            await message.delete()
        except Exception:
            pass

# Обработчик для ввода Email кода
@dp.message(SteamGuardStates.waiting_for_email_code)
async def process_email_code(message: Message, state: FSMContext):
    """Обработка Email кода"""
    user_id = message.from_user.id
    email_code = message.text.strip()
    
    if user_id not in pending_logins:
        await message.answer("❌ Сессия истекла. Попробуйте запустить аккаунт заново.")
        await state.clear()
        return
    
    login_data = pending_logins[user_id]
    account_name = login_data['account_name']
    account_data = login_data['account_data']
    original_message = login_data.get('original_message')
    
    # Обновляем исходное сообщение
    if original_message:
        text = f"📧 *Требуется код с Email*\n\n"
        text += f"👤 Аккаунт: `{account_data['username']}`\n\n"
        text += "⏳ Проверяем Email код..."
        cancel_keyboard = create_cancel_keyboard()
        await safe_edit_message(original_message, text, cancel_keyboard, 'Markdown')
    
    # Запускаем вход с кодом
    thread = threading.Thread(
        target=run_steam_client, 
        args=(account_name, account_data, user_id, None, email_code)
    )
    thread.daemon = True
    thread.start()
    client_threads[account_name] = thread
    
    await asyncio.sleep(3)
    
    if account_name in clients and clients[account_name].logged_on:
        # Успешный вход - обновляем исходное сообщение
        if original_message:
            text = f"✅ *Успешный вход!*\n\n"
            text += f"👤 Аккаунт: `{account_data['username']}`\n"
            text += f"🎮 Игры: {', '.join(map(str, account_data['games']))}\n\n"
            text += "🚀 Аккаунт запущен!\n⏰ Накрутка часов активна"
            
            keyboard = create_account_keyboard(account_name)
            await safe_edit_message(original_message, text, keyboard, 'Markdown')
        
        # Удаляем сообщение пользователя с кодом
        try:
            await message.delete()
        except Exception:
            pass  # Игнорируем ошибки удаления
        
        await state.clear()
    else:
        # Неверный код - обновляем исходное сообщение
        if original_message:
            text = f"📧 *Требуется код с Email*\n\n"
            text += f"👤 Аккаунт: `{account_data['username']}`\n\n"
            text += "📧 Введите код, отправленный на ваш email:\n\n"
            text += "💡 Код состоит из 5 символов\n"
            text += "❌ Неверный код. Попробуйте еще раз"
            cancel_keyboard = create_cancel_keyboard()
            await safe_edit_message(original_message, text, cancel_keyboard, 'Markdown')
        
        # Удаляем неверное сообщение пользователя
        try:
            await message.delete()
        except Exception:
            pass

# Обработчик неизвестных команд
@dp.message()
async def unknown_command(message: Message, state: FSMContext):
    """Обработчик неизвестных команд"""
    # Проверяем, не ожидается ли ввод кода
    current_state = await state.get_state()
    if current_state in [SteamGuardStates.waiting_for_guard_code, SteamGuardStates.waiting_for_email_code]:
        # Пользователь ввел что-то не то во время ожидания кода
        user_id = message.from_user.id
        
        # Удаляем неправильное сообщение
        try:
            await message.delete()
        except Exception:
            pass
        
        # Обновляем исходное сообщение с подсказкой
        if user_id in pending_logins:
            login_data = pending_logins[user_id]
            original_message = login_data.get('original_message')
            account_data = login_data['account_data']
            
            if original_message:
                if current_state == SteamGuardStates.waiting_for_guard_code:
                    text = f"🔐 *Требуется Steam Guard*\n\n"
                    text += f"👤 Аккаунт: `{account_data['username']}`\n\n"
                    text += "📱 Введите код из мобильного приложения Steam Guard:\n\n"
                    text += "😊 Код состоит из 5 символов (например: ABC12)\n"
                    text += "⚠️ Пожалуйста, введите только код Steam Guard"
                else:
                    text = f"📧 *Требуется код с Email*\n\n"
                    text += f"👤 Аккаунт: `{account_data['username']}`\n\n"
                    text += "📧 Введите код, отправленный на ваш email:\n\n"
                    text += "💡 Код состоит из 5 символов\n"
                    text += "⚠️ Пожалуйста, введите только код с Email"
                
                cancel_keyboard = create_cancel_keyboard()
                await safe_edit_message(original_message, text, cancel_keyboard, 'Markdown')
        return
    
    text = "❓ Неизвестная команда. Используйте /start для начала работы."
    await message.answer(text)

# Обработчик для получения статистики аккаунта
async def main():
    """Главная функция для запуска бота"""
    logger.info("🤖 Бот запущен!")
    await dp.start_polling(bot)

# Запуск бота
if __name__ == "__main__":
    asyncio.run(main())
