from app.effects.effects_mcp import effects_mcp
from app.provision.provision_mcp import provision_mcp

# Provision tools are also exposed on the effects MCP endpoint so that
# consumers (gMART agents, ChatStorage replay) reach every tool via the
# single OBJECTS_EFFECTS_MCP_SERVER URL.
effects_mcp.mount(provision_mcp)

effects_mcp_app = effects_mcp.http_app(path="/")
provision_mcp_app = provision_mcp.http_app(path="/")
