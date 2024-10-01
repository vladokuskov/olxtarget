from helpers.helpers import fetch_data
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, LinkPreviewOptions
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import requests
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

ALLOWED_USERS = [4145105674]

async def check_authorization(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("Sorry, you are not authorized.")
        return True
    return False


def authorized(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if await check_authorization(update, context):
            return
        return await func(update, context)
    return wrapper

# Menu
def create_reply_keyboard():
    keyboard = [
        [KeyboardButton("/search")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# Commands
@authorized
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""

    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("Sorry, you are not authorized to use this command.")
        return

    reply_markup = create_reply_keyboard()

    await update.message.reply_text('Welcome! Please choose an option:', reply_markup=reply_markup)

@authorized
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Please enter the item name you want to search for:')
    context.user_data['waiting_for_item'] = True


# Input
@authorized
async def handle_item_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('waiting_for_item'):
        item_name = update.message.text
        context.user_data['item_name'] = item_name
        context.user_data['waiting_for_item'] = False
        await fetch_olx_data(update, context)
    else:
        await update.message.reply_text("Please use /search to start a new search.")


async def fetch_olx_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch data from OLX API and send it to the user."""
    item_name = context.user_data.get('item_name')
    if not item_name:
        await update.message.reply_text("Please use /search to specify an item name first.")
        return

    url = "https://www.olx.ua/api/v1/offers/"
    params = {
        "offset": 0,
        "limit": 10,
        "query": item_name,
        "currency": "UAH",
        "sort_by": "created_at:desc",
        "filter_refiners": "spell_checker",
        "suggest_filters": "true",
    }

    try:
        data = fetch_data(url, params)
        items = data.get('data', [])

        if not items:
            await update.message.reply_text(f"No items found for '{item_name}'.")
            return

        response = f"Found {len(items)} offers for '{item_name}':\n\n"

        for item in items[:10]:  # Limit to first 10 items to avoid message length issues
            title = item.get('title', 'No title')
            url = item.get('url', 'No URL')
            price_label = ''
            for param in item.get('params', []):
                if param.get('key') == 'price':
                    price_label = param.get('value', {}).get('label', 'Price not available')
                    break
            response += f"• {title}\n{price_label}\n{url}\n\n\n"

        if len(items) > 10:
            response += f"... and {len(items) - 10} more items."

        link_preview_options = LinkPreviewOptions(is_disabled=True)

        await update.message.reply_text(response, link_preview_options=link_preview_options)
    except requests.RequestException:
        await update.message.reply_text("Sorry, I couldn't fetch the data. Please try again later.")



def main() -> None:
    """Set up and run the bot."""
    # Create the Application and pass it your bot's token.
    application = ApplicationBuilder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_item_input))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == '__main__':
    main()