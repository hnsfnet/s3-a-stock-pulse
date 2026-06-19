import logging
import sys
import os
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from pathlib import Path
from typing import Optional

from config import config, get_user_logs_dir


_LOGGERS: dict[str, logging.Logger] = {}
_INITIALIZED = False


def _setup_logging() -> None:
    global _INITIALIZED
    if _INITIALIZED:
        return

    log_level_str = config.get('logging.level', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    log_format = config.get('logging.format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    backup_count = config.get('logging.backup_count', 30)

    logs_dir = get_user_logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_filename = config.get('logging.filename', 'app_{date}.log')
    today_str = datetime.now().strftime('%Y%m%d')
    log_file = logs_dir / log_filename.format(date=today_str)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    formatter = logging.Formatter(log_format)

    file_handler = TimedRotatingFileHandler(
        filename=str(log_file),
        when='midnight',
        interval=1,
        backupCount=backup_count,
        encoding='utf-8',
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    _INITIALIZED = True


def get_logger(name: str) -> logging.Logger:
    _setup_logging()
    if name in _LOGGERS:
        return _LOGGERS[name]
    logger = logging.getLogger(name)
    _LOGGERS[name] = logger
    return logger


def log_sql(logger: logging.Logger, sql: str, params: Optional[tuple] = None) -> None:
    if logger.isEnabledFor(logging.DEBUG):
        sql_preview = sql.strip().replace('\n', ' ')[:200]
        if params:
            logger.debug(f"SQL: {sql_preview} | params: {params}")
        else:
            logger.debug(f"SQL: {sql_preview}")


def log_transaction(logger: logging.Logger, action: str, txn_id: Optional[int] = None, **kwargs) -> None:
    details = ', '.join(f"{k}={v}" for k, v in kwargs.items())
    if txn_id:
        logger.info(f"Transaction {action}: id={txn_id}, {details}")
    else:
        logger.info(f"Transaction {action}: {details}")


def log_budget_warning(logger: logging.Logger, category_name: str, spent: float, budget: float, ratio: float) -> None:
    logger.warning(
        f"Budget warning: {category_name} - spent={spent:.2f}, budget={budget:.2f}, "
        f"ratio={ratio:.2%}"
    )


def log_recurring_generated(logger: logging.Logger, rule_id: int, rule_name: str, txn_id: int) -> None:
    logger.info(
        f"Recurring transaction generated: rule_id={rule_id}, rule_name='{rule_name}', "
        f"txn_id={txn_id}"
    )
