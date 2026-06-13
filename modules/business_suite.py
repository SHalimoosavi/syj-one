"""
SYJ ONE — Business Suite  (syj business)
Invoices, quotations, expense tracking, client management, GST calculators.
"""

import datetime
import json
import re
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box

from core.config import get, load as load_config
from core.utils import get_db, section, success, error, warn, INVOICE_DIR, EXPORT_DIR, timestamp

console = Console()

TOOLS = {
    "1": ("🧾", "New Invoice",          "invoice"),
    "2": ("📝", "New Quotation",        "quotation"),
    "3": ("💰", "Log Expense",          "expense"),
    "4": ("📊", "Expense Report",       "expense_report"),
    "5": ("👥", "Client Manager",       "clients"),
    "6": ("🧮", "GST Calculator",       "gst"),
    "7": ("💹", "Profit/Margin Calc",   "margin"),
    "8": ("📄", "View Invoices",        "list_invoices"),
}


# ── Database setup ────────────────────────────────────────────────────────────

def _init_db():
    conn = get_db("business.db")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            address TEXT,
            gstin TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_no TEXT UNIQUE NOT NULL,
            client_id INTEGER,
            client_name TEXT,
            date TEXT,
            due_date TEXT,
            items TEXT,
            subtotal REAL,
            gst_rate REAL,
            gst_amount REAL,
            total REAL,
            status TEXT DEFAULT 'draft',
            notes TEXT,
            type TEXT DEFAULT 'invoice',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            category TEXT,
            description TEXT,
            amount REAL,
            gst REAL DEFAULT 0,
            vendor TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    return conn


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cfg():
    cfg = load_config()
    return cfg.get("preferences", {}), cfg.get("user", {})

def _sym() -> str:
    prefs, _ = _cfg()
    return prefs.get("currency_symbol", "₹")

def _gst_rate() -> float:
    prefs, _ = _cfg()
    return float(prefs.get("gst_rate", 18.0))

def _next_invoice_no(conn, prefix="INV") -> str:
    row = conn.execute(f"SELECT COUNT(*) FROM invoices WHERE type='invoice'").fetchone()
    n = (row[0] or 0) + 1
    return f"{prefix}-{datetime.date.today().year}-{n:04d}"

def _next_quote_no(conn) -> str:
    row = conn.execute("SELECT COUNT(*) FROM invoices WHERE type='quotation'").fetchone()
    n = (row[0] or 0) + 1
    return f"QT-{datetime.date.today().year}-{n:04d}"


# ── Invoice/Quotation creator ─────────────────────────────────────────────────

def _create_document(doc_type: str = "invoice") -> None:
    label = "INVOICE" if doc_type == "invoice" else "QUOTATION"
    section(f"🧾 NEW {label}")

    conn  = _init_db()
    sym   = _sym()
    grate = _gst_rate()
    prefs, user = _cfg()

    # Client
    client_name = Prompt.ask("Client name")
    client_email = Prompt.ask("Client email", default="")
    client_addr  = Prompt.ask("Client address", default="")
    client_gstin = Prompt.ask("Client GSTIN", default="")

    # Items
    console.print("\n[bold]Add line items[/bold] [dim](blank name to finish)[/dim]")
    items = []
    total_sub = 0.0
    while True:
        item_name = Prompt.ask("  Item/Service name", default="")
        if not item_name:
            break
        qty_str   = Prompt.ask("  Quantity", default="1")
        rate_str  = Prompt.ask(f"  Rate ({sym})", default="0")
        try:
            qty  = float(qty_str)
            rate = float(rate_str)
        except ValueError:
            qty, rate = 1.0, 0.0
        amount = qty * rate
        total_sub += amount
        items.append({"name": item_name, "qty": qty, "rate": rate, "amount": amount})
        console.print(f"  [dim]→ {qty} × {sym}{rate} = {sym}{amount:.2f}[/dim]")

    if not items:
        warn("No items added. Cancelled.")
        return

    # GST
    gst_rate_str = Prompt.ask(f"GST rate (%)", default=str(grate))
    try:
        gst_rate = float(gst_rate_str)
    except ValueError:
        gst_rate = grate

    gst_amount = total_sub * gst_rate / 100
    total      = total_sub + gst_amount

    # Dates
    today    = datetime.date.today().isoformat()
    due_days = Prompt.ask("Payment due (days)", default="15")
    due_date = (datetime.date.today() + datetime.timedelta(days=int(due_days))).isoformat()
    notes    = Prompt.ask("Notes", default="Thank you for your business!")

    # Save
    inv_no = _next_invoice_no(conn) if doc_type == "invoice" else _next_quote_no(conn)

    conn.execute("""
        INSERT INTO invoices (invoice_no, client_name, date, due_date, items,
            subtotal, gst_rate, gst_amount, total, status, notes, type)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
    """, (inv_no, client_name, today, due_date, json.dumps(items),
          total_sub, gst_rate, gst_amount, total, "draft", notes, doc_type))
    conn.commit()

    # Display
    _print_invoice(inv_no, doc_type, client_name, client_email, client_addr,
                   client_gstin, today, due_date, items, total_sub, gst_rate, gst_amount, total, notes, user)

    # Export HTML
    if Confirm.ask(f"\nExport {label} as HTML?", default=True):
        _export_html(inv_no, doc_type, client_name, client_email, client_addr,
                     client_gstin, today, due_date, items, total_sub, gst_rate, gst_amount, total, notes, user, sym)


def _print_invoice(inv_no, doc_type, client_name, client_email, client_addr,
                   client_gstin, date, due_date, items, subtotal, gst_rate, gst_amount, total, notes, user) -> None:
    sym = _sym()
    label = "INVOICE" if doc_type == "invoice" else "QUOTATION"

    table = Table(show_header=True, box=box.DOUBLE_EDGE, padding=(0, 1), title=f"[bold cyan]{label} {inv_no}[/bold cyan]")
    table.add_column("Item/Service", style="white",     width=35)
    table.add_column("Qty",          style="dim",       width=6,  justify="right")
    table.add_column("Rate",         style="cyan",      width=12, justify="right")
    table.add_column("Amount",       style="bold cyan", width=12, justify="right")

    for it in items:
        table.add_row(it["name"], str(it["qty"]), f"{sym}{it['rate']:.2f}", f"{sym}{it['amount']:.2f}")

    table.add_section()
    table.add_row("", "", "[dim]Subtotal[/dim]",     f"[white]{sym}{subtotal:.2f}[/white]")
    table.add_row("", "", f"[dim]GST ({gst_rate}%)[/dim]", f"[white]{sym}{gst_amount:.2f}[/white]")
    table.add_row("", "", "[bold]TOTAL[/bold]",      f"[bold green]{sym}{total:.2f}[/bold green]")

    console.print()
    console.print(f"  [bold]From:[/bold] {user.get('company', '')}  |  [bold]To:[/bold] {client_name}")
    console.print(f"  [bold]Date:[/bold] {date}  |  [bold]Due:[/bold] {due_date}")
    if client_gstin:
        console.print(f"  [bold]GSTIN:[/bold] {client_gstin}")
    console.print()
    console.print(table)
    if notes:
        console.print(f"\n  [dim]{notes}[/dim]")


def _export_html(inv_no, doc_type, client_name, client_email, client_addr,
                 client_gstin, date, due_date, items, subtotal, gst_rate, gst_amount, total, notes, user, sym) -> None:
    label   = "INVOICE" if doc_type == "invoice" else "QUOTATION"
    rows    = "".join(f"<tr><td>{i['name']}</td><td>{i['qty']}</td><td>{sym}{i['rate']:.2f}</td><td>{sym}{i['amount']:.2f}</td></tr>" for i in items)
    company = user.get("company", "My Company")
    email   = user.get("email", "")

    html = f"""<!DOCTYPE html><html lang="en">
<head><meta charset="UTF-8"><title>{label} {inv_no}</title>
<style>
  body{{font-family:sans-serif;max-width:800px;margin:40px auto;color:#333;padding:0 20px}}
  h1{{color:#0a3d62}}
  .meta{{display:flex;justify-content:space-between;margin-bottom:2rem}}
  table{{width:100%;border-collapse:collapse;margin:1rem 0}}
  th{{background:#0a3d62;color:#fff;padding:10px;text-align:left}}
  td{{padding:10px;border-bottom:1px solid #eee}}
  .total{{text-align:right;font-size:1.2rem;font-weight:bold;color:#0a3d62}}
  .footer{{margin-top:2rem;color:#888;font-size:0.9rem}}
</style></head><body>
<h1>{company}</h1>
<p>{email}</p>
<div class="meta">
  <div><strong>{label}</strong><br>{inv_no}<br>Date: {date}<br>Due: {due_date}</div>
  <div><strong>Bill To:</strong><br>{client_name}<br>{client_email}<br>{client_addr}<br>{client_gstin}</div>
</div>
<table><tr><th>Item / Service</th><th>Qty</th><th>Rate</th><th>Amount</th></tr>
{rows}
</table>
<p style="text-align:right">Subtotal: {sym}{subtotal:.2f}<br>
GST ({gst_rate}%): {sym}{gst_amount:.2f}<br></p>
<p class="total">TOTAL: {sym}{total:.2f}</p>
<p class="footer">{notes}</p>
</body></html>"""

    INVOICE_DIR.mkdir(parents=True, exist_ok=True)
    path = INVOICE_DIR / f"{inv_no}.html"
    path.write_text(html)
    success(f"Exported: {path}")


# ── Expense Tracker ───────────────────────────────────────────────────────────

EXPENSE_CATEGORIES = ["Office", "Travel", "Food", "Software", "Hardware", "Marketing", "Utilities", "Other"]

def _log_expense() -> None:
    section("💰 LOG EXPENSE")
    conn = _init_db()
    sym  = _sym()

    date  = Prompt.ask("Date (YYYY-MM-DD)", default=datetime.date.today().isoformat())
    console.print("  Categories: " + " | ".join(f"[{i+1}] {c}" for i, c in enumerate(EXPENSE_CATEGORIES)))
    cat_idx = Prompt.ask("Category #", default="8")
    try:
        category = EXPENSE_CATEGORIES[int(cat_idx) - 1]
    except (ValueError, IndexError):
        category = "Other"
    desc    = Prompt.ask("Description")
    amount  = float(Prompt.ask(f"Amount ({sym})"))
    gst_str = Prompt.ask(f"GST included ({sym})", default="0")
    vendor  = Prompt.ask("Vendor/Payee", default="")

    conn.execute(
        "INSERT INTO expenses (date, category, description, amount, gst, vendor) VALUES (?,?,?,?,?,?)",
        (date, category, desc, amount, float(gst_str), vendor)
    )
    conn.commit()
    success(f"Expense logged: {category} — {sym}{amount:.2f}")


def _expense_report() -> None:
    section("📊 EXPENSE REPORT")
    conn = _init_db()
    sym  = _sym()

    month = Prompt.ask("Month (YYYY-MM or 'all')", default=datetime.date.today().strftime("%Y-%m"))
    if month == "all":
        rows = conn.execute("SELECT * FROM expenses ORDER BY date DESC").fetchall()
    else:
        rows = conn.execute("SELECT * FROM expenses WHERE date LIKE ? ORDER BY date DESC", (f"{month}%",)).fetchall()

    if not rows:
        info("No expenses found.")
        return

    table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
    table.add_column("Date",     style="dim",   width=12)
    table.add_column("Category", style="cyan",  width=12)
    table.add_column("Description", style="white", width=30)
    table.add_column("Amount",   style="green", width=12, justify="right")
    table.add_column("Vendor",   style="dim",   width=16)

    total = 0.0
    for r in rows:
        table.add_row(r["date"], r["category"], r["description"],
                      f"{sym}{r['amount']:.2f}", r["vendor"] or "")
        total += r["amount"]

    console.print(table)
    console.print(f"\n  [bold]Total:[/bold] [green]{sym}{total:.2f}[/green]  [dim]({len(rows)} entries)[/dim]")


# ── Client Manager ────────────────────────────────────────────────────────────

def _clients() -> None:
    section("👥 CLIENT MANAGER")
    conn = _init_db()

    action = Prompt.ask("Action", choices=["add", "list", "search"], default="list")

    if action == "add":
        name  = Prompt.ask("Client name")
        email = Prompt.ask("Email", default="")
        phone = Prompt.ask("Phone", default="")
        addr  = Prompt.ask("Address", default="")
        gstin = Prompt.ask("GSTIN", default="")
        conn.execute("INSERT INTO clients (name, email, phone, address, gstin) VALUES (?,?,?,?,?)",
                     (name, email, phone, addr, gstin))
        conn.commit()
        success(f"Client '{name}' added.")

    elif action == "list":
        rows = conn.execute("SELECT * FROM clients ORDER BY name").fetchall()
        if not rows:
            info("No clients yet.")
            return
        table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
        table.add_column("ID",    style="dim",   width=4)
        table.add_column("Name",  style="bold",  width=25)
        table.add_column("Email", style="cyan",  width=25)
        table.add_column("Phone", style="white", width=15)
        table.add_column("GSTIN", style="dim",   width=18)
        for r in rows:
            table.add_row(str(r["id"]), r["name"], r["email"] or "", r["phone"] or "", r["gstin"] or "")
        console.print(table)

    elif action == "search":
        q = Prompt.ask("Search name")
        rows = conn.execute("SELECT * FROM clients WHERE name LIKE ?", (f"%{q}%",)).fetchall()
        for r in rows:
            console.print(f"  [bold]{r['name']}[/bold]  {r['email']}  {r['phone']}")


def _list_invoices() -> None:
    section("📄 INVOICES & QUOTATIONS")
    conn = _init_db()
    sym  = _sym()

    rows = conn.execute("SELECT * FROM invoices ORDER BY created_at DESC LIMIT 30").fetchall()
    if not rows:
        info("No invoices yet.")
        return

    table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
    table.add_column("No.",     style="bold cyan", width=16)
    table.add_column("Type",    style="dim",       width=10)
    table.add_column("Client",  style="white",     width=22)
    table.add_column("Date",    style="dim",       width=12)
    table.add_column("Total",   style="green",     width=12, justify="right")
    table.add_column("Status",  style="yellow",    width=8)

    for r in rows:
        table.add_row(r["invoice_no"], r["type"].upper(), r["client_name"],
                      r["date"], f"{sym}{r['total']:.2f}", r["status"])
    console.print(table)


# ── Calculators ───────────────────────────────────────────────────────────────

def _gst_calc() -> None:
    section("🧮 GST CALCULATOR")
    sym    = _sym()
    amount = float(Prompt.ask(f"Amount ({sym})"))
    rate   = float(Prompt.ask("GST rate (%)", default=str(_gst_rate())))
    incl   = Confirm.ask("Amount includes GST?", default=False)

    if incl:
        base_amount = amount / (1 + rate / 100)
        gst_amount  = amount - base_amount
    else:
        base_amount = amount
        gst_amount  = amount * rate / 100

    total = base_amount + gst_amount
    cgst  = gst_amount / 2
    sgst  = gst_amount / 2

    table = Table(show_header=False, box=box.SIMPLE, padding=(0, 2))
    table.add_column("Label", style="dim",         width=25)
    table.add_column("Value", style="bold green",  width=15, justify="right")
    table.add_row("Base Amount",   f"{sym}{base_amount:.2f}")
    table.add_row(f"GST @ {rate}%", f"{sym}{gst_amount:.2f}")
    table.add_row("  CGST",        f"{sym}{cgst:.2f}")
    table.add_row("  SGST/UTGST",  f"{sym}{sgst:.2f}")
    table.add_row("[bold]Total[/bold]", f"[bold]{sym}{total:.2f}[/bold]")
    console.print(table)


def _margin_calc() -> None:
    section("💹 PROFIT / MARGIN CALCULATOR")
    sym  = _sym()
    mode = Prompt.ask("Mode", choices=["margin", "markup", "break-even"], default="margin")

    if mode == "margin":
        cost   = float(Prompt.ask(f"Cost price ({sym})"))
        sell   = float(Prompt.ask(f"Selling price ({sym})"))
        profit = sell - cost
        margin = (profit / sell * 100) if sell else 0
        markup = (profit / cost * 100) if cost else 0
        console.print(f"\n  Profit: [green]{sym}{profit:.2f}[/green]")
        console.print(f"  Gross Margin: [cyan]{margin:.2f}%[/cyan]")
        console.print(f"  Markup: [yellow]{markup:.2f}%[/yellow]")

    elif mode == "markup":
        cost   = float(Prompt.ask(f"Cost price ({sym})"))
        markup = float(Prompt.ask("Markup (%)"))
        sell   = cost * (1 + markup / 100)
        profit = sell - cost
        margin = (profit / sell * 100) if sell else 0
        console.print(f"\n  Selling price: [green]{sym}{sell:.2f}[/green]")
        console.print(f"  Profit: [cyan]{sym}{profit:.2f}[/cyan]")
        console.print(f"  Gross Margin: [yellow]{margin:.2f}%[/yellow]")

    elif mode == "break-even":
        fixed  = float(Prompt.ask(f"Fixed costs ({sym}/month)"))
        var    = float(Prompt.ask(f"Variable cost per unit ({sym})"))
        price  = float(Prompt.ask(f"Selling price per unit ({sym})"))
        contrib = price - var
        if contrib <= 0:
            error("Price must be higher than variable cost.")
            return
        bes = fixed / contrib
        console.print(f"\n  Break-even quantity: [green]{bes:.0f} units/month[/green]")
        console.print(f"  Break-even revenue: [cyan]{sym}{bes * price:.2f}/month[/cyan]")


# ── Main ──────────────────────────────────────────────────────────────────────

def run(args=None) -> None:
    console.print(Panel(
        "[bold cyan]💼 BUSINESS SUITE[/bold cyan]",
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
    _, _, key = TOOLS.get(choice, ("", "", "invoice"))

    dispatch = {
        "invoice":        lambda: _create_document("invoice"),
        "quotation":      lambda: _create_document("quotation"),
        "expense":        _log_expense,
        "expense_report": _expense_report,
        "clients":        _clients,
        "gst":            _gst_calc,
        "margin":         _margin_calc,
        "list_invoices":  _list_invoices,
    }
    fn = dispatch.get(key)
    if fn:
        fn()
    console.print()
