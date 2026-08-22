import logging
import sys
import utils
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(filename)s:%(lineno)d | %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)],
)
logger = logging.getLogger("mcp-config")

config = utils.load_config()
logger.info(f"config: {config}")

workingDir = os.path.dirname(os.path.abspath(__file__))
logger.info(f"workingDir: {workingDir}")

mcp_user_config = {}


def load_config(mcp_type):
    """Load MCP server config. Names must match application/mcp.list."""
    if mcp_type == "tavily":
        return {
            "mcpServers": {
                "tavily-search": {
                    "command": "python",
                    "args": [f"{workingDir}/mcp_server_tavily.py"],
                }
            }
        }

    elif mcp_type == "web_fetch":
        return {
            "mcpServers": {
                "web_fetch": {
                    "command": "npx",
                    "args": ["-y", "mcp-server-fetch-typescript"],
                }
            }
        }

    elif mcp_type == "text_extraction":
        return {
            "mcpServers": {
                "text_extraction": {
                    "command": "python",
                    "args": [f"{workingDir}/mcp_server_text_extraction.py"],
                }
            }
        }

    elif mcp_type == "graph memory":
        return {
            "mcpServers": {
                "graph memory": {
                    "command": "python",
                    "args": [f"{workingDir}/mcp_server_graph_memory.py"],
                    "env": {
                        "PYTHONPATH": workingDir,
                    },
                }
            }
        }

    elif mcp_type == "docgraph":
        return {
            "mcpServers": {
                "docgraph": {
                    "command": "python",
                    "args": [f"{workingDir}/mcp_server_docgraph.py"],
                    "env": {
                        "PYTHONPATH": workingDir,
                    },
                }
            }
        }

    elif mcp_type == "사용자 설정":
        return mcp_user_config

    logger.warning(f"Unknown MCP type (not in mcp.list?): {mcp_type}")
    return {}


def load_selected_config(mcp_servers: dict):
    logger.info(f"mcp_servers: {mcp_servers}")

    loaded_config = {}
    for server in mcp_servers:
        config = load_config(server)
        if config:
            loaded_config.update(config["mcpServers"])
    return {
        "mcpServers": loaded_config,
    }
