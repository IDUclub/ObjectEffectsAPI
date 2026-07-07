import sys

from loguru import logger

from app.common.api_handler.api_handler import APIHandler
from app.common.config.config import Config
from app.common.exceptions.http_exception_wrapper import http_exception
from app.common.modules.effects_api_gateway import EffectsAPIGateway
from app.effects.effects_service import EffectsService
from app.provision.provision_service import ProvisionService

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
urban_api_mcp_handler = APIHandler(config.get("MCP_URBAN_API"))

effects_api_gateway = EffectsAPIGateway(urban_api_handler)
effects_api_mcp_gateway = EffectsAPIGateway(urban_api_mcp_handler)

effects_service = EffectsService(effects_api_gateway)
effects_mcp_service = EffectsService(effects_api_mcp_gateway)

provision_service = ProvisionService(effects_api_gateway)
provision_mcp_service = ProvisionService(effects_api_mcp_gateway)
