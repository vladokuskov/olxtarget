from helpers.api import fetch_olx_products
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, LinkPreviewOptions
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import requests
import os
from dotenv import load_dotenv
import uuid

from scheduler import scheduler, start_scheduler_thread

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

allowed_users_str = os.getenv('ALLOWED_USERS')
if allowed_users_str:
    ALLOWED_USERS = list(map(int, allowed_users_str.split(',')))
else:
    ALLOWED_USERS = []

TRACKING_LIMIT = 5


async def check_authorization(update: Update):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("Sorry, you are not authorized.")
        return True
    return False


def authorized(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if await check_authorization(update):
            return
        return await func(update, context)
    return wrapper


# Menu
def main_reply_keyboard():
    keyboard = [
        [KeyboardButton("/search")],
        [KeyboardButton("/tracking")]
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
    await update.message.reply_text('Please enter the product name you want to search for:')
    context.user_data['waiting_for_search'] = True


@authorized
async def tracking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tracked_products = context.user_data.get('tracked_products', [])

    # Initialize the keyboard with the "Back" button
    keyboard = [[KeyboardButton("Back")]]

    if not tracked_products:
        keyboard.insert(0, [KeyboardButton("Add product to track")])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text('You have not added any products to track.', reply_markup=reply_markup)
    else:
        response = "You have the following products tracked:\n\n" + "\n".join(product['name'] for product in tracked_products)

        for product in tracked_products:
            keyboard.insert(-1, [KeyboardButton(product["name"])])

        if not len(tracked_products) + 1 > TRACKING_LIMIT:
            keyboard.insert(0, [KeyboardButton("Add product to track")])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        response += "\n\nUse the button below to go back."
        await update.message.reply_text(response, reply_markup=reply_markup)


# Input
@authorized
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Check if the user is in the process of adding an product
    if context.user_data.get('waiting_for_search'):
        product_name = update.message.text
        context.user_data['product_name'] = product_name
        context.user_data['waiting_for_search'] = False
        await search_olx_products(update, context)
    elif context.user_data.get('adding_product'):
        # Add product to track
        user_id = update.effective_user.id
        product_name = update.message.text
        product_id = uuid.uuid4().hex
        tracked_products = context.user_data.setdefault('tracked_products', [])
        if not any(product['name'] == product_name for product in tracked_products):
            tracked_products.append({'id': product_id, 'name': product_name})
            scheduler.schedule_job(product_id, product_name, 10, user_id)
            await update.message.reply_text(f'Product "{product_name}" has been added to your tracked products.')
        else:
            await update.message.reply_text(f'You already have "{product_name}" in your tracked products.')
        await tracking(update, context)
        context.user_data['adding_product'] = False  # Reset adding_product flag
    elif update.message.text == "Add product to track":
        # Set flag to indicate waiting for product name
        context.user_data['adding_product'] = True
        await update.message.reply_text("Type product name:")
    elif any(product['name'] == update.message.text for product in context.user_data.get('tracked_products', [])):
        # Remove the selected product
        product_to_remove = update.message.text
        tracked_products = context.user_data['tracked_products']

        product_to_remove_obj = next(product for product in tracked_products if product['name'] == product_to_remove)
        product_id = product_to_remove_obj['id']

        scheduler.cancel_job(product_id)

        tracked_products = [product for product in tracked_products if product['name'] != product_to_remove]
        context.user_data['tracked_products'] = tracked_products
        await update.message.reply_text(f'product "{product_to_remove}" has been removed from your tracked products.')
        await tracking(update, context)
    elif update.message.text == "Back":
        await update.message.reply_text('Main menu. Choose an option:', reply_markup=main_reply_keyboard())
    else:
        await update.message.reply_text("Please use /search to start a new search.")


async def search_olx_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch data from OLX API and send it to the user."""
    product_name = context.user_data.get('product_name')
    if not product_name:
        await update.message.reply_text("Please use /search to specify an product name first.")
        return

    try:
        products = await fetch_olx_products(product_name)

        if not products:
            await update.message.reply_text(f"No products found for '{product_name}'.")
            return

        response = f"Found {len(products)} offers for '{product_name}':\n\n"

        for product in products[:10]:
            title = product.get('title', 'No title')
            url = product.get('url', 'No URL')
            price_label = ''
            for param in product.get('params', []):
                if param.get('key') == 'price':
                    price_label = param.get('value', {}).get('label', 'Price not available')
                    break
            response += f"• {title}\n{price_label}\n{url}\n\n\n"

        if len(products) > 10:
            response += f"... and {len(products) - 10} more products."

        link_preview_options = LinkPreviewOptions(is_disabled=True)

        await update.message.reply_text(response, link_preview_options=link_preview_options)
    except requests.RequestException:
        await update.message.reply_text("Sorry, I couldn't fetch the data. Please try again later.")


def main() -> None:
    """Set up and run the bot."""
    # Create the Application and pass it your bot's token.
    application = ApplicationBuilder().token(TOKEN).build()
    start_scheduler_thread()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("tracking", tracking))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))

    application.run_polling()


if __name__ == '__main__':
    main()
