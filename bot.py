from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from db import db
from helpers.api import fetch_olx_products
from scheduler import scheduler
from utils import check_authorization, main_reply_keyboard


# Command to start the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await check_authorization(update):
        return
    reply_markup = main_reply_keyboard()
    await update.message.reply_text('Welcome! Please choose an option:', reply_markup=reply_markup)


# Command to search for products
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Please enter the product name you want to search for:')
    context.user_data['waiting_for_search'] = True


# Command to manage product tracking
async def tracking(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    tracked_products = db.get_tracked_products(user_id)

    keyboard = [["Back"]]
    if not tracked_products:
        keyboard.insert(0, ["Add product to track"])
        response = "You have no tracked products."
    else:
        response = "You have the following products tracked:\n\n" + "\n".join(product for product in tracked_products)
        for product in tracked_products:
            keyboard.insert(-1, [product])
        if len(tracked_products) + 1 <= 5:
            keyboard.insert(0, ["Add product to track"])

    await update.message.reply_text(response, reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))


# Handle user inputs
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id

    if context.user_data.get('waiting_for_search'):
        await handle_search_input(update, context)
    elif context.user_data.get('adding_product'):
        await handle_add_product(update, context)
    elif update.message.text == "Add product to track":
        await prompt_product_name(update, context)
    elif any(product == update.message.text for product in db.get_tracked_products(user_id)):
        await handle_remove_product(update, context)
    elif update.message.text == "Back":
        await back_to_main_menu(update)
    else:
        await update.message.reply_text("Please use /search to start a new search.")


async def handle_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    product_name = update.message.text
    context.user_data['product_name'] = product_name
    context.user_data['waiting_for_search'] = False
    await search_olx_products(update, context)


async def handle_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    product_name = update.message.text
    user_id = update.effective_user.id
    tracked_products = db.get_tracked_products(user_id)

    if not any(product == product_name for product in tracked_products):
        db.add_product(product_name, user_id)
        scheduler.schedule_job_for_user(user_id)
        # scheduler.schedule_job(product_name, 10, update.effective_user.id)
        await update.message.reply_text(f'Product "{product_name}" has been added to your tracked products.')
    else:
        await update.message.reply_text(f'You already have "{product_name}" in your tracked products.')

    await tracking(update, context)
    context.user_data['adding_product'] = False  # Reset flag


async def prompt_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data['adding_product'] = True
    await update.message.reply_text("Type product name:")


async def handle_remove_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    product_to_remove = update.message.text
    user_id = update.effective_user.id
    job_id = f"{user_id}_{product_to_remove}"

    db.remove_product(product_to_remove, user_id)
    scheduler.cancel_job(job_id)
    await update.message.reply_text(f'Product "{product_to_remove}" has been removed from your tracked products.')
    await tracking(update, context)


async def back_to_main_menu(update: Update) -> None:
    await update.message.reply_text('Main menu. Choose an option:', reply_markup=main_reply_keyboard())


async def search_olx_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch data from OLX API and send it to the user."""
    product_name = context.user_data.get('product_name')
    if not product_name:
        await update.message.reply_text("Please use /search to specify a product name first.")
        return

    products = await fetch_olx_products(product_name)

    if not products:
        await update.message.reply_text(f"No products found for '{product_name}'.")
        return

    response = f"Found {len(products)} offers for '{product_name}':\n\n"

    for product in products[:10]:
        title = product.get('title', 'No title')
        url = product.get('url', 'No URL')
        response += f"• {title}\n{url}\n\n\n"

    await update.message.reply_text(response)

