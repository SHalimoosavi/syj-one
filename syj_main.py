#!/usr/bin/env python3
"""
SYJ ONE — Main Entry Point
The Ultimate Mobile Productivity & Security Platform for Termux
by Sayanjali Nexus | github.com/SHalimoosavi | shalimoosavi@gmail.com
"""

import sys
import os

# ── Ensure project root on sys.path ───────────────────────────────────────────
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── Dependency check (graceful) ───────────────────────────────────────────────
def _check_deps():
    missing = []
    for pkg in ("rich", "requests"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[!] Missing packages: {', '.join(missing)}")
        print(f"    Run: pip install {' '.join(missing)}")
        sys.exit(1)

_check_deps()

from rich.console import Console
from core.banner import print_banner, print_menu

console = Console()

# ── Module router ─────────────────────────────────────────────────────────────

COMMANDS = {
    "ai":       ("modules.ai_workspace",  "run", "🤖 AI Workspace"),
    "seo":      ("modules.seo_intel",     "run", "🔍 SEO Intelligence"),
    "shield":   ("modules.cyber_shield",  "run", "🛡️  Cyber Shield"),
    "dev":      ("modules.dev_hub",       "run", "💻 Developer Hub"),
    "business": ("modules.business_suite","run", "💼 Business Suite"),
    "pdf":      ("modules.pdf_toolkit",   "run", "📄 PDF Toolkit"),
    "backup":   ("modules.backup_center", "run", "☁️  Backup Center"),
    "monitor":  ("modules.web_monitor",   "run", "📡 Web Monitor"),
    "config":   ("core.config",           "run", "⚙️  Settings"),
}

ALIASES = {
    "s":  "seo",
    "sh": "shield",
    "d":  "dev",
    "b":  "business",
    "p":  "pdf",
    "bk": "backup",
    "m":  "monitor",
    "c":  "config",
    "a":  "ai",
}

HELP_TEXT = """
[bold cyan]SYJ ONE[/bold cyan] — The Ultimate Mobile Productivity & Security Platform for Termux
[dim]by Sayanjali Nexus  ·  v1.0.0[/dim]

[bold]Usage:[/bold]  [green]syj [command] [options][/green]

[bold]Commands:[/bold]
  [green]ai[/green]         🤖  AI Workspace      — Chat, code, content, SEO advice
  [green]seo[/green]        🔍  SEO Intelligence  — On-page audit, meta, headings, score
  [green]shield[/green]     🛡️   Cyber Shield      — DNS, WHOIS, SSL, headers, ports
  [green]dev[/green]        💻  Developer Hub     — GitHub, scaffolding, git tools
  [green]business[/green]   💼  Business Suite    — Invoices, expenses, clients, GST
  [green]pdf[/green]        📄  PDF Toolkit       — Merge, split, convert, info
  [green]backup[/green]     ☁️   Backup Center     — Local & encrypted backups
  [green]monitor[/green]    📡  Web Monitor       — Uptime, SSL expiry, performance
  [green]config[/green]     ⚙️   Settings          — API keys, preferences

[bold]Quick usage:[/bold]
  [green]syj seo https://example.com[/green]
  [green]syj monitor example.com[/green]
  [green]syj shield --dns example.com[/green]
  [green]syj ai "explain this: print(x**2)"[/green]
  [green]syj config setup[/green]
  [green]syj config set api_keys.anthropic sk-ant-...[/green]

[bold]Aliases:[/bold]  a, s, sh, d, b, p, bk, m, c

[dim]GitHub: github.com/SHalimoosavi  ·  Email: shalimoosavi@gmail.com[/dim]
"""


def _dispatch(cmd: str, args: list) -> None:
    # Resolve alias
    cmd = ALIASES.get(cmd, cmd)

    if cmd not in COMMANDS:
        console.print(f"[red]Unknown command:[/red] [bold]{cmd}[/bold]")
        console.print(f"[dim]Run [bold green]syj --help[/bold green] for available commands.[/dim]")
        sys.exit(1)

    module_path, fn_name, label = COMMANDS[cmd]
    console.print(f"\n[dim]── {label} ──[/dim]\n")

    try:
        import importlib
        mod = importlib.import_module(module_path)
        fn  = getattr(mod, fn_name)
        fn(args)
    except KeyboardInterrupt:
        console.print("\n\n[dim]Interrupted. Goodbye.[/dim]")
    except ImportError as e:
        console.print(f"[red]Import error:[/red] {e}")
        console.print("[dim]Some packages may be missing. Run: pip install -r requirements.txt[/dim]")
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        if "--debug" in sys.argv:
            import traceback
            console.print_exception()


def main() -> None:
    argv = sys.argv[1:]

    # No args → interactive menu
    if not argv:
        print_banner()
        print_menu()
        return

    cmd  = argv[0].lstrip("-")
    rest = argv[1:]

    # Help
    if cmd in ("help", "h", "-h", "--help"):
        print_banner(compact=True)
        from rich.markdown import Markdown
        console.print(HELP_TEXT)
        return

    # Version
    if cmd in ("version", "v", "--version", "-v"):
        console.print("[bold cyan]SYJ ONE[/bold cyan] v1.0.0  ·  Sayanjali Nexus")
        return

    # Dispatch
    _dispatch(cmd, rest)


if __name__ == "__main__":
    main()
