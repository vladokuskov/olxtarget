from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from bot import start, search, tracking, handle_user_input
from scheduler import start_scheduler_thread
from dotenv import load_dotenv
import os

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')


def main() -> None:
    application = ApplicationBuilder().token(TOKEN).build()
    start_scheduler_thread()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("tracking", tracking))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))

    application.run_polling()


if __name__ == "__main__":
    main()
