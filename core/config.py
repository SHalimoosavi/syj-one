"""
SYJ ONE — Configuration Manager
Handles reading/writing settings and API keys from ~/.syj-one/config/settings.json
"""

import json
import os
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

console = Console()

# ── Paths ─────────────────────────────────────────────────────────────────────
SYJ_HOME   = Path.home() / ".syj-one"
CONFIG_DIR = SYJ_HOME / "config"
CONFIG_FILE = CONFIG_DIR / "settings.json"

# Fallback: config next to the script (for dev/portable use)
_SCRIPT_DIR = Path(__file__).resolve().parent.parent
_LOCAL_CONFIG = _SCRIPT_DIR / "config" / "settings.json"

DEFAULT_CONFIG: dict = {
    "version": "1.0.0",
    "user": {
        "name": "",
        "email": "",
        "company": "",
    },
    "api_keys": {
        "anthropic": "",
        "github": "",
    },
    "preferences": {
        "theme": "dark",
        "currency": "INR",
        "currency_symbol": "₹",
        "gst_rate": 18.0,
    },
    "monitoring": {
        "sites": [],
    },
}


def _resolve_config_path() -> Path:
    if CONFIG_FILE.exists():
        return CONFIG_FILE
    if _LOCAL_CONFIG.exists():
        return _LOCAL_CONFIG
    # Bootstrap
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2))
    return CONFIG_FILE


def load() -> dict:
    path = _resolve_config_path()
    try:
        data = json.loads(path.read_text())
        # Merge any missing default keys
        merged = _deep_merge(DEFAULT_CONFIG, data)
        return merged
    except Exception:
        return dict(DEFAULT_CONFIG)


def save(config: dict) -> None:
    path = _resolve_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2))


def get(key_path: str, default: Any = None) -> Any:
    """Get a value by dot-notation path, e.g. 'api_keys.anthropic'"""
    cfg = load()
    parts = key_path.split(".")
    node = cfg
    for part in parts:
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return default
    return node


def set_value(key_path: str, value: Any) -> None:
    """Set a value by dot-notation path and save."""
    cfg = load()
    parts = key_path.split(".")
    node = cfg
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value
    save(cfg)


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


# ── CLI ───────────────────────────────────────────────────────────────────────

def run(args=None) -> None:
    """syj config [setup|show|set key value]"""
    subcommand = args[0] if args else "show"

    if subcommand == "setup":
        _wizard()
    elif subcommand == "show":
        _show()
    elif subcommand == "set" and len(args) >= 3:
        key_path, value = args[1], args[2]
        set_value(key_path, value)
        console.print(f"[green]✓[/green] Set [bold]{key_path}[/bold] = [cyan]{value}[/cyan]")
    else:
        console.print("[yellow]Usage:[/yellow]  syj config setup")
        console.print("        syj config show")
        console.print("        syj config set api_keys.anthropic sk-ant-...")


def _show() -> None:
    cfg = load()
    # Redact keys
    display = json.loads(json.dumps(cfg))
    for k in display.get("api_keys", {}):
        v = display["api_keys"][k]
        if v:
            display["api_keys"][k] = v[:8] + "..." + v[-4:] if len(v) > 14 else "****"
        else:
            display["api_keys"][k] = "[dim]not set[/dim]"

    console.print(Panel(
        json.dumps(display, indent=2),
        title="[bold cyan]SYJ ONE — Configuration[/bold cyan]",
        border_style="cyan"
    ))
    config_path = _resolve_config_path()
    console.print(f"[dim]Config file: {config_path}[/dim]")


def _wizard() -> None:
    console.print(Panel(
        "[bold cyan]SYJ ONE — First-Time Setup Wizard[/bold cyan]\n"
        "[dim]Press Enter to skip any field[/dim]",
        border_style="cyan"
    ))

    cfg = load()

    # User info
    console.print("\n[bold]User Info[/bold]")
    name    = Prompt.ask("Your name",    default=cfg["user"]["name"]    or "")
    email   = Prompt.ask("Your email",   default=cfg["user"]["email"]   or "")
    company = Prompt.ask("Company name", default=cfg["user"]["company"] or "")

    cfg["user"]["name"]    = name
    cfg["user"]["email"]   = email
    cfg["user"]["company"] = company

    # API keys
    console.print("\n[bold]API Keys[/bold]")
    console.print("[dim]Get Anthropic key: https://console.anthropic.com[/dim]")
    ant_key = Prompt.ask("Anthropic API key", default=cfg["api_keys"]["anthropic"] or "", password=True)
    console.print("[dim]Get GitHub token: https://github.com/settings/tokens[/dim]")
    gh_key  = Prompt.ask("GitHub token",      default=cfg["api_keys"]["github"]    or "", password=True)

    if ant_key: cfg["api_keys"]["anthropic"] = ant_key
    if gh_key:  cfg["api_keys"]["github"]    = gh_key

    # Preferences
    console.print("\n[bold]Preferences[/bold]")
    currency = Prompt.ask("Currency code", default=cfg["preferences"]["currency"] or "INR")
    symbol   = Prompt.ask("Currency symbol", default=cfg["preferences"]["currency_symbol"] or "₹")
    gst_str  = Prompt.ask("Default GST rate (%)", default=str(cfg["preferences"]["gst_rate"]))
    try:
        gst = float(gst_str)
    except ValueError:
        gst = 18.0

    cfg["preferences"]["currency"]        = currency
    cfg["preferences"]["currency_symbol"] = symbol
    cfg["preferences"]["gst_rate"]        = gst

    save(cfg)
    console.print("\n[bold green]✅ Configuration saved![/bold green]")
    console.print(f"[dim]Location: {_resolve_config_path()}[/dim]\n")
