"""
SYJ ONE — Cyber Shield  (syj shield)
Defensive intelligence: DNS, WHOIS, SSL, security headers, ports, tech fingerprinting.
"""

import socket
import ssl
import subprocess
import datetime
import re
import json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich import box

from core.utils import fetch, extract_domain, ssl_cert_info, section, success, error, warn, info

console = Console()

# ── Sub-tools ─────────────────────────────────────────────────────────────────

TOOLS = {
    "1": ("🌐", "Full Scan",          "full"),
    "2": ("📡", "DNS Lookup",         "dns"),
    "3": ("📋", "WHOIS Lookup",       "whois"),
    "4": ("🔒", "SSL Certificate",    "ssl"),
    "5": ("🛡️", "Security Headers",   "headers"),
    "6": ("🔌", "Port Scan",          "ports"),
    "7": ("🔎", "Tech Detection",     "tech"),
}

COMMON_PORTS = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP",
    53: "DNS", 80: "HTTP", 110: "POP3", 143: "IMAP",
    443: "HTTPS", 465: "SMTPS", 587: "SMTP-TLS",
    993: "IMAPS", 995: "POP3S", 3306: "MySQL",
    5432: "PostgreSQL", 6379: "Redis", 8080: "HTTP-Alt",
    8443: "HTTPS-Alt", 27017: "MongoDB",
}

SECURITY_HEADERS = [
    "Strict-Transport-Security",
    "Content-Security-Policy",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Referrer-Policy",
    "Permissions-Policy",
    "X-XSS-Protection",
    "Cross-Origin-Embedder-Policy",
    "Cross-Origin-Opener-Policy",
]


# ── DNS ───────────────────────────────────────────────────────────────────────

def _dns_lookup(domain: str) -> dict:
    results = {}
    try:
        import dns.resolver
        for rtype in ("A", "AAAA", "MX", "NS", "TXT", "CNAME"):
            try:
                answers = dns.resolver.resolve(domain, rtype, lifetime=5)
                records = []
                for r in answers:
                    if rtype == "MX":
                        records.append(f"{r.preference} {r.exchange}")
                    else:
                        records.append(str(r))
                results[rtype] = records
            except Exception:
                pass
    except ImportError:
        # Fallback: socket-based A record
        try:
            ip = socket.gethostbyname(domain)
            results["A"] = [ip]
        except Exception:
            results["error"] = "dnspython not installed; only A record via socket"
    return results


def _print_dns(domain: str) -> None:
    section("📡 DNS LOOKUP")
    console.print(f"  [dim]Domain:[/dim] [cyan]{domain}[/cyan]\n")

    with console.status("[cyan]Resolving DNS records...[/cyan]"):
        records = _dns_lookup(domain)

    if "error" in records:
        warn(records["error"])

    table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
    table.add_column("Type",   style="bold cyan", width=8)
    table.add_column("Value",  style="white")

    for rtype, values in records.items():
        if rtype == "error":
            continue
        for v in values:
            table.add_row(rtype, v)

    if records:
        console.print(table)
    else:
        warn("No DNS records found.")


# ── WHOIS ─────────────────────────────────────────────────────────────────────

def _whois_lookup(domain: str) -> str:
    # Try system whois command first
    try:
        result = subprocess.run(
            ["whois", domain],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: WHOIS API
    try:
        resp = fetch(f"https://api.whois.vu/?q={domain}", timeout=10)
        if resp and resp.status_code == 200:
            return resp.text[:2000]
    except Exception:
        pass

    return ""


def _print_whois(domain: str) -> None:
    section("📋 WHOIS LOOKUP")
    console.print(f"  [dim]Domain:[/dim] [cyan]{domain}[/cyan]\n")

    with console.status("[cyan]Fetching WHOIS data...[/cyan]"):
        data = _whois_lookup(domain)

    if not data:
        warn("WHOIS lookup failed. Install 'whois': pkg install whois")
        return

    # Print relevant lines only
    important_keys = (
        "Domain Name", "Registrar", "Registrant", "Creation Date",
        "Updated Date", "Expiry Date", "Expiration Date",
        "Name Server", "Status", "DNSSEC", "Registrant Country",
        "Registry Domain ID",
    )
    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    table.add_column("Field", style="dim", width=25)
    table.add_column("Value", style="white")

    shown = set()
    for line in data.splitlines():
        for key in important_keys:
            if line.lower().startswith(key.lower() + ":") and key not in shown:
                value = line.split(":", 1)[-1].strip()
                if value:
                    table.add_row(key, value)
                    shown.add(key)

    if shown:
        console.print(table)
    else:
        # Print raw (trimmed)
        console.print(f"[dim]{data[:1000]}[/dim]")


# ── SSL ───────────────────────────────────────────────────────────────────────

def _print_ssl(domain: str) -> None:
    section("🔒 SSL CERTIFICATE")
    console.print(f"  [dim]Domain:[/dim] [cyan]{domain}[/cyan]\n")

    with console.status("[cyan]Inspecting SSL certificate...[/cyan]"):
        info_data = ssl_cert_info(domain)

    if not info_data.get("valid"):
        error(f"SSL check failed: {info_data.get('error', 'Unknown error')}")
        return

    days = info_data.get("days_left")
    if days is not None:
        if days > 30:
            days_str = f"[green]{days} days remaining[/green]"
        elif days > 7:
            days_str = f"[yellow]{days} days remaining[/yellow]"
        else:
            days_str = f"[bold red]{days} days remaining — EXPIRING SOON![/bold red]"
    else:
        days_str = "[dim]unknown[/dim]"

    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    table.add_column("Field", style="dim", width=20)
    table.add_column("Value", style="white")
    table.add_row("Subject / CN",  info_data.get("subject", ""))
    table.add_row("Issuer",        info_data.get("issuer", ""))
    table.add_row("Valid From",    info_data.get("not_before", ""))
    table.add_row("Expires",       info_data.get("not_after", ""))
    table.add_row("Days Left",     days_str)

    san = info_data.get("san", [])
    if san:
        table.add_row("SAN",  ", ".join(san[:5]) + ("…" if len(san) > 5 else ""))

    console.print(table)


# ── Security Headers ──────────────────────────────────────────────────────────

def _print_headers(url: str) -> None:
    section("🛡️ SECURITY HEADERS")
    if not url.startswith("http"):
        url = "https://" + url
    console.print(f"  [dim]URL:[/dim] [cyan]{url}[/cyan]\n")

    with console.status("[cyan]Fetching HTTP headers...[/cyan]"):
        resp = fetch(url)

    if not resp:
        error("Could not fetch URL.")
        return

    # All response headers
    console.print("[bold]Response Headers:[/bold]")
    all_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    all_table.add_column("Header", style="dim", width=35)
    all_table.add_column("Value",  style="white")
    for k, v in resp.headers.items():
        all_table.add_row(k, v[:100])
    console.print(all_table)
    console.print()

    # Security-specific check
    console.print("[bold]Security Header Analysis:[/bold]")
    sec_table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    sec_table.add_column("Status", width=4)
    sec_table.add_column("Header", style="white", width=35)
    sec_table.add_column("Value",  style="dim")

    for header in SECURITY_HEADERS:
        value = resp.headers.get(header, "")
        status = "[green]✓[/green]" if value else "[red]✗[/red]"
        sec_table.add_row(status, header, value[:70] if value else "[red]MISSING[/red]")

    console.print(sec_table)

    present = sum(1 for h in SECURITY_HEADERS if resp.headers.get(h))
    total   = len(SECURITY_HEADERS)
    score   = int(present / total * 100)
    console.print(f"\n  Security Header Score: [{'green' if score>=70 else 'yellow' if score>=40 else 'red'}]{score}%[/] ({present}/{total} headers set)")


# ── Port Scan ─────────────────────────────────────────────────────────────────

def _port_scan(hostname: str, timeout: float = 1.0) -> dict:
    results = {}
    for port, service in COMMON_PORTS.items():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((hostname, port))
            sock.close()
            results[port] = {"service": service, "open": result == 0}
        except Exception:
            results[port] = {"service": service, "open": False}
    return results


def _print_ports(domain: str) -> None:
    section("🔌 PORT SCAN")
    console.print(f"  [dim]Target:[/dim] [cyan]{domain}[/cyan]")
    console.print(f"  [dim]Checking {len(COMMON_PORTS)} common ports...[/dim]\n")

    with console.status("[cyan]Scanning ports (this may take ~30s)...[/cyan]"):
        results = _port_scan(domain)

    open_ports   = {p: v for p, v in results.items() if v["open"]}
    closed_ports = {p: v for p, v in results.items() if not v["open"]}

    table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
    table.add_column("Port",    style="bold", width=8)
    table.add_column("Service", style="cyan", width=15)
    table.add_column("Status",  width=10)

    for port in sorted(results.keys()):
        v = results[port]
        status = "[bold green]OPEN[/bold green]" if v["open"] else "[dim]closed[/dim]"
        table.add_row(str(port), v["service"], status)

    console.print(table)
    console.print(f"\n  [green]Open: {len(open_ports)}[/green]  [dim]Closed: {len(closed_ports)}[/dim]")

    if open_ports:
        warnings = []
        for p in open_ports:
            if p in (21, 23):
                warnings.append(f"Port {p} ({COMMON_PORTS[p]}) is OPEN — consider disabling if not needed")
        for w in warnings:
            warn(w)


# ── Tech Detection ────────────────────────────────────────────────────────────

TECH_SIGNATURES = {
    "WordPress":   (["wp-content", "wp-json", "wp-includes"], "X-Powered-By"),
    "Shopify":     (["cdn.shopify.com", "myshopify.com"], "X-Shopify-Stage"),
    "Wix":         (["wix.com", "static.wixstatic"], "X-Wix-Server-Artifact"),
    "React":       (["react", "_next/static", "react-dom"], ""),
    "Next.js":     (["_next/", "__nextjs"], "X-Powered-By"),
    "Vue.js":      (["vue", "__vue"], ""),
    "Angular":     (["ng-version", "angular"], ""),
    "Bootstrap":   (["bootstrap.min.css", "bootstrap.min.js"], ""),
    "jQuery":      (["jquery.min.js", "jquery.js"], ""),
    "Cloudflare":  ([], "CF-Cache-Status"),
    "Nginx":       ([], "Server"),
    "Apache":      ([], "Server"),
    "PHP":         ([], "X-Powered-By"),
    "Node.js":     ([], "X-Powered-By"),
    "Django":      (["csrfmiddlewaretoken", "django"], "X-Frame-Options"),
    "Laravel":     (["laravel_session", "_token"], ""),
}

def _detect_tech(url: str) -> list:
    if not url.startswith("http"):
        url = "https://" + url
    resp = fetch(url)
    if not resp:
        return []

    html    = resp.text.lower()
    headers = {k.lower(): v.lower() for k, v in resp.headers.items()}
    detected = []

    for tech, (html_sigs, header_name) in TECH_SIGNATURES.items():
        found = False
        for sig in html_sigs:
            if sig.lower() in html:
                found = True
                break
        if not found and header_name:
            hval = headers.get(header_name.lower(), "")
            if tech.lower() in hval.lower():
                found = True
            elif header_name.lower() == "server" and tech.lower() in hval:
                found = True
        if found:
            detected.append(tech)

    return detected


def _print_tech(url: str) -> None:
    section("🔎 TECHNOLOGY DETECTION")
    console.print(f"  [dim]URL:[/dim] [cyan]{url}[/cyan]\n")

    with console.status("[cyan]Fingerprinting technologies...[/cyan]"):
        techs = _detect_tech(url)

    if techs:
        for t in techs:
            console.print(f"  [green]✓[/green] [bold]{t}[/bold]")
    else:
        console.print("  [dim]No common technologies detected.[/dim]")


# ── Full Scan ─────────────────────────────────────────────────────────────────

def full_scan(target: str) -> None:
    domain = extract_domain(target)
    url    = f"https://{domain}"

    console.print(Panel(
        f"[bold cyan]🛡️  CYBER SHIELD — FULL SCAN[/bold cyan]\n[dim]Target:[/dim] [white]{domain}[/white]",
        border_style="cyan"
    ))

    _print_dns(domain)
    _print_ssl(domain)
    _print_headers(url)
    _print_tech(url)


# ── Menu ──────────────────────────────────────────────────────────────────────

def run(args=None) -> None:
    """syj shield [target] [--dns|--whois|--ssl|--headers|--ports|--tech]"""
    args = args or []

    # Flags
    flags = {f[2:] for f in args if f.startswith("--")}
    targets = [a for a in args if not a.startswith("-")]

    if targets:
        target = targets[0]
    else:
        target = Prompt.ask("[bold green]Enter target (domain or URL)[/bold green]", default="example.com")

    domain = extract_domain(target)
    url    = f"https://{domain}"

    if not flags:
        # Show menu
        console.print(Panel(
            "[bold cyan]🛡️  CYBER SHIELD[/bold cyan]",
            border_style="cyan"
        ))
        console.print()
        from rich.table import Table
        t = Table(show_header=False, box=None, padding=(0, 2))
        t.add_column("num", style="bold green", width=4)
        t.add_column("icon", width=3)
        t.add_column("name", style="white")
        for num, (icon, name, _) in TOOLS.items():
            t.add_row(f"[{num}]", icon, name)
        console.print(t)
        console.print()
        choice = Prompt.ask("[bold green]Select tool[/bold green]", default="1")
        _, _, tool_key = TOOLS.get(choice, ("", "", "full"))
        flags = {tool_key}

    tool = next(iter(flags), "full")

    if tool == "full":    full_scan(target)
    elif tool == "dns":   _print_dns(domain)
    elif tool == "whois": _print_whois(domain)
    elif tool == "ssl":   _print_ssl(domain)
    elif tool == "headers": _print_headers(url)
    elif tool == "ports": _print_ports(domain)
    elif tool == "tech":  _print_tech(url)
    else:
        full_scan(target)

    console.print()
