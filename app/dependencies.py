import sys

from iduconfig import Config
from loguru import logger

from app.common.api_handler.api_handler import APIHandler
from app.common.exceptions.http_exception_wrapper import http_exception

logger.remove()
logger.add(sys.stderr, level="INFO")
log_level = "INFO"
log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <b>{message}</b>"
logger.add(sys.stderr, format=log_format, level=log_level, colorize=True)

config = Config()

logger.add(
    ".log",
    format=log_format,
    level="INFO",
)

urban_api_handler = APIHandler(config.get("URBAN_API"))
