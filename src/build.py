"""Build index.html from content/profile.json. Standard library only.

    python src/build.py            Write index.html.
    python src/build.py --strict   Refuse to build while owner facts are unconfirmed or no portrait exists. Use before deploy.
"""
import argparse
import hashlib
import json
import re
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content" / "profile.json"
OUTPUT = ROOT / "index.html"
PHOTOS = ROOT / "assets" / "photo"
CASES = ROOT / "case-studies"

CSP = (
    "default-src 'none'; style-src 'self'; script-src 'self'; font-src 'self'; img-src 'self'; "
    "base-uri 'none'; form-action 'none'"
)
KIND_LABEL = {"gate": "Control point", "store": "Data", "step": "Step"}


def e(value: str) -> str:
    return escape(value, quote=True)


def external(url: str, label: str) -> str:
    return f'<a class="ul" href="{e(url)}" rel="noopener noreferrer">{e(label)}</a>'


def items(values: list[str]) -> str:
    return "".join(f"<li>{e(value)}</li>" for value in values)


def versioned(path: str) -> str:
    """Add a hash of the file to its URL, so a browser cannot keep an earlier version."""
    digest = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()[:8]
    return f"{path}?v={digest}"


def photo_files() -> list[tuple[int, str]]:
    """Return (width, stem) for each prepared portrait, where the stem carries a hash of the image."""
    found = []
    for path in PHOTOS.glob("portrait-*.webp"):
        match = re.fullmatch(r"portrait-(\d+)\.[0-9a-f]{8}\.webp", path.name)
        if match:
            found.append((int(match.group(1)), path.stem))
    return sorted(found)


def render_photo(person: dict) -> str:
    files = photo_files()
    if not files:
        # No stand-in photograph is ever used. The strict build refuses to publish this state.
        return (
            '<div class="frame-empty" role="img" aria-label="Portrait not yet added">'
            '<span class="frame-mono" aria-hidden="true">MTA</span>'
            '<span class="frame-text" aria-hidden="true">Formal portrait to be added</span></div>'
        )
    largest, largest_stem = files[-1]
    srcset = ", ".join(f"assets/photo/{stem}.webp {w}w" for w, stem in files)
    fallback = ", ".join(f"assets/photo/{stem}.jpg {w}w" for w, stem in files)
    sizes = "(max-width: 640px) calc(100vw - 58px), (max-width: 960px) 34vw, 346px"
    return (
        f'<picture><source type="image/webp" srcset="{srcset}" sizes="{sizes}">'
        f'<img src="assets/photo/{largest_stem}.jpg" srcset="{fallback}" sizes="{sizes}" '
        f'width="{largest}" height="{round(largest * 5 / 4)}" alt="Portrait of {e(person["name"])}" fetchpriority="high"></picture>'
    )


def render_path(project: dict) -> str:
    """The hero's small path: the same stages as the project's full trace, read from the same data."""
    stages = "".join(
        f'<li class="stage-{stage["kind"]}"><span class="path-mark" aria-hidden="true"></span>'
        f'<span class="path-name">{e(stage["name"])}</span></li>'
        for stage in project["trace"]
    )
    return (
        f'<figure class="path enter d7"><figcaption><span>{e(project["trace_title"])} in {e(project["name"])}, a prototype</span>'
        f'<a class="ul" href="#{e(project["id"])}">See how it works</a></figcaption>'
        f'<div class="path-track"><ol>{stages}</ol><span class="path-pulse" aria-hidden="true"></span></div></figure>'
    )


def render_trace(project: dict) -> str:
    pid = project["id"]
    stages = []
    for index, stage in enumerate(project["trace"]):
        note_id = f"{pid}-stage-{index}"
        kind = stage["kind"]
        stages.append(
            f'<li class="stage stage-{kind}">'
            f'<button type="button" class="stage-btn" aria-expanded="false" aria-controls="{note_id}">'
            f'<span class="stage-mark" aria-hidden="true"></span>'
            f'<span class="stage-name">{e(stage["name"])}</span>'
            f'<span class="sr">, {KIND_LABEL[kind].lower()}</span></button>'
            f'<div class="stage-note" id="{note_id}"><p><span class="stage-kind">{KIND_LABEL[kind]}</span> {e(stage["note"])}</p></div></li>'
        )
    return (
        f'<figure class="trace-wrap"><figcaption>{e(project["trace_title"])}</figcaption>'
        f'<ol class="trace">{"".join(stages)}</ol></figure>'
    )


def render_media(media: dict, prefix: str = "") -> str:
    return (
        f'<figure class="media"><img src="{prefix}{e(media["src"])}" width="{media["width"]}" height="{media["height"]}" '
        f'alt="{e(media["alt"])}" loading="lazy"><figcaption>{e(media["caption"])}</figcaption></figure>'
    )


def render_evidence(evidence: list[dict], labels: dict) -> str:
    return "".join(
        f'<li><span class="tag tag-{e(item["kind"])}">{e(labels[item["kind"]])}</span> {e(item["text"])}</li>' for item in evidence
    )


def render_source(project: dict) -> str:
    source = project["source"]
    return external(source["url"], source["label"]) if source["url"] else e(source["label"])


def render_project(project: dict, labels: dict) -> str:
    media = render_media(project["media"]) if project.get("media") else ""
    return f"""
    <article class="project" data-reveal id="{e(project["id"])}" aria-labelledby="{e(project["id"])}-name">
      <header class="project-head">
        <div class="project-kicker"><p class="shows">{e(project["shows"])}</p><p class="state">{e(project["state"])}</p></div>
        <h3 id="{e(project["id"])}-name">{e(project["name"])}</h3>
        <p class="purpose">{e(project["problem"])}</p>
      </header>
      {media}
      <div class="cells">
        <section class="cell" aria-label="What I built in {e(project["name"])}"><h4>What I built</h4><ul>{items(project["built"])}</ul></section>
        <section class="cell" aria-label="What works in {e(project["name"])}"><h4>What works</h4><ul>{items(project["works"])}</ul></section>
        <section class="cell" aria-label="Architecture of {e(project["name"])}"><h4>Architecture and stack</h4><p>{e(project["architecture"])}</p><p class="stack">{e(project["stack"])}</p></section>
        <section class="cell" aria-label="Evidence for {e(project["name"])}"><h4>Evidence</h4><ul class="evidence">{render_evidence(project["evidence"], labels)}</ul></section>
      </div>
      <footer class="project-foot">
        <dl class="foot-facts">
          <div><dt>Status</dt><dd>{e(project["status"])}</dd></div>
          <div><dt>Source</dt><dd>{render_source(project)}</dd></div>
        </dl>
        <a class="btn" href="case-studies/{e(project["id"])}.html">Read the case study <span class="btn-arrow" aria-hidden="true">&rarr;</span></a>
      </footer>
    </article>"""


def page_head(title: str, description: str, person: dict, prefix: str, canonical: str, extra: str = "") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{e(CSP)}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#0B0F12">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{e(canonical)}">
<meta property="og:type" content="profile">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(canonical)}">
<meta property="og:image" content="{e(person["site_url"])}assets/og.png">
<meta property="og:image:alt" content="{e(person["name"])}, AI Engineer.">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="{prefix}assets/favicon.svg" type="image/svg+xml">
<link rel="preload" href="{prefix}assets/fonts/archivo.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{prefix}assets/fonts/source-serif-4.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{prefix}{versioned("assets/site.css")}">
<script src="{prefix}{versioned("assets/site.js")}"></script>{extra}
</head>
"""


def page_header(person: dict, home: str, section_prefix: str) -> str:
    return f"""<body>
<a class="skip" href="#main">Skip to content</a>
<header class="top">
  <div class="top-inner">
    <a class="home" href="{home}"><span class="home-full">{e(person["name"])}</span><span class="home-short" aria-hidden="true">MTA</span></a>
    <button type="button" class="menu-btn" aria-expanded="false" aria-controls="site-nav">
      <span class="menu-icon" aria-hidden="true"><span></span><span></span></span>Menu
    </button>
    <nav id="site-nav" aria-label="Sections">
      <ul>
        <li><a href="{section_prefix}#work">Work</a></li>
        <li><a href="{section_prefix}#about">About</a></li>
        <li><a href="{section_prefix}#expertise">Expertise</a></li>
        <li><a href="{section_prefix}#experience">Experience</a></li>
        <li><a href="{section_prefix}#contact">Contact</a></li>
      </ul>
    </nav>
  </div>
</header>
"""


def page_footer(person: dict, top: str) -> str:
    return f"""<footer class="foot">
  <div class="foot-inner">
    <p>{e(person["name"])}, {e(person["title"])}</p>
    <a class="ul" href="{top}">Back to top</a>
  </div>
</footer>
</body>
</html>
"""


def render_case_study(project: dict, data: dict) -> str:
    person = data["person"]
    media = render_media(project["media"], "../") if project.get("media") else ""
    title = f'{project["name"]} case study | {person["name"]}'
    return (
        page_head(title, project["problem"], person, "../", f'{person["site_url"]}case-studies/{project["id"]}.html')
        + page_header(person, "../index.html", "../index.html")
        + f"""
<main id="main" class="case">
  <section class="case-head">
    <p class="crumb"><a class="ul" href="../index.html#{e(project["id"])}">Back to selected work</a></p>
    <div class="project-kicker"><p class="shows">{e(project["shows"])}</p><p class="state">{e(project["state"])}</p></div>
    <h1 id="name">{e(project["name"])}</h1>
    <p class="statement">{e(project["problem"])}</p>
    <dl class="foot-facts">
      <div><dt>Status</dt><dd>{e(project["status"])}</dd></div>
      <div><dt>Source</dt><dd>{render_source(project)}</dd></div>
      <div><dt>Stack</dt><dd>{e(project["stack"])}</dd></div>
    </dl>
  </section>
  {media}
  <section class="case-block" data-reveal aria-labelledby="role-title">
    <h2 id="role-title">My role</h2>
    <p class="case-text">{e(project["role"])}</p>
  </section>
  <section class="case-block" aria-labelledby="path-title">
    <h2 id="path-title">How it works</h2>
    <div class="case-text"><p>This diagram follows the real path through the code. Select a stage to read what happens there. Stages marked with a diamond <span class="legend-mark" aria-hidden="true"></span> are control points, where the system checks, stops or waits for a person.</p></div>
    <div class="project case-panel" data-reveal>{render_trace(project)}</div>
  </section>
  <section class="case-block" data-reveal aria-labelledby="decisions-title">
    <h2 id="decisions-title">Engineering decisions</h2>
    <ul class="case-list">{items(project["decisions"])}</ul>
  </section>
  <section class="case-block" data-reveal aria-labelledby="tested-title">
    <h2 id="tested-title">What was tested</h2>
    <ul class="case-list">{items(project["tested"])}</ul>
  </section>
  <section class="case-block" data-reveal aria-labelledby="limits-title">
    <h2 id="limits-title">Limits and open work</h2>
    <ul class="case-list">{items(project["limits"])}</ul>
  </section>
</main>
"""
        + page_footer(person, "#main")
    )


def render_experience(job: dict) -> str:
    lead = f'<p class="job-lead">{e(job["lead"])}</p>' if job["lead"] else ""
    # A fact the owner has not confirmed is shown as pending, never as settled.
    pending = (
        f'<p class="job-pending"><span class="tag tag-gap">Pending confirmation</span> {e(job["pending"])}</p>'
        if job.get("pending")
        else ""
    )
    return f"""
    <article class="job">
      <header>
        <h3>{e(job["role"])}</h3>
        <p class="job-dates">{e(job["dates"])}</p>
        <p class="job-meta">{e(job["org"])}, {e(job["place"])}</p>
      </header>
      {pending}{lead}<ul>{items(job["points"])}</ul>
    </article>"""


def render_certificate(cert: dict) -> str:
    name = external(cert["url"], cert["name"]) if cert["url"] else e(cert["name"])
    meta = " ".join(f"{e(part)}." for part in (cert["issuer"], cert["note"]) if part)
    return f'<li><span class="cert-name">{name}</span><span class="cert-meta">{meta}</span></li>'


def json_ld(person: dict, education: dict) -> str:
    data = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": person["name"],
        "jobTitle": person["title"],
        "url": person["site_url"],
        "email": f"mailto:{person['email']}",
        "address": {"@type": "PostalAddress", "addressLocality": "Amman", "addressCountry": "JO"},
        "alumniOf": {"@type": "CollegeOrUniversity", "name": "Philadelphia University"},
        "sameAs": [link["url"] for link in person["links"]],
    }
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


COUNT_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}


def published_projects(data: dict) -> list[dict]:
    """Projects shown on the site. Held projects wait for the owner's approval and are not rendered."""
    held = set(data.get("held_projects", []))
    return [p for p in data["projects"] if p["id"] not in held]


def render(data: dict) -> str:
    person, education = data["person"], data["education"]
    title = f'{person["name"]} | {person["title"]}'
    labels = data["evidence_labels"]
    links = "".join(f"<li>{external(link['url'], link['label'])}</li>" for link in person["links"])
    shown = published_projects(data)
    featured = next((p for p in shown if p["id"] == data.get("featured", "")), shown[0])
    index = "".join(
        f'<li><a href="#{e(p["id"])}"><span class="index-name">{e(p["name"])}</span><span class="index-shows">{e(p["shows"])}</span></a></li>'
        for p in shown
    )
    projects = "".join(render_project(p, labels) for p in shown)
    cv = person.get("cv_url")
    hero_cv = f'<li><a class="btn" href="{e(cv)}" download>Download resume</a></li>' if cv else ""
    contact_cv = f'<li><a class="ul" href="{e(cv)}" download>Resume (PDF)</a></li>' if cv else ""
    more = "".join(
        f'<li>{render_media(m["media"]) if m.get("media") else ""}<a class="more-name ul" href="{e(m["url"])}" rel="noopener noreferrer">{e(m["name"])}</a>'
        f'<p>{e(m["text"])}</p><p class="more-evidence"><span class="tag tag-ran">Ran</span> {e(m["evidence"])}</p><p class="more-status">{e(m["status"])}</p></li>'
        for m in data["more_work"]
    )
    about = "".join(f"<p>{e(p)}</p>" for p in data["about"])
    shown_ids = {p["id"] for p in shown}
    approach = "".join(
        f'<li><h3>{e(a["title"])}</h3><p>{e(a["text"])}'
        + (f' <a href="#{e(a["see"])}">See {e(a["see_label"])}</a>' if a["see"] in shown_ids else "")
        + "</p></li>"
        for a in data["approach"]
    )
    expertise = "".join(
        f'<div class="skill-group"><h3>{e(g["heading"])}</h3><ul>{items(g["items"])}</ul></div>' for g in data["expertise"]
    )
    experience = "".join(render_experience(job) for job in data["experience"])
    certificates = "".join(render_certificate(c) for c in education["certificates"])
    stack = "".join(f"<li>{e(s)}</li>" for s in person["stack_line"])
    extra = f'\n<script type="application/ld+json">{json_ld(person, education)}</script>'
    return page_head(title, person["description"], person, "", person["site_url"], extra) + page_header(person, "#main", "") + f"""
<main id="main">
  <section class="hero" aria-labelledby="name">
    <div class="hero-grid">
      <div class="hero-text">
        <div class="hero-id">
          <h1 id="name" class="enter d1">{e(person["name"])}</h1>
          <p class="role enter d2">{e(person["title"])}</p>
        </div>
        <p class="statement enter d3">{e(person["statement"])}</p>
        <ul class="actions enter d4">
          <li><a class="btn btn-primary" href="#work">View selected work <span class="btn-arrow" aria-hidden="true">&rarr;</span></a></li>
          {hero_cv}
        </ul>
        <ul class="hero-links enter d5">{links}<li><a class="ul" href="mailto:{e(person["email"])}">Email</a></li></ul>
        <ul class="stack-line enter d6" aria-label="Main technologies">{stack}</ul>
      </div>
      <div class="portrait">
        <div class="frame">{render_photo(person)}</div>
        <p class="hero-note enter d6">{e(person["location"])}</p>
      </div>
      {render_path(featured)}
    </div>
    <nav class="index enter d7" aria-label="Selected projects">
      <p class="index-title">Selected systems</p>
      <ul>{index}</ul>
    </nav>
  </section>

  <section id="work" class="work" aria-labelledby="work-title">
    <div class="section-head" data-reveal>
      <h2 id="work-title">Selected work</h2>
      <div class="section-note">
        <p>Each project states the problem, what I built, what works, and how far it has been tested. All {COUNT_WORDS.get(len(shown), len(shown))} are prototypes or unfinished contributions, not deployed products.</p>
        <ul class="legend">
          <li><span class="tag tag-ran">Ran</span> Executed on 2026-11-07, or as stated.</li>
          <li><span class="tag tag-code">In code</span> Confirmed by reading the code, not run.</li>
          <li><span class="tag tag-gap">Not done</span> Not yet done or not verified.</li>
        </ul>
      </div>
    </div>
    {projects}
    <div class="more" data-reveal>
      <h3>Smaller public projects</h3>
      <ul>{more}</ul>
    </div>
  </section>

  <section id="about" class="band band-alt" aria-labelledby="about-title">
    <div class="band-inner" data-reveal>
      <h2 id="about-title">About</h2>
      <div class="about-text">{about}</div>
      <div class="approach" data-reveal>
        <h3 class="approach-title">How I work</h3>
        <ul>{approach}</ul>
      </div>
    </div>
  </section>

  <section id="expertise" class="band" aria-labelledby="expertise-title">
    <div class="band-inner" data-reveal>
      <h2 id="expertise-title">Technical expertise</h2>
      <div class="skills" data-reveal>{expertise}</div>
    </div>
  </section>

  <section id="experience" class="band band-alt" aria-labelledby="experience-title">
    <div class="band-inner" data-reveal>
      <h2 id="experience-title">Experience</h2>
      <div class="jobs">{experience}</div>
    </div>
  </section>

  <section id="education" class="band" aria-labelledby="education-title">
    <div class="band-inner" data-reveal>
      <h2 id="education-title">Education</h2>
      <div class="edu">
        <p class="degree">{e(education["degree"])}</p>
        <p class="degree-meta">{e(education["school"])}, {e(education["year"])}</p>
        <h3 class="cert-title">Certificates and training</h3>
        <ul class="certs">{certificates}</ul>
      </div>
    </div>
  </section>

  <section id="contact" class="band band-alt" aria-labelledby="contact-title">
    <div class="band-inner" data-reveal>
      <h2 id="contact-title">Contact</h2>
      <div>
        <p class="contact-line">{e(person["availability"])} Based in {e(person["location"])}.</p>
        <p class="contact-mail"><a class="ul" href="mailto:{e(person["email"])}">{e(person["email"])}</a></p>
        <ul class="contact-links">{links}{contact_cv}</ul>
      </div>
    </div>
  </section>
</main>

""" + page_footer(person, "#main")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="Fail while facts remain unconfirmed.")
    args = parser.parse_args()
    data = json.loads(CONTENT.read_text(encoding="utf-8"))
    unconfirmed = list(data.get("unconfirmed", []))
    if not photo_files():
        unconfirmed.insert(0, "Portrait: assets/photo is empty. Add the supplied formal photograph with tools/prepare_photo.py.")
    if unconfirmed:
        stream = sys.stderr if args.strict else sys.stdout
        print(f"{len(unconfirmed)} unconfirmed item(s):", file=stream)
        for item in unconfirmed:
            print(f"  - {item}", file=stream)
        if args.strict:
            print("Strict build refused. Resolve these before deploying.", file=sys.stderr)
            return 1
    OUTPUT.write_text(render(data), encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT.name}")
    CASES.mkdir(exist_ok=True)
    shown = published_projects(data)
    for project in shown:
        (CASES / f'{project["id"]}.html').write_text(render_case_study(project, data), encoding="utf-8", newline="\n")
    for held in data.get("held_projects", []):
        (CASES / f"{held}.html").unlink(missing_ok=True)  # a held project must not stay reachable by URL
    print(f"Wrote {len(shown)} case studies; held: {', '.join(data.get('held_projects', [])) or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
