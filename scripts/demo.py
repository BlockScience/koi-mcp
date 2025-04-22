#!/usr/bin/env python3
"""
demo_full.py

A full‑blown KOI‑MCP integration demo that:

  1. Starts Coordinator, Agent 1, Agent 2 (streaming logs via rich)
  2. Waits for each /resources/list and /tools/list to respond
  3. Prints KOI resources and MCP tools in tables
  4. Invokes a sample trait on each agent via POST
  5. Examines the KOI cache directory
  6. Cleans up on Ctrl+C
"""

import subprocess, threading, time, signal, sys, os, urllib.parse
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner

console = Console()

# ——— CONFIGURATION ———
COORD_CMD    = ["python", "-m", "koi_mcp.main", "coordinator", "--config", "configs/coordinator.json"]
AGENT1_CMD   = ["python", "-m", "koi_mcp.main", "agent",       "--config", "configs/agent1.json"]
AGENT2_CMD   = ["python", "-m", "koi_mcp.main", "agent",       "--config", "configs/agent2.json"]

COORD_URL    = "http://localhost:9000"
AGENT1_URL   = "http://localhost:8101"
AGENT2_URL   = "http://localhost:8102"

# ——— LOG STREAMING ———
def _stream(name, stream, style):
    for line in iter(stream.readline, ""):
        if not line:
            break
        console.print(f"[{style}][{name}][/] {line.rstrip()}")

def start(name, cmd, style):
    console.print(f"[bold]{name}[/bold] → {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1,
        env={**os.environ, "PYTHONUNBUFFERED":"1", "LOG_LEVEL":"DEBUG"}
    )
    threading.Thread(target=_stream, args=(name, proc.stdout, style), daemon=True).start()
    threading.Thread(target=_stream, args=(name+" ERR", proc.stderr, style), daemon=True).start()
    return proc

# ——— WAIT FOR ENDPOINT ———
def wait_for(url, path, timeout=30):
    client = httpx.Client(timeout=2)
    spinner = Spinner("dots", text=f"Waiting for {url}{path}")
    with Live(spinner, console=console, refresh_per_second=10):
        for _ in range(timeout*10):
            try:
                r = client.get(f"{url}{path}")
                if r.status_code == 200:
                    console.log(f"[green]✔[/green] {url}{path}")
                    return True
            except Exception:
                pass
            time.sleep(0.1)
    console.log(f"[red]✖[/red] {url}{path} timed out")
    return False

# ——— DISPLAY RESOURCES & TOOLS ———
def show_resources(url):
    r = httpx.get(f"{url}/resources/list")
    data = r.json().get("resources", [])
    table = Table(title=f"Resources @ {url}")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Type", style="magenta")
    table.add_column("Desc", style="green")
    for res in data:
        table.add_row(res["id"], res["type"], res.get("description",""))
    console.print(table)
    return data

def show_tools(url):
    r = httpx.get(f"{url}/tools/list")
    data = r.json().get("tools", [])
    table = Table(title=f"Tools @ {url}")
    table.add_column("Name", style="cyan")
    table.add_column("URL", style="blue")
    for tool in data:
        table.add_row(tool["name"], tool["url"])
    console.print(table)
    return data

# ——— INVOKE TRAIT ———
def invoke_trait(base_url, tool):
    """
    tool: { "name": "...", "url": "..." }
    we POST {} to the full URL
    """
    raw = tool["url"]
    # resolve relative URLs
    full = raw if raw.startswith("http") else urllib.parse.urljoin(base_url, raw)
    console.print(Panel(f"Calling [bold]{tool['name']}[/bold] → {full}", style="yellow"))
    try:
        r = httpx.post(full, json={})  # empty JSON or {"expr":"2+2"} etc
        console.print(f"[green]200[/green] {r.text}")
    except Exception as e:
        console.print(f"[red]ERROR[/red] {e}")

# ——— EXAMINE CACHE ———
def examine_cache(dirpath="rid_cache"):
    console.print(Panel(f"Inspecting cache: {dirpath}", style="blue"))
    if not os.path.isdir(dirpath):
        console.print("[red]No cache directory found[/red]")
        return
    files = sorted(os.listdir(dirpath))
    tbl = Table(title="Cache Files")
    tbl.add_column("File", style="cyan")
    tbl.add_column("Size", style="green", justify="right")
    for fn in files:
        tbl.add_row(fn, str(os.path.getsize(os.path.join(dirpath, fn))))
    console.print(tbl)

# ——— CLEANUP ———
def shutdown(procs):
    console.print("\n[bold yellow]Stopping services…[/bold yellow]")
    for p in procs:
        p.terminate()
        try: p.wait(3)
        except: p.kill()
    console.print("[bold green]Shutdown complete[/bold green]")

# ——— MAIN ———
def main():
    procs = []
    signal.signal(signal.SIGINT, lambda s,f: (shutdown(procs), sys.exit(0)))

    # 1) Start Coordinator & Agents
    procs.append(start("Coordinator", COORD_CMD, "blue"))
    assert wait_for(COORD_URL,   "/resources/list")
    procs.append(start("Agent 1",  AGENT1_CMD,  "green"))
    assert wait_for(AGENT1_URL,  "/resources/list")
    procs.append(start("Agent 2",  AGENT2_CMD,  "magenta"))
    assert wait_for(AGENT2_URL,  "/resources/list")

    # 2) Show network state
    show_resources(COORD_URL)
    show_tools(COORD_URL)
    show_resources(AGENT1_URL)
    show_tools(AGENT1_URL)
    show_resources(AGENT2_URL)
    show_tools(AGENT2_URL)

    # 3) Call one trait per agent
    tools1 = show_tools(AGENT1_URL)
    if tools1:
        invoke_trait(AGENT1_URL, tools1[0])

    tools2 = show_tools(AGENT2_URL)
    if tools2:
        invoke_trait(AGENT2_URL, tools2[0])

    # 4) Inspect cache
    examine_cache()

    console.print("\n[bold yellow]Demo running. Ctrl+C to exit.[/bold yellow]")
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()