import os
import sys
import time
import argparse
import logging
import asyncio
import uvicorn
import multiprocessing
from koi_mcp.utils.logging.setup import setup_logging
from koi_mcp.config import load_config, Config
from koi_mcp.koi.node.coordinator import CoordinatorAdapterNode
from koi_mcp.koi.node.agent import KoiAgentNode

logger = setup_logging()

def run_coordinator(config_path: str = "configs/coordinator.json"):
    """Run the KOI-MCP Coordinator Node."""
    config = load_config(config_path)
    if not config.coordinator:
        logger.error("Coordinator configuration not found in config file")
        sys.exit(1)
        
    logger.info(f"Starting coordinator node {config.coordinator.name}")
    
    # Create Coordinator-Adapter node
    coordinator = CoordinatorAdapterNode(
        name=config.coordinator.name,
        base_url=config.coordinator.base_url,
        mcp_registry_port=config.coordinator.mcp_registry_port
    )
    
    # Start node
    coordinator.start()
    
    # Start MCP Registry Server
    logger.info(f"Starting MCP registry server on port {config.coordinator.mcp_registry_port}")
    uvicorn.run(
        coordinator.registry_server.app, 
        host="0.0.0.0", 
        port=config.coordinator.mcp_registry_port
    )

def run_agent(config_path: str = "configs/agent1.json"):
    """Run a KOI-MCP Agent Node."""
    config = load_config(config_path)
    if not config.agent:
        logger.error("Agent configuration not found in config file")
        sys.exit(1)
        
    logger.info(f"Starting agent node {config.agent.name}")
    
    # Create Agent node
    agent = KoiAgentNode(
        name=config.agent.name,
        version=config.agent.version,
        traits=config.agent.traits,
        base_url=config.agent.base_url,
        mcp_port=config.agent.mcp_port,
        first_contact=config.network.first_contact
    )
    
    # Start node
    agent.start()
    
    # Start MCP Server
    logger.info(f"Starting MCP agent server on port {config.agent.mcp_port}")
    uvicorn.run(
        agent.mcp_server.app, 
        host="0.0.0.0", 
        port=config.agent.mcp_port
    )

def run_process(target, config_path=None):
    """Run a function in a separate process."""
    kwargs = {}
    if config_path:
        kwargs["config_path"] = config_path
        
    process = multiprocessing.Process(target=target, kwargs=kwargs)
    process.start()
    return process

def run_demo():
    """Run a demonstration with coordinator and two agent nodes."""
    logger.info("Starting KOI-MCP demonstration")
    
    # Start coordinator
    logger.info("Starting coordinator node")
    coordinator_process = run_process(run_coordinator, "configs/coordinator.json")
    
    # Give coordinator time to start
    time.sleep(5)
    
    # Start first agent
    logger.info("Starting agent 1")
    agent1_process = run_process(run_agent, "configs/agent1.json")
    
    # Start second agent
    logger.info("Starting agent 2")
    agent2_process = run_process(run_agent, "configs/agent2.json")
    
    try:
        # Keep main process running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping demo")
    finally:
        # Terminate processes
        for process in [coordinator_process, agent1_process, agent2_process]:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="KOI-MCP Integration")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Coordinator command
    coordinator_parser = subparsers.add_parser("coordinator", help="Run coordinator node")
    coordinator_parser.add_argument("--config", default="configs/coordinator.json", help="Path to config file")
    
    # Agent command
    agent_parser = subparsers.add_parser("agent", help="Run agent node")
    agent_parser.add_argument("--config", default="configs/agent1.json", help="Path to config file")
    
    # Demo command
    subparsers.add_parser("demo", help="Run demonstration with coordinator and two agents")
    
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
