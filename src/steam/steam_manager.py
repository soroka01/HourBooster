import asyncio
import logging
import threading
from steam.client import SteamClient, EResult

logger = logging.getLogger(__name__)

# Словарь для хранения клиентов и их состояний
clients = {}
client_threads = {}
pending_logins = {}  # Для хранения данных незавершенных входов

# Функция для запуска Steam клиента в отдельном потоке
def run_steam_client(account_name, account_data, user_id=None, two_factor_code=None, auth_code=None):
    """Запустить Steam клиент для аккаунта в отдельном потоке"""
    try:
        client = SteamClient()
        clients[account_name] = client
        
        logger.info(f"Попытка входа для аккаунта {account_name}")
        
        # Пробуем войти с дополнительными кодами если они есть
        if two_factor_code:
            result = client.login(
                username=account_data['username'], 
                password=account_data['password'],
                two_factor_code=two_factor_code
            )
        elif auth_code:
            result = client.login(
                username=account_data['username'], 
                password=account_data['password'],
                auth_code=auth_code
            )
        else:
            result = client.login(
                username=account_data['username'], 
                password=account_data['password']
            )
        
        logger.info(f"Результат входа для аккаунта {account_name}: {result} (код: {result.value})")
        
        if result == EResult.OK:
            logger.info(f"Успешный вход для аккаунта {account_name}")
            client.games_played(account_data['games'])
            # Очищаем данные ожидающего входа
            if user_id and user_id in pending_logins:
                del pending_logins[user_id]
            client.run_forever()
        elif result.value == 85:  # EResult.AccountLogonDenied - требуется Steam Guard
            logger.info(f"Требуется Steam Guard код для аккаунта {account_name}")
            if user_id:
                pending_logins[user_id] = {
                    'account_name': account_name,
                    'account_data': account_data,
                    'client': client,
                    'guard_type': 'mobile'
                }
                # Не удаляем клиент в этом случае
                return
        elif result.value == 63:  # EResult.InvalidLoginAuthCode - требуется код с email
            logger.info(f"Требуется Email код для аккаунта {account_name}")
            if user_id:
                pending_logins[user_id] = {
                    'account_name': account_name,
                    'account_data': account_data,
                    'client': client,
                    'guard_type': 'email'
                }
                # Не удаляем клиент в этом случае
                return
        else:
            logger.error(f"Ошибка входа для аккаунта {account_name}: {result} (код: {result.value})")
            
    except Exception as e:
        logger.error(f"Ошибка в потоке для аккаунта {account_name}: {e}")
    finally:
        # Удаляем клиент только если вход был неудачным
        # НЕ удаляем если ждем Steam Guard код
        if user_id and user_id in pending_logins:
            # Ждем ввод кода, клиент не удаляем
            return
            
        # Удаляем клиент в остальных случаях
        if account_name in clients and (not hasattr(clients[account_name], 'logged_on') or not clients[account_name].logged_on):
            if account_name in clients:
                del clients[account_name]
        if account_name in client_threads:
            del client_threads[account_name]

# Функция для остановки Steam клиента
def stop_steam_client(account_name):
    """Остановить Steam клиент"""
    if account_name not in clients:
        return False
    
    try:
        client = clients[account_name]
        client.logout()
        
        if account_name in client_threads:
            # Ждем завершения потока
            client_threads[account_name].join(timeout=5)
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при остановке клиента {account_name}: {e}")
        return False
