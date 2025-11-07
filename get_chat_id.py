"""
Скрипт для получения Chat ID групп Telegram
Используйте этот скрипт чтобы узнать ID ваших групповых чатов
"""
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

load_dotenv()

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получает и выводит Chat ID любого чата"""
    chat = update.effective_chat
    user = update.effective_user

    info = (
        f"📊 ИНФОРМАЦИЯ О ЧАТЕ\n\n"
        f"Chat ID: {chat.id}\n"
        f"Тип чата: {chat.type}\n"
        f"Название: {chat.title if chat.title else 'Личный чат'}\n"
    )

    if chat.type in ['group', 'supergroup']:
        info += f"\n✅ Это групповой чат!\n"
        info += f"Используйте этот ID в config.py:\n"
        info += f"`{chat.id}`\n\n"
        info += f"Отправил: @{user.username if user.username else user.first_name} ({user.id})"
    else:
        info += f"\n⚠️ Это не групповой чат.\n"
        info += f"Добавьте бота в группу и отправьте любое сообщение там."

    await update.message.reply_text(info)

    # Выводим в консоль для удобства
    print(f"\n{'='*50}")
    print(f"Chat ID: {chat.id}")
    print(f"Тип: {chat.type}")
    print(f"Название: {chat.title if chat.title else 'Личный чат'}")
    print(f"{'='*50}\n")

def main():
    """Запуск бота для получения Chat ID"""
    token = os.getenv('BOT_TOKEN')

    if not token:
        print("❌ Ошибка: BOT_TOKEN не найден в .env файле")
        return

    print("🤖 Бот для получения Chat ID запущен!")
    print("\nКак использовать:")
    print("1. Добавьте бота в вашу группу")
    print("2. Отправьте любое сообщение в группу")
    print("3. Бот покажет Chat ID группы")
    print("\nДля остановки нажмите Ctrl+C\n")

    application = Application.builder().token(token).build()
    application.add_handler(MessageHandler(filters.ALL, get_chat_id))
    application.run_polling()

if __name__ == '__main__':
    main()

