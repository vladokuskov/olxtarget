import schedule
from helpers.logger import logger

class Scheduler:
    def __init__(self):
        self.scheduled_jobs = {}

    @staticmethod
    def job(self, name: str):
        print(f"I'm working... {name}")

    def schedule_job(self, job_id: str, name: str, interval: int):
        self.scheduled_jobs[job_id] = {
            "name": name,
            "job": schedule.every(interval).seconds.do(self.job, name)
        }
        logger.info(f"Job for item: {name} and ID: ({job_id}) - scheduled every {interval} seconds.")

    def cancel_job(self, job_id: str):
        if job_id in self.scheduled_jobs:
            schedule.cancel_job(self.scheduled_jobs[job_id]["job"])
            del self.scheduled_jobs[job_id]
            logger.info(f"Job for item ID: {job_id} cancelled.")
        else:
            logger.info(f"Job for item ID: {job_id} not found.")

    @staticmethod
    def run_scheduler(self):
        schedule.run_pending()


scheduler = Scheduler()