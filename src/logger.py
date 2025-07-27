# src/logger.py
import logging
import os
from datetime import datetime # (You can remove this if you didn't use it, but keep it if it's there)
def setup_logger():
    """
    Sets up a structured logger for the trading bot.
    Logs will be written to 'bot.log' in the project root directory.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    log_file_path = os.path.join(project_root, 'bot.log')

    logger = logging.getLogger('binance_bot_logger')
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        file_handler = logging.FileHandler(log_file_path)
        file_handler.setLevel(logging.INFO)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        formatter = logging.Formatter('[%(asctime)s] %(levelname)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    # --- ADD THIS PRINT STATEMENT BEFORE RETURNING LOGGER ---
    

    return logger

logger = setup_logger()

# --- The __name__ == "__main__" block ---
if __name__ == "__main__":
    
    logger.info("Logger initialized successfully. (This should go to console and bot.log)")
    logger.info("REQUEST | GET /futures/account | params: None (This should go to console and bot.log)")
    logger.error("ERROR | BinanceAPIException | status_code: -1000 | message: Unknown error occurred (This should go to console and bot.log)")
    