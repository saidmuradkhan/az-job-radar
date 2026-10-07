from dataclasses import replace
from html import escape
from typing import TYPE_CHECKING
from urllib.parse import parse_qsl, urlencode

from az_job_radar.analysis import CATEGORY_LABELS
from az_job_radar.models import Vacancy
from az_job_radar.search import Filters, facets

if TYPE_CHECKING:
    from az_job_radar.app import Catalog

PER_PAGE = 50
SENIORITY_LABELS = {
    "intern": "Intern",
    "junior": "Junior",
    "middle": "Middle",
    "senior": "Senior",
    "lead": "Lead",
}
WORK_MODE_LABELS = {"remote": "Remote", "hybrid": "Hybrid"}
EMPLOYMENT_LABELS = {
    "full_time": "Full-time",
    "part_time": "Part-time",
    "project": "Project / freelance",
}
EXPERIENCE_OPTIONS = [
    ("0", "No experience"),
    ("1", "Up to 1 year"),
    ("2", "Up to 2 years"),
    ("3", "Up to 3 years"),
    ("5", "Up to 5 years"),
]


def label(value: str, labels: dict[str, str]) -> str:
    return labels.get(value, value.replace("_", " ").capitalize())


def format_salary(vacancy: Vacancy) -> str:
    low, high = vacancy.salary_min, vacancy.salary_max
    if low is None and high is None:
        return ""
    if low is not None and high is not None and low != high:
        return f"{low:,.0f} – {high:,.0f} {vacancy.currency}"
    return f"{(low or high):,.0f} {vacancy.currency}"


def option_list(name, counts, selected, labels, all_label) -> str:
    options = [f'<option value="">{all_label}</option>']
    values = [value for value, _ in counts]
    if selected and selected not in values:
        counts = [(selected, 0), *counts]
    for value, count in counts:
        mark = " selected" if value == selected else ""
        options.append(
            f'<option value="{escape(value, quote=True)}"{mark}>'
            f"{escape(label(value, labels))} ({count})</option>"
        )
    return f'<select name="{name}">{"".join(options)}</select>'


def checkbox_list(name, counts, selected, labels) -> str:
    present = {value for value, _ in counts}
    counts = [(value, 0) for value in selected if value not in present] + list(counts)
    if not counts:
        return '<p class="meta">Nothing to filter yet</p>'
    items = []
    for value, count in counts:
        mark = " checked" if value in selected else ""
        items.append(
            f'<label class="check"><input type="checkbox" name="{name}" '
            f'value="{escape(value, quote=True)}"{mark}> {escape(label(value, labels))}'
            f' <span class="meta">{count}</span></label>'
        )
    return "".join(items)


def render_filters(catalog: "Catalog", filters: Filters, found: list[Vacancy]) -> str:
    counts = catalog.facets(found)
    # Count categories as if none was picked, so the other options stay visible.
    any_category = catalog.search(replace(filters, category=None))
    category_counts = facets(any_category)["category"]
    experience = "".join(
        f'<option value="{value}"{" selected" if str(filters.max_experience) == value else ""}>'
        f"{text}</option>"
        for value, text in EXPERIENCE_OPTIONS
    )
    return f"""
<form method="get" action="/" class="filters" id="filters">
  <input type="search" name="q" value="{escape(filters.q, quote=True)}"
         placeholder="Search title, company, text…">
  <h3>Category</h3>
  {option_list("category", category_counts, filters.category, CATEGORY_LABELS, "All categories")}
  <h3>Skills &amp; requirements</h3>
  <div class="checks">{checkbox_list("tag", counts["tags"], filters.tags, {})}</div>
  <h3>Common in these ads</h3>
  <div class="checks">{checkbox_list("phrase", counts["phrases"], filters.phrases, {})}</div>
  <h3>Languages</h3>
  <div class="checks">{checkbox_list("language", counts["languages"], filters.languages, {})}</div>
  <h3>Experience</h3>
  <select name="max_experience"><option value="">Any</option>{experience}</select>
  <h3>Level</h3>
  {option_list("seniority", counts["seniority"], filters.seniority, SENIORITY_LABELS, "Any")}
  <h3>Work mode</h3>
  {option_list("work_mode", counts["work_mode"], filters.work_mode, WORK_MODE_LABELS, "Any")}
  <h3>Employment</h3>
  {option_list("employment_type", counts["employment_type"], filters.employment_type,
               EMPLOYMENT_LABELS, "Any")}
  <h3>Salary</h3>
  <input type="number" name="min_salary" min="0" step="100" placeholder="Minimum, AZN"
         value="{filters.min_salary or ""}">
  <label class="check"><input type="checkbox" name="salary_only" value="true"
         {"checked" if filters.salary_only else ""}> Only with salary</label>
  <label class="check"><input type="checkbox" name="no_degree" value="true"
         {"checked" if filters.no_degree else ""}> No degree required</label>
  <h3>City</h3>
  {option_list("city", counts["city"], filters.city, {}, "Any city")}
  <h3>Source</h3>
  {option_list("source", counts["source"], filters.source, {}, "All sites")}
  <div class="buttons"><button type="submit">Apply</button> <a href="/">Reset</a></div>
</form>"""


def render_card(vacancy: Vacancy, copies: list[Vacancy]) -> str:
    details = [
        escape(vacancy.company),
        escape(format_salary(vacancy)),
        escape(vacancy.location or ""),
        vacancy.published_on.isoformat() if vacancy.published_on else "",
    ]
    category = escape(label(vacancy.category, CATEGORY_LABELS))
    chips = [f'<span class="chip category">{category}</span>']
    chips += [f'<span class="chip">{escape(tag)}</span>' for tag in vacancy.tags]
    if vacancy.experience_years is not None:
        chips.append(f'<span class="chip">{vacancy.experience_years}+ yrs</span>')
    sources = [(vacancy.source, vacancy.url)] + [(c.source, c.url) for c in copies]
    links = " · ".join(
        f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener">{escape(source)}</a>'
        for source, url in sources
    )
    url = escape(vacancy.url, quote=True)
    return f"""
<article class="card">
  <h2><a href="{url}" target="_blank" rel="noopener">{escape(vacancy.title)}</a></h2>
  <p class="meta">{" · ".join(d for d in details if d)}</p>
  <p>{"".join(chips)}</p>
  <p class="meta">{"Also on " if copies else "On "}{links}</p>
</article>"""


def page_links(query: str, page: int, pages: int) -> str:
    if pages <= 1:
        return ""
    params = [(k, v) for k, v in parse_qsl(query) if k != "page"]
    links = []
    for number in range(1, pages + 1):
        if number == page:
            links.append(f"<strong>{number}</strong>")
        else:
            href = escape(urlencode([*params, ("page", number)]))
            links.append(f'<a href="/?{href}">{number}</a>')
    return f'<nav class="pages">{" ".join(links)}</nav>'


def render_dashboard(
    catalog: "Catalog", filters: Filters, query: str = "", page: int = 1, show_logout: bool = False
) -> str:
    found = catalog.search(filters)
    pages = max(1, -(-len(found) // PER_PAGE))
    page = min(max(page, 1), pages)
    shown = found[(page - 1) * PER_PAGE : page * PER_PAGE]
    merged = sum(len(copies) for copies in catalog.copies.values())
    cards = "".join(render_card(v, catalog.copies.get(v.uid, [])) for v in shown)
    logout = '<a href="/logout">Log out</a>' if show_logout else ""
    return DASHBOARD_HTML.format(
        filters=render_filters(catalog, filters, found),
        count=len(found),
        merged=merged,
        cards=cards or '<p class="meta">No vacancies match these filters.</p>',
        pages=page_links(query, page, pages),
        logout=logout,
    )


DASHBOARD_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>az-job-radar</title>
<style>
  :root {{ --text: #1f2328; --muted: #656d76; --bg: #f6f8fa; --surface: #fff;
          --border: #d8dee4; --accent: #0969da; --chip: #eef2f6; color-scheme: light dark; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --text: #e6edf3; --muted: #8d96a0; --bg: #0d1117; --surface: #161b22;
            --border: #30363d; --accent: #4493f8; --chip: #21262d; }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ font: 15px/1.5 system-ui, sans-serif; margin: 0; padding: 1.5rem 1rem;
         color: var(--text); background: var(--bg); }}
  main {{ max-width: 1150px; margin: 0 auto; }}
  header {{ display: flex; justify-content: space-between; align-items: baseline;
           gap: 1rem; flex-wrap: wrap; }}
  h1 {{ margin: 0; font-size: 1.5rem; }}
  a {{ color: var(--accent); text-decoration: none; }}
  .meta {{ color: var(--muted); margin: .2rem 0; }}
  .layout {{ display: grid; grid-template-columns: 270px 1fr; gap: 1.25rem; margin-top: 1rem; }}
  .filters {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
             padding: 1rem; align-self: start; }}
  .filters h3 {{ font-size: .8rem; text-transform: uppercase; letter-spacing: .04em;
                color: var(--muted); margin: 1rem 0 .4rem; }}
  input, select, button {{ font: inherit; color: inherit; width: 100%; padding: .45rem .55rem;
                          border: 1px solid var(--border); border-radius: 6px;
                          background: var(--bg); }}
  .checks {{ max-height: 220px; overflow-y: auto; }}
  .check {{ display: flex; gap: .4rem; align-items: center; padding: .1rem 0; }}
  .check input {{ width: auto; }}
  .buttons {{ display: flex; gap: .75rem; align-items: center; margin-top: 1rem; }}
  .buttons button {{ width: auto; background: var(--accent); color: #fff; border: none;
                    padding: .5rem 1.2rem; cursor: pointer; }}
  .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px;
          padding: .9rem 1rem; margin-bottom: .75rem; }}
  .card h2 {{ font-size: 1.05rem; margin: 0; }}
  .card p {{ margin: .3rem 0 0; }}
  .chip {{ display: inline-block; background: var(--chip); border-radius: 999px;
          padding: .05rem .55rem; margin: 0 .3rem .3rem 0; font-size: .82rem; }}
  .chip.category {{ background: var(--accent); color: #fff; }}
  .pages {{ display: flex; gap: .6rem; flex-wrap: wrap; margin: 1rem 0; }}
  @media (max-width: 760px) {{ .layout {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<main>
  <header>
    <h1>az-job-radar</h1>
    <span class="meta"><a href="/docs">API docs</a> {logout}</span>
  </header>
  <p class="meta">{count} vacancies · {merged} duplicate posts merged</p>
  <div class="layout">
    {filters}
    <section>
      {cards}
      {pages}
    </section>
  </div>
</main>
<script>
  const form = document.getElementById("filters");
  form.addEventListener("submit", () => {{
    for (const field of form.elements) if (field.name && field.value === "") field.disabled = true;
  }});
  form.addEventListener("change", (event) => {{
    if (!["q", "min_salary"].includes(event.target.name)) form.requestSubmit();
  }});
</script>
</body>
</html>
"""
