import threading
import time

import schedule
from helpers.logger import logger

class Scheduler:
    def __init__(self):
        self.scheduled_jobs = {}

    def job(self, name: str):
        print(f"I'm working... {name}")

    def schedule_job(self, job_id: str, name: str, interval: int):
        self.scheduled_jobs[job_id] = {
            "name": name,
            "job": schedule.every(interval).minutes.do(self.job, name)
        }
        logger.info(f"Job for product: {name} and ID: ({job_id}) - scheduled every {interval} minutes.")

    def cancel_job(self, job_id: str):
        if job_id in self.scheduled_jobs:
            schedule.cancel_job(self.scheduled_jobs[job_id]["job"])
            del self.scheduled_jobs[job_id]
            logger.info(f"Job for product ID: {job_id} cancelled.")
        else:
            logger.info(f"Job for product ID: {job_id} not found.")

    def run_scheduler(self):
        while True:
            schedule.run_pending()
            time.sleep(1)  # Add a short sleep to prevent high CPU usage


def start_scheduler_thread(scheduler):
    thread = threading.Thread(target=scheduler.run_scheduler)
    thread.daemon = True  # Daemonize thread
    thread.start()  # Start the scheduler thread


scheduler = Scheduler()