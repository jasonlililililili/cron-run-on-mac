## this python script defines the logic of the task
## it will be run im case of the task id is returned by the cron-event script

import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run():
    logger.info("Running example task")
    current_time = datetime.now().strftime("%H:%M")
    logger.info(f"Current time: {current_time}")
    return True