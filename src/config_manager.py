import configparser
import logging

logger = logging.getLogger(__name__)

# ConfigManager для управления конфигурацией
# Читает данные из config.ini и предоставляет методы для доступа к ним
class ConfigManager:
    def __init__(self, config_file='config/config.ini'):
        self.config = configparser.ConfigParser()
        self.config.read(config_file, encoding='utf-8')
    
    def get_bot_token(self):
        """Получить токен бота"""
        return self.config['telegram']['bot_token']
    
    def get_allowed_user_id(self):
        """Получить ID разрешенного пользователя"""
        return int(self.config['telegram']['allowed_user_id'])
    
    def get_accounts_from_config(self):
        """Получить информацию об аккаунтах из config.ini"""
        accounts = {}
        for i in range(1, 4):  # account1, account2, account3
            section = f'account{i}'
            if section in self.config:
                accounts[section] = {
                    'username': self.config[section]['username'],
                    'password': self.config[section]['password'],
                    'games': [int(game.strip()) for game in self.config[section]['games'].split(',') if game.strip()]
                }
        return accounts
