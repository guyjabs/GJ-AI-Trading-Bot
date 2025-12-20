from datetime import datetime
from config import LOG_LEVEL

# Print log message
def log(level, msg):
    log_levels = {"DEBUG": 1, "INFO": 2, "WARNING": 3, "ERROR": 4, "CRITICAL": 5}
    level_color_codes = {
        "DEBUG": "\033[94m",
        "INFO": "\033[92m",
        "WARNING": "\033[93m",
        "ERROR": "\033[91m",
        "CRITICAL": "\033[91m\033[1m"  # Red + Bold
    }
    timestamp_color_code = "\033[96m"
    reset_color_code = "\033[0m"
    if log_levels.get(level, 2) >= log_levels.get(LOG_LEVEL, 2):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        level_space = " " * (8 - len(level))
        print(f"{timestamp_color_code}[{timestamp}] {level_color_codes[level]}[{level}]{reset_color_code}{level_space}{msg}")


# Print debug log message
def debug(msg):
    log("DEBUG", msg)


# Print info log message
def info(msg):
    log("INFO", msg)


# Print warning log message
def warning(message):
    log("WARNING", message)

def critical(message):
    log("CRITICAL", message)

# Print error log message
def error(message):
    log("ERROR", message)

def log_client_event(msg):
    """Log client events to a dedicated file"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        with open("client_events.log", "a") as f:
            f.write(f"[{timestamp}] {msg}\n")
    except Exception as e:
        print(f"Error writing to client log: {e}")
