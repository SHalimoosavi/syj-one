"""
SYJ ONE — SEO Intelligence  (syj seo)
Full on-page SEO audit: meta, headings, images, links, robots, sitemap.
Inspired by the NexusRank AI ecosystem.
"""

import re
import time
from urllib.parse import urljoin, urlparse

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich import box

from core.utils import fetch, clean_url, extract_domain, section, success, error, warn, info

console = Console()

try:
    from html.parser import HTMLParser
except ImportError:
    HTMLParser = None


# ── HTML Parser ───────────────────────────────────────────────────────────────

class _SEOParser(HTMLParser if HTMLParser else object):
    def __init__(self):
        super().__init__()
        self.title          = ""
        self.meta           = {}          # name/property → content
        self.headings       = {f"h{i}": [] for i in range(1, 7)}
        self.links          = []          # (href, text)
        self.images         = []          # (src, alt)
        self.canonical      = ""
        self.lang           = ""
        self._in_title      = False
        self._in_heading    = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag in self.headings:
            self._in_heading = tag
        elif tag == "meta":
            name = attrs.get("name") or attrs.get("property") or ""
            if name and "content" in attrs:
                self.meta[name.lower()] = attrs["content"]
        elif tag == "link":
            if attrs.get("rel") == "canonical":
                self.canonical = attrs.get("href", "")
        elif tag == "html":
            self.lang = attrs.get("lang", "")
        elif tag == "a":
            self.links.append((attrs.get("href", ""), attrs.get("title", "")))
        elif tag == "img":
            self.images.append((attrs.get("src", ""), attrs.get("alt", "")))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in self.headings:
            self._in_heading = None

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._in_heading:
            self.headings[self._in_heading].append(data.strip())


# ── Audit functions ───────────────────────────────────────────────────────────

def _score_badge(score: int) -> str:
    if score >= 80: return f"[bold green]{score}/100[/bold green]"
    if score >= 50: return f"[bold yellow]{score}/100[/bold yellow]"
    return f"[bold red]{score}/100[/bold red]"


def _status(ok: bool, msg_ok: str, msg_fail: str) -> str:
    return f"[green]✓[/green] {msg_ok}" if ok else f"[red]✗[/red] {msg_fail}"


def audit(url: str) -> None:
    url = clean_url(url)
    domain = extract_domain(url)

    console.print(Panel(
        f"[bold cyan]🔍 SEO INTELLIGENCE[/bold cyan]\n[dim]Auditing:[/dim] [white]{url}[/white]",
        border_style="cyan"
    ))

    # ── Fetch page ────────────────────────────────────────────────────────────
    with console.status("[cyan]Fetching page...[/cyan]"):
        t0 = time.time()
        resp = fetch(url)
        load_time = round(time.time() - t0, 2)

    if not resp:
        error("Could not fetch the URL. Check your internet or the address.")
        return

    # ── Parse HTML ────────────────────────────────────────────────────────────
    parser = _SEOParser()
    try:
        parser.feed(resp.text)
    except Exception:
        pass

    content_type = resp.headers.get("Content-Type", "")
    word_count   = len(re.findall(r"\b\w+\b", re.sub(r"<[^>]+>", " ", resp.text)))
    status_code  = resp.status_code

    # ── Robots.txt ────────────────────────────────────────────────────────────
    with console.status("[cyan]Checking robots.txt...[/cyan]"):
        robots_url  = f"https://{domain}/robots.txt"
        robots_resp = fetch(robots_url)
        robots_ok   = robots_resp and robots_resp.status_code == 200
        robots_text = robots_resp.text if robots_ok else ""

    # ── Sitemap ───────────────────────────────────────────────────────────────
    with console.status("[cyan]Checking sitemap...[/cyan]"):
        sitemap_locs = []
        for sm in ["/sitemap.xml", "/sitemap_index.xml", "/sitemap/"]:
            sm_resp = fetch(f"https://{domain}{sm}")
            if sm_resp and sm_resp.status_code == 200 and "xml" in sm_resp.text[:100].lower():
                sitemap_locs = re.findall(r"<loc>(.*?)</loc>", sm_resp.text)
                break

    # ── Score calculation ─────────────────────────────────────────────────────
    score = 0
    title = parser.title.strip()
    description = parser.meta.get("description", "")
    keywords    = parser.meta.get("keywords", "")
    og_title    = parser.meta.get("og:title", "")
    og_desc     = parser.meta.get("og:description", "")
    og_image    = parser.meta.get("og:image", "")
    twitter_card= parser.meta.get("twitter:card", "")

    checks = []

    # Title
    title_len = len(title)
    t_ok = 30 <= title_len <= 65
    checks.append((_status(bool(title), "Title tag present", "Title tag MISSING"), 10))
    checks.append((_status(t_ok, f"Title length optimal ({title_len} chars)", f"Title length off ({title_len} chars — target 30-65)"), 5))
    score += 10 if title else 0
    score += 5 if t_ok else 0

    # Description
    desc_len = len(description)
    d_ok = 120 <= desc_len <= 165
    checks.append((_status(bool(description), "Meta description present", "Meta description MISSING"), 10))
    checks.append((_status(d_ok, f"Description length optimal ({desc_len} chars)", f"Description length off ({desc_len} chars — target 120-165)"), 5))
    score += 10 if description else 0
    score += 5 if d_ok else 0

    # H1
    h1s = parser.headings.get("h1", [])
    checks.append((_status(len(h1s) == 1, f"Single H1 tag found", f"{len(h1s)} H1 tag(s) found (should be exactly 1)"), 10))
    score += 10 if len(h1s) == 1 else 0

    # Images
    imgs_without_alt = [s for s, a in parser.images if not a]
    checks.append((_status(not imgs_without_alt, "All images have alt text",
                            f"{len(imgs_without_alt)} image(s) missing alt text"), 8))
    score += 8 if not imgs_without_alt else 0

    # OG tags
    checks.append((_status(bool(og_title and og_desc and og_image), "Open Graph tags complete", "Open Graph tags incomplete"), 8))
    score += 8 if (og_title and og_desc and og_image) else 0

    # Twitter
    checks.append((_status(bool(twitter_card), "Twitter Card meta present", "Twitter Card meta missing"), 4))
    score += 4 if twitter_card else 0

    # Canonical
    checks.append((_status(bool(parser.canonical), "Canonical URL set", "Canonical URL not set"), 6))
    score += 6 if parser.canonical else 0

    # Lang
    checks.append((_status(bool(parser.lang), f"HTML lang attribute: {parser.lang}", "HTML lang attribute missing"), 4))
    score += 4 if parser.lang else 0

    # Load time
    lt_ok = load_time < 3
    checks.append((_status(lt_ok, f"Page load time: {load_time}s", f"Slow load time: {load_time}s (target <3s)"), 10))
    score += 10 if lt_ok else (5 if load_time < 5 else 0)

    # Robots
    checks.append((_status(robots_ok, "robots.txt found", "robots.txt not found"), 5))
    score += 5 if robots_ok else 0

    # Sitemap
    checks.append((_status(bool(sitemap_locs), f"Sitemap found ({len(sitemap_locs)} URLs)", "Sitemap not found"), 5))
    score += 5 if sitemap_locs else 0

    # HTTPS
    is_https = url.startswith("https://")
    checks.append((_status(is_https, "HTTPS enabled", "Not HTTPS — security risk"), 10))
    score += 10 if is_https else 0

    # ── Print results ─────────────────────────────────────────────────────────

    section("📊 SEO SCORE")
    console.print(f"  Overall Score: {_score_badge(score)}")
    console.print(f"  [dim]Status:[/dim] {status_code}  [dim]Load:[/dim] {load_time}s  [dim]Words:[/dim] {word_count}")
    console.print()

    section("📋 PAGE META")
    meta_table = Table(show_header=False, box=box.SIMPLE, padding=(0,1))
    meta_table.add_column("key",  style="dim", width=22)
    meta_table.add_column("val",  style="white")

    meta_table.add_row("Title",        title or "[red]MISSING[/red]")
    meta_table.add_row("Description",  description or "[red]MISSING[/red]")
    meta_table.add_row("Keywords",     keywords or "[dim]not set[/dim]")
    meta_table.add_row("Canonical",    parser.canonical or "[dim]not set[/dim]")
    meta_table.add_row("OG Title",     og_title or "[dim]not set[/dim]")
    meta_table.add_row("OG Desc",      og_desc[:80] + "…" if len(og_desc)>80 else og_desc or "[dim]not set[/dim]")
    meta_table.add_row("OG Image",     og_image or "[dim]not set[/dim]")
    meta_table.add_row("Twitter Card", twitter_card or "[dim]not set[/dim]")
    meta_table.add_row("HTML Lang",    parser.lang or "[dim]not set[/dim]")
    console.print(meta_table)

    section("🗂️ HEADINGS")
    for lvl in ("h1","h2","h3","h4","h5","h6"):
        hs = parser.headings[lvl]
        if hs:
            for h in hs[:3]:
                console.print(f"  [{lvl.upper()}] {h[:80]}")
            if len(hs) > 3:
                console.print(f"  [dim]...and {len(hs)-3} more[/dim]")

    section("🔗 LINKS")
    internal = [l for l, _ in parser.links if l and (domain in l or l.startswith("/"))]
    external = [l for l, _ in parser.links if l and l.startswith("http") and domain not in l]
    console.print(f"  [green]Internal:[/green] {len(internal)}   [cyan]External:[/cyan] {len(external)}   [dim]Total:[/dim] {len(parser.links)}")

    section("🖼️ IMAGES")
    console.print(f"  Total: {len(parser.images)}   Missing alt: [{'red' if imgs_without_alt else 'green'}]{len(imgs_without_alt)}[/{'red' if imgs_without_alt else 'green'}]")

    section("✅ AUDIT CHECKS")
    for msg, _ in checks:
        console.print(f"  {msg}")

    section("🤖 ROBOTS & SITEMAP")
    console.print(f"  robots.txt: {'[green]✓ Found[/green]' if robots_ok else '[red]✗ Not found[/red]'}")
    if robots_ok and robots_text:
        # Show first 3 non-blank lines
        for line in robots_text.splitlines()[:5]:
            if line.strip():
                console.print(f"  [dim]{line}[/dim]")
    console.print(f"  sitemap.xml: {'[green]✓ Found (' + str(len(sitemap_locs)) + ' URLs)[/green]' if sitemap_locs else '[red]✗ Not found[/red]'}")

    # ── Quick recommendations ─────────────────────────────────────────────────
    section("💡 QUICK WINS")
    recs = []
    if not title:                     recs.append("Add a <title> tag with your primary keyword")
    if not description:               recs.append("Add a meta description (120-165 chars) with a call to action")
    if len(h1s) != 1:                 recs.append("Ensure exactly one <h1> tag per page")
    if imgs_without_alt:              recs.append(f"Add alt text to {len(imgs_without_alt)} image(s)")
    if not og_title:                  recs.append("Add Open Graph tags for better social sharing")
    if not parser.canonical:          recs.append("Set a canonical URL to prevent duplicate content")
    if load_time >= 3:                recs.append("Optimize page speed (target <3s): compress images, minify CSS/JS")
    if not sitemap_locs:              recs.append("Create a sitemap.xml and submit to Google Search Console")
    if not parser.lang:               recs.append("Add lang attribute to <html> tag (e.g. lang='en')")

    if recs:
        for i, r in enumerate(recs, 1):
            console.print(f"  [yellow]{i}.[/yellow] {r}")
    else:
        success("Great on-page SEO! Keep monitoring for off-page signals.")

    console.print()


def run(args=None) -> None:
    """syj seo [url]"""
    args = args or []
    if args and not args[0].startswith("-"):
        url = args[0]
    else:
        url = Prompt.ask("[bold green]Enter URL to audit[/bold green]", default="https://example.com")
    audit(url)
