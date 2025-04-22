import sys
import time
import argparse
import logging
import multiprocessing
import uvicorn
from koi_mcp.utils.logging.setup import setup_logging
from koi_mcp.config import load_config
from koi_mcp.koi.node.coordinator import CoordinatorAdapterNode
from koi_mcp.koi.node.agent import KoiAgentNode

logger = setup_logging()

def run_coordinator(config_path: str = "configs/coordinator.json"):
    config = load_config(config_path)
    if not config.coordinator:
        logger.error("Coordinator configuration not found")
        sys.exit(1)
        
    logger.info(f"Starting coordinator node {config.coordinator.name}")
    coordinator = CoordinatorAdapterNode(
        name=config.coordinator.name,
        base_url=config.coordinator.base_url,
        mcp_registry_port=config.coordinator.mcp_registry_port
    )
    coordinator.start()
    
    logger.info(f"MCP registry server running on port {config.coordinator.mcp_registry_port}")
    uvicorn.run(
        coordinator.registry_server.app,
        host="0.0.0.0",
        port=config.coordinator.mcp_registry_port
    )

def run_agent(config_path: str = "configs/agent1.json"):
    config = load_config(config_path)
    if not config.agent:
        logger.error("Agent configuration not found")
        sys.exit(1)
        
    logger.info(f"Starting agent node {config.agent.name}")
    agent = KoiAgentNode(
        name=config.agent.name,
        version=config.agent.version,
        traits=config.agent.traits,
        base_url=config.agent.base_url,
        mcp_port=config.agent.mcp_port,
        first_contact=config.network.first_contact
    )
    agent.start()
    
    logger.info(f"MCP agent server running on port {config.agent.mcp_port}")
    uvicorn.run(
        agent.mcp_server.app, 
        host="0.0.0.0", 
        port=config.agent.mcp_port
    )

def run_process(target, config_path=None):
    kwargs = {}
    if config_path:
        kwargs["config_path"] = config_path
    process = multiprocessing.Process(target=target, kwargs=kwargs)
    process.start()
    return process

def run_demo():
    logger.info("Starting koi-mcp demo")
    coord_proc = run_process(run_coordinator, "configs/coordinator.json")
    time.sleep(5)
    a1 = run_process(run_agent, "configs/agent1.json")
    time.sleep(2)
    a2 = run_process(run_agent, "configs/agent2.json")
    time.sleep(2)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping demo")
    finally:
        for p in [coord_proc, a1, a2]:
            if p.is_alive():
                p.terminate()
                p.join(timeout=5)

def main():
    parser = argparse.ArgumentParser(description="koi-mcp demo")
    sub = parser.add_subparsers(dest="command")
    # Coordinator subcommand accepts --config
    coord_parser = sub.add_parser("coordinator")
    coord_parser.add_argument("--config", default="configs/coordinator.json")
    # Agent subcommand accepts --config
    agent_parser = sub.add_parser("agent")
    agent_parser.add_argument("--config", default="configs/agent1.json")
    # Demo subcommand
    sub.add_parser("demo")
    args = parser.parse_args()
    
    if args.command == "coordinator":
        run_coordinator(args.config)
    elif args.command == "agent":
        run_agent(args.config)
    elif args.command == "demo":
        run_demo()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()