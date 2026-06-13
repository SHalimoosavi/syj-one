from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.align import Align

console = Console()

VERSION = "1.0.0"
AUTHOR  = "Sayanjali Nexus"
WEBSITE = "syj-token.com"

ASCII_ART = """[bold cyan]
  ███████╗██╗   ██╗     ██╗    ██████╗ ███╗   ██╗███████╗
  ██╔════╝╚██╗ ██╔╝     ██║   ██╔═══██╗████╗  ██║██╔════╝
  ███████╗ ╚████╔╝      ██║   ██║   ██║██╔██╗ ██║█████╗
  ╚════██║  ╚██╔╝       ██║   ██║   ██║██║╚██╗██║██╔══╝
  ███████║   ██║        ╚═╝   ╚██████╔╝██║ ╚████║███████╗
  ╚══════╝   ╚═╝               ╚═════╝ ╚═╝  ╚═══╝╚══════╝[/bold cyan]"""

TAGLINE = "[italic dim]The Ultimate Mobile Productivity & Security Platform for Termux[/italic dim]"

MENU_ITEMS = [
    ("ai",       "🤖", "AI Workspace",       "Chat, code, generate, summarize"),
    ("seo",      "🔍", "SEO Intelligence",   "Meta, sitemap, audits, keywords"),
    ("shield",   "🛡️", "Cyber Shield",       "DNS, WHOIS, SSL, headers, ports"),
    ("dev",      "💻", "Developer Hub",      "GitHub, scaffolding, git tools"),
    ("business", "💼", "Business Suite",     "Invoices, expenses, clients, GST"),
    ("pdf",      "📄", "PDF Toolkit",        "Merge, split, compress, convert"),
    ("backup",   "☁️", "Backup Center",      "Local & encrypted backups"),
    ("monitor",  "📡", "Web Monitor",        "Uptime, SSL expiry, performance"),
    ("config",   "⚙️", "Settings",           "API keys, preferences, setup"),
]

def print_banner(compact: bool = False) -> None:
    console.print(ASCII_ART)
    if not compact:
        console.print(Align.center(TAGLINE))
        console.print(Align.center(
            f"[dim]v{VERSION}  ·  {AUTHOR}  ·  {WEBSITE}[/dim]"
        ))
    console.print()

def print_menu() -> None:
    from rich.table import Table
    table = Table(
        show_header=False,
        box=None,
        padding=(0, 2),
        expand=False
    )
    table.add_column("cmd",  style="bold green",  width=12)
    table.add_column("icon", width=3)
    table.add_column("name", style="bold white",  width=22)
    table.add_column("desc", style="dim",         width=42)

    for cmd, icon, name, desc in MENU_ITEMS:
        table.add_row(f"syj {cmd}", icon, name, desc)

    panel = Panel(
        table,
        title="[bold cyan]MODULES[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(panel)
    console.print()
    console.print("  [dim]Usage:[/dim]  [bold green]syj [command][/bold green]   [dim]e.g.[/dim]  [green]syj ai[/green]  [dim]·[/dim]  [green]syj seo https://example.com[/green]")
    console.print("          [dim]Type[/dim] [bold green]syj [command] --help[/bold green] [dim]for module options[/dim]")
    console.print()
