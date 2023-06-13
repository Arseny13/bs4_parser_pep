import argparse
import logging

from logging.handlers import RotatingFileHandler
from constants import (
    LOG_DIR, LOG_FORMAT, LOG_FILE,
    DATETIME_FORMAT,
    PRETTY_MODE, FILE_MODE
)


def configure_argument_parser(available_modes):
    parser = argparse.ArgumentParser(description='Парсер документации Python')
    parser.add_argument(
        'mode',
        choices=available_modes,
        help='Режимы работы парсера'
    )
    parser.add_argument(
        '-c',
        '--clear-cache',
        action='store_true',
        help='Очистка кеша'
    )
    parser.add_argument(
        '-o',
        '--output',
        choices=(PRETTY_MODE, FILE_MODE),
        help='Дополнительные способы вывода данных'
    )
    return parser


def configure_logging():
    try:
        LOG_DIR.mkdir(exist_ok=True)
    except PermissionError:
        raise PermissionError('Нет прав')
    rotating_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=10 ** 6, backupCount=5
    )
    logging.basicConfig(
        datefmt=DATETIME_FORMAT,
        format=LOG_FORMAT,
        level=logging.INFO,
        handlers=(rotating_handler, logging.StreamHandler())
    )
