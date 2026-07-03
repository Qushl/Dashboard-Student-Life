"""Журнал ошибок и событий."""

import logging
from pathlib import Path
from datetime import datetime

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


def get_logger(name: str = "student_life") -> logging.Logger:
    """Возвращает настроенный логгер."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    log_file = LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter("%(levelname)-8s | %(message)s"))
    logger.addHandler(ch)

    return logger


log = get_logger()


def log_error(context: str, error: Exception):
    log.error(f"{context}: {type(error).__name__}: {error}")


def log_warning(context: str, message: str):
    log.warning(f"{context}: {message}")


def log_info(context: str, message: str):
    log.info(f"{context}: {message}")


def get_recent_logs(n: int = 20) -> list[str]:
    """Последние N записей из журнала."""
    log_file = LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    if not log_file.exists():
        return []
    lines = log_file.read_text(encoding="utf-8").strip().split("\n")
    return lines[-n:]
