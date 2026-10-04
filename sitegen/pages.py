"""Page builders.

Each function returns the HTML for one page body. ``build.py`` handles writing
them to disk; nothing here touches the filesystem.
"""

from __future__ import annotations

from .core import (
    button,
    definition_list,
    empty_state,
    esc,
    inline_list,
    is_viewable,
    paragraphs,
    rel,
    render_page,
    resolve_link,
    rich_text,
    section,
    social_link,
)

# --------------------------------------------------------------------------
# Shared blocks
# --------------------------------------------------------------------------


def link_row(links: list) -> str:
    """A row of understated text links, e.g. [Project page] [PDF] [Materials]."""
    items = []
    for link in links:
        if isinstance(link, str):
            continue
        href = link.get("href", "")
        label = link.get("label", "")
        if not href or not label:
            continue
        external = link.get("external", False)
        attrs = ' target="_blank" rel="noopener noreferrer"' if external else ""
        if link.get("download"):
            attrs += ' download'
        items.append(f'<li><a class="text-link" href="{esc(href)}"{attrs}>{esc(label)}</a></li>')
    if not items:
        return ""
    return f'<ul class="link-row">{"".join(items)}</ul>'


def document_links(doc: dict, depth: int, *, label_prefix: str = "") -> list:
    """Turn one entry of the document library into a list of links."""
    file_path = str(doc.get("file") or "").strip()
    if not file_path:
        return []
    href = rel(depth, file_path)
    name = file_path.rsplit("/", 1)[-1]
    prefix = f"{label_prefix} " if label_prefix else ""
    links = []
    if is_viewable(file_path):
        links.append({"label": f"{prefix}View", "href": href, "external": True})
    links.append({"label": f"{prefix}Download", "href": href, "download": True, "title": name})
    return links


def document_row(doc: dict, depth: int) -> str:
    """One row in the document library (list layout, not a card)."""
    category_labels = {c["id"]: c["label"] for c in CATEGORY_LABELS}
    meta_parts = [
        str(doc.get("type") or "").strip(),
        str(doc.get("year") or "").strip(),
        category_labels.get(str(doc.get("category") or ""), ""),
    ]
    meta = " · ".join(part for part in meta_parts if part)
    tags = [str(tag).strip() for tag in doc.get("tags", []) if str(tag).strip()]
    file_path = str(doc.get("file") or "").strip()
    href = rel(depth, file_path) if file_path else ""

    title_html = (
        f'<h3 class="doc-title"><a class="text-link" href="{esc(href)}">{esc(doc.get("title", ""))}</a></h3>'
        if href
        else f'<h3 class="doc-title">{esc(doc.get("title", ""))}</h3>'
    )
    tags_html = f'<p class="doc-tags">{", ".join(esc(tag) for tag in tags)}</p>' if tags else ""
    description_html = (
        f'<p class="doc-desc">{rich_text(doc.get("description", ""))}</p>' if doc.get("description") else ""
    )

    search_blob = " ".join(
        [str(doc.get("title", "")), str(doc.get("description", "")), " ".join(tags), str(doc.get("type", ""))]
    ).lower()

    return f"""<li class="doc-row" data-doc data-title="{esc(search_blob)}" data-type="{esc(str(doc.get("type") or ""))}" data-year="{esc(str(doc.get("year") or ""))}" data-category="{esc(str(doc.get("category") or ""))}" data-project="{esc(str(doc.get("project") or ""))}">
          <div class="doc-main">
            <p class="doc-meta">{esc(meta)}</p>
            {title_html}
            {description_html}
            {tags_html}
          </div>
          <div class="doc-actions">{link_row(document_links(doc, depth))}</div>
        </li>"""


# Filled in by documents_page() so document_row() can label categories.
CATEGORY_LABELS: list = []


def project_links(project: dict, depth: int, *, include_self: bool = True) -> list:
    """Links shown under a project on the research list and project pages."""
    slug = str(project.get("slug", "")).strip()
    links = []
    if slug and include_self:
        links.append({"label": "Project page", "href": rel(depth, f"research/{slug}/")})
    for doc in project.get("documents", []):
        href = resolve_link(depth, doc)
        if href:
            links.append({"label": str(doc.get("label") or "Document"), "href": href, "external": is_viewable(str(doc.get("file") or ""))})
    for link in project.get("externalLinks", []):
        href = resolve_link(depth, link)
        if href:
            links.append({"label": str(link.get("label") or "Link"), "href": href, "external": True})
    return links


def project_entry(project: dict, depth: int) -> str:
    """A project in the research list: compact, no card, no overload."""
    slug = str(project.get("slug", "")).strip()
    href = rel(depth, f"research/{slug}/")
    meta_parts = [str(project.get("year") or "").strip(), str(project.get("status") or "").strip()]
    meta = " · ".join(part for part in meta_parts if part)

    return f"""<li class="entry">
          <p class="entry-meta">{esc(meta)}</p>
          <h3 class="entry-title"><a class="text-link" href="{esc(href)}">{esc(project.get("title", ""))}</a></h3>
          <p class="entry-desc">{rich_text(project.get("short", ""))}</p>
          {inline_list(project.get("methods", []), label="Methods")}
          {inline_list(project.get("focus", []), label="Focus")}
          {link_row(project_links(project, depth))}
        </li>"""


def project_page(project: dict, site: dict, *, depth: int) -> str:
    """A full project page."""
    slug = str(project.get("slug", "")).strip()
    meta_parts = [str(project.get("year") or "").strip(), str(project.get("status") or "").strip()]
    meta = " · ".join(part for part in meta_parts if part)

    method = project.get("method") or {}
    method_rows = [
        ("Participants", method.get("participants", "")),
        ("Design", method.get("design", "")),
        ("Measures", method.get("measures", "")),
        ("Stimuli", method.get("stimuli", "")),
        ("Task", method.get("task", "")),
        ("Procedure", method.get("procedure", "")),
        ("Software", ", ".join(str(item) for item in method.get("software", []) if str(item).strip())),
    ]
    analysis_row = [("Analysis", method.get("analysis", ""))]
    detail_rows = [
        ("Institution", project.get("institution", "")),
        ("Role", project.get("role", "")),
        ("Supervisor", project.get("supervisor", "")),
        ("Collaborators", ", ".join(str(item) for item in project.get("collaborators", []) if str(item).strip())),
        ("Methods", ", ".join(str(item) for item in project.get("methods", []) if str(item).strip())),
        ("Focus", ", ".join(str(item) for item in project.get("focus", []) if str(item).strip())),
        ("Skills", ", ".join(str(item) for item in project.get("skills", []) if str(item).strip())),
    ]

    question = project.get("researchQuestion", "")
    question_block = (
        f'<section class="section" id="research-question"><h2 class="section-title">Research question</h2>'
        f'<p class="question">{rich_text(question)}</p></section>'
        if question
        else ""
    )

    status_block = ""
    if str(project.get("currentStatus") or "").strip():
        status_block = (
            '<section class="section" id="status"><h2 class="section-title">Current status</h2>'
            f'<p class="status-line">{rich_text(project.get("currentStatus"))}</p></section>'
        )

    materials = link_row(project_links(project, depth, include_self=False))
    materials_block = (
        f'<section class="section" id="materials"><h2 class="section-title">Materials</h2>{materials}</section>'
        if materials
        else '<section class="section" id="materials"><h2 class="section-title">Materials</h2>'
        + empty_state("Materials for this project will be added as they become available.")
        + "</section>"
    )

    references = project.get("references", [])
    references_block = ""
    if references:
        items = "".join(
            f'<li class="reference">{rich_text(ref.get("reference", "") or ref)}{esc(" " + str(ref.get("doi", "")))}</li>'
            for ref in references
        )
        references_block = f'<section class="section" id="references"><h2 class="section-title">References</h2><ul class="reference-list">{items}</ul></section>'

    body = f"""
      <nav class="breadcrumb" aria-label="Breadcrumb"><a class="text-link" href="{rel(depth, "research/")}">Research</a><span aria-hidden="true"> / </span><span aria-current="page">{esc(project.get("title", ""))}</span></nav>
      <header class="page-header">
        <p class="entry-meta">{esc(meta)}</p>
        <h1 class="page-title">{esc(project.get("title", ""))}</h1>
        {link_row(project_links(project, depth, include_self=False))}
      </header>

      {section("Overview", paragraphs(project.get("description", [])))}
      {question_block}
      {section("Background", paragraphs(project.get("background", [])))}
      {section("Method", definition_list(method_rows))}
      {section("Analysis", definition_list(analysis_row))}
      {section("Project details", definition_list(detail_rows))}
      {status_block}
      {materials_block}
      {references_block}
    """

    return render_page(
        site=site,
        path=f"research/{slug}/index.html",
        title=str(project.get("title", "")),
        description=str(project.get("short", "")) or f"{project.get('title', '')} — research project.",
        body=body,
    )


def publications_block(content: dict, depth: int, *, heading: str, anchor: str, foot_link=None) -> str:
    """Publications grouped by category, or an elegant empty state."""
    data = content["publications"]
    entries = data.get("entries", [])
    inner = ""
    if not entries:
        inner = empty_state(data.get("emptyState", ""))
        if foot_link:
            label, href = foot_link
            inner += f'<p class="section-foot"><a class="text-link" href="{esc(href)}">{esc(label)}</a></p>'
    else:
        blocks = []
        for category in data.get("categories", []):
            group = [entry for entry in entries if entry.get("category") == category.get("id")]
            if not group:
                continue
            items = []
            for entry in group:
                meta_parts = [
                    str(entry.get("venue") or "").strip(),
                    str(entry.get("year") or "").strip(),
                    str(entry.get("status") or "").strip(),
                ]
                meta = " · ".join(part for part in meta_parts if part)
                links = []
                for link in entry.get("links", []):
                    href = resolve_link(depth, link)
                    if href:
                        links.append(
                            {
                                "label": str(link.get("label") or "Document"),
                                "href": href,
                                "external": is_viewable(str(link.get("file") or "")),
                            }
                        )
                if entry.get("externalUrl"):
                    links.append({"label": "External link", "href": str(entry["externalUrl"]), "external": True})
                if entry.get("doi"):
                    doi = str(entry["doi"])
                    doi_url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
                    links.append({"label": "DOI", "href": doi_url, "external": True})
                citation = f"{entry.get('authors', '')} ({entry.get('year', '')}). {entry.get('title', '')}"
                items.append(
                    f'<li class="entry citation"><p class="entry-meta">{esc(meta)}</p>'
                    f'<p class="entry-title plain">{esc(str(citation).strip())}</p>{link_row(links)}</li>'
                )
            blocks.append(
                f'<div class="pub-group"><h3 class="group-title">{esc(category.get("title", ""))}</h3>'
                f'<ul class="entry-list">{"".join(items)}</ul></div>'
            )
        inner = "".join(blocks)

    return section(heading, inner, anchor=anchor)


def person_jsonld(site: dict) -> str:
    """Minimal structured data for the homepage. Only grounded facts are used."""
    import json as _json

    profile = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": str(site.get("name", "")),
        "jobTitle": str(site.get("role", "")),
    }
    base = str(site.get("baseUrl") or "").strip().rstrip("/")
    if base:
        profile["url"] = f"{base}/"
    same_as = [str(value).strip() for value in (site.get("links") or {}).values() if str(value).strip()]
    same_as = [value for value in same_as if value.startswith("http")]
    if same_as:
        profile["sameAs"] = same_as
    return (
        '<script type="application/ld+json">'
        + _json.dumps(profile, ensure_ascii=False)
        + "</script>"
    )


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------


def home_page(content: dict, depth: int) -> str:
    site = content["site"]
    home = content["home"]
    project = content["projects_by_slug"].get(str(home.get("featuredProject") or ""))

    hero_links = [
        {"label": "CV", "href": rel(depth, "cv/")},
        {"label": "Research", "href": rel(depth, "research/")},
    ]
    for key in ("scholar", "linkedin", "email"):
        entry = social_link(site, key, depth=depth, inline=True)
        hero_links.append({"label_html": entry})

    themes = "".join(
        f'<div class="theme"><h3 class="theme-title">{esc(theme.get("title", ""))}</h3>'
        f'<p class="theme-text">{rich_text(theme.get("text", ""))}</p></div>'
        for theme in home.get("themes", [])
    )
    themes_block = (
        f'<div class="theme-grid">{themes}</div>' if themes else ""
    )

    featured = ""
    if project:
        method = project.get("method") or {}
        rows = [
            ("Participants", method.get("participants", "")),
            ("Measures", method.get("measures", "")),
            ("Task", method.get("task", "")),
            ("Analysis", method.get("analysis", "")),
        ]
        featured = f"""<section class="section" id="current-research">
        <h2 class="section-title">{esc(home.get("featuredHeading", "Current research"))}</h2>
        <div class="featured">
          <p class="entry-meta">{esc(" · ".join([str(project.get("year") or "").strip(), str(project.get("status") or "").strip()]).strip(" ·"))}</p>
          <h3 class="featured-title">{esc(project.get("title", ""))}</h3>
          <p class="featured-question">{rich_text(project.get("researchQuestion", ""))}</p>
          {inline_list(project.get("methods", []), label="Methods")}
          {definition_list(rows)}
          {link_row(project_links(project, depth))}
        </div>
      </section>"""

    documents = [doc for doc in content["documents"].get("documents", []) if not doc.get("private")]
    featured_docs = [doc for doc in documents if doc.get("featured")][:1] or documents[:1]
    doc_items = "".join(document_row(doc, depth) for doc in featured_docs)
    documents_block = section(
        home.get("documentsHeading", "Documents"),
        paragraphs(home.get("documentsText", ""))
        + f'<ul class="doc-list">{doc_items}</ul>'
        + f'<p class="section-foot"><a class="text-link" href="{rel(depth, "resources/")}">All documents</a></p>',
        anchor="documents",
    )

    contact_links = " ".join(
        social_link(site, key, depth=depth, inline=True) for key in ("email", "scholar", "github", "linkedin")
    )

    body = f"""
      <header class="hero">
        <h1 class="hero-name">{esc(site["name"])}</h1>
        <p class="hero-tagline">{esc(site["tagline"])}</p>
        {paragraphs(home.get("intro", []), classes="hero-intro")}
        <ul class="link-row hero-links">
          {''.join(f'<li><a class="text-link" href="{esc(item["href"])}">{esc(item["label"])}</a></li>' for item in hero_links if item.get("href"))}
          {''.join(f'<li>{item["label_html"]}</li>' for item in hero_links if item.get("label_html"))}
        </ul>
      </header>

      {section(home.get("themesHeading", "Research"), themes_block, anchor="research", lead="")}
      {featured}
      {publications_block(content, depth, heading=home.get("publicationsHeading", "Publications & writing"), anchor="publications", foot_link=("All writing", rel(depth, "writing/")))}
      {documents_block}

      {section(home.get("contactHeading", "Contact"), f'<p class="prose-text">{rich_text(home.get("contactText", ""))}</p><ul class="link-row">{contact_links}</ul>', anchor="contact")}
    """

    return render_page(
        site=site,
        path="index.html",
        title=site["siteTitle"],
        description=site["siteDescription"],
        body=body,
        extra_head=person_jsonld(site),
    )


def about_page(content: dict, depth: int) -> str:
    site = content["site"]
    about = content["about"]

    education_items = "".join(
        f'<li class="entry">{entry_summary(item, depth)}</li>' for item in about.get("education", [])
    )
    education_block = section(about.get("educationHeading", "Education"), f'<ul class="entry-list">{education_items}</ul>')

    experience = about.get("experience", [])
    if experience:
        experience_items = "".join(f'<li class="entry">{entry_summary(item, depth)}</li>' for item in experience)
        experience_inner = f'<ul class="entry-list">{experience_items}</ul>'
    else:
        experience_inner = empty_state(about.get("experienceEmpty", ""))
    experience_block = section(about.get("experienceHeading", "Research experience"), experience_inner)

    skills_block = skills_section(content["skills"], depth)
    goals_block = section(about.get("goalsHeading", "Current direction"), paragraphs(about.get("goals", [])))

    body = f"""
      <header class="page-header">
        <h1 class="page-title">About</h1>
      </header>
      {section(about.get("bioHeading", "About me"), paragraphs(about.get("bio", []), classes="prose-text"))}
      {education_block}
      {experience_block}
      {skills_block}
      {goals_block}
    """

    return render_page(
        site=site,
        path="about/index.html",
        title="About",
        description=f"{site['name']} — {site['tagline']}. Academic background, research experience and skills.",
        body=body,
    )


def entry_summary(item: dict, depth: int) -> str:
    """A compact entry: title, subtitle, date, body, bullets, links."""
    title = str(item.get("title") or "")
    if item.get("url"):
        title = f'<a class="text-link" href="{esc(str(item["url"]))}">{esc(title)}</a>'
    subtitle = f'<p class="entry-subtitle">{rich_text(item.get("subtitle", ""))}</p>' if item.get("subtitle") else ""
    date = f'<p class="entry-date">{esc(str(item.get("date")))}</p>' if item.get("date") else ""
    body_html = f'<p class="entry-body">{rich_text(item.get("body", ""))}</p>' if item.get("body") else ""
    bullets = "".join(f"<li>{rich_text(bullet)}</li>" for bullet in item.get("bullets", []) if str(bullet).strip())
    bullets_html = f'<ul class="entry-bullets">{bullets}</ul>' if bullets else ""
    links = []
    for link in item.get("links", []):
        href = resolve_link(depth, link)
        if href:
            links.append({"label": str(link.get("label") or "Link"), "href": href, "external": is_viewable(str(link.get("file") or ""))})
    links_html = link_row(links)

    return f"""
            {title_html(title)}
            {subtitle}
            {date}
            {body_html}
            {bullets_html}
            {links_html}"""


def title_html(title: str) -> str:
    if not title:
        return ""
    if title.startswith("<a"):
        return f'<h3 class="entry-title plain">{title}</h3>'
    return f'<h3 class="entry-title plain">{esc(title)}</h3>'


def skills_section_inner(skills: dict) -> str:
    categories = skills.get("categories", [])
    if not categories:
        return ""
    groups = "".join(
        f'<div class="skill-group"><h3 class="group-title">{esc(category.get("title", ""))}</h3>'
        f'<ul class="skill-list">{"".join(f"<li>{esc(item)}</li>" for item in category.get("items", []))}</ul></div>'
        for category in categories
    )
    return f'<div class="skill-grid">{groups}</div>'


def skills_section(skills: dict, depth: int, *, heading: str = "") -> str:
    inner = skills_section_inner(skills)
    if not inner:
        return ""
    return section(heading or skills.get("heading", "Skills"), inner)


def research_page(content: dict, depth: int) -> str:
    site = content["site"]
    research = content["research"]
    projects = content["projects"]

    if projects:
        entries = "".join(project_entry(project, depth) for project in projects)
        projects_inner = f'<ul class="entry-list">{entries}</ul>'
    else:
        projects_inner = empty_state(research.get("projectsEmpty", ""))

    body = f"""
      <header class="page-header">
        <h1 class="page-title">{esc(research.get("heading", "Research"))}</h1>
        {paragraphs(research.get("intro", []), classes="prose-text")}
      </header>
      {section("Projects", projects_inner, anchor="projects")}
      {publications_block(content, depth, heading=research.get("publicationsHeading", "Publications"), anchor="publications")}
    """

    return render_page(
        site=site,
        path="research/index.html",
        title="Research",
        description=f"Research projects, methods and publications by {site['name']}, psychology researcher in cognitive and clinical psychology.",
        body=body,
    )


def cv_page(content: dict, depth: int) -> str:
    site = content["site"]
    about = content["about"]
    cv = content["cv"]

    download = cv.get("download") or {}
    download_href = resolve_link(depth, download)
    download_html = (
        button(esc(download.get("label", "Download CV (PDF)")), download_href, variant="btn btn-primary")
        if download_href
        else '<span class="ph">[Download CV (PDF) — add the file path in content/cv.json]</span>'
    )
    meta_bits = []
    if cv.get("lastUpdated"):
        meta_bits.append(f'<p class="cv-meta">Last updated: {esc(str(cv["lastUpdated"]))}</p>')

    sections = []
    for entry in cv.get("sections", []):
        source = entry.get("source")

        # A section can pull in shared content instead of holding its own items.
        if source == "education":
            if not (cv.get("showEducation", True) and about.get("education")):
                continue
            items = "".join(f'<li class="entry">{entry_summary(item, depth)}</li>' for item in about["education"])
            inner = f'<ul class="entry-list">{items}</ul>'
        elif source == "projects":
            if not (cv.get("showProjects", True) and content["projects"]):
                continue
            items = "".join(project_entry(project, depth) for project in content["projects"])
            inner = f'<ul class="entry-list">{items}</ul>'
        elif source == "skills":
            if not cv.get("showSkills", True):
                continue
            inner = skills_section_inner(content["skills"])
            if not inner:
                continue
        elif entry.get("items"):
            rendered = "".join(f'<li class="entry">{entry_summary(item, depth)}</li>' for item in entry["items"])
            inner = f'<ul class="entry-list">{rendered}</ul>'
        elif entry.get("emptyState"):
            inner = empty_state(entry["emptyState"])
        else:
            continue

        sections.append(section(str(entry.get("title", "")), inner))

    body = f"""
      <header class="page-header">
        <h1 class="page-title">{esc(cv.get("heading", "Curriculum vitae"))}</h1>
        {paragraphs(cv.get("intro", ""), classes="prose-text")}
        <p class="cv-actions">{download_html}<a class="text-link" href="#web-cv">Web version below</a></p>
        {"".join(meta_bits)}
      </header>
      <div id="web-cv" class="cv-body">
        {"".join(sections)}
      </div>
    """

    return render_page(
        site=site,
        path="cv/index.html",
        title="CV",
        description=f"Curriculum vitae of {site['name']} — education, research experience, projects, publications and skills.",
        body=body,
    )


def documents_page(content: dict, depth: int) -> str:
    global CATEGORY_LABELS
    site = content["site"]
    data = content["documents"]
    CATEGORY_LABELS = data.get("categories", [])

    documents = [doc for doc in data.get("documents", []) if not doc.get("private")]
    rows = "".join(document_row(doc, depth) for doc in documents)

    def options(values) -> str:
        return "".join(f'<option value="{esc(value)}">{esc(label)}</option>' for value, label in values)

    category_options = options(
        [(c["id"], c["label"]) for c in data.get("categories", []) if any(doc.get("category") == c["id"] for doc in documents)]
    )
    year_options = options(
        [(year, year) for year in sorted({str(doc.get("year")) for doc in documents if doc.get("year")}, reverse=True)]
    )
    type_options = options(
        [(kind, kind) for kind in sorted({str(doc.get("type")) for doc in documents if doc.get("type")})]
    )

    results = f'<ul class="doc-list" id="doc-list">{rows}</ul>' if rows else empty_state(data.get("emptyState", ""))
    results = (
        '<div id="doc-results" class="doc-results">'
        '<h2 class="visually-hidden">Documents</h2>'
        f"{results}</div>"
    )

    filters = f"""<div class="filters js-only" id="doc-filters">
          <div class="filter-field">
            <label class="filter-label" for="doc-search">Search</label>
            <input class="filter-input" type="search" id="doc-search" name="search" placeholder="Search documents" autocomplete="off">
          </div>
          <div class="filter-field">
            <label class="filter-label" for="doc-category">Category</label>
            <select class="filter-input" id="doc-category" name="category">
              <option value="">All categories</option>
              {category_options}
            </select>
          </div>
          <div class="filter-field">
            <label class="filter-label" for="doc-year">Year</label>
            <select class="filter-input" id="doc-year" name="year">
              <option value="">All years</option>
              {year_options}
            </select>
          </div>
          <div class="filter-field">
            <label class="filter-label" for="doc-type">Type</label>
            <select class="filter-input" id="doc-type" name="type">
              <option value="">All types</option>
              {type_options}
            </select>
          </div>
          <button class="btn btn-quiet filter-reset" type="button" id="doc-reset">Reset</button>
        </div>
        <p class="doc-count" id="doc-count" aria-live="polite" hidden></p>"""

    body = f"""
      <header class="page-header">
        <h1 class="page-title">Resources</h1>
        {paragraphs(data.get("intro", []), classes="prose-text")}
      </header>
      {filters}
      {results}
      <p class="page-note">Documents are public and stored in this repository. Materials that are not listed here are available on request.</p>
    """

    return render_page(
        site=site,
        path="resources/index.html",
        title="Resources",
        description=f"Academic documents, proposals and materials archived by {site['name']} — view and download PDFs and other files.",
        body=body,
        extra_head="",
    )


def writing_page(content: dict, depth: int) -> str:
    site = content["site"]
    data = content["writing"]
    entries = data.get("entries", [])

    if not entries:
        inner = empty_state(data.get("emptyState", ""))
    else:
        blocks = []
        for category in data.get("categories", []):
            group = [entry for entry in entries if entry.get("category") == category.get("id")]
            if not group:
                continue
            items = []
            for entry in group:
                meta_parts = [
                    str(entry.get("date") or "").strip(),
                    str(entry.get("type") or "").strip(),
                    str(entry.get("publication") or "").strip(),
                ]
                meta = " · ".join(part for part in meta_parts if part)
                href = resolve_link(depth, entry)
                links = []
                if href:
                    links.append(
                        {
                            "label": "Read",
                            "href": href,
                            "external": bool(entry.get("url")) or is_viewable(str(entry.get("file") or "")),
                        }
                    )
                if entry.get("url"):
                    links.append({"label": "Source", "href": str(entry["url"]), "external": True})
                items.append(
                    f'<li class="entry"><p class="entry-meta">{esc(meta)}</p>'
                    f'<h3 class="entry-title plain">{esc(str(entry.get("title", "")))}</h3>'
                    f'<p class="entry-desc">{rich_text(entry.get("description", ""))}</p>{link_row(links)}</li>'
                )
            blocks.append(
                f'<div class="writing-group"><h3 class="group-title">{esc(category.get("title", ""))}</h3>'
                f'<ul class="entry-list">{items}</ul></div>'
            )
        inner = "".join(blocks)

    body = f"""
      <header class="page-header">
        <h1 class="page-title">Writing</h1>
        {paragraphs(data.get("intro", []), classes="prose-text")}
      </header>
      {section("Selected writing", inner, anchor="writing")}
    """

    return render_page(
        site=site,
        path="writing/index.html",
        title="Writing",
        description=f"Academic and public writing by {site['name']} — literature reviews, science communication and coursework.",
        body=body,
    )


def contact_page(content: dict, depth: int) -> str:
    site = content["site"]
    labels = {"email": "Email", "scholar": "Google Scholar", "linkedin": "LinkedIn", "github": "GitHub"}
    rows = []
    for key, hint in (
        ("email", "Add your email address in content/site.json"),
        ("scholar", "Add your Google Scholar profile URL in content/site.json"),
        ("linkedin", "Add your LinkedIn URL in content/site.json"),
        ("github", "Add your GitHub URL in content/site.json"),
    ):
        entry = social_link(site, key, depth=depth, inline=True)
        value = entry if not entry.startswith("<span") else f'<span class="ph">{esc(hint)}</span>'
        rows.append(
            f'<div class="contact-row"><dt class="contact-term">{esc(labels[key])}</dt>'
            f'<dd class="contact-desc">{value}</dd></div>'
        )

    body = f"""
      <header class="page-header">
        <h1 class="page-title">Contact</h1>
        <p class="prose-text">{rich_text("I am interested in research collaborations, academic opportunities, and conversations around psychology and behavioral science.")}</p>
      </header>
      <section class="section" id="contact-details">
        <h2 class="section-title">Details</h2>
        <dl class="contact-list">{"".join(rows)}</dl>
      </section>
    """

    return render_page(
        site=site,
        path="contact/index.html",
        title="Contact",
        description=f"Contact details for {site['name']}, psychology researcher.",
        body=body,
    )


def not_found_page(content: dict, depth: int) -> str:
    site = content["site"]
    body = f"""
      <header class="page-header">
        <h1 class="page-title">Page not found</h1>
        <p class="prose-text">The page you were looking for is not here. It may have moved.</p>
        <p class="link-row">
          <a class="text-link" href="{rel(depth, "")}">Home</a>
          <a class="text-link" href="{rel(depth, "research/")}">Research</a>
          <a class="text-link" href="{rel(depth, "resources/")}">Resources</a>
          <a class="text-link" href="{rel(depth, "contact/")}">Contact</a>
        </p>
      </header>
    """
    return render_page(
        site=site,
        path="404.html",
        title="Page not found",
        description="Page not found.",
        body=body,
        body_class="page-404",
    )


def sitemap_xml(content: dict) -> str:
    site = content["site"]
    base = str(site.get("baseUrl") or "").strip().rstrip("/")
    if not base:
        return ""
    pages = [("index.html", "1.0"), ("about/index.html", "0.7"), ("research/index.html", "0.9")]
    for project in content["projects"]:
        pages.append((f"research/{project['slug']}/index.html", "0.8"))
    pages += [
        ("cv/index.html", "0.8"),
        ("writing/index.html", "0.6"),
        ("resources/index.html", "0.6"),
        ("contact/index.html", "0.5"),
    ]
    entries = "".join(
        f"  <url><loc>{base}/{path}</loc><changefreq>{freq}</changefreq></url>" for path, freq in pages
    )
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>\n'