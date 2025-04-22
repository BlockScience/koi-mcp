#!/usr/bin/env python3
# scripts/demo.py

"""
demo_full.py

A full‑blown KOI‑MCP integration demo that:

  1. Starts Coordinator, Agent 1, Agent 2 (streaming logs via rich)
  2. Waits for each /resources/list and /tools/list to respond
  3. Prints KOI resources and MCP tools in tables
  4. Invokes a sample trait on each agent via POST
  5. Examines the KOI cache directory
  6. Cleans up on Ctrl+C or SIGTERM
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

# Global list to hold process objects
procs = []

# ——— LOG STREAMING ———
def _stream(name, stream, style):
    for line in iter(stream.readline, ""):
        if not line:
            break
        console.print(f"[{style}][{name}][/] {line.rstrip()}")

def start(name, cmd, style):
    global procs
    console.print(f"[bold]{name}[/bold] → {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, bufsize=1,
        env={**os.environ, "PYTHONUNBUFFERED":"1", "LOG_LEVEL":"DEBUG"},
        preexec_fn=os.setsid if sys.platform != "win32" else None
    )
    threading.Thread(target=_stream, args=(name, proc.stdout, style), daemon=True).start()
    threading.Thread(target=_stream, args=(name+" ERR", proc.stderr, style), daemon=True).start()
    procs.append(proc)
    return proc

# ——— WAIT FOR ENDPOINT ———
def wait_for(url, path, timeout=30):
    spinner = Spinner("dots", text=f"Waiting for {url}{path}")
    with httpx.Client(timeout=2) as client:
        with Live(spinner, console=console, refresh_per_second=10):
            start_time = time.monotonic()
            while time.monotonic() - start_time < timeout:
                try:
                    r = client.get(f"{url}{path}")
                    if r.status_code == 200:
                        console.log(f"[green]✔[/green] {url}{path}")
                        return True
                except httpx.RequestError:
                    pass
                except Exception as e:
                    console.log(f"[red]✖[/red] Error checking {url}{path}: {e}")
                time.sleep(0.1)
    console.log(f"[red]✖[/red] {url}{path} timed out after {timeout}s")
    return False

# ——— DISPLAY RESOURCES & TOOLS ———
def show_resources(url):
    try:
        r = httpx.get(f"{url}/resources/list")
        r.raise_for_status()
        data = r.json().get("resources", [])
        table = Table(title=f"Resources @ {url}")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta")
        table.add_column("Desc", style="green")
        for res in data:
            table.add_row(res["id"], res["type"], res.get("description",""))
        console.print(table)
        return data
    except Exception as e:
        console.print(f"[red]Error fetching resources from {url}: {e}[/red]")
        return []

def show_tools(url):
    try:
        r = httpx.get(f"{url}/tools/list")
        r.raise_for_status()
        data = r.json().get("tools", [])
        table = Table(title=f"Tools @ {url}")
        table.add_column("Name", style="cyan")
        table.add_column("URL", style="blue")
        for tool in data:
            table.add_row(tool["name"], tool["url"])
        console.print(table)
        return data
    except Exception as e:
        console.print(f"[red]Error fetching tools from {url}: {e}[/red]")
        return []

# ——— INVOKE TRAIT ———
def invoke_trait(base_url, tool):
    raw = tool["url"]
    full = raw if raw.startswith("http") else urllib.parse.urljoin(base_url, raw)
    console.print(Panel(f"Calling [bold]{tool['name']}[/bold] → {full}", style="yellow"))
    try:
        with httpx.Client() as client:
            r = client.post(full, json={})
        console.print(f"[green]{r.status_code}[/green] {r.text}")
    except Exception as e:
        console.print(f"[red]ERROR[/red] calling {tool['name']}: {e}")

# ——— EXAMINE CACHE ———
def examine_cache(dirpath="rid_cache"):
    console.print(Panel(f"Inspecting cache: {dirpath}", style="blue"))
    if not os.path.isdir(dirpath):
        console.print("[yellow]Cache directory not found[/yellow]")
        return
    try:
        files = sorted(os.listdir(dirpath))
        if not files:
            console.print("[dim]Cache directory is empty[/dim]")
            return
        tbl = Table(title="Cache Files")
        tbl.add_column("File", style="cyan")
        tbl.add_column("Size", style="green", justify="right")
        for fn in files:
            try:
                size = os.path.getsize(os.path.join(dirpath, fn))
                tbl.add_row(fn, str(size))
            except OSError as e:
                tbl.add_row(fn, f"[red]Error: {e.strerror}[/red]")
        console.print(tbl)
    except OSError as e:
        console.print(f"[red]Error listing cache directory {dirpath}: {e.strerror}[/red]")

# ——— CLEANUP ———
_shutdown_initiated = False
def shutdown(signum=None, frame=None):
    global procs, _shutdown_initiated
    if _shutdown_initiated:
        return
    _shutdown_initiated = True
    if signum:
        sig_name = signal.Signals(signum).name
        console.print(f"\n[bold yellow]Received {sig_name}. Stopping services…[/bold yellow]")
    else:
        console.print("\n[bold yellow]Shutting down due to error or completion…[/bold yellow]")
    for p in reversed(procs):
        if p.poll() is None:
            console.print(f"[yellow]Terminating process {p.pid}...[/yellow]")
            try:
                if sys.platform != "win32":
                    os.killpg(os.getpgid(p.pid), signal.SIGTERM)
                else:
                    p.terminate()
                p.wait(5)
                if p.poll() is None:
                    console.print(f"[red]Process {p.pid} did not terminate gracefully, killing...[/red]")
                    if sys.platform != "win32":
                        os.killpg(os.getpgid(p.pid), signal.SIGKILL)
                    else:
                        p.kill()
                    p.wait(2)
            except ProcessLookupError:
                console.print(f"[dim]Process {p.pid} already exited.[/dim]")
            except Exception as e:
                console.print(f"[red]Error during termination of {p.pid}: {e}[/red]")
        else:
            console.print(f"[dim]Process {p.pid} already finished.[/dim]")
    for p in procs:
        if p.stdout:
            try: p.stdout.close()
            except: pass
        if p.stderr:
            try: p.stderr.close()
            except: pass
    console.print("[bold green]Shutdown complete[/bold green]")
    if signum:
        sys.exit(0)

# ——— MAIN ———
def main():
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)
    try:
        global procs
        procs = []
        start("Coordinator", COORD_CMD, "blue")
        if not wait_for(COORD_URL,   "/resources/list"): return
        start("Agent 1",  AGENT1_CMD,  "green")
        if not wait_for(AGENT1_URL,  "/resources/list"): return
        start("Agent 2",  AGENT2_CMD,  "magenta")
        if not wait_for(AGENT2_URL,  "/resources/list"): return
        console.print("[cyan]Waiting for coordinator to discover agents...[/cyan]")
        time.sleep(2)
        if not wait_for(COORD_URL, "/resources/list", timeout=10):
            console.print("[yellow]Coordinator might not have discovered all agents yet.[/yellow]")
        console.print("\n[bold]--- Network State ---[/bold]")
        show_resources(COORD_URL)
        show_tools(COORD_URL)
        show_resources(AGENT1_URL)
        show_tools(AGENT1_URL)
        show_resources(AGENT2_URL)
        show_tools(AGENT2_URL)
        console.print("[bold]---------------------[/bold]\n")
        tools1 = show_tools(AGENT1_URL)
        if tools1:
            invoke_trait(AGENT1_URL, tools1[0])
        tools2 = show_tools(AGENT2_URL)
        if tools2:
            invoke_trait(AGENT2_URL, tools2[0])
        examine_cache()
        console.print("\n[bold yellow]Demo running. Ctrl+C or kill to exit.[/bold yellow]")
        while True:
            for p in procs:
                if p.poll() is not None:
                    console.print(f"[bold red]Process {p.pid} exited unexpectedly with code {p.returncode}. Shutting down.[/bold red]")
                    shutdown()
                    return
            time.sleep(1)
    except Exception as e:
        console.print(f"\n[bold red]An unexpected error occurred in the main demo script: {e}[/bold red]")
    finally:
        if not _shutdown_initiated:
            shutdown()

if __name__ == "__main__":
    main()