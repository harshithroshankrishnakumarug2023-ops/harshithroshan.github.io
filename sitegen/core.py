"""Shared helpers for the site generator.

The build is deliberately small and dependency-free: content lives in JSON files
under ``content/``, this module knows how to turn that content into a page, and
``build.py`` writes the result to ``dist/``.

Everything is rendered with relative links, so the built site works unchanged
from a repository root, from ``/my-repo/`` on GitHub Pages, and from a local
file server.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content"
PUBLIC_DIR = ROOT / "public"
SRC_DIR = ROOT / "src"
DIST_DIR = ROOT / "dist"

# --------------------------------------------------------------------------
# Content loading
# --------------------------------------------------------------------------


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_content() -> dict:
    """Load every content file once, at the start of a build."""
    content = {
        "site": _read_json(CONTENT_DIR / "site.json"),
        "home": _read_json(CONTENT_DIR / "home.json"),
        "about": _read_json(CONTENT_DIR / "about.json"),
        "skills": _read_json(CONTENT_DIR / "skills.json"),
        "research": _read_json(CONTENT_DIR / "research.json"),
        "cv": _read_json(CONTENT_DIR / "cv.json"),
        "documents": _read_json(CONTENT_DIR / "documents.json"),
        "publications": _read_json(CONTENT_DIR / "publications.json"),
        "writing": _read_json(CONTENT_DIR / "writing.json"),
    }

    projects = []
    projects_dir = CONTENT_DIR / "projects"
    if projects_dir.is_dir():
        for project_file in sorted(projects_dir.glob("*.json")):
            # Files beginning with "_" are templates / notes and are skipped.
            if project_file.name.startswith("_"):
                continue
            project = _read_json(project_file)
            project.setdefault("slug", project_file.stem)
            projects.append(project)

    projects.sort(key=lambda item: (str(item.get("year", "")), item.get("title", "")), reverse=True)
    content["projects"] = projects
    content["projects_by_slug"] = {project["slug"]: project for project in projects}
    return content


# --------------------------------------------------------------------------
# Small text helpers
# --------------------------------------------------------------------------

PLACEHOLDER_RE = re.compile(r"^\[[^\[\]]+\]$")
MARKDOWN_LINK_RE = re.compile(r"\[([^\[\]]+)\]\(([^)\s]+)\)")
BARE_URL_RE = re.compile(r"(?<![\"'=>])\bhttps?://[^\s<>\"')]+")
EMPHASIS_RE = re.compile(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])")
SAFE_URL_RE = re.compile(r"^(https?:|mailto:|tel:|/|\.\.?/|[A-Za-z0-9_\-./]+\.[A-Za-z0-9]+)")

# Files a browser can render directly; everything else is offered as a download.
VIEWABLE_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".txt",
}


def esc(value) -> str:
    """Escape a value for HTML output."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def is_placeholder(value) -> bool:
    """True for the ``[bracketed]`` placeholder text used in content files."""
    if not isinstance(value, str):
        return False
    return bool(PLACEHOLDER_RE.match(value.strip()))


def _link(label: str, url: str, *, classes: str = "", external: bool = False) -> str:
    attrs = [f'href="{esc(url)}"']
    if classes:
        attrs.append(f'class="{esc(classes)}"')
    if external:
        attrs.extend(['target="_blank"', 'rel="noopener noreferrer"'])
    return f"<a {' '.join(attrs)}>{label}</a>"


def rich_text(value, *, classes: str = "") -> str:
    """Escape text, then honour a tiny subset of markup.

    Supported: ``[label](url)`` links, bare URLs, *emphasis*, and ``[square
    bracketed]`` placeholder text (rendered in a muted style).
    """
    if not value:
        return ""
    raw = str(value).strip()
    if is_placeholder(raw):
        return f'<span class="ph" title="Placeholder — replace this in your content file">{esc(raw)}</span>'

    text = esc(raw)
    text = MARKDOWN_LINK_RE.sub(
        lambda m: (
            _link(m.group(1), m.group(2), classes="text-link")
            if SAFE_URL_RE.match(m.group(2))
            else m.group(0)
        ),
        text,
    )
    text = BARE_URL_RE.sub(lambda m: _link(esc(m.group(0)), m.group(0), classes="text-link", external=True), text)
    text = EMPHASIS_RE.sub(r"<em>\1</em>", text)

    if classes:
        return f'<span class="{esc(classes)}">{text}</span>'
    return text


def paragraphs(values, *, classes: str = "") -> str:
    """Render a list of strings as <p> elements."""
    if isinstance(values, str):
        values = [values]
    body = "".join(f"<p>{rich_text(value)}</p>" for value in values or [] if str(value).strip())
    return f'<div class="{esc(classes)}">{body}</div>' if classes else body


def inline_list(values, *, label: str = "") -> str:
    """Render a short list of strings as `Label: a, b and c`."""
    items = [str(value).strip() for value in (values or []) if str(value).strip()]
    if not items:
        return ""
    prefix = f'<span class="meta-label">{esc(label)}</span> ' if label else ""
    return f'<p class="meta-line">{prefix}{", ".join(esc(item) for item in items)}</p>'


def extension_of(path: str) -> str:
    name = str(path).split("?")[0]
    return ("." + name.rsplit(".", 1)[-1].lower()) if "." in name.rsplit("/", 1)[-1] else ""


def is_viewable(path: str) -> bool:
    return extension_of(path) in VIEWABLE_EXTENSIONS


# --------------------------------------------------------------------------
# URLs
# --------------------------------------------------------------------------


def page_depth(path: str) -> int:
    """How many directories deep a built page sits below the site root."""
    return path.count("/")


def rel(depth: int, target: str) -> str:
    """Return a relative URL from a page at `depth` to a root-relative target."""
    prefix = "../" * depth
    target = target.lstrip("/")
    if not target:
        return prefix or "./"
    return prefix + target


def resolve_link(depth: int, link: dict) -> str:
    """Build an href for a content link: {'file': ...} or {'url': ...}."""
    if not isinstance(link, dict):
        return ""
    target = str(link.get("url") or link.get("file") or "").strip()
    if not target:
        return ""
    if link.get("url"):
        return target
    return rel(depth, target)


# --------------------------------------------------------------------------
# Layout components
# --------------------------------------------------------------------------

FONT_STACK = (
    "https://fonts.googleapis.com/css2"
    "?family=Inter:wght@400;500;600"
    "&family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400"
    "&display=swap"
)


def head_tags(site: dict, *, title: str, description: str, path: str, depth: int) -> str:
    """Meta tags, fonts and stylesheet for one page."""
    page_title = title if title == site["siteTitle"] else f"{title} — {site['name']}"
    base_url = str(site.get("baseUrl") or "").strip().rstrip("/")
    page_path = path.replace("index.html", "")
    canonical = f"{base_url}/{page_path}" if base_url else ""
    og_type = "website" if path == "index.html" else "article"

    tags = [
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{esc(page_title)}</title>",
        f'<meta name="description" content="{esc(description)}">',
        f'<meta name="author" content="{esc(site["name"])}">',
        '<meta name="color-scheme" content="light">',
        '<meta name="theme-color" content="#fbfbfa">',
    ]
    if canonical:
        tags.append(f'<link rel="canonical" href="{esc(canonical)}">')
    tags += [
        f'<meta property="og:type" content="{og_type}">',
        f'<meta property="og:site_name" content="{esc(site["name"])}">',
        f'<meta property="og:title" content="{esc(page_title)}">',
        f'<meta property="og:description" content="{esc(description)}">',
        f'<meta property="og:locale" content="{esc(str(site.get("language") or "en")).replace("-", "_")}">',
    ]
    if canonical:
        tags.append(f'<meta property="og:url" content="{esc(canonical)}">')

    # Social preview image. Optional: drop a 1200x630 PNG/JPG into public/images/
    # and set "ogImage" in content/site.json to share images that look right.
    og_image = str(site.get("ogImage") or "").strip()
    if og_image and base_url:
        image_url = og_image if og_image.startswith("http") else f"{base_url}/{og_image.lstrip('/')}"
        tags.append(f'<meta property="og:image" content="{esc(image_url)}">')
        if site.get("ogImageAlt"):
            tags.append(f'<meta property="og:image:alt" content="{esc(site["ogImageAlt"])}">')

    tags += [
        f'<meta name="twitter:card" content="{"summary_large_image" if og_image else "summary"}">',
        '<meta name="twitter:title" content="' + esc(page_title) + '">',
        '<meta name="twitter:description" content="' + esc(description) + '">',
        '<link rel="icon" href="' + rel(depth, "favicon.svg") + '" type="image/svg+xml">',
        '<link rel="apple-touch-icon" href="' + rel(depth, "favicon.svg") + '">',
        '<link rel="preconnect" href="https://fonts.googleapis.com">',
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
        f'<link rel="stylesheet" href="{FONT_STACK}">',
        f'<link rel="stylesheet" href="{rel(depth, "assets/main.css")}">',
        # Adds the "js" class as early as possible so CSS can hide controls that
        # need JavaScript, and so the mobile menu can collapse without flashing.
        "<script>document.documentElement.classList.add('js')</script>",
    ]
    return "\n    ".join(tags)


def header(site: dict, *, depth: int, current: str) -> str:
    """Site header: name on the left, primary navigation on the right."""
    items = []
    for entry in site.get("nav", []):
        label = entry.get("label", "")
        target = str(entry.get("path", "")).strip("/")
        href = rel(depth, entry.get("path", ""))
        is_active = target == current
        attrs = [f'href="{esc(href)}"']
        if is_active:
            attrs.append('aria-current="page"')
        items.append(f'<li class="nav-item"><a class="nav-link" {" ".join(attrs)}>{esc(label)}</a></li>')

    return f"""<header class="site-header">
      <div class="container site-header-inner">
        <a class="site-name" href="{rel(depth, "")}">{esc(site["name"])}</a>
        <nav class="site-nav" aria-label="Primary">
          <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="primary-navigation">
            <span class="nav-toggle-label">Menu</span>
          </button>
          <ul class="nav-list" id="primary-navigation">
            {"".join(items)}
          </ul>
        </nav>
      </div>
    </header>"""


def footer(site: dict, *, depth: int) -> str:
    """Minimal footer: name, role, external links, copyright."""
    links = []
    for key in ("email", "scholar", "github", "linkedin"):
        entry = social_link(site, key, depth=depth, inline=True)
        if entry:
            links.append(entry)
    link_line = (
        f'<p class="footer-links">{" · ".join(links)}</p>' if links else '<p class="footer-links ph">Add your links in content/site.json</p>'
    )
    year = str(site.get("copyrightYear") or "")

    return f"""<footer class="site-footer">
      <div class="container footer-inner">
        <div class="footer-identity">
          <p class="footer-name">{esc(site["name"])}</p>
          <p class="footer-role">{esc(site.get("footerRole") or site.get("role") or "")}</p>
        </div>
        {link_line}
        <p class="footer-copyright">&copy; {esc(year)} {esc(site["name"])}</p>
      </div>
    </footer>"""


def social_link(site: dict, key: str, *, depth: int, inline: bool = False) -> str:
    """Render one of the site-wide links (email / scholar / github / linkedin).

    When no URL has been configured yet, a clearly marked placeholder is shown
    instead of an invented or broken link.
    """
    labels = {
        "email": "Email",
        "scholar": "Google Scholar",
        "github": "GitHub",
        "linkedin": "LinkedIn",
    }
    label = labels.get(key, key.title())
    configured = str((site.get("links") or {}).get(key) or "").strip()

    if not configured:
        return (
            '<span class="ph" title="Placeholder — add this link in content/site.json">'
            f"[{esc(label)}]</span>"
        )

    if key == "email" and not configured.startswith(("mailto:", "http")):
        configured = f"mailto:{configured}"
    external = not configured.startswith("mailto:")
    if external and configured.startswith("/"):
        configured = rel(depth, configured)

    cls = "social-link" if inline else "btn btn-quiet"
    return _link(esc(label), esc(configured), classes=cls, external=external)


def section(title: str, body: str, *, anchor: str = "", lead: str = "") -> str:
    """A page section: hairline rule, serif heading, optional lead paragraph."""
    if not body:
        return ""
    id_attr = f' id="{esc(anchor)}"' if anchor else ""
    lead_html = f'<p class="section-lead">{rich_text(lead)}</p>' if lead else ""
    heading = f'<h2 class="section-title">{esc(title)}</h2>' if title else ""
    return f'<section class="section"{id_attr}>{heading}{lead_html}{body}</section>'


def empty_state(message: str) -> str:
    return f'<p class="empty-state">{rich_text(message)}</p>'


def definition_list(rows, *, classes: str = "") -> str:
    """Render (label, value) pairs, skipping empty values."""
    items = []
    for label, value in rows:
        value = str(value or "").strip()
        if not value:
            continue
        items.append(
            f'<div class="def-row"><dt class="def-term">{esc(label)}</dt>'
            f'<dd class="def-desc">{rich_text(value)}</dd></div>'
        )
    if not items:
        return ""
    class_attr = f" {classes}" if classes else ""
    return f'<dl class="def-list{class_attr}">{"".join(items)}</dl>'


def button(label: str, href: str, *, variant: str = "btn", external: bool = False, extra: str = "") -> str:
    attrs = ""
    if external:
        attrs = ' target="_blank" rel="noopener noreferrer"'
    if extra:
        attrs = f"{attrs} {extra}"
    return f'<a class="{esc(variant)}" href="{esc(href)}"{attrs}>{label}</a>'


def render_page(
    *,
    site: dict,
    path: str,
    title: str,
    description: str,
    body: str,
    body_class: str = "",
    extra_head: str = "",
) -> str:
    """Wrap page content in the shared layout."""
    depth = page_depth(path)
    current = path.replace("index.html", "").strip("/")
    body_attr = f' class="{esc(body_class)}"' if body_class else ""

    return f"""<!DOCTYPE html>
<html lang="{esc(site.get("language") or "en")}">
  <head>
    {head_tags(site, title=title, description=description, path=path, depth=depth)}
    {extra_head}
  </head>
  <body{body_attr}>
    <a class="skip-link" href="#main">Skip to content</a>
    {header(site, depth=depth, current=current)}
    <main id="main" class="site-main container">
{body}
    </main>
    {footer(site, depth=depth)}
    <script src="{rel(depth, "assets/main.js")}" defer></script>
  </body>
</html>
"""