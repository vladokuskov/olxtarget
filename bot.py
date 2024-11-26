from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from helpers.api import fetch_olx_products
from utils import check_authorization, main_reply_keyboard
from scheduler import scheduler

import uuid


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
    tracked_products = context.user_data.get('tracked_products', [])
    keyboard = [["Back"]]
    if not tracked_products:
        keyboard.insert(0, ["Add product to track"])
    else:
        response = "You have the following products tracked:\n\n" + "\n".join(product['name'] for product in tracked_products)
        for product in tracked_products:
            keyboard.insert(-1, [product["name"]])
        if len(tracked_products) + 1 <= 5:
            keyboard.insert(0, ["Add product to track"])

    await update.message.reply_text(response if tracked_products else "You have no tracked products.", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))


# Handle user inputs
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('waiting_for_search'):
        product_name = update.message.text
        context.user_data['product_name'] = product_name
        context.user_data['waiting_for_search'] = False
        await search_olx_products(update, context)
    elif context.user_data.get('adding_product'):
        # Add product to track
        product_name = update.message.text
        product_id = uuid.uuid4().hex
        tracked_products = context.user_data.setdefault('tracked_products', [])
        if not any(product['name'] == product_name for product in tracked_products):
            tracked_products.append({'id': product_id, 'name': product_name})
            scheduler.schedule_job(product_id, product_name, 10, update.effective_user.id)
            await update.message.reply_text(f'Product "{product_name}" has been added to your tracked products.')
        else:
            await update.message.reply_text(f'You already have "{product_name}" in your tracked products.')
        await tracking(update, context)
        context.user_data['adding_product'] = False
    elif update.message.text == "Add product to track":
        # Set flag to indicate waiting for product name
        context.user_data['adding_product'] = True
        await update.message.reply_text("Type product name:")
    elif any(product['name'] == update.message.text for product in context.user_data.get('tracked_products', [])):
        # Remove the selected product
        product_to_remove = update.message.text
        tracked_products = context.user_data['tracked_products']
        product_to_remove_obj = next(product for product in tracked_products if product['name'] == product_to_remove)
        scheduler.cancel_job(product_to_remove_obj['id'])
        context.user_data['tracked_products'] = [product for product in tracked_products if product['name'] != product_to_remove]
        await update.message.reply_text(f'Product "{product_to_remove}" has been removed from your tracked products.')
        await tracking(update, context)
    elif update.message.text == "Back":
        await update.message.reply_text('Main menu. Choose an option:', reply_markup=main_reply_keyboard())
    else:
        await update.message.reply_text("Please use /search to start a new search.")


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
