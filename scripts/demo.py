#!/usr/bin/env python3
"""
KOI-MCP Debug Demo Script

This script demonstrates the KOI-MCP integration with enhanced debugging.
"""

import os
import sys
import time
import json
import signal
import subprocess
import threading
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress

console = Console()

def read_process_output(process, name, color, console_obj):
    """Read output from process and print with formatting."""
    for line in iter(process.stdout.readline, ""):
        if line:
            console_obj.print(f"[{color}][{name}][/] {line.strip()}")
    
    for line in iter(process.stderr.readline, ""):
        if line:
            console_obj.print(f"[{color}][{name} ERROR][/] {line.strip()}", style="bold red")

def start_process_with_logging(command, name, color):
    """Start a process with the given command and log its output."""
    console.print(f"Starting {name}...", style=color)
    
    # Set environment variable to increase logging verbosity
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["LOG_LEVEL"] = "DEBUG"  # Try to set higher logging level
    
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env
    )
    
    console.print(f"{name} started with PID {process.pid}", style=color)
    
    # Start thread to read and display output
    thread = threading.Thread(
        target=read_process_output,
        args=(process, name, color, console),
        daemon=True
    )
    thread.start()
    
    return process, thread

def check_endpoint(url, max_attempts=10, delay=1):
    """Check if an endpoint is available."""
    for i in range(max_attempts):
        try:
            console.print(f"Checking endpoint {url}...", style="dim")
            response = httpx.get(url)
            if response.status_code == 200:
                console.print(f"Endpoint {url} is available", style="green")
                return True
            console.print(f"Attempt {i+1}: Got status code {response.status_code} from {url}", style="yellow")
        except Exception as e:
            console.print(f"Attempt {i+1}: Error connecting to {url}: {e}", style="yellow")
            
        time.sleep(delay)
    
    console.print(f"Endpoint {url} is not available after {max_attempts} attempts", style="red")
    return False

def print_resources(url):
    """Print resources from an MCP endpoint."""
    try:
        response = httpx.get(f"{url}/resources/list")
        data = response.json()
        
        table = Table(title="Resources")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Description", style="yellow")
        
        for resource in data.get("resources", []):
            table.add_row(
                resource.get("id", ""),
                resource.get("type", ""),
                resource.get("description", "")
            )
        
        console.print(table)
        
        # Return count of resources for verification
        return len(data.get("resources", []))
    except Exception as e:
        console.print(f"Error fetching resources from {url}: {e}", style="red")
        return 0

def print_tools(url):
    """Print tools from an MCP endpoint."""
    try:
        response = httpx.get(f"{url}/tools/list")
        data = response.json()
        
        table = Table(title="Tools")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="yellow")
        
        for tool in data.get("tools", []):
            table.add_row(
                tool.get("name", ""),
                tool.get("description", "")
            )
        
        console.print(table)
        
        # Return count of tools for verification
        return len(data.get("tools", []))
    except Exception as e:
        console.print(f"Error fetching tools from {url}: {e}", style="red")
        return 0

def examine_cache_directory():
    """Examine the KOI cache directory to see what's been saved."""
    console.print("Examining KOI cache directory...", style="yellow")
    if os.path.exists("rid_cache"):
        files = os.listdir("rid_cache")
        console.print(f"Found {len(files)} files in cache directory", style="blue")
        for filename in files:
            try:
                if filename.endswith(".json"):
                    with open(os.path.join("rid_cache", filename), 'r') as f:
                        content = json.load(f)
                        console.print(f"Cache file {filename}: {json.dumps(content, indent=2)}", style="dim")
            except Exception as e:
                console.print(f"Error reading cache file {filename}: {e}", style="red")
    else:
        console.print("Cache directory 'rid_cache' not found", style="yellow")

def wait_with_spinner(seconds, message):
    """Wait with a spinner to show progress."""
    with Progress() as progress:
        task = progress.add_task(message, total=seconds)
        for _ in range(seconds):
            time.sleep(1)
            progress.update(task, advance=1)

def analyze_agent_config(config_file, verbose=False):
    """Analyze an agent config file and check for issues."""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
            
        console.print(f"Contents of {config_file}:", style="bold")
        if verbose:
            console.print_json(json.dumps(config))
        
        # Check important fields
        if "agent" not in config:
            console.print(f"ERROR: Missing 'agent' section in {config_file}", style="red")
            return False
            
        if "network" not in config or "first_contact" not in config["network"]:
            console.print(f"ERROR: Missing network.first_contact in {config_file}", style="red")
            return False
            
        agent_url = config["agent"]["base_url"]
        mcp_port = config["agent"]["mcp_port"]
        first_contact = config["network"]["first_contact"]
        
        console.print(f"Agent base_url: {agent_url}", style="blue")
        console.print(f"Agent MCP port: {mcp_port}", style="blue")
        console.print(f"First contact: {first_contact}", style="blue")
        
        # Critical Issue: Check if base_url includes the /koi-net path
        if not agent_url.endswith("/koi-net"):
            console.print(f"CRITICAL ISSUE: Agent base_url doesn't end with /koi-net: {agent_url}", style="bold red")
            console.print("This will cause problems with KOI-net discovery and communication", style="red")
            console.print(f"Should be: {agent_url}/koi-net", style="green")
        
        return True
    except FileNotFoundError:
        console.print(f"ERROR: Config file not found: {config_file}", style="red")
        return False
    except json.JSONDecodeError:
        console.print(f"ERROR: Invalid JSON in config file: {config_file}", style="red")
        return False

def main():
    """Run the debug demo."""
    console.print(Panel("KOI-MCP Integration Debug Demo", style="bold green"))
    
    # Check and analyze configs with critical issue detection
    console.print(Panel("Checking Configuration", style="bold yellow"))
    analyze_agent_config("configs/coordinator.json", verbose=True)
    analyze_agent_config("configs/agent1.json", verbose=True)
    analyze_agent_config("configs/agent2.json", verbose=True)
    
    # Get confirmation to continue
    console.print("\nConfiguration check complete. Continue with demo? (y/n)", style="bold")
    response = input().strip().lower()
    if response != 'y':
        console.print("Demo aborted by user", style="yellow")
        return
    
    processes = []
    threads = []
    
    try:
        # Start coordinator with logging but WITHOUT the --debug flag
        console.print(Panel("Starting Coordinator", style="bold blue"))
        coordinator, coord_thread = start_process_with_logging(
            ["python", "-m", "koi_mcp.main", "coordinator"],
            "Coordinator",
            "blue"
        )
        processes.append(coordinator)
        threads.append(coord_thread)
        
        # Wait for coordinator to start
        console.print("Waiting for coordinator to start...", style="yellow")
        coordinator_url = "http://localhost:9000/koi-net"
        if not check_endpoint(f"{coordinator_url}/resources/list", max_attempts=20, delay=1):
            console.print("Coordinator failed to start", style="red")
            return
        
        # Add a delay before starting agents
        time.sleep(5)
        
        # Start agent 1 with logging but WITHOUT the --debug flag
        console.print(Panel("Starting Agent 1", style="bold green"))
        agent1, agent1_thread = start_process_with_logging(
            ["python", "-m", "koi_mcp.main", "agent", "--config", "configs/agent1.json"],
            "Agent 1",
            "green"
        )
        processes.append(agent1)
        threads.append(agent1_thread)
        
        # Add a delay between agent starts
        time.sleep(5)
        
        # Start agent 2 with logging but WITHOUT the --debug flag
        console.print(Panel("Starting Agent 2", style="bold magenta"))
        agent2, agent2_thread = start_process_with_logging(
            ["python", "-m", "koi_mcp.main", "agent", "--config", "configs/agent2.json"],
            "Agent 2",
            "magenta"
        )
        processes.append(agent2)
        threads.append(agent2_thread)
        
        # Wait for agents to start with longer timeout
        wait_with_spinner(15, "Waiting for agents to initialize...")
        
        agent1_url = "http://localhost:8101"
        agent2_url = "http://localhost:8102"
        agent1_available = check_endpoint(f"{agent1_url}/tools/list")
        agent2_available = check_endpoint(f"{agent2_url}/tools/list")
        
        if not (agent1_available and agent2_available):
            console.print("Not all agent endpoints are available", style="yellow")
            return
        
        # Give KOI network more time to propagate knowledge
        wait_with_spinner(30, "Waiting for KOI network to propagate knowledge...")
        
        # Examine cache directory to see what's been saved
        examine_cache_directory()
        
        # Check coordinator resources multiple times
        for i in range(3):
            console.print(f"\n[bold]Checking Coordinator Resources (Attempt {i+1}/3)[/bold]", style="blue")
            resource_count = print_resources(coordinator_url)
            
            if resource_count >= 2:
                console.print("Success! Both agents registered with coordinator", style="green")
                break
                
            if i < 2:  # Don't wait after the last attempt
                wait_with_spinner(10, "Waiting before next check...")
        
        if resource_count < 2:
            console.print(
                "\n[bold red]ERROR: Not all agent resources found on coordinator![/bold red]",
                style="red"
            )
        
        # Check other endpoints
        console.print("\n[bold]Coordinator Tools[/bold]", style="blue")
        print_tools(coordinator_url)
        
        console.print("\n[bold]Agent 1 Tools[/bold]", style="green")
        print_tools(agent1_url)
        
        console.print("\n[bold]Agent 2 Tools[/bold]", style="magenta")
        print_tools(agent2_url)
        
        # Wait for user to press Ctrl+C
        console.print("\nMonitoring logs... Press Ctrl+C to exit", style="yellow")
        try:
            # Keep reading logs until user interrupts
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
            
    except Exception as e:
        console.print(f"Error in demo: {e}", style="red")
    finally:
        # Terminate all processes
        console.print("Terminating processes...", style="yellow")
        for process in processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except Exception as e:
                console.print(f"Error terminating process: {e}", style="red")
        
        console.print("Demo completed", style="green")

if __name__ == "__main__":
    main()