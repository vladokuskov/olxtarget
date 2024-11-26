import asyncio
import os
import threading
import time
from telegram import Bot
from dotenv import load_dotenv
import schedule
from helpers.api import fetch_olx_products
from helpers.logger import logger
from db import db

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = Bot(token=TOKEN)

sent_product_urls = {}


def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)  # Add a short sleep to prevent high CPU usage


class Scheduler:
    def __init__(self):
        self.scheduled_jobs = {}
        self.loop = asyncio.get_event_loop()

    async def job(self, product_name: str, user_id: str):
        # Fetch products based on the name from OLX
        olx_products = await fetch_olx_products(product_name)

        if user_id not in sent_product_urls:
            sent_product_urls[user_id] = set()

        for olx_product in olx_products:
            url = olx_product.get('url', 'No URL')
            if url in sent_product_urls[user_id]:
                continue

            title = olx_product.get('title', 'No title')
            price_label = ''
            for param in olx_product.get('params', []):
                if param.get('key') == 'price':
                    price_label = param.get('value', {}).get('label', 'Price not available')
                    break

            message = (
                f"🔔 New Product Found!\n\n"
                f"Title: {title}\n"
                f"Price: {price_label}\n"
                f"{url}\n"
            )

            # Send a notification to the user
            try:
                await bot.send_message(chat_id=user_id, text=message)
                sent_product_urls[user_id].add(url)
                logger.info(f"Sent product to user {user_id}: {url}")
            except Exception as e:
                logger.error(f"Error sending message to user: {e}")

    def run_async_job(self, product_name: str, user_id: str):
        # Run the asynchronous job for a specific user/product
        asyncio.run_coroutine_threadsafe(self.job(product_name, user_id), self.loop)

    def schedule_job_for_user(self, user_id: str):
        tracked_products = db.get_tracked_products(user_id)

        for product in tracked_products:
            product_name = product
            job_id = f"{user_id}_{product}"

            # Check if the job for this product already exists
            if job_id not in self.scheduled_jobs:
                self.scheduled_jobs[job_id] = {
                    "name": product_name,  # Store just the name or any other relevant info
                    "job": schedule.every(10).minutes.do(self.run_async_job, product_name, user_id)
                }
                logger.info(f"Job for product: {product_name} and user ID: {user_id} - scheduled every 1 minute.")
            else:
                logger.info(f"Job for product: {product_name} and user ID: {user_id} already scheduled.")

    def cancel_job(self, job_id: str):
        if job_id in self.scheduled_jobs:
            schedule.cancel_job(self.scheduled_jobs[job_id]["job"])
            del self.scheduled_jobs[job_id]
            logger.info(f"Job for product ID: {job_id} cancelled.")
        else:
            logger.info(f"Job for product ID: {job_id} not found.")


def start_scheduler_thread():
    thread = threading.Thread(target=run_scheduler)
    thread.daemon = True
    thread.start()


scheduler = Scheduler()


def start_scheduling_for_all_users():
    all_users = db.get_all_users()

    for user in all_users:
        scheduler.schedule_job_for_user(user['user_id'])