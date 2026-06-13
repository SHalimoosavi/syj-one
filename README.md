# SYJ ONE

> **The Ultimate Mobile Productivity & Security Platform for Termux**

<pre>
  ███████╗██╗   ██╗     ██╗    ██████╗ ███╗   ██╗███████╗
  ██╔════╝╚██╗ ██╔╝     ██║   ██╔═══██╗████╗  ██║██╔════╝
  ███████╗ ╚████╔╝      ██║   ██║   ██║██╔██╗ ██║█████╗
  ╚════██║  ╚██╔╝       ██║   ██║   ██║██║╚██╗██║██╔══╝
  ███████║   ██║        ╚═╝   ╚██████╔╝██║ ╚████║███████╗
  ╚══════╝   ╚═╝               ╚═════╝ ╚═╝  ╚═══╝╚══════╝
</pre>

**One installation. One command. Everything you need.**

Built by [Sayanjali Nexus](https://syj-token.com) · [shalimoosavi@gmail.com](mailto:shalimoosavi@gmail.com) · [GitHub: SHalimoosavi](https://github.com/SHalimoosavi)

---

## What is SYJ ONE?

SYJ ONE is an open-source all-in-one productivity, business, developer, SEO, and security platform built specifically for **Termux on Android**. Instead of installing dozens of separate tools, you install one platform that handles everything from website audits to invoice generation — directly from your phone.

---

## Modules

| Command | Module | What it does |
|---|---|---|
| `syj ai` | 🤖 AI Workspace | Chat with Claude AI, explain/generate code, draft content, business ideas, SEO advice |
| `syj seo` | 🔍 SEO Intelligence | Full on-page audit: meta tags, headings, images, robots.txt, sitemap, score |
| `syj shield` | 🛡️ Cyber Shield | DNS lookup, WHOIS, SSL certificate, security headers, port scan, tech detection |
| `syj dev` | 💻 Developer Hub | GitHub API (repos, issues, create), project scaffolding, git shortcuts |
| `syj business` | 💼 Business Suite | Invoices, quotations, expense tracker, client manager, GST & margin calculators |
| `syj pdf` | 📄 PDF Toolkit | Merge, split, info, text-to-PDF |
| `syj backup` | ☁️ Backup Center | Local & encrypted backups, restore, stats |
| `syj monitor` | 📡 Web Monitor | Uptime checks, SSL expiry alerts, response time, site dashboard |
| `syj config` | ⚙️ Settings | API keys, user info, currency, GST rate |

---

## Installation

### On Termux (Android)

```bash
# 1. Clone the repo
git clone https://github.com/SHalimoosavi/syj-one.git
cd syj-one

# 2. Run the installer
bash install.sh

# 3. Restart Termux, then:
syj
<pre>

### Manual install

```bash
pip install rich requests dnspython anthropic pypdf reportlab python-dotenv tabulate schedule
chmod +x syj
./syj
<pre>

---

## Quick Start

```bash
# First-time setup (add your Anthropic & GitHub keys)
syj config setup

# SEO audit a website
syj seo https://yourdomain.com

# Chat with AI
syj ai

# Quick AI query
syj ai "write a cold email for my SaaS product"

# Security scan
syj shield example.com

# DNS-only lookup
syj shield --dns example.com

# Check uptime instantly
syj monitor example.com

# Create an invoice
syj business

# Generate code scaffold
syj dev
<pre>

---

## Configuration

Config file: `~/.syj-one/config/settings.json`

```json
{
  "user": {
    "name": "Your Name",
    "email": "you@example.com",
    "company": "Your Company"
  },
  "api_keys": {
    "anthropic": "sk-ant-...",
    "github": "ghp_..."
  },
  "preferences": {
    "currency": "INR",
    "currency_symbol": "₹",
    "gst_rate": 18.0
  }
}
<pre>

**Set values from CLI:**
```bash
syj config set api_keys.anthropic sk-ant-your-key-here
syj config set preferences.currency USD
syj config show
<pre>

---

## API Keys

| Service | Required for | Get it at |
|---|---|---|
| Anthropic | `syj ai` (AI Workspace) | https://console.anthropic.com |
| GitHub | `syj dev` (GitHub tools) | https://github.com/settings/tokens |

All other modules work without any API keys.

---

## Project Structure

<pre>
syj-one/
├── syj                    # Shell launcher
├── syj_main.py            # Main router
├── install.sh             # Termux installer
├── requirements.txt
├── core/
│   ├── banner.py          # ASCII art & menu
│   ├── config.py          # Config manager
│   └── utils.py           # Shared utilities
├── modules/
│   ├── ai_workspace.py    # Claude AI integration
│   ├── seo_intel.py       # SEO auditor
│   ├── cyber_shield.py    # Security tools
│   ├── dev_hub.py         # Developer tools
│   ├── business_suite.py  # Business operations
│   ├── pdf_toolkit.py     # PDF operations
│   ├── backup_center.py   # Backup manager
│   └── web_monitor.py     # Uptime monitor
├── config/                # User config (auto-created)
├── data/                  # SQLite databases
├── invoices/              # Generated invoices (HTML)
├── exports/               # PDF exports
└── backups/               # Backup archives
<pre>

---

## Requirements

- Android 8+ with Termux (or any Linux)
- Python 3.8+
- Internet connection
- 2GB+ RAM (4GB recommended)

---

## License

MIT License — Open source, free forever.

---

*Built with ❤️ by Sayanjali Nexus, Hyderabad, Telangana, India*
