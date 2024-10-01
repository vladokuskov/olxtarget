from helpers.helpers import fetch_data
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, LinkPreviewOptions
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import requests
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

ALLOWED_USERS = [414510674]
NOTIFICATIONS_LIMIT = 5

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
def main_reply_keyboard():
    keyboard = [
        [KeyboardButton("/search")],
        [KeyboardButton("/notifications")]
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

    reply_markup = main_reply_keyboard()

    await update.message.reply_text('Welcome! Please choose an option:', reply_markup=reply_markup)


@authorized
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Please enter the item name you want to search for:')
    context.user_data['waiting_for_search'] = True


@authorized
async def notifications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tracked_items = context.user_data.get('tracked_items', [])

    # Initialize the keyboard with the "Back" button
    keyboard = [[KeyboardButton("Back")]]

    if not tracked_items:
        # No items added, show "Add item to track" button
        keyboard.insert(0, [KeyboardButton("Add item to track")])  # Insert at the top
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text('You have not added any items to track.', reply_markup=reply_markup)
    else:
        response = "You have the following items tracked:\n\n" + "\n".join(tracked_items)

        # Add buttons for item removal
        for item in tracked_items:
            keyboard.insert(-1, [KeyboardButton(item)])  # Add item buttons before "Back"

        if not len(tracked_items) + 1 > NOTIFICATIONS_LIMIT:
            keyboard.insert(0, [KeyboardButton("Add item to track")])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        response += "\n\nUse the button below to go back."
        await update.message.reply_text(response, reply_markup=reply_markup)


# Input
@authorized
async def handle_item_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Check if the user is in the process of adding an item
    if context.user_data.get('waiting_for_search'):
        item_name = update.message.text
        context.user_data['item_name'] = item_name
        context.user_data['waiting_for_search'] = False
        await fetch_olx_data(update, context)
    elif context.user_data.get('adding_item'):
        # Add item to track
        item_name = update.message.text
        tracked_items = context.user_data.setdefault('tracked_items', [])
        if item_name not in tracked_items:
            tracked_items.append(item_name)
            await update.message.reply_text(f'Item "{item_name}" has been added to your tracked items.')
        else:
            await update.message.reply_text(f'You already have "{item_name}" in your tracked items.')
        await notifications(update, context)
        context.user_data['adding_item'] = False  # Reset adding_item flag
    elif update.message.text == "Add item to track":
        # Set flag to indicate waiting for item name
        context.user_data['adding_item'] = True
        await update.message.reply_text("Type item name:")
    elif update.message.text in context.user_data.get('tracked_items', []):
        # Remove the selected item
        item_to_remove = update.message.text
        tracked_items = context.user_data['tracked_items']
        tracked_items.remove(item_to_remove)
        await update.message.reply_text(f'Item "{item_to_remove}" has been removed from your tracked items.')
        await notifications(update, context)
    elif update.message.text == "Back":
        await update.message.reply_text('Main menu. Choose an option:', reply_markup=main_reply_keyboard())
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
    application.add_handler(CommandHandler("notifications", notifications))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_item_input))

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == '__main__':
    main()