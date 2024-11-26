from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
import os

load_dotenv()

ALLOWED_USERS = list(map(int, os.getenv('ALLOWED_USERS', '').split(',')))


async def check_authorization(update: Update):
    """Check if a user is authorized."""
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("Sorry, you are not authorized.")
        return True
    return False


def main_reply_keyboard():
    """Return the main reply keyboard."""
    keyboard = [
        [KeyboardButton("/search")],
        [KeyboardButton("/tracking")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
