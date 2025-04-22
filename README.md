# KOI-MCP Integration

A lightweight bridge that lets autonomous KOI network **agent nodes** exchange richly‑typed _personality_ objects and surface them as live **MCP resources & tools**.

## Quick Start

```bash
# Install dependencies
uv venv
source .venv/bin/activate
uv pip install -e .

# Run demo (starts coordinator and two agents)
python -m koi_mcp.main demo

# Or run individual components
python -m koi_mcp.main coordinator
python -m koi_mcp.main agent --config configs/agent1.json
```

Visit:
- Coordinator: http://localhost:9000/resources/list
- Agent1: http://localhost:8101/tools/list
- Agent2: http://localhost:8102/tools/list

## Architecture

This integration uses a Coordinator-Adapter pattern where:
1. A central Coordinator Node acts as both KOI network hub and MCP registry
2. Agent Nodes publish personality traits to the network
3. The Coordinator registers these traits and makes them discoverable via MCP
4. LLM clients can discover and use agent traits through standard MCP endpoints

For more details, see the [Design Document](docs/design.md).

## License

MIT
