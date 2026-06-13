"""
SYJ ONE — Backup Center  (syj backup)
Local backups with optional zip encryption.
"""

import os
import zipfile
import tarfile
import shutil
import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box

from core.utils import section, success, error, warn, info, BACKUP_DIR, timestamp

console = Console()

TOOLS = {
    "1": ("📦", "Backup a Directory",   "backup_dir"),
    "2": ("🔐", "Encrypted Backup",     "backup_enc"),
    "3": ("📋", "List Backups",         "list"),
    "4": ("♻️", "Restore Backup",       "restore"),
    "5": ("🗑️", "Delete Backup",        "delete"),
    "6": ("📊", "Backup Stats",         "stats"),
}


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1_000_000:
        return f"{size/1024:.1f} KB"
    if size < 1_000_000_000:
        return f"{size/1_000_000:.1f} MB"
    return f"{size/1_000_000_000:.2f} GB"


def _backup_dir(encrypted: bool = False) -> None:
    label = "🔐 ENCRYPTED BACKUP" if encrypted else "📦 BACKUP DIRECTORY"
    section(label)
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    source_str = Prompt.ask("Directory to backup", default=str(Path.home()))
    source = Path(source_str)
    if not source.exists():
        error(f"Directory not found: {source}")
        return

    name = Prompt.ask("Backup name", default=source.name)
    ts   = timestamp()
    zip_name = f"{name}_{ts}.zip"
    zip_path = BACKUP_DIR / zip_name

    if encrypted:
        password = Prompt.ask("Password", password=True)
        confirm  = Prompt.ask("Confirm password", password=True)
        if password != confirm:
            error("Passwords do not match.")
            return
    else:
        password = None

    # Count files
    all_files = [f for f in source.rglob("*") if f.is_file()]
    console.print(f"  [dim]Found {len(all_files)} files to backup[/dim]")

    with console.status(f"[cyan]Creating backup...[/cyan]"):
        if encrypted and password:
            _create_encrypted_zip(source, zip_path, password, all_files)
        else:
            with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
                for f in all_files:
                    try:
                        arcname = f.relative_to(source.parent)
                        zf.write(str(f), str(arcname))
                    except Exception:
                        pass

    size = zip_path.stat().st_size
    console.print()
    success(f"Backup created: {zip_path}")
    console.print(f"  [dim]Size: {_format_size(size)}  |  Files: {len(all_files)}[/dim]")
    if encrypted:
        info("Encrypted with your password. Store it safely — it cannot be recovered!")


def _create_encrypted_zip(source: Path, out_path: Path, password: str, files: list) -> None:
    """Create password-protected zip (requires pyminizip or uses pyzipper)."""
    try:
        import pyzipper
        with pyzipper.AESZipFile(str(out_path), "w",
                                  compression=pyzipper.ZIP_LZMA,
                                  encryption=pyzipper.WZ_AES) as zf:
            zf.setpassword(password.encode())
            for f in files:
                try:
                    arcname = str(f.relative_to(source.parent))
                    zf.write(str(f), arcname)
                except Exception:
                    pass
    except ImportError:
        # Fallback: regular zip (not encrypted) with a warning
        warn("pyzipper not installed — creating unencrypted zip instead.")
        warn("Install it: pip install pyzipper")
        with zipfile.ZipFile(str(out_path), "w", zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                try:
                    arcname = str(f.relative_to(source.parent))
                    zf.write(str(f), arcname)
                except Exception:
                    pass


def _list_backups() -> None:
    section("📋 BACKUPS")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    backups = sorted(BACKUP_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not backups:
        info("No backups found.")
        return

    table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
    table.add_column("#",     style="dim",        width=4)
    table.add_column("Name",  style="bold white",  width=40)
    table.add_column("Size",  style="cyan",        width=12, justify="right")
    table.add_column("Date",  style="dim",         width=20)

    for i, b in enumerate(backups, 1):
        mtime = datetime.datetime.fromtimestamp(b.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        table.add_row(str(i), b.name, _format_size(b.stat().st_size), mtime)

    console.print(table)
    total = sum(b.stat().st_size for b in backups)
    console.print(f"\n  [dim]{len(backups)} backups  ·  Total: {_format_size(total)}[/dim]")


def _restore() -> None:
    section("♻️ RESTORE BACKUP")
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    backups = sorted(BACKUP_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not backups:
        info("No backups found.")
        return

    for i, b in enumerate(backups, 1):
        console.print(f"  [{i}] {b.name}")
    console.print()

    choice = Prompt.ask("Select backup #")
    try:
        backup = backups[int(choice) - 1]
    except (ValueError, IndexError):
        error("Invalid selection.")
        return

    dest_str = Prompt.ask("Restore destination", default=str(Path.home() / "restored"))
    dest = Path(dest_str)
    dest.mkdir(parents=True, exist_ok=True)

    with console.status("[cyan]Extracting...[/cyan]"):
        try:
            with zipfile.ZipFile(str(backup), "r") as zf:
                zf.extractall(str(dest))
            success(f"Restored to: {dest}")
        except RuntimeError:
            # Try with password
            password = Prompt.ask("Password", password=True)
            try:
                import pyzipper
                with pyzipper.AESZipFile(str(backup), "r") as zf:
                    zf.setpassword(password.encode())
                    zf.extractall(str(dest))
                success(f"Restored (encrypted) to: {dest}")
            except Exception as e:
                error(f"Restore failed: {e}")
        except Exception as e:
            error(f"Restore failed: {e}")


def _delete() -> None:
    section("🗑️ DELETE BACKUP")
    backups = sorted(BACKUP_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not backups:
        info("No backups to delete.")
        return

    for i, b in enumerate(backups, 1):
        console.print(f"  [{i}] {b.name}  ({_format_size(b.stat().st_size)})")
    console.print()

    choice = Prompt.ask("Select backup # to delete")
    try:
        backup = backups[int(choice) - 1]
    except (ValueError, IndexError):
        error("Invalid selection.")
        return

    if Confirm.ask(f"Delete [bold red]{backup.name}[/bold red]?", default=False):
        backup.unlink()
        success(f"Deleted: {backup.name}")
    else:
        info("Cancelled.")


def _stats() -> None:
    section("📊 BACKUP STATS")
    backups = list(BACKUP_DIR.glob("*.zip"))
    if not backups:
        info("No backups.")
        return

    total_size = sum(b.stat().st_size for b in backups)
    oldest = min(backups, key=lambda p: p.stat().st_mtime)
    newest = max(backups, key=lambda p: p.stat().st_mtime)

    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    table.add_column("Label", style="dim",   width=22)
    table.add_column("Value", style="white")
    table.add_row("Total Backups",  str(len(backups)))
    table.add_row("Total Size",     _format_size(total_size))
    table.add_row("Backup Location", str(BACKUP_DIR))
    table.add_row("Oldest",         oldest.name)
    table.add_row("Newest",         newest.name)
    console.print(table)


# ── Main ──────────────────────────────────────────────────────────────────────

def run(args=None) -> None:
    console.print(Panel(
        "[bold cyan]☁️  BACKUP CENTER[/bold cyan]",
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

    choice = Prompt.ask("[bold green]Select tool[/bold green]", default="1")
    _, _, key = TOOLS.get(choice, ("", "", "backup_dir"))

    dispatch = {
        "backup_dir": lambda: _backup_dir(encrypted=False),
        "backup_enc": lambda: _backup_dir(encrypted=True),
        "list":       _list_backups,
        "restore":    _restore,
        "delete":     _delete,
        "stats":      _stats,
    }
    fn = dispatch.get(key)
    if fn:
        fn()
    console.print()
