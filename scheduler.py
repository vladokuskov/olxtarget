import asyncio
import os
import threading
import time
from telegram import Bot
from dotenv import load_dotenv
import schedule
from helpers.api import fetch_olx_products
from helpers.logger import logger
from store import store


load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = Bot(token=TOKEN)


def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)  # Add a short sleep to prevent high CPU usage


class Scheduler:
    def __init__(self):
        self.scheduled_jobs = {}
        self.loop = asyncio.get_event_loop()

    async def job(self, name: str, user_id: str):
        products = await fetch_olx_products(name)

        for product in products:
            title = product.get('title', 'No title')
            url = product.get('url', 'No URL')

            if store.is_product_exist(url, user_id):
                continue

            price_label = ''
            for param in product.get('params', []):
                if param.get('key') == 'price':
                    price_label = param.get('value', {}).get('label', 'Price not available')
                    break

            message = (
                f"🔔 New Product Found!\n\n"
                f"Title: {title}\n"
                f"Price: {price_label}\n"
                f"{url}\n"
            )

            try:
                # Send a notification to the user
                await bot.send_message(chat_id=user_id, text=message)
            except Exception as e:
                logger.error(f"Error sending message to user: {e}")

            store.add_product(url, user_id)

    def run_async_job(self, name: str, user_id: str):
        # Create an event loop and run the async job
        asyncio.run_coroutine_threadsafe(self.job(name, user_id), self.loop)

    def schedule_job(self, job_id: str, name: str, interval: int, user_id: str):
        self.scheduled_jobs[job_id] = {
            "name": name,
            "job": schedule.every(1).minutes.do(self.run_async_job, name, user_id)
        }
        logger.info(f"Job for product: {name} and ID: ({job_id}) - scheduled every {interval} minutes.")

    def cancel_job(self, job_id: str):
        if job_id in self.scheduled_jobs:
            schedule.cancel_job(self.scheduled_jobs[job_id]["job"])
            del self.scheduled_jobs[job_id]
            logger.info(f"Job for product ID: {job_id} cancelled.")
        else:
            logger.info(f"Job for product ID: {job_id} not found.")


def start_scheduler_thread():
    thread = threading.Thread(target=run_scheduler)
    thread.daemon = True  # Daemonize thread
    thread.start()  # Start the scheduler thread


scheduler = Scheduler()
