import logging
from backend.core.config import config
import sys
def setup_logging():
    
    log_level = getattr(logging, config.LOG_LEVEL, logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", # Standard log format
        handlers=[
            logging.StreamHandler(sys.stdout) # Log to console
            ,
            logging.FileHandler("app.log", mode='a', encoding='utf-8') # Log to a file as well
        ],
        force = True
 )