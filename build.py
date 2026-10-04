"""Static site generator for the academic website.

Run ``python build.py`` to build the site into ``dist/``, or
``python build.py --serve`` to build and preview it at http://localhost:8000.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import re
import shutil
import sys
from pathlib import Path

from sitegen import pages
from sitegen.core import DIST_DIR, PUBLIC_DIR, SRC_DIR, load_content

CSS_FILE = SRC_DIR / "styles" / "main.css"
JS_FILE = SRC_DIR / "scripts" / "main.js"


def build() -> list[Path]:
    """Render every page, copy static assets, and return the list of built pages."""
    content = load_content()
    site = content["site"]

    DIST_DIR.mkdir(parents=True, exist_ok=True)

    built: list[tuple[str, str]] = [
        ("index.html", pages.home_page(content, depth=0)),
        ("about/index.html", pages.about_page(content, depth=1)),
        ("research/index.html", pages.research_page(content, depth=1)),
        ("cv/index.html", pages.cv_page(content, depth=1)),
        ("writing/index.html", pages.writing_page(content, depth=1)),
        ("resources/index.html", pages.documents_page(content, depth=1)),
        ("contact/index.html", pages.contact_page(content, depth=1)),
        ("404.html", pages.not_found_page(content, depth=0)),
    ]
    for project in content["projects"]:
        built.append((f"research/{project['slug']}/index.html", pages.project_page(project, site, depth=2)))

    written: list[Path] = []
    for relative_path, html in built:
        target = DIST_DIR / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        written.append(target)

    written += copy_static_files()

    sitemap = pages.sitemap_xml(content)
    if sitemap:
        (DIST_DIR / "sitemap.xml").write_text(sitemap, encoding="utf-8")
        written.append(DIST_DIR / "sitemap.xml")

    base = str(site.get("baseUrl") or "").strip().rstrip("/")
    robots_lines = ["User-agent: *", "Allow: /"]
    if base:
        robots_lines.append(f"Sitemap: {base}/sitemap.xml")
    (DIST_DIR / "robots.txt").write_text("\n".join(robots_lines) + "\n", encoding="utf-8")
    written.append(DIST_DIR / "robots.txt")

    return written


def copy_static_files() -> list[Path]:
    """Copy public/ and the compiled CSS/JS into dist/."""
    copied: list[Path] = []

    if PUBLIC_DIR.is_dir():
        for source in PUBLIC_DIR.rglob("*"):
            if source.is_dir():
                continue
            target = DIST_DIR / source.relative_to(PUBLIC_DIR)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.append(target)

    for source, relative_path in ((CSS_FILE, "assets/main.css"), (JS_FILE, "assets/main.js")):
        target = DIST_DIR / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied.append(target)

    return copied


# --------------------------------------------------------------------------
# Link checking
# --------------------------------------------------------------------------

LINK_RE = re.compile(r'(?:href|src)="([^"]+)"')


def check_links() -> list[str]:
    """Verify that every relative link and asset in dist/ resolves to a file."""
    problems: list[str] = []
    for html_file in sorted(DIST_DIR.rglob("*.html")):
        markup = html_file.read_text(encoding="utf-8")
        for reference in LINK_RE.findall(markup):
            reference = reference.strip()
            if not reference or reference.startswith(("#", "http", "mailto:", "tel:", "data:", "//")):
                continue
            target = (html_file.parent / reference.split("#")[0].split("?")[0]).resolve()
            if reference.endswith("/"):
                target = target / "index.html"
            if not target.exists():
                problems.append(f"{html_file.relative_to(DIST_DIR)} -> {reference}")
    return problems


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def serve(directory: Path, port: int) -> None:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), handler) as httpd:
        print(f"Serving {directory} at http://localhost:{port}/  (Ctrl+C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the static academic website.")
    parser.add_argument("--serve", action="store_true", help="build, then serve dist/ locally")
    parser.add_argument("--port", type=int, default=8000, help="port used with --serve (default: 8000)")
    parser.add_argument("--out", default=None, help="output directory (default: dist/)")
    parser.add_argument(
        "--allow-broken-links",
        action="store_true",
        help="exit successfully even when internal links are missing (useful while drafting)",
    )
    args = parser.parse_args()

    global DIST_DIR
    if args.out:
        DIST_DIR = Path(args.out).resolve()

    written = build()
    print(f"Built {len(written)} files into {DIST_DIR}")

    problems = check_links()
    if problems:
        print("\nBroken local links or missing files:")
        for problem in problems:
            print(f"  - {problem}")
        if not args.serve and not args.allow_broken_links:
            print(
                "\nBuild failed. Fix the paths above (a document entry points at a file "
                "that is not in public/), or pass --allow-broken-links while drafting."
            )
            return 1
        print("\nContinuing anyway.")
    else:
        print("All local links resolve.")

    if args.serve:
        serve(DIST_DIR, args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())