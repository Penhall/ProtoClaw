import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()
console = Console()


@click.group()
def cli():
    """ProtoClaw — Intelligent Agent Factory\n\nDeploy focused AI agents from a mission string."""
    pass


@cli.command()
@click.argument("mission")
def deploy(mission: str):
    """Deploy a new agent from a mission description.

    Example: protoclaw deploy "Pesquisar tendências de IA no Reddit nos últimos 30 dias"
    """
    from protoclaw.orchestrator.graph import build_graph

    initial_state = {
        "mission": mission,
        "subtasks": [],
        "guardrails": [],
        "framework": None,
        "generated_files": {},
        "workspace_dir": "",
        "container_id": "",
        "error": None,
    }

    with console.status("[bold green]Deploying agent...[/bold green]"):
        graph = build_graph()
        result = graph.invoke(initial_state)

    if result.get("error"):
        console.print(f"[bold red]Error:[/bold red] {result['error']}")
        raise SystemExit(1)

    console.print(result.get("report", "Agent deployed."))


@cli.command(name="list")
def list_agents():
    """List all running ProtoClaw agents."""
    from protoclaw.deployer.docker import list_agents as _list

    agents = _list()
    if not agents:
        console.print("[yellow]No agents running.[/yellow]")
        return

    table = Table(title="Running Agents")
    table.add_column("Name", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("ID", style="dim")
    for agent in agents:
        table.add_row(agent["name"], agent["status"], agent["id"])
    console.print(table)


@cli.command()
@click.argument("name")
def logs(name: str):
    """Tail logs for an agent container."""
    from protoclaw.deployer.docker import get_logs
    console.print(get_logs(name))


@cli.command()
@click.argument("name")
def stop(name: str):
    """Stop and remove an agent container."""
    from protoclaw.deployer.docker import stop_agent
    stop_agent(name)
    console.print(f"[green]✓[/green] Agent [cyan]{name}[/cyan] stopped and removed.")


@cli.command()
@click.argument("name")
def status(name: str):
    """Show status of an agent container."""
    from protoclaw.deployer.docker import list_agents
    agents = {a["name"]: a for a in list_agents()}
    if name not in agents:
        console.print(f"[yellow]Agent '{name}' not found.[/yellow]")
        raise SystemExit(1)
    agent = agents[name]
    console.print(f"  Name   : {agent['name']}")
    console.print(f"  Status : [green]{agent['status']}[/green]")
    console.print(f"  ID     : {agent['id']}")
