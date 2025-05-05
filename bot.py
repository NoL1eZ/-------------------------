"""
Telegram бот с интеграцией GigaChat API для обработки юридических запросов.

Основные функции:
- Инициализация сессии с GigaChat
- Обработка текстовых запросов пользователя
- Управление сессиями
- Обратная связь о статусе недоступных функций
"""
"""
Логирование настроено на запись в файл bot.log
"""


import logging
from typing import Dict, Any
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from gigachat import GigaChat
from gigachat.exceptions import GigaChatException

# Настройка логирования
def setup_logging():
    """Настраивает логирование в файл и консоль"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Обработчик для файла
    file_handler = logging.FileHandler('bot.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # Обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.WARNING)

    # Добавляем обработчики
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

logger = setup_logging()

# Константы
CHATTING = 1
CONFIG_FILE = "config.txt"
MODELS = {
    "GigaChat": "GigaChat (активная)",
    "GigaChat-Pro": "GigaChat-Pro (не доступен)",
    "GigaChat-Plus": "GigaChat-Plus (не доступен)",
}

class GigaChatBot:
    """Основной класс бота, инкапсулирующий логику работы."""
    
    def __init__(self):
        self.config = self._load_config()
        self.user_sessions: Dict[int, GigaChat] = {}
        logger.info("Бот инициализирован")

    def _load_config(self) -> Dict[str, str]:
        """Загружает конфигурацию из файла."""
        config = {}
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as file:
                for line in file:
                    if "=" in line:
                        key, value = line.strip().split("=", 1)
                        config[key] = value
            
            if not all(k in config for k in ["TELEGRAM_BOT_TOKEN", "GIGACHAT_AUTH_KEY"]):
                raise ValueError("Не хватает обязательных параметров в конфигурации")
            
            logger.info("Конфигурация успешно загружена")
            return config
            
        except FileNotFoundError as e:
            logger.error("Файл конфигурации не найден: %s", e)
            raise
        except Exception as e:
            logger.error("Ошибка загрузки конфигурации: %s", e)
            raise ValueError("Ошибка загрузки конфигурации") from e

    def _init_gigachat(self, user_id: int) -> None:
        """Инициализирует сессию GigaChat для пользователя."""
        try:
            self.user_sessions[user_id] = GigaChat(
                credentials=self.config["GIGACHAT_AUTH_KEY"],
                model="GigaChat",
                verify_ssl_certs=False
            )
            logger.info("Инициализирована сессия GigaChat для пользователя %s", user_id)
        except GigaChatException as e:
            logger.error("Ошибка инициализации GigaChat: %s", e)
            raise

    @staticmethod
    def _model_keyboard() -> ReplyKeyboardMarkup:
        """Создает клавиатуру с доступными моделями."""
        return ReplyKeyboardMarkup(
            [[KeyboardButton(model)] for model in MODELS.values()],
            resize_keyboard=True,
            one_time_keyboard=False
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработчик команды /start."""
        user_id = update.message.from_user.id
        try:
            self._init_gigachat(user_id)
            await update.message.reply_text(
                "Демонстрационная версия бота с моделью GigaChat.\n"
                "Другие модели недоступны в демонстрационной версии.\n\n"
                "Можете отправлять свои запросы:",
                reply_markup=self._model_keyboard()
            )
            logger.info("Пользователь %s начал сессию", user_id)
            return CHATTING
        except Exception as e:
            await update.message.reply_text(
                f"Ошибка при инициализации: {str(e)}\nПопробуйте позже."
            )
            logger.exception("Ошибка в обработчике start для пользователя %s", user_id)
            return ConversationHandler.END

    async def handle_model_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обрабатывает выбор недоступных моделей."""
        selected_model = update.message.text
        if "(не доступен)" in selected_model:
            await update.message.reply_text(
                "Эта модель недоступна в демонстрационной версии. Продолжаем использовать GigaChat.",
                reply_markup=self._model_keyboard()
            )
            logger.info("Пользователь %s попытался выбрать недоступную модель %s", 
                      update.message.from_user.id, selected_model)
        return CHATTING

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обрабатывает текстовые сообщения пользователя."""
        user_id = update.message.from_user.id

        if user_id not in self.user_sessions:
            await update.message.reply_text(
                "Сессия не инициализирована. Нажмите /start чтобы начать.",
                reply_markup=None
            )
            return ConversationHandler.END

        try:
            logger.debug("Обработка запроса от %s: %s", user_id, update.message.text)
            response = self.user_sessions[user_id].chat(update.message.text)
            await update.message.reply_text(
                response.choices[0].message.content,
                reply_markup=self._model_keyboard()
            )
            logger.info("Успешно обработан запрос от пользователя %s", user_id)
            return CHATTING
        except GigaChatException as e:
            await update.message.reply_text(
                f"Ошибка GigaChat: {str(e)}\nНажмите /start чтобы перезапустить бота.",
                reply_markup=None
            )
            logger.error("Ошибка GigaChat для пользователя %s: %s", user_id, e)
            return ConversationHandler.END
        except Exception as e:
            await update.message.reply_text(
                "Произошла внутренняя ошибка. Пожалуйста, попробуйте позже.",
                reply_markup=None
            )
            logger.exception("Неожиданная ошибка при обработке сообщения от %s", user_id)
            return ConversationHandler.END

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработчик команды /cancel."""
        user_id = update.message.from_user.id
        if user_id in self.user_sessions:
            del self.user_sessions[user_id]
            logger.info("Сессия пользователя %s завершена", user_id)
        await update.message.reply_text(
            "Сессия сброшена. Нажмите /start чтобы начать заново.",
            reply_markup=None
        )
        return ConversationHandler.END

    def run(self) -> None:
        """Запускает бота."""
        try:
            application = Application.builder().token(self.config["TELEGRAM_BOT_TOKEN"]).build()

            conv_handler = ConversationHandler(
                entry_points=[CommandHandler('start', self.start)],
                states={
                    CHATTING: [
                        MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message),
                        MessageHandler(filters.Regex(r"\(не доступен\)$"), self.handle_model_selection)
                    ],
                },
                fallbacks=[CommandHandler('cancel', self.cancel)],
            )

            application.add_handler(conv_handler)
            
            logger.info("Бот запускается...")
            application.run_polling()
            logger.info("Бот успешно запущен")
        except Exception as e:
            logger.critical("Критическая ошибка при запуске бота: %s", e)
            raise

if __name__ == '__main__':
    try:
        bot = GigaChatBot()
        bot.run()
    except Exception as e:
        logger.critical("Не удалось запустить бота: %s", e)
        raise