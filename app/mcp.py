from app.effects.effects_mcp import effects_mcp
from app.provision.provision_mcp import provision_mcp

effects_mcp_app = effects_mcp.http_app(path="/")
provision_mcp_app = provision_mcp.http_app(path="/")
