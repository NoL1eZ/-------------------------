import unittest
from unittest.mock import patch, MagicMock, mock_open
import logging
from bot import GigaChatBot, setup_logging

class TestGigaChatBot(unittest.TestCase):
    """Тесты для GigaChatBot."""
    
    def setUp(self):
        """Настройка перед каждым тестом."""
        self.logger = setup_logging()
        self.logger.handlers[0].stream = MagicMock()  # Мокаем файловый обработчик
        
    def test_load_config_success(self):
        """Тест успешной загрузки конфигурации."""
        test_config = "TELEGRAM_BOT_TOKEN=test_token\nGIGACHAT_AUTH_KEY=test_key\n"
        
        with patch('builtins.open', mock_open(read_data=test_config)):
            bot = GigaChatBot()
            self.assertEqual(bot.config["TELEGRAM_BOT_TOKEN"], "test_token")
            self.assertEqual(bot.config["GIGACHAT_AUTH_KEY"], "test_key")
            
        # Проверяем запись в лог
        self.assertIn("Конфигурация успешно загружена", 
                     self.logger.handlers[0].stream.write.call_args[0][0])

    def test_load_config_missing_file(self):
        """Тест отсутствия файла конфигурации."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            with self.assertRaises(FileNotFoundError):
                GigaChatBot()
                
        # Проверяем запись ошибки в лог
        self.assertIn("Файл конфигурации не найден", 
                     self.logger.handlers[0].stream.write.call_args[0][0])

    @patch('gigachat.GigaChat')
    def test_init_gigachat_success(self, mock_giga):
        """Тест успешной инициализации GigaChat."""
        bot = GigaChatBot()
        bot.config = {"GIGACHAT_AUTH_KEY": "test_key"}
        bot._init_gigachat(123)
        self.assertIn(123, bot.user_sessions)
        
        # Проверяем запись в лог
        self.assertIn("Инициализирована сессия GigaChat для пользователя 123", 
                     self.logger.handlers[0].stream.write.call_args[0][0])

    @patch('gigachat.GigaChat', side_effect=GigaChatException("Auth failed"))
    def test_init_gigachat_failure(self, mock_giga):
        """Тест ошибки инициализации GigaChat."""
        bot = GigaChatBot()
        bot.config = {"GIGACHAT_AUTH_KEY": "test_key"}
        
        with self.assertRaises(GigaChatException):
            bot._init_gigachat(123)
            
        # Проверяем запись ошибки в лог
        self.assertIn("Ошибка инициализации GigaChat", 
                     self.logger.handlers[0].stream.write.call_args[0][0])

class TestLoggingSetup(unittest.TestCase):
    """Тесты настройки логирования."""
    
    def test_logging_setup(self):
        """Тест корректности настройки логирования."""
        logger = setup_logging()
        
        # Проверяем количество обработчиков
        self.assertEqual(len(logger.handlers), 2)
        
        # Проверяем уровни логирования
        self.assertEqual(logger.level, logging.INFO)
        self.assertEqual(logger.handlers[0].level, logging.INFO)  # Файловый
        self.assertEqual(logger.handlers[1].level, logging.WARNING)  # Консольный

if __name__ == '__main__':
    unittest.main()