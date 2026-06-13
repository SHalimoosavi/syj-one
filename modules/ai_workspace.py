"""
SYJ ONE — AI Workspace  (syj ai)
Interactive Claude-powered assistant for code, business, SEO, and content.
"""

import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.markdown import Markdown
from rich.table import Table

console = Console()

MODES = {
    "1": ("💬", "Free Chat",         "chat"),
    "2": ("🧠", "Explain Code",      "code_explain"),
    "3": ("⚡", "Generate Code",     "code_gen"),
    "4": ("📝", "Write Content",     "content"),
    "5": ("💡", "Business Ideas",    "business"),
    "6": ("🔍", "SEO Advice",        "seo"),
    "7": ("📧", "Draft Email/Msg",   "email"),
    "8": ("📄", "Summarize Text",    "summarize"),
}

SYSTEM_PROMPTS = {
    "chat":        "You are ARIA, the SYJ ONE AI assistant built by Sayanjali Nexus. Be concise, helpful, and practical.",
    "code_explain":"You are an expert programmer. Explain the provided code clearly — what it does, how it works, and any potential issues. Be concise.",
    "code_gen":    "You are an expert developer. Generate clean, production-quality code with comments. Ask clarifying questions if needed.",
    "content":     "You are a professional content writer. Write engaging, SEO-friendly content. Follow the user's tone and format instructions.",
    "business":    "You are a business strategy expert with experience in Indian markets. Give practical, actionable advice.",
    "seo":         "You are an SEO specialist. Give specific, actionable SEO recommendations based on current best practices.",
    "email":       "You are a professional communication expert. Draft clear, effective messages and emails.",
    "summarize":   "You are a summarization expert. Provide concise, accurate summaries that capture the key points.",
}


def _get_client():
    try:
        import anthropic as _ant
        from core.config import get
        key = get("api_keys.anthropic") or ""
        if not key:
            console.print(Panel(
                "[yellow]Anthropic API key not set.[/yellow]\n\n"
                "Run [bold green]syj config setup[/bold green] to add your key.\n"
                "Get one free at [cyan]https://console.anthropic.com[/cyan]",
                title="[red]API Key Required[/red]",
                border_style="red"
            ))
            return None
        return _ant.Anthropic(api_key=key)
    except ImportError:
        console.print("[red]anthropic package not installed. Run: pip install anthropic[/red]")
        return None


def _chat_loop(client, mode: str, system_prompt: str) -> None:
    history = []
    console.print(f"\n[dim]Type your message. [bold]exit[/bold] or [bold]quit[/bold] to leave. [bold]clear[/bold] to reset.[/dim]\n")

    while True:
        try:
            user_input = Prompt.ask("[bold green]You[/bold green]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Exiting AI Workspace.[/dim]")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q", "bye"):
            console.print("[dim]Leaving AI Workspace.[/dim]")
            break
        if user_input.lower() == "clear":
            history.clear()
            console.print("[dim]Conversation cleared.[/dim]\n")
            continue

        history.append({"role": "user", "content": user_input})

        try:
            with console.status("[cyan]ARIA is thinking...[/cyan]", spinner="dots"):
                response = client.messages.create(
                    model="claude-sonnet-4-6",
                    max_tokens=2048,
                    system=system_prompt,
                    messages=history,
                )
            reply = response.content[0].text
            history.append({"role": "assistant", "content": reply})

            console.print()
            console.print(Panel(
                Markdown(reply),
                title="[bold cyan]ARIA[/bold cyan]",
                border_style="cyan",
                padding=(0, 1),
            ))
            console.print()

        except Exception as e:
            console.print(f"[red]API error:[/red] {e}")


def _single_query(client, mode: str, system_prompt: str, query: str) -> None:
    try:
        with console.status("[cyan]ARIA is thinking...[/cyan]", spinner="dots"):
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": query}],
            )
        reply = response.content[0].text
        console.print()
        console.print(Panel(
            Markdown(reply),
            title="[bold cyan]ARIA — AI Response[/bold cyan]",
            border_style="cyan",
            padding=(0, 1),
        ))
    except Exception as e:
        console.print(f"[red]API error:[/red] {e}")


def _show_menu() -> str:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("num",  style="bold green", width=4)
    table.add_column("icon", width=3)
    table.add_column("name", style="bold white", width=20)

    for num, (icon, name, _) in MODES.items():
        table.add_row(f"[{num}]", icon, name)

    console.print(Panel(
        table,
        title="[bold cyan]🤖 AI WORKSPACE[/bold cyan]",
        border_style="cyan",
        padding=(1, 2),
    ))
    return Prompt.ask("[bold green]Select mode[/bold green]", default="1")


def run(args=None) -> None:
    """syj ai [mode] [--query 'text']"""
    args = args or []

    client = _get_client()
    if not client:
        return

    # Quick inline query: syj ai "explain this code: ..."
    if args and not args[0].startswith("-"):
        # Treat first arg as query in chat mode
        mode, system_prompt = "chat", SYSTEM_PROMPTS["chat"]
        _single_query(client, mode, system_prompt, " ".join(args))
        return

    # Check for --query flag
    if "--query" in args or "-q" in args:
        flag = "--query" if "--query" in args else "-q"
        idx = args.index(flag)
        if idx + 1 < len(args):
            query = args[idx + 1]
            _single_query(client, "chat", SYSTEM_PROMPTS["chat"], query)
            return

    # Interactive menu
    console.print()
    console.print(Panel(
        "[bold cyan]ARIA[/bold cyan] — [dim]SYJ ONE AI Assistant powered by Claude[/dim]",
        border_style="cyan"
    ))

    choice = _show_menu()
    if choice not in MODES:
        console.print("[red]Invalid selection.[/red]")
        return

    icon, name, mode_key = MODES[choice]
    system_prompt = SYSTEM_PROMPTS[mode_key]

    console.print(f"\n[bold cyan]{icon} {name}[/bold cyan] mode activated.\n")

    # Modes that need a paste/input
    if mode_key in ("code_explain", "summarize"):
        console.print("[dim]Paste your content (end with a blank line):[/dim]")
        lines = []
        try:
            while True:
                line = input()
                if line == "" and lines:
                    break
                lines.append(line)
        except EOFError:
            pass
        content = "\n".join(lines).strip()
        if content:
            _single_query(client, mode_key, system_prompt, content)
        return

    # All other modes: chat loop
    _chat_loop(client, mode_key, system_prompt)
