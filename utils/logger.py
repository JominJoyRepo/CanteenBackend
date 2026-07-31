import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent

class ColorFormatter(logging.Formatter):
    LEVEL_COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[35m',
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.LEVEL_COLORS.get(record.levelname, self.RESET)
        formatted = super().format(record)
        return f"{color}{formatted}{self.RESET}"

def setup_logger():
    logger = logging.getLogger('canteen')
    logger.setLevel(getattr(logging, (Path(LOG_DIR / '.env').read_text().split('LOG_LEVEL=')[1].split('\n')[0] if Path(LOG_DIR / '.env').exists() and 'LOG_LEVEL=' in Path(LOG_DIR / '.env').read_text() else 'info').upper(), logging.INFO))

    file_fmt = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(ColorFormatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))

    info_handler = RotatingFileHandler(
        LOG_DIR / 'server.log',
        maxBytes=5242880,
        backupCount=3,
        encoding='utf-8'
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(file_fmt)

    error_handler = RotatingFileHandler(
        LOG_DIR / 'server.err',
        maxBytes=5242880,
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_fmt)

    logger.addHandler(console_handler)
    logger.addHandler(info_handler)
    logger.addHandler(error_handler)

    return logger

logger = setup_logger()
