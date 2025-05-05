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
SELECTING_MODEL, CHATTING = range(2)

# Доступные модели GigaChat
MODELS = {
    "GigaChat": "GigaChat",
    "GigaChat-Pro": "GigaChat-Pro",
    "GigaChat-Plus": "GigaChat-Plus",
}

# Хранение сессий пользователей
user_sessions = {}


# Инициализация GigaChat
def init_gigachat(model_name, user_id):
    credentials = config["GIGACHAT_AUTH_KEY"]
    user_sessions[user_id] = GigaChat(
        credentials=credentials,
        model=model_name,
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
    await update.message.reply_text(
        "Привет! Я бот с интеграцией GigaChat. Выбери модель:",
        reply_markup=model_keyboard()
    )
    return SELECTING_MODEL


# Обработчик выбора модели
async def select_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    model_name = update.message.text

    if model_name not in MODELS.values():
        await update.message.reply_text(
            "Пожалуйста, выбери модель из предложенных вариантов:",
            reply_markup=model_keyboard()
        )
        return SELECTING_MODEL

    try:
        init_gigachat(model_name, user_id)
        await update.message.reply_text(
            f"Модель {model_name} выбрана. Теперь ты можешь отправлять текстовые запросы.",
            reply_markup=None  # Убираем клавиатуру
        )
        return CHATTING
    except Exception as e:
        await update.message.reply_text(
            f"Ошибка при инициализации GigaChat: {str(e)}"
        )
        return SELECTING_MODEL


# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    if user_id not in user_sessions:
        await update.message.reply_text(
            "Сначала выбери модель GigaChat из меню.",
            reply_markup=model_keyboard()
        )
        return SELECTING_MODEL

    try:
        response = user_sessions[user_id].chat(update.message.text)
        await update.message.reply_text(response.choices[0].message.content)
        return CHATTING
    except Exception as e:
        await update.message.reply_text(
            f"Ошибка при обработке запроса: {str(e)}\nПопробуй выбрать модель снова.",
            reply_markup=model_keyboard()
        )
        return SELECTING_MODEL


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
            SELECTING_MODEL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_model)
            ],
            CHATTING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    print("Бот запущен...")
    application.run_polling()


if __name__ == '__main__':
    main()