"""
SYJ ONE — Shared Utilities
"""

import os
import re
import sys
import sqlite3
import socket
import ssl
import datetime
from pathlib import Path
from typing import Optional

import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

SYJ_HOME   = Path.home() / ".syj-one"
DATA_DIR   = SYJ_HOME / "data"
BACKUP_DIR = SYJ_HOME / "backups"
INVOICE_DIR= SYJ_HOME / "invoices"
EXPORT_DIR = SYJ_HOME / "exports"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 12; SM-G991B) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/112.0.0.0 Mobile Safari/537.36"
    )
}


# ── HTTP ──────────────────────────────────────────────────────────────────────

def fetch(url: str, timeout: int = 15, allow_redirects: bool = True) -> Optional[requests.Response]:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=allow_redirects)
        return resp
    except requests.exceptions.SSLError:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout,
                                allow_redirects=allow_redirects, verify=False)
            return resp
        except Exception as e:
            console.print(f"[red]HTTP error:[/red] {e}")
            return None
    except Exception as e:
        console.print(f"[red]HTTP error:[/red] {e}")
        return None


def clean_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def extract_domain(url: str) -> str:
    url = clean_url(url)
    m = re.match(r"https?://([^/]+)", url)
    return m.group(1) if m else url


# ── SSL ───────────────────────────────────────────────────────────────────────

def ssl_cert_info(hostname: str) -> dict:
    hostname = re.sub(r"https?://", "", hostname).split("/")[0]
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(
            socket.create_connection((hostname, 443), timeout=10),
            server_hostname=hostname
        ) as ssock:
            cert = ssock.getpeercert()

        expiry_str = cert.get("notAfter", "")
        expiry = datetime.datetime.strptime(expiry_str, "%b %d %H:%M:%S %Y %Z") if expiry_str else None
        days_left = (expiry - datetime.datetime.utcnow()).days if expiry else None

        subject = dict(x[0] for x in cert.get("subject", []))
        issuer  = dict(x[0] for x in cert.get("issuer", []))

        return {
            "valid": True,
            "subject": subject.get("commonName", ""),
            "issuer": issuer.get("organizationName", ""),
            "not_before": cert.get("notBefore", ""),
            "not_after": expiry_str,
            "days_left": days_left,
            "san": [v for _, v in cert.get("subjectAltName", [])],
        }
    except ssl.SSLCertVerificationError as e:
        return {"valid": False, "error": f"Cert verification failed: {e}"}
    except Exception as e:
        return {"valid": False, "error": str(e)}


# ── Database ──────────────────────────────────────────────────────────────────

def get_db(db_name: str = "syj_one.db") -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db_path = DATA_DIR / db_name
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


# ── Spinner ───────────────────────────────────────────────────────────────────

def spinner(message: str):
    """Context manager: with spinner('Checking...')"""
    return Progress(
        SpinnerColumn(style="cyan"),
        TextColumn("[cyan]{task.description}[/cyan]"),
        transient=True,
        console=console,
    )


# ── Display helpers ───────────────────────────────────────────────────────────

def section(title: str, color: str = "cyan") -> None:
    console.print()
    console.rule(f"[bold {color}]{title}[/bold {color}]", style=color)
    console.print()


def success(msg: str) -> None:
    console.print(f"[bold green]✅ {msg}[/bold green]")


def error(msg: str) -> None:
    console.print(f"[bold red]❌ {msg}[/bold red]")


def warn(msg: str) -> None:
    console.print(f"[yellow]⚠️  {msg}[/yellow]")


def info(msg: str) -> None:
    console.print(f"[cyan]ℹ  {msg}[/cyan]")


def badge(label: str, value: str, color: str = "white") -> str:
    return f"[dim]{label}:[/dim] [{color}]{value}[/{color}]"


# ── File / Path ───────────────────────────────────────────────────────────────

def ensure_dirs() -> None:
    for d in [DATA_DIR, BACKUP_DIR, INVOICE_DIR, EXPORT_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def now_str() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
