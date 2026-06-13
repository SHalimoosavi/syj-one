#!/usr/bin/env bash
# =============================================================================
# SYJ ONE — Installer for Termux / Linux
# =============================================================================
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

banner() {
cat << 'EOF'

  ███████╗██╗   ██╗     ██╗    ██████╗ ███╗   ██╗███████╗
  ██╔════╝╚██╗ ██╔╝     ██║   ██╔═══██╗████╗  ██║██╔════╝
  ███████╗ ╚████╔╝      ██║   ██║   ██║██╔██╗ ██║█████╗
  ╚════██║  ╚██╔╝       ██║   ██║   ██║██║╚██╗██║██╔══╝
  ███████║   ██║        ╚═╝   ╚██████╔╝██║ ╚████║███████╗
  ╚══════╝   ╚═╝               ╚═════╝ ╚═╝  ╚═══╝╚══════╝

  The Ultimate Mobile Productivity & Security Platform
  Version 1.0  |  by Sayanjali Nexus  |  github.com/SHalimoosavi
EOF
}

step() { echo -e "${CYAN}[*]${RESET} $1"; }
ok()   { echo -e "${GREEN}[✓]${RESET} $1"; }
warn() { echo -e "${YELLOW}[!]${RESET} $1"; }
fail() { echo -e "${RED}[✗]${RESET} $1"; exit 1; }

clear
banner
echo ""

# ── Detect environment ────────────────────────────────────────────────────────
IS_TERMUX=false
if [ -n "$PREFIX" ] && [ -d "$PREFIX/bin" ]; then
    IS_TERMUX=true
    step "Detected Termux environment"
else
    warn "Not running in Termux. Continuing for Linux..."
fi

# ── System packages ───────────────────────────────────────────────────────────
step "Installing system dependencies..."
if $IS_TERMUX; then
    pkg update -y -o Dpkg::Options::="--force-confdef" 2>/dev/null
    pkg install -y python python-pip git curl wget openssl 2>/dev/null
    # Optional: whois, nmap (may fail on some devices)
    pkg install -y whois 2>/dev/null || warn "whois not available — WHOIS lookups will use API fallback"
else
    sudo apt-get update -qq
    sudo apt-get install -y python3 python3-pip git curl wget openssl whois 2>/dev/null || true
fi
ok "System dependencies installed"

# ── Python packages ───────────────────────────────────────────────────────────
step "Installing Python dependencies (this may take a moment)..."
pip install --upgrade pip --quiet 2>/dev/null || pip3 install --upgrade pip --quiet 2>/dev/null || true
pip install rich requests dnspython anthropic pypdf reportlab python-dotenv tabulate schedule --quiet \
    2>/dev/null || pip3 install rich requests dnspython anthropic pypdf reportlab python-dotenv tabulate schedule --quiet
ok "Python dependencies installed"

# ── Setup home directory ──────────────────────────────────────────────────────
SYJ_HOME="$HOME/.syj-one"
step "Setting up SYJ ONE home at $SYJ_HOME..."
mkdir -p "$SYJ_HOME"/{config,data,backups,logs,invoices,exports,scaffolds}

# Copy project files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -rf "$SCRIPT_DIR"/* "$SYJ_HOME/" 2>/dev/null || true
chmod +x "$SYJ_HOME/syj"
ok "Files installed"

# ── PATH setup ────────────────────────────────────────────────────────────────
step "Configuring PATH..."
add_to_path() {
    local rcfile="$1"
    if [ -f "$rcfile" ] && ! grep -q "SYJ ONE" "$rcfile" 2>/dev/null; then
        echo "" >> "$rcfile"
        echo "# SYJ ONE" >> "$rcfile"
        echo "export PATH=\"\$PATH:$SYJ_HOME\"" >> "$rcfile"
        ok "Added to $rcfile"
    fi
}
add_to_path "$HOME/.bashrc"
add_to_path "$HOME/.zshrc"
add_to_path "$HOME/.profile"

# Symlink to bin
if $IS_TERMUX; then
    ln -sf "$SYJ_HOME/syj" "$PREFIX/bin/syj" 2>/dev/null && ok "Linked to $PREFIX/bin/syj"
else
    sudo ln -sf "$SYJ_HOME/syj" "/usr/local/bin/syj" 2>/dev/null || \
        ln -sf "$SYJ_HOME/syj" "$HOME/.local/bin/syj" 2>/dev/null || true
fi

# ── Initial config ────────────────────────────────────────────────────────────
CONFIG_FILE="$SYJ_HOME/config/settings.json"
if [ ! -f "$CONFIG_FILE" ]; then
    step "Creating default configuration..."
    cat > "$CONFIG_FILE" << 'JSONEOF'
{
  "version": "1.0.0",
  "user": {
    "name": "",
    "email": "",
    "company": ""
  },
  "api_keys": {
    "anthropic": "",
    "github": ""
  },
  "preferences": {
    "theme": "dark",
    "currency": "INR",
    "currency_symbol": "₹",
    "gst_rate": 18.0
  },
  "monitoring": {
    "sites": []
  }
}
JSONEOF
    ok "Default config created"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}════════════════════════════════════════════${RESET}"
echo -e "${GREEN}${BOLD}  ✅  SYJ ONE installed successfully!${RESET}"
echo -e "${GREEN}${BOLD}════════════════════════════════════════════${RESET}"
echo ""
echo -e "  ${BOLD}Restart your terminal, then run:${RESET}"
echo ""
echo -e "    ${CYAN}syj${RESET}              — Interactive menu"
echo -e "    ${CYAN}syj config setup${RESET} — Add API keys (Anthropic, GitHub)"
echo -e "    ${CYAN}syj ai${RESET}           — AI Workspace"
echo -e "    ${CYAN}syj seo${RESET}          — SEO Intelligence"
echo -e "    ${CYAN}syj shield${RESET}       — Cyber Shield"
echo -e "    ${CYAN}syj --help${RESET}       — All commands"
echo ""
echo -e "  ${YELLOW}Powered by Sayanjali Nexus | shalimoosavi@gmail.com${RESET}"
echo ""
