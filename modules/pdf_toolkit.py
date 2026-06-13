"""
SYJ ONE — PDF Toolkit  (syj pdf)
Merge, split, info, text-to-PDF using pypdf and reportlab.
"""

import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box

from core.utils import section, success, error, warn, info, EXPORT_DIR

console = Console()

TOOLS = {
    "1": ("📎", "Merge PDFs",         "merge"),
    "2": ("✂️", "Split PDF",          "split"),
    "3": ("ℹ️", "PDF Info",           "info_pdf"),
    "4": ("📝", "Text to PDF",        "text2pdf"),
    "5": ("📋", "List PDF files",     "list_pdf"),
    "6": ("🔢", "Count Pages",        "pages"),
}


def _get_pypdf():
    try:
        import pypdf
        return pypdf
    except ImportError:
        error("pypdf not installed. Run: pip install pypdf")
        return None


def _get_rl():
    try:
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib.pagesizes import A4
        return rl_canvas, A4
    except ImportError:
        error("reportlab not installed. Run: pip install reportlab")
        return None, None


# ── Tools ─────────────────────────────────────────────────────────────────────

def _merge() -> None:
    section("📎 MERGE PDFs")
    pypdf = _get_pypdf()
    if not pypdf:
        return

    console.print("[dim]Enter PDF file paths one by one (blank to finish):[/dim]")
    files = []
    while True:
        path = Prompt.ask(f"PDF #{len(files)+1}", default="").strip()
        if not path:
            break
        p = Path(path)
        if not p.exists():
            warn(f"File not found: {path}")
        else:
            files.append(p)

    if len(files) < 2:
        warn("Need at least 2 PDFs to merge.")
        return

    out_name = Prompt.ask("Output filename", default="merged.pdf")
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = EXPORT_DIR / out_name

    writer = pypdf.PdfWriter()
    total_pages = 0
    for f in files:
        try:
            reader = pypdf.PdfReader(str(f))
            for page in reader.pages:
                writer.add_page(page)
            total_pages += len(reader.pages)
            info(f"Added {len(reader.pages)} pages from {f.name}")
        except Exception as e:
            warn(f"Could not read {f.name}: {e}")

    with open(str(out_path), "wb") as fh:
        writer.write(fh)

    success(f"Merged {len(files)} PDFs → {out_path} ({total_pages} pages total)")


def _split() -> None:
    section("✂️ SPLIT PDF")
    pypdf = _get_pypdf()
    if not pypdf:
        return

    path_str = Prompt.ask("PDF file path")
    path = Path(path_str)
    if not path.exists():
        error(f"File not found: {path}")
        return

    reader = pypdf.PdfReader(str(path))
    total  = len(reader.pages)
    console.print(f"  Total pages: [cyan]{total}[/cyan]")

    mode = Prompt.ask("Split mode", choices=["all", "range", "every_n"], default="all")

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    stem = path.stem

    if mode == "all":
        for i, page in enumerate(reader.pages):
            writer = pypdf.PdfWriter()
            writer.add_page(page)
            out = EXPORT_DIR / f"{stem}_page_{i+1:03d}.pdf"
            with open(str(out), "wb") as fh:
                writer.write(fh)
        success(f"Split into {total} single-page PDFs in {EXPORT_DIR}")

    elif mode == "range":
        r = Prompt.ask("Page range (e.g. 1-5)")
        start, end = map(int, r.split("-"))
        writer = pypdf.PdfWriter()
        for i in range(start - 1, min(end, total)):
            writer.add_page(reader.pages[i])
        out = EXPORT_DIR / f"{stem}_{start}-{end}.pdf"
        with open(str(out), "wb") as fh:
            writer.write(fh)
        success(f"Extracted pages {start}–{end} → {out}")

    elif mode == "every_n":
        n = int(Prompt.ask("Pages per chunk", default="10"))
        chunk = 0
        for start in range(0, total, n):
            chunk += 1
            writer = pypdf.PdfWriter()
            for i in range(start, min(start + n, total)):
                writer.add_page(reader.pages[i])
            out = EXPORT_DIR / f"{stem}_part{chunk:02d}.pdf"
            with open(str(out), "wb") as fh:
                writer.write(fh)
        success(f"Split into {chunk} chunks of ≤{n} pages each in {EXPORT_DIR}")


def _info_pdf() -> None:
    section("ℹ️ PDF INFO")
    pypdf = _get_pypdf()
    if not pypdf:
        return

    path_str = Prompt.ask("PDF file path")
    path = Path(path_str)
    if not path.exists():
        error(f"File not found: {path}")
        return

    reader = pypdf.PdfReader(str(path))
    meta   = reader.metadata or {}

    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 1))
    table.add_column("Field",  style="dim",   width=20)
    table.add_column("Value",  style="white")

    file_size = path.stat().st_size
    table.add_row("File",          path.name)
    table.add_row("Size",          f"{file_size / 1024:.1f} KB")
    table.add_row("Pages",         str(len(reader.pages)))
    table.add_row("Encrypted",     str(reader.is_encrypted))
    table.add_row("Title",         meta.get("/Title", "") or "")
    table.add_row("Author",        meta.get("/Author", "") or "")
    table.add_row("Creator",       meta.get("/Creator", "") or "")
    table.add_row("Producer",      meta.get("/Producer", "") or "")
    table.add_row("Created",       str(meta.get("/CreationDate", "")) or "")
    table.add_row("Modified",      str(meta.get("/ModDate", "")) or "")

    console.print(table)

    # Page sizes
    if reader.pages:
        page = reader.pages[0]
        mb = page.mediabox
        console.print(f"  [dim]Page size (p.1): {float(mb.width):.0f} × {float(mb.height):.0f} pt[/dim]")


def _text_to_pdf() -> None:
    section("📝 TEXT TO PDF")
    rl_canvas, A4 = _get_rl()
    if not rl_canvas:
        return

    console.print("[dim]Enter text content (blank line to finish):[/dim]")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if not line and lines:
            break
        lines.append(line)

    if not lines:
        warn("No content.")
        return

    out_name = Prompt.ask("Output filename", default="output.pdf")
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = str(EXPORT_DIR / out_name)

    title = Prompt.ask("Document title", default="")

    c = rl_canvas.Canvas(out_path, pagesize=A4)
    w, h = A4
    margin = 50
    y = h - margin

    if title:
        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin, y, title)
        y -= 30
        c.setLineWidth(1)
        c.line(margin, y, w - margin, y)
        y -= 20

    c.setFont("Helvetica", 11)
    for line in lines:
        if y < margin + 20:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = h - margin
        c.drawString(margin, y, line)
        y -= 16

    c.save()
    success(f"PDF created: {out_path}")


def _list_pdfs() -> None:
    section("📋 PDF FILES")
    search_dir = Prompt.ask("Search in directory", default=str(Path.home()))
    path = Path(search_dir)
    if not path.exists():
        error(f"Directory not found: {search_dir}")
        return

    pdfs = list(path.rglob("*.pdf"))[:50]
    if not pdfs:
        info("No PDF files found.")
        return

    table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
    table.add_column("File",  style="cyan",  width=40)
    table.add_column("Size",  style="dim",   width=12, justify="right")
    table.add_column("Path",  style="dim",   width=40)

    for p in sorted(pdfs):
        size = p.stat().st_size
        size_str = f"{size/1024:.1f} KB" if size < 1_000_000 else f"{size/1_000_000:.1f} MB"
        table.add_row(p.name, size_str, str(p.parent))

    console.print(table)
    console.print(f"\n  [dim]Found {len(pdfs)} PDF(s)[/dim]")


def _count_pages() -> None:
    section("🔢 COUNT PDF PAGES")
    pypdf = _get_pypdf()
    if not pypdf:
        return
    path_str = Prompt.ask("PDF file path")
    path = Path(path_str)
    if not path.exists():
        error(f"File not found: {path}")
        return
    reader = pypdf.PdfReader(str(path))
    console.print(f"  [bold]{path.name}[/bold]: [green]{len(reader.pages)} pages[/green]")


# ── Main ──────────────────────────────────────────────────────────────────────

def run(args=None) -> None:
    console.print(Panel(
        "[bold cyan]📄 PDF TOOLKIT[/bold cyan]",
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
    _, _, key = TOOLS.get(choice, ("", "", "merge"))

    dispatch = {
        "merge":    _merge,
        "split":    _split,
        "info_pdf": _info_pdf,
        "text2pdf": _text_to_pdf,
        "list_pdf": _list_pdfs,
        "pages":    _count_pages,
    }
    fn = dispatch.get(key)
    if fn:
        fn()
    console.print()
