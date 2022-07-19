"""
WALOUS - Copyright (C) <2022> <Service Public de Wallonie (SWP)>.

Set d'utilitaires pour le logger.
"""
import logging
from pathlib import Path

LOGGER_NAME = "walousmaj"
STREAM_LEVEL = logging.INFO
STREAM_FORMATTER = "%(asctime)s | WalOUSMàJ | %(message)s"
FILE_LEVEL = logging.DEBUG
FILE_FORMATTER = (
    "%(asctime)s | %(levelname)s | [%(filename)s/%(funcName)s]: %(message)s"
)


def get_logger(log_filepath: str, exist_delete: bool = True) -> logging.Logger:
    """Obtenir un Logger écrivant dans le terminal et un fichier.

    :param log_filepath: Path vers le fichier où seront écrits les logs.
    :type log_filepath: str
    :param exist_delete: Option pour supprimer le fichier log existant, s'il existe
        déjà. True par défaut.
    :type exist_delete: bool, optional
    :return: Un Logger avec un stream et file handlers.
    :rtype: logging.Logger
    """
    log_filepath = Path(log_filepath)
    if exist_delete and log_filepath.exists():
        log_filepath.unlink()
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(STREAM_LEVEL)
    stream_formatter = logging.Formatter(STREAM_FORMATTER)
    stream_handler.setFormatter(stream_formatter)
    logger.addHandler(stream_handler)
    file_handler = logging.FileHandler(log_filepath)
    file_handler.setLevel(FILE_LEVEL)
    file_formatter = logging.Formatter(FILE_FORMATTER)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    return logger
