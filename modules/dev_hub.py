"""
SYJ ONE — Developer Hub  (syj dev)
GitHub API, project scaffolding, repo management, git shortcuts.
"""

import os
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box

from core.config import get
from core.utils import section, success, error, warn, info, EXPORT_DIR

console = Console()

TOOLS = {
    "1": ("📦", "List My Repos",       "list_repos"),
    "2": ("➕", "Create Repo",         "create_repo"),
    "3": ("🐛", "View Issues",         "issues"),
    "4": ("⭐", "Star a Repo",         "star"),
    "5": ("🏗️", "Scaffold Project",    "scaffold"),
    "6": ("📊", "Git Status",          "git_status"),
    "7": ("🔄", "Git Quick Commit",    "git_commit"),
    "8": ("🔍", "Search GitHub",       "search"),
}

# ── GitHub API helper ─────────────────────────────────────────────────────────

def _gh_request(method: str, endpoint: str, data: dict = None):
    import requests
    token = get("api_keys.github") or ""
    if not token:
        console.print(Panel(
            "[yellow]GitHub token not set.[/yellow]\n\n"
            "Run [bold green]syj config setup[/bold green] to add your token.\n"
            "Create one at [cyan]https://github.com/settings/tokens[/cyan]",
            title="[red]Token Required[/red]", border_style="red"
        ))
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = f"https://api.github.com{endpoint}"
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=15)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=data, timeout=15)
        elif method == "PUT":
            resp = requests.put(url, headers=headers, json=data, timeout=15)
        elif method == "DELETE":
            resp = requests.delete(url, headers=headers, timeout=15)
        else:
            return None

        if resp.status_code in (200, 201, 204):
            return resp.json() if resp.content else {}
        else:
            error(f"GitHub API error {resp.status_code}: {resp.json().get('message', 'Unknown error')}")
            return None
    except Exception as e:
        error(f"Request failed: {e}")
        return None


# ── GitHub tools ──────────────────────────────────────────────────────────────

def _list_repos() -> None:
    section("📦 MY GITHUB REPOSITORIES")
    with console.status("[cyan]Fetching repositories...[/cyan]"):
        repos = _gh_request("GET", "/user/repos?sort=updated&per_page=30")
    if not repos:
        return

    table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
    table.add_column("#",          style="dim",        width=4)
    table.add_column("Repository", style="bold cyan",  width=30)
    table.add_column("⭐",         style="yellow",     width=5)
    table.add_column("Language",   style="green",      width=14)
    table.add_column("Visibility", style="dim",        width=10)
    table.add_column("Updated",    style="dim",        width=16)

    for i, r in enumerate(repos, 1):
        updated = r.get("updated_at", "")[:10]
        table.add_row(
            str(i),
            r["full_name"],
            str(r.get("stargazers_count", 0)),
            r.get("language") or "—",
            "🔓 public" if not r.get("private") else "🔒 private",
            updated,
        )
    console.print(table)
    console.print(f"\n  [dim]Total: {len(repos)} repos[/dim]")


def _create_repo() -> None:
    section("➕ CREATE REPOSITORY")
    name    = Prompt.ask("Repository name")
    desc    = Prompt.ask("Description", default="")
    private = Confirm.ask("Make private?", default=False)
    auto_init = Confirm.ask("Initialize with README?", default=True)

    with console.status("[cyan]Creating repository...[/cyan]"):
        result = _gh_request("POST", "/user/repos", {
            "name": name,
            "description": desc,
            "private": private,
            "auto_init": auto_init,
        })

    if result:
        success(f"Repository created: {result.get('html_url', '')}")
        console.print(f"  Clone: [cyan]git clone {result.get('clone_url', '')}[/cyan]")


def _view_issues() -> None:
    section("🐛 GITHUB ISSUES")
    repo = Prompt.ask("Repository (owner/name)", default="")
    if not repo:
        return

    with console.status("[cyan]Fetching issues...[/cyan]"):
        issues = _gh_request("GET", f"/repos/{repo}/issues?state=open&per_page=20")

    if issues is None:
        return
    if not issues:
        info("No open issues.")
        return

    table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
    table.add_column("#",      style="dim",       width=6)
    table.add_column("Title",  style="white",     width=50)
    table.add_column("Labels", style="cyan",      width=20)
    table.add_column("Author", style="dim",       width=16)

    for issue in issues:
        labels = ", ".join(l["name"] for l in issue.get("labels", []))
        table.add_row(
            f"#{issue['number']}",
            issue["title"][:50],
            labels[:20],
            issue.get("user", {}).get("login", ""),
        )
    console.print(table)


def _star_repo() -> None:
    section("⭐ STAR REPOSITORY")
    repo = Prompt.ask("Repository to star (owner/name)")
    if not repo:
        return

    with console.status("[cyan]Starring...[/cyan]"):
        result = _gh_request("PUT", f"/user/starred/{repo}")

    if result is not None:
        success(f"Starred {repo}")


def _search_github() -> None:
    section("🔍 SEARCH GITHUB")
    query = Prompt.ask("Search query")
    stype = Prompt.ask("Search type", choices=["repositories", "users", "topics"], default="repositories")

    import requests as req
    url = f"https://api.github.com/search/{stype}?q={query}&per_page=10"
    try:
        resp = req.get(url, timeout=15)
        data = resp.json()
        items = data.get("items", [])
    except Exception as e:
        error(str(e))
        return

    table = Table(show_header=True, box=box.SIMPLE, padding=(0, 1))
    if stype == "repositories":
        table.add_column("Repo",   style="bold cyan", width=35)
        table.add_column("⭐",     style="yellow",    width=6)
        table.add_column("Lang",   style="green",     width=14)
        table.add_column("Desc",   style="dim",       width=40)
        for item in items:
            table.add_row(
                item.get("full_name", ""),
                str(item.get("stargazers_count", 0)),
                item.get("language") or "—",
                (item.get("description") or "")[:40],
            )
    elif stype == "users":
        table.add_column("User",   style="bold cyan", width=25)
        table.add_column("URL",    style="dim")
        for item in items:
            table.add_row(item.get("login", ""), item.get("html_url", ""))

    console.print(table)


# ── Scaffolding ───────────────────────────────────────────────────────────────

SCAFFOLD_TYPES = {
    "1": "Python Script",
    "2": "Python Flask API",
    "3": "Node.js / Express",
    "4": "HTML / CSS / JS",
    "5": "Bash Tool",
}

def _scaffold() -> None:
    section("🏗️ PROJECT SCAFFOLDING")
    console.print()
    for k, v in SCAFFOLD_TYPES.items():
        console.print(f"  [{k}] {v}")
    console.print()

    choice  = Prompt.ask("Choose template", default="1")
    name    = Prompt.ask("Project name", default="my-project")
    base    = Path.cwd() / name
    base.mkdir(parents=True, exist_ok=True)

    stype = SCAFFOLD_TYPES.get(choice, "Python Script")

    if stype == "Python Script":
        (base / "main.py").write_text('"""Main entry point."""\n\ndef main():\n    print("Hello from ' + name + '")\n\nif __name__ == "__main__":\n    main()\n')
        (base / "requirements.txt").write_text("")
        (base / "README.md").write_text(f"# {name}\n\nProject description here.\n")
        _init_git(base)

    elif stype == "Python Flask API":
        (base / "app.py").write_text(
            'from flask import Flask, jsonify\n\napp = Flask(__name__)\n\n'
            '@app.route("/")\ndef index():\n    return jsonify({"status": "ok", "project": "' + name + '"})\n\n'
            'if __name__ == "__main__":\n    app.run(debug=True)\n'
        )
        (base / "requirements.txt").write_text("flask\n")
        (base / "README.md").write_text(f"# {name}\n\nFlask API.\n\n## Run\n\n```bash\npip install flask\npython app.py\n```\n")
        _init_git(base)

    elif stype == "Node.js / Express":
        (base / "index.js").write_text(
            "const express = require('express');\nconst app = express();\n\n"
            "app.get('/', (req, res) => res.json({ status: 'ok', project: '" + name + "' }));\n\n"
            "app.listen(3000, () => console.log('Running on port 3000'));\n"
        )
        pkg = {"name": name, "version": "1.0.0", "main": "index.js", "scripts": {"start": "node index.js"}, "dependencies": {"express": "^4.18.0"}}
        import json
        (base / "package.json").write_text(json.dumps(pkg, indent=2))
        (base / "README.md").write_text(f"# {name}\n\n## Run\n\n```bash\nnpm install\nnpm start\n```\n")
        _init_git(base)

    elif stype == "HTML / CSS / JS":
        (base / "index.html").write_text(
            f'<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  <title>{name}</title>\n  <link rel="stylesheet" href="style.css">\n</head>\n<body>\n  <h1>{name}</h1>\n  <script src="script.js"></script>\n</body>\n</html>\n'
        )
        (base / "style.css").write_text("* { box-sizing: border-box; margin: 0; padding: 0; }\nbody { font-family: sans-serif; padding: 2rem; }\n")
        (base / "script.js").write_text(f'console.log("{name} loaded");\n')
        _init_git(base)

    elif stype == "Bash Tool":
        script = base / f"{name}.sh"
        script.write_text(
            f'#!/usr/bin/env bash\n# {name}\nset -e\n\necho "Running {name}..."\n'
        )
        script.chmod(0o755)
        (base / "README.md").write_text(f"# {name}\n\nBash tool.\n\n## Run\n\n```bash\nbash {name}.sh\n```\n")
        _init_git(base)

    success(f"Project scaffolded at: {base}")


def _init_git(path: Path) -> None:
    try:
        subprocess.run(["git", "init"], cwd=str(path), capture_output=True)
        (path / ".gitignore").write_text("__pycache__/\n*.pyc\n.env\nnode_modules/\n.DS_Store\n")
        subprocess.run(["git", "add", "."], cwd=str(path), capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit via SYJ ONE"], cwd=str(path), capture_output=True)
        info("Git repo initialized with initial commit.")
    except Exception:
        warn("Git not available — skipping git init.")


# ── Git helpers ───────────────────────────────────────────────────────────────

def _git_status() -> None:
    section("📊 GIT STATUS")
    try:
        result = subprocess.run(["git", "status"], capture_output=True, text=True)
        console.print(result.stdout)
        result2 = subprocess.run(["git", "log", "--oneline", "-5"], capture_output=True, text=True)
        if result2.stdout:
            console.print("[bold]Last 5 commits:[/bold]")
            console.print(result2.stdout)
    except Exception as e:
        error(f"Git error: {e}")


def _git_commit() -> None:
    section("🔄 GIT QUICK COMMIT")
    try:
        result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
        if not result.stdout.strip():
            info("Nothing to commit.")
            return
        console.print(result.stdout)
        msg = Prompt.ask("Commit message", default="Update via SYJ ONE")
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", msg], check=True)
        if Confirm.ask("Push to remote?", default=False):
            branch = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True).stdout.strip()
            subprocess.run(["git", "push", "origin", branch], check=True)
            success("Pushed to remote.")
        else:
            success("Committed locally.")
    except subprocess.CalledProcessError as e:
        error(f"Git command failed: {e}")
    except Exception as e:
        error(str(e))


# ── Main ──────────────────────────────────────────────────────────────────────

def run(args=None) -> None:
    """syj dev"""
    console.print(Panel(
        "[bold cyan]💻 DEVELOPER HUB[/bold cyan]",
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
    _, _, key = TOOLS.get(choice, ("", "", "list_repos"))

    dispatch = {
        "list_repos":  _list_repos,
        "create_repo": _create_repo,
        "issues":      _view_issues,
        "star":        _star_repo,
        "scaffold":    _scaffold,
        "git_status":  _git_status,
        "git_commit":  _git_commit,
        "search":      _search_github,
    }
    fn = dispatch.get(key)
    if fn:
        fn()
    console.print()
