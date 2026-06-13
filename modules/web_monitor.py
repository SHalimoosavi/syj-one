"""
SYJ ONE — Web Monitor  (syj monitor)
Uptime checks, SSL expiry alerts, response time, site status dashboard.
"""

import datetime
import json
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box

from core.utils import (
    fetch, extract_domain, ssl_cert_info,
    get_db, section, success, error, warn, info, now_str
)

console = Console()

TOOLS = {
    "1": ("📡", "Check Site Now",        "check_one"),
    "2": ("📊", "Dashboard (all sites)", "dashboard"),
    "3": ("➕", "Add Site to Monitor",   "add_site"),
    "4": ("📋", "List Monitored Sites",  "list_sites"),
    "5": ("🗑️", "Remove Site",           "remove_site"),
    "6": ("🔒", "SSL Expiry Report",     "ssl_report"),
    "7": ("⚡", "Bulk Check All",        "bulk_check"),
}


# ── Database ──────────────────────────────────────────────────────────────────

def _init_db():
    conn = get_db("monitor.db")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT UNIQUE NOT NULL,
            name TEXT,
            added_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            site_id INTEGER,
            url TEXT,
            status_code INTEGER,
            response_time REAL,
            ssl_days_left INTEGER,
            is_up INTEGER,
            checked_at TEXT DEFAULT CURRENT_TIMESTAMP,
            error_msg TEXT,
            FOREIGN KEY (site_id) REFERENCES sites(id)
        );
    """)
    conn.commit()
    return conn


# ── Core check ────────────────────────────────────────────────────────────────

def _check_site(url: str, store: bool = True, site_id: int = None) -> dict:
    if not url.startswith("http"):
        url = "https://" + url

    result = {
        "url":           url,
        "is_up":         False,
        "status_code":   None,
        "response_time": None,
        "ssl_days_left": None,
        "error":         None,
        "checked_at":    now_str(),
    }

    # HTTP check
    try:
        t0   = time.time()
        resp = fetch(url, timeout=10)
        rt   = round(time.time() - t0, 3)

        if resp:
            result["is_up"]         = resp.status_code < 500
            result["status_code"]   = resp.status_code
            result["response_time"] = rt
        else:
            result["error"] = "No response"
    except Exception as e:
        result["error"] = str(e)

    # SSL check
    domain = extract_domain(url)
    try:
        ssl_info = ssl_cert_info(domain)
        if ssl_info.get("valid"):
            result["ssl_days_left"] = ssl_info.get("days_left")
    except Exception:
        pass

    # Store result
    if store:
        try:
            conn = _init_db()
            conn.execute("""
                INSERT INTO checks
                  (site_id, url, status_code, response_time, ssl_days_left, is_up, error_msg)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (site_id, url,
                  result["status_code"],
                  result["response_time"],
                  result["ssl_days_left"],
                  1 if result["is_up"] else 0,
                  result["error"]))
            conn.commit()
        except Exception:
            pass

    return result


def _render_result(r: dict) -> None:
    url  = r["url"]
    up   = r["is_up"]
    code = r["status_code"]
    rt   = r["response_time"]
    ssl  = r["ssl_days_left"]
    err  = r.get("error", "")

    status_str = "[bold green]✅ UP[/bold green]" if up else "[bold red]❌ DOWN[/bold red]"
    code_str   = f"[cyan]{code}[/cyan]" if code else "[dim]—[/dim]"
    rt_str     = f"[{'green' if rt and rt<1 else 'yellow' if rt and rt<3 else 'red'}]{rt}s[/]" if rt else "[dim]—[/dim]"

    if ssl is None:
        ssl_str = "[dim]—[/dim]"
    elif ssl > 30:
        ssl_str = f"[green]{ssl}d[/green]"
    elif ssl > 7:
        ssl_str = f"[yellow]{ssl}d ⚠[/yellow]"
    else:
        ssl_str = f"[bold red]{ssl}d 🚨[/bold red]"

    console.print(f"  {status_str}  {url}")
    console.print(f"  HTTP: {code_str}  ·  Response: {rt_str}  ·  SSL: {ssl_str}")
    if err and not up:
        console.print(f"  [dim]Error: {err}[/dim]")
    console.print()


# ── Tools ─────────────────────────────────────────────────────────────────────

def _check_one() -> None:
    section("📡 CHECK SITE")
    url = Prompt.ask("Enter URL or domain")
    if not url:
        return
    with console.status(f"[cyan]Checking {url}...[/cyan]"):
        result = _check_site(url, store=False)
    _render_result(result)

    domain = extract_domain(url)
    # Additional info
    ssl_info = ssl_cert_info(domain)
    if ssl_info.get("valid"):
        table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
        table.add_column("Field", style="dim",   width=20)
        table.add_column("Value", style="white")
        table.add_row("SSL Issuer",   ssl_info.get("issuer", ""))
        table.add_row("SSL Subject",  ssl_info.get("subject", ""))
        table.add_row("Expires",      ssl_info.get("not_after", ""))
        table.add_row("Days Left",    str(ssl_info.get("days_left", "—")))
        console.print(table)


def _add_site() -> None:
    section("➕ ADD SITE TO MONITOR")
    url  = Prompt.ask("URL or domain to monitor")
    name = Prompt.ask("Friendly name", default=extract_domain(url))

    if not url.startswith("http"):
        url = "https://" + url

    conn = _init_db()
    try:
        conn.execute("INSERT INTO sites (url, name) VALUES (?, ?)", (url, name))
        conn.commit()
        success(f"Added: {name} ({url})")
    except Exception as e:
        if "UNIQUE" in str(e):
            warn(f"{url} is already in the monitor list.")
        else:
            error(str(e))


def _list_sites() -> None:
    section("📋 MONITORED SITES")
    conn  = _init_db()
    sites = conn.execute("SELECT * FROM sites ORDER BY name").fetchall()

    if not sites:
        info("No sites monitored yet. Use option [3] to add one.")
        return

    table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
    table.add_column("ID",   style="dim",       width=4)
    table.add_column("Name", style="bold cyan", width=22)
    table.add_column("URL",  style="white",     width=40)
    table.add_column("Added",style="dim",       width=12)

    for s in sites:
        table.add_row(str(s["id"]), s["name"], s["url"], s["added_at"][:10])

    console.print(table)
    console.print(f"\n  [dim]{len(sites)} sites monitored[/dim]")


def _remove_site() -> None:
    section("🗑️ REMOVE SITE")
    conn  = _init_db()
    sites = conn.execute("SELECT * FROM sites ORDER BY name").fetchall()
    if not sites:
        info("No sites to remove.")
        return

    for s in sites:
        console.print(f"  [{s['id']}] {s['name']}  —  {s['url']}")
    console.print()

    choice = Prompt.ask("Enter site ID to remove")
    try:
        site_id = int(choice)
    except ValueError:
        error("Invalid ID.")
        return

    site = conn.execute("SELECT * FROM sites WHERE id=?", (site_id,)).fetchone()
    if not site:
        error("Site not found.")
        return

    if Confirm.ask(f"Remove [bold red]{site['name']}[/bold red]?", default=False):
        conn.execute("DELETE FROM sites WHERE id=?", (site_id,))
        conn.execute("DELETE FROM checks WHERE site_id=?", (site_id,))
        conn.commit()
        success(f"Removed: {site['name']}")
    else:
        info("Cancelled.")


def _ssl_report() -> None:
    section("🔒 SSL EXPIRY REPORT")
    conn  = _init_db()
    sites = conn.execute("SELECT * FROM sites").fetchall()

    if not sites:
        info("No sites monitored. Add sites first.")
        return

    table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
    table.add_column("Site",      style="bold white", width=25)
    table.add_column("Domain",    style="cyan",       width=30)
    table.add_column("Expires",   style="white",      width=22)
    table.add_column("Days Left", style="white",      width=12)
    table.add_column("Issuer",    style="dim",        width=25)

    for s in sites:
        domain = extract_domain(s["url"])
        with console.status(f"[cyan]Checking SSL for {domain}...[/cyan]"):
            ssl_info = ssl_cert_info(domain)

        if ssl_info.get("valid"):
            days = ssl_info.get("days_left")
            if days is None:
                days_str = "[dim]—[/dim]"
            elif days > 30:
                days_str = f"[green]{days}[/green]"
            elif days > 7:
                days_str = f"[yellow]{days} ⚠[/yellow]"
            else:
                days_str = f"[bold red]{days} 🚨[/bold red]"

            table.add_row(
                s["name"],
                domain,
                ssl_info.get("not_after", "")[:24],
                days_str,
                ssl_info.get("issuer", "")[:25],
            )
        else:
            table.add_row(s["name"], domain, "[red]SSL Error[/red]",
                          "[red]—[/red]", ssl_info.get("error", "")[:25])

    console.print(table)


def _bulk_check() -> None:
    section("⚡ BULK CHECK — ALL SITES")
    conn  = _init_db()
    sites = conn.execute("SELECT * FROM sites").fetchall()

    if not sites:
        info("No sites to check. Add sites first.")
        return

    console.print(f"  Checking [cyan]{len(sites)}[/cyan] sites...\n")

    results = []
    for s in sites:
        with console.status(f"[cyan]Checking {s['name']}...[/cyan]"):
            r = _check_site(s["url"], store=True, site_id=s["id"])
        results.append((s["name"], r))

    # Summary table
    table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
    table.add_column("Site",     style="bold white",  width=22)
    table.add_column("Status",   style="white",       width=10)
    table.add_column("HTTP",     style="cyan",        width=6,  justify="right")
    table.add_column("Time",     style="white",       width=8,  justify="right")
    table.add_column("SSL",      style="white",       width=8,  justify="right")

    up_count = 0
    for name, r in results:
        status = "[green]UP[/green]" if r["is_up"] else "[red]DOWN[/red]"
        code   = str(r["status_code"]) if r["status_code"] else "—"
        rt     = f"{r['response_time']}s" if r["response_time"] else "—"
        ssl    = f"{r['ssl_days_left']}d" if r["ssl_days_left"] is not None else "—"
        if r["is_up"]:
            up_count += 1
        table.add_row(name, status, code, rt, ssl)

    console.print(table)
    down = len(results) - up_count
    console.print(f"\n  [green]Up: {up_count}[/green]  [red]Down: {down}[/red]  [dim]Total: {len(results)}[/dim]")
    console.print(f"  [dim]Checked at: {now_str()}[/dim]")


def _dashboard() -> None:
    section("📊 MONITOR DASHBOARD")
    conn  = _init_db()
    sites = conn.execute("SELECT * FROM sites").fetchall()

    if not sites:
        info("No sites configured. Add sites with option [3].")
        return

    for s in sites:
        # Get last check
        last = conn.execute(
            "SELECT * FROM checks WHERE site_id=? ORDER BY checked_at DESC LIMIT 1",
            (s["id"],)
        ).fetchone()

        # Uptime from last 10 checks
        checks = conn.execute(
            "SELECT is_up FROM checks WHERE site_id=? ORDER BY checked_at DESC LIMIT 10",
            (s["id"],)
        ).fetchall()
        uptime = (sum(c["is_up"] for c in checks) / len(checks) * 100) if checks else None

        console.print(f"  [bold cyan]{s['name']}[/bold cyan]  [dim]{s['url']}[/dim]")
        if last:
            status = "[green]✅ UP[/green]" if last["is_up"] else "[red]❌ DOWN[/red]"
            rt     = f"{last['response_time']}s" if last["response_time"] else "—"
            ssl    = f"[green]{last['ssl_days_left']}d[/green]" if last["ssl_days_left"] and last["ssl_days_left"] > 30 \
                     else f"[yellow]{last['ssl_days_left']}d[/yellow]" if last["ssl_days_left"] and last["ssl_days_left"] > 7 \
                     else f"[red]{last['ssl_days_left']}d[/red]" if last["ssl_days_left"] else "[dim]—[/dim]"
            up_str = f"[green]{uptime:.0f}%[/green]" if uptime and uptime >= 90 \
                     else f"[yellow]{uptime:.0f}%[/yellow]" if uptime else "[dim]—[/dim]"
            console.print(f"  {status}  HTTP {last['status_code']}  ·  {rt}  ·  SSL: {ssl}  ·  Uptime: {up_str}")
            console.print(f"  [dim]Last checked: {last['checked_at']}[/dim]")
        else:
            console.print("  [dim]Not checked yet — run Bulk Check[/dim]")
        console.print()


# ── Main ──────────────────────────────────────────────────────────────────────

def run(args=None) -> None:
    args = args or []

    # Quick inline check: syj monitor example.com
    if args and not args[0].startswith("-"):
        url = args[0]
        with console.status(f"[cyan]Checking {url}...[/cyan]"):
            result = _check_site(url, store=False)
        _render_result(result)
        return

    console.print(Panel(
        "[bold cyan]📡 WEB MONITOR[/bold cyan]",
        border_style="cyan"
    ))

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("num",  style="bold green", width=4)
    table.add_column("icon", width=3)
    table.add_column("name", style="white")
    for num, (icon, name, _) in TOOLS.items():
        table.add_row(f"[{num}]", icon, name)
    console.print(table)
    console.print()

    choice = Prompt.ask("[bold green]Select tool[/bold green]", default="2")
    _, _, key = TOOLS.get(choice, ("", "", "dashboard"))

    dispatch = {
        "check_one":   _check_one,
        "dashboard":   _dashboard,
        "add_site":    _add_site,
        "list_sites":  _list_sites,
        "remove_site": _remove_site,
        "ssl_report":  _ssl_report,
        "bulk_check":  _bulk_check,
    }
    fn = dispatch.get(key)
    if fn:
        fn()
    console.print()
