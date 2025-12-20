import time
import functools
from src.utils import logger

def retry_with_backoff(retries=3, backoff_in_seconds=1, error_types=(Exception,)):
    """
    Decorator to retry a function with exponential backoff.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except error_types as e:
                    if x == retries:
                        logger.error(f"Failed after {retries} retries: {e}")
                        raise
                    
                    sleep_time = (backoff_in_seconds * 2 ** x)
                    logger.warning(f"Error: {e}. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                    x += 1
        return wrapper
    return decorator
