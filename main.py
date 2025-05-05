import os
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


# Загрузка конфигурации
def load_config():
    config = {}
    with open("config.txt", "r") as file:
        for line in file:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                config[key] = value
    return config


config = load_config()

# Состояния для ConversationHandler
CHATTING = 1

# Доступные модели GigaChat
MODELS = {
    "GigaChat": "GigaChat (активная)",
    "GigaChat-Pro": "GigaChat-Pro (не доступен)",
    "GigaChat-Plus": "GigaChat-Plus (не доступен)",
}

# Хранение сессий пользователей
user_sessions = {}


# Инициализация GigaChat
def init_gigachat(user_id):
    credentials = config["GIGACHAT_AUTH_KEY"]
    user_sessions[user_id] = GigaChat(
        credentials=credentials,
        model="GigaChat",  # Всегда используем базовую модель
        verify_ssl_certs=False
    )


# Клавиатура выбора модели
def model_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton(model)] for model in MODELS.values()],
        resize_keyboard=True,
        one_time_keyboard=True
    )


# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    try:
        init_gigachat(user_id)
        await update.message.reply_text(
            "Демонстрационная версия бота с моделью GigaChat.\n"
            "Другие модели недоступны в демонстрационной версии.\n\n"
            "Можешь отправлять свои запросы:",
            reply_markup=model_keyboard()
        )
        return CHATTING
    except Exception as e:
        await update.message.reply_text(
            f"Ошибка при инициализации GigaChat: {str(e)}\nПопробуйте позже."
        )
        return ConversationHandler.END


# Обработчик выбора модели (для недоступных моделей)
async def handle_model_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_model = update.message.text
    if "(не доступен)" in selected_model:
        await update.message.reply_text(
            "Эта модель недоступна в демонстрационной версии. Продолжаем использовать GigaChat.",
            reply_markup=model_keyboard()
        )
    return CHATTING


# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in user_sessions:
        await update.message.reply_text(
            "Сессия не инициализирована. Нажмите /start чтобы начать.",
            reply_markup=None
        )
        return ConversationHandler.END

    try:
        response = user_sessions[user_id].chat(update.message.text)
        await update.message.reply_text(
            response.choices[0].message.content,
            reply_markup=model_keyboard()
        )
        return CHATTING
    except Exception as e:
        await update.message.reply_text(
            f"Ошибка при обработке запроса: {str(e)}\nНажмите /start чтобы перезапустить бота.",
            reply_markup=None
        )
        return ConversationHandler.END


# Обработчик команды /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
    await update.message.reply_text(
        "Сессия сброшена. Нажми /start чтобы начать заново.",
        reply_markup=None
    )
    return ConversationHandler.END


def main():
    application = Application.builder().token(config["TELEGRAM_BOT_TOKEN"]).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHATTING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message),
                MessageHandler(filters.Regex(r"\(не доступен\)$"), handle_model_selection)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    print("Бот запущен...")
    application.run_polling()


if __name__ == '__main__':
    main()