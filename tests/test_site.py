"""Checks on the built page. Run with: python -m pytest"""
import json
import re
import subprocess
import sys
from html import escape
from html.parser import HTMLParser
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "assets" / "site.css").read_text(encoding="utf-8")
DATA = json.loads((ROOT / "content" / "profile.json").read_text(encoding="utf-8"))
HELD = set(DATA.get("held_projects", []))
SHOWN = [p for p in DATA["projects"] if p["id"] not in HELD]
CASE_PAGES = {p["id"]: (ROOT / "case-studies" / f'{p["id"]}.html').read_text(encoding="utf-8") for p in SHOWN}
ALL_PAGES = [HTML, *CASE_PAGES.values()]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.counts = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.tags.append((tag, attributes))
        self.counts[tag] = self.counts.get(tag, 0) + 1


@pytest.fixture(scope="module")
def page():
    parser = Page()
    parser.feed(HTML)
    return parser


def test_index_matches_the_build():
    sys.path.insert(0, str(ROOT / "src"))
    import build

    assert build.render(DATA) == HTML
    for project in SHOWN:
        assert build.render_case_study(project, DATA) == CASE_PAGES[project["id"]]


def test_strict_build_refuses_unconfirmed_facts():
    if not DATA["unconfirmed"]:
        pytest.skip("All facts are confirmed.")
    result = subprocess.run(
        [sys.executable, str(ROOT / "src" / "build.py"), "--strict"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 1
    assert "Strict build refused" in result.stderr


def test_one_h1_and_language(page):
    assert page.counts["h1"] == 1
    assert ("html", {"lang": "en"}) in page.tags


def test_heading_levels_do_not_skip(page):
    levels = [int(tag[1]) for tag, _ in page.tags if re.fullmatch(r"h[1-6]", tag)]
    assert all(after - before <= 1 for before, after in zip(levels, levels[1:]))


def test_required_seo_tags(page):
    metas = {a.get("name") or a.get("property"): a.get("content") for t, a in page.tags if t == "meta"}
    assert metas["description"] and metas["og:title"] and metas["og:image"].endswith("assets/og.png")
    assert any(t == "link" and a.get("rel") == "canonical" for t, a in page.tags)
    assert "<title>Mohammad Taha Alhmad | AI Engineer</title>" in HTML
    ld = re.search(r'<script type="application/ld\+json">(.+?)</script>', HTML).group(1)
    assert json.loads(ld)["name"] == "Mohammad Taha Alhmad"


def test_internal_anchors_resolve(page):
    ids = {a["id"] for _, a in page.tags if "id" in a}
    for tag, attributes in page.tags:
        if tag == "a" and attributes.get("href", "").startswith("#"):
            assert attributes["href"][1:] in ids, attributes["href"]


def test_no_third_party_requests(page):
    for tag, attributes in page.tags:
        if tag in {"script", "img", "iframe"} or (tag == "link" and attributes.get("rel") != "canonical"):
            target = attributes.get("src") or attributes.get("href") or ""
            assert not target.startswith(("http:", "https:", "//")), target
    assert "http" not in CSS


def test_local_assets_exist(page):
    for tag, attributes in page.tags:
        target = attributes.get("src") or (attributes.get("href") if tag in {"link", "a"} else None)
        if target and target.startswith("assets/"):
            assert (ROOT / target.split("?")[0]).exists(), target
        for entry in (attributes.get("srcset") or "").split(","):
            if entry.strip():
                assert (ROOT / entry.strip().split(" ")[0]).exists(), entry
    for name in re.findall(r'url\("(fonts/[^"]+)"\)', CSS):
        assert (ROOT / "assets" / name).exists()


def test_fonts_are_light_and_licensed():
    fonts = list((ROOT / "assets" / "fonts").glob("*.woff2"))
    assert len(fonts) == 3
    assert sum(f.stat().st_size for f in fonts) < 300_000
    assert len(list((ROOT / "assets" / "fonts").glob("OFL-*.txt"))) == 3


def test_external_links_are_safe(page):
    for tag, attributes in page.tags:
        if tag == "a" and attributes.get("href", "").startswith("http"):
            assert "noopener" in attributes.get("rel", "")


@pytest.mark.parametrize(
    "text",
    [
        "kaggle.com/tahamohmadf19",
        "github.com/tahamohmadf19/",
        'github.com/tahamohmadf19"',
        "utm_",
        "lnkd.in",
        "20260122",
        "WhatsApp",
        "Production Ready",
        "production-ready",
        "Senior",
        "@BabyPutcast",
        "mb-digital",
        "MB DIGITAL",
        "clientpilot-ai",
        "GreenLead",
        "Microsoft Certified",
    ],
)
def test_banned_text_is_absent(text):
    assert text not in HTML


def test_no_phone_number_on_the_page():
    assert not re.search(r"\+?962[\s\d-]{6,}|07[789]\d{7}", HTML)


def test_the_linked_resume_exists():
    if not DATA["person"]["cv_url"]:
        pytest.skip("No resume is published in this release.")
    cv = ROOT / DATA["person"]["cv_url"]
    assert cv.exists() and cv.suffix == ".pdf" and cv.stat().st_size < 300_000


def test_without_an_approved_resume_no_pdf_is_published_or_linked():
    if DATA["person"]["cv_url"]:
        pytest.skip("A resume is published.")
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    assert not [f for f in tracked if f.lower().endswith(".pdf")]
    for page in ALL_PAGES:
        assert ".pdf" not in page and "Download resume" not in page


def test_held_projects_are_not_published():
    assert HELD == {"clientpilot", "shortform"}
    for held in HELD:
        assert f'id="{held}"' not in HTML and f"case-studies/{held}.html" not in HTML
        assert not (ROOT / "case-studies" / f"{held}.html").exists()
    for page in ALL_PAGES:
        assert "ClientPilot" not in page and "Shortform" not in page


def test_hero_has_identity_photo_and_actions():
    hero = re.search(r'<section class="hero".*?</section>', HTML, re.DOTALL).group(0)
    assert DATA["person"]["statement"] in hero
    assert "<h1" in hero and "Mohammad" in hero and "Alhmad" in hero
    assert 'alt="Portrait of Mohammad Taha Alhmad"' in hero or 'class="frame-empty"' in hero
    assert 'href="#work"' in hero and "mailto:" in hero
    assert (DATA["person"]["cv_url"] in hero) if DATA["person"]["cv_url"] else ("download" not in hero)


def test_accuracy_is_not_a_homepage_headline():
    first = HTML.split('<section id="work"')[0]
    for text in ("0.979", "0.684", "<del", "<ins"):
        assert text not in first
    assert "<del" not in HTML and "<ins" not in HTML


def test_old_hoodie_photo_is_gone_from_the_portfolio():
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    assert "WhatsApp" not in tracked
    # The old crop had no hash in its name. A new photo may share its width, but never this name.
    for name in ("portrait-410.jpg", "portrait-410.webp"):
        assert name not in tracked and name not in HTML
        assert not (ROOT / "assets" / "photo" / name).exists()
    assert not list(ROOT.glob("WhatsApp*"))


def test_portrait_is_either_a_hashed_prepared_file_or_an_empty_frame():
    files = list((ROOT / "assets" / "photo").glob("portrait-*"))
    if files:
        assert all(re.fullmatch(r"portrait-\d+\.[0-9a-f]{8}\.(webp|jpg)", f.name) for f in files)
        assert re.search(r'<img src="assets/photo/portrait-\d+\.[0-9a-f]{8}\.jpg"[^>]* width="\d+" height="\d+"', HTML)
        assert 'class="frame-empty"' not in HTML
    else:
        assert 'class="frame-empty"' in HTML
        assert "<img" not in HTML


def test_served_portrait_is_the_supplied_file_byte_for_byte():
    supplied = ROOT.parents[1] / "inputs" / "formal_portrait_mohammad_taha.webp"
    if not supplied.exists():
        pytest.skip("The supplied file is not in this checkout.")
    served = [f.read_bytes() for f in (ROOT / "assets" / "photo").glob("portrait-*.webp")]
    assert supplied.read_bytes() in served


def test_hero_shows_the_real_portrait_with_alt_text():
    hero = re.search(r'<section class="hero".*?</section>', HTML, re.DOTALL).group(0)
    assert 'alt="Portrait of Mohammad Taha Alhmad"' in hero
    assert 'class="frame-empty"' not in HTML
    assert "MTA</span></div>" not in HTML


def test_strict_build_refuses_a_missing_portrait():
    if list((ROOT / "assets" / "photo").glob("portrait-*")):
        pytest.skip("A portrait exists.")
    result = subprocess.run(
        [sys.executable, str(ROOT / "src" / "build.py"), "--strict"], capture_output=True, text=True, check=False
    )
    assert result.returncode == 1 and "Portrait: assets/photo is empty" in result.stderr


def test_css_and_js_urls_carry_a_content_hash():
    assert re.search(r'href="assets/site\.css\?v=[0-9a-f]{8}"', HTML)
    assert re.search(r'src="assets/site\.js\?v=[0-9a-f]{8}"', HTML)


def test_green_circle_matches_the_resume():
    job = DATA["experience"][0]
    source = ROOT.parents[1] / "deliverables" / "resume" / "src" / "resume_content.json"
    resume = json.loads(source.read_text(encoding="utf-8"))["experience"][0]
    assert (job["role"], job["dates"], job["org"]) == (resume["title"], resume["dates"], resume["org"])


def test_ai900_is_described_as_attendance():
    assert "not the Microsoft exam" in HTML


def test_every_project_answers_the_seven_questions_on_the_homepage():
    for project in SHOWN:
        for key in ("problem", "built", "works", "architecture", "stack", "evidence", "status", "source"):
            assert project[key], f"{project['id']} is missing {key}"
        block = re.search(rf'<article class="project"[^>]*id="{project["id"]}".*?</article>', HTML, re.DOTALL).group(0)
        for heading in ("What I built", "What works", "Architecture and stack", "Evidence", "Status", "Source"):
            assert heading in block, (project["id"], heading)
        assert f'href="case-studies/{project["id"]}.html"' in block


def test_evidence_labels_are_known():
    for project in DATA["projects"]:
        assert project["evidence"]
        assert any(item["kind"] == "ran" for item in project["evidence"]), project["id"]
        for item in project["evidence"]:
            assert item["kind"] in DATA["evidence_labels"]


def test_workflow_detail_lives_in_the_case_studies():
    assert 'class="stage-btn"' not in HTML
    for project in SHOWN:
        page = CASE_PAGES[project["id"]]
        assert len(project["trace"]) == 7, "site.css lays out seven stages"
        assert any(stage["kind"] == "gate" for stage in project["trace"])
        assert page.count('class="stage-btn"') == 7
        for key in ("decisions", "tested", "limits"):
            assert project[key]
            for line in project[key]:
                assert escape(line, quote=True) in page, line
        assert escape(project["role"], quote=True) in page
        assert "<h1" in page and page.count("<h1") == 1


@pytest.mark.parametrize(
    "text",
    [
        "Sole author",
        "sole author",
        "production chat",
        "real chat pipeline",
        "Meta messaging",
        "reliable",
        "team graduation",
        "lines added",
        "commits,",
        "live demo",
        "diagnostic that proves",
        "Days_Active",
        "never run against",
        "Tool calling",
    ],
)
def test_corrected_claims_do_not_return(text):
    for page in ALL_PAGES:
        assert text not in page


def test_ai_assistance_is_disclosed_where_known():
    by_id = {p["id"]: p for p in DATA["projects"]}
    assert "AI coding agent" in by_id["shortform"]["role"]
    assert "AI coding agent" in by_id["edusmartai"]["role"]
    for item in DATA["more_work"]:
        assert "AI coding agent" in item["status"], item["name"]
    assert "AI coding agents" in " ".join(DATA["about"])


def test_work_published_on_2026_11_14_says_so():
    for item in DATA["more_work"]:
        assert re.search(r"Public since 2026-11-\d\d", item["status"]) and "not public" not in item["status"], item["name"]
    assert any("public repository still shows version 1" in x for x in {p["id"]: p for p in DATA["projects"]}["shortform"]["limits"])


def test_attribution_of_others_work_is_explicit():
    edu = {p["id"]: p for p in DATA["projects"]}["edusmartai"]
    assert "He had already documented" in edu["role"] and "wrote the retriever" in edu["role"]
    client = {p["id"]: p for p in DATA["projects"]}["clientpilot"]
    assert "Nic Chin" in client["role"] and "MIT" in client["role"]
    assert "Onyx" in {p["id"]: p for p in DATA["projects"]}["rag-quality-lab"]["role"]


def test_clientpilot_states_its_failing_tests_and_no_live_run():
    if "clientpilot" in HELD:
        pytest.skip("ClientPilot is held from this release.")
    block = re.search(r'<article class="project"[^>]*id="clientpilot".*?</article>', HTML, re.DOTALL).group(0)
    assert "56 passed, 9 failed, 1 suite did not load" in block
    assert "They are not fixed" in block
    assert "No live run" in block


def test_every_featured_project_states_it_is_not_deployed_or_merged():
    for project in DATA["projects"]:
        assert re.search(r"not deployed|not merged|never uploaded", project["status"], re.I), project["id"]


def test_evidence_images_exist_with_alt_text_and_captions():
    media = [p["media"] for p in SHOWN if p.get("media")] + [m["media"] for m in DATA["more_work"] if m.get("media")]
    assert len(media) == 2 - sum(1 for p in DATA["projects"] if p["id"] in HELD and p.get("media"))
    for item in media:
        assert (ROOT / item["src"]).exists() and item["alt"] and "real" in item["caption"].lower()


def test_case_pages_have_working_local_links():
    for page in CASE_PAGES.values():
        parser = Page()
        parser.feed(page)
        ids = {a["id"] for _, a in parser.tags if "id" in a}
        for tag, attributes in parser.tags:
            target = attributes.get("src") or (attributes.get("href") if tag in {"link", "a"} else None)
            if target and target.startswith("../"):
                assert (ROOT / "case-studies" / target.split("#")[0].split("?")[0]).resolve().exists(), target
            if tag == "a" and attributes.get("href", "").startswith("#"):
                assert attributes["href"][1:] in ids
        assert not [a for _, a in parser.tags if "style" in a]


def test_private_projects_link_to_no_source():
    for project in DATA["projects"]:
        if project["id"] in {"rag-quality-lab", "clientpilot", "shortform"}:
            assert project["source"]["url"] is None


def test_derived_work_is_credited():
    text = {p["id"]: json.dumps(p) for p in DATA["projects"]}
    assert "Onyx" in text["rag-quality-lab"]
    assert "DocsFlow" in text["clientpilot"]
    assert "@bahaaed07706" in text["edusmartai"] and "not merged" in text["edusmartai"]


def test_page_keeps_working_without_js_or_motion():
    assert "html:not(.js) .stage-note" in CSS
    assert ".js .stage-note { visibility: hidden" in CSS
    assert ".js .stage-note { display: none" in CSS
    assert all('class="stage-note"' in page for page in CASE_PAGES.values())
    assert "prefers-reduced-motion: no-preference" in CSS
    assert "forced-colors: active" in CSS


def test_buttons_are_wired_to_what_they_control(page):
    for html in ALL_PAGES:
        parser = Page()
        parser.feed(html)
        ids = {a["id"] for _, a in parser.tags if "id" in a}
        buttons = [a for t, a in parser.tags if t == "button"]
        assert buttons
        for attributes in buttons:
            assert attributes["aria-controls"] in ids
            assert attributes["aria-expanded"] == "false"
            assert attributes["type"] == "button"


def test_csp_allows_what_the_page_uses(page):
    # An inline style was once blocked by style-src 'self', which silently broke the diagram layout.
    assert not [a for _, a in page.tags if "style" in a]
    assert "data:" not in CSS


def test_no_form_and_mail_contact_present(page):
    assert "form" not in page.counts
    assert f'href="mailto:{DATA["person"]["email"]}"' in HTML


def _luminance(value):
    channels = [int(value[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(a, b):
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


TOKENS = dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9A-Fa-f]{6});", CSS))


def test_the_owners_palette_is_used_exactly():
    names = ("bg", "bg-2", "surface", "line", "text", "text-2", "accent", "gold")
    assert {k: TOKENS[k].upper() for k in names} == {
        "bg": "#0B0F12",
        "bg-2": "#10171B",
        "surface": "#151D22",
        "line": "#273039",
        "text": "#F3F4F2",
        "text-2": "#AAB5B8",
        "accent": "#42C8AD",
        "gold": "#C4A274",
    }


def test_colors_come_only_from_the_token_block():
    body = CSS.split("--ease:", 1)[1]
    assert not re.findall(r"#[0-9A-Fa-f]{3,8}\b", body)


def test_earlier_themes_are_gone():
    favicon = (ROOT / "assets" / "favicon.svg").read_text(encoding="utf-8")
    for text in (CSS, HTML, favicon):
        for old in ("1B3BC4", "F6B31B", "cobalt", "marigold", "F7F5F0", "0C7868", "C49A62"):
            assert old.lower() not in text.lower()


def test_all_motion_is_opt_in():
    still, _, moving = CSS.partition("@media screen and (prefers-reduced-motion: no-preference)")
    assert moving, "the motion block is missing"
    assert "animation:" not in still and "transition:" not in still and "scroll-behavior" not in still
    assert "@keyframes" in moving


def test_motion_stays_restrained():
    _, _, moving = CSS.partition("@media screen and (prefers-reduced-motion: no-preference)")
    assert moving.count("infinite") == 2, "only the two ambient lights loop"
    assert "is-away" in moving, "they pause once the hero is out of view"
    for banned in ("background-clip: text", "conic-gradient", "steps("):
        assert banned not in CSS
    for moved in re.findall(r"@keyframes [\w-]+ \{(.+?)\n  \}", moving, re.DOTALL):
        assert not re.search(r"\b(width|height|top|left|right|bottom|margin|padding)\s*:", moved), "keyframes must not cause layout"


def test_script_respects_reduced_motion_and_replays_only_on_request():
    script = (ROOT / "assets" / "site.js").read_text(encoding="utf-8")
    assert "prefers-reduced-motion: no-preference" in script
    assert "setInterval" not in script


def test_hidden_states_depend_on_the_script():
    # Anything hidden before it appears must be gated by .js, so the page is complete without the script.
    for selector in re.findall(r"([^\n{}]*:not\(\.in\)[^\n{}]*)\{", CSS):
        assert selector.strip().startswith(".js"), selector


def test_hero_path_matches_the_real_project():
    project = next(p for p in SHOWN if p["id"] == DATA.get("featured", "clientpilot"))
    block = re.search(r'<figure class="path.*?</figure>', HTML, re.DOTALL).group(0)
    assert re.findall(r'<span class="path-name">(.+?)</span>', block) == [s["name"] for s in project["trace"]]
    assert "a prototype" in block
    assert f'href="#{project["id"]}"' in block


def test_mobile_menu_is_wired():
    assert re.search(r'<button type="button" class="menu-btn" aria-expanded="false" aria-controls="site-nav">', HTML)
    assert '<nav id="site-nav"' in HTML
    assert "html:not(.js) .menu-btn { display: none; }" in CSS


def test_page_is_one_dark_theme():
    assert "prefers-color-scheme" not in CSS
    assert '<meta name="color-scheme" content="dark">' in HTML
    assert '<meta name="theme-color" content="#0B0F12">' in HTML


def test_name_stays_at_a_balanced_scale():
    block = re.search(r"\nh1 \{(.+?)\}", CSS, re.DOTALL).group(1)
    largest = float(re.search(r"font-size: clamp\([^)]*,\s*([\d.]+)rem\)", block).group(1))
    assert largest <= 3.25


@pytest.mark.parametrize(
    "foreground, background",
    [
        ("text", "bg"), ("text", "bg-2"), ("text", "surface"),
        ("text-2", "bg"), ("text-2", "bg-2"), ("text-2", "surface"),
        ("accent", "bg"), ("accent", "bg-2"), ("accent", "surface"),
        ("accent-hover", "bg"), ("accent-hover", "surface"),
        ("gold", "bg"), ("gold", "bg-2"), ("gold", "surface"),
        ("on-accent", "accent"), ("on-accent", "accent-hover"),
    ],
)
def test_text_colors_meet_wcag_aa(foreground, background):
    ratio = _contrast(TOKENS[foreground], TOKENS[background])
    assert ratio >= 4.5, f"{foreground} on {background}: {ratio:.2f}"


@pytest.mark.parametrize("foreground", ["accent", "gold", "text-2"])
@pytest.mark.parametrize("background", ["bg", "bg-2", "surface"])
def test_graphics_and_focus_rings_meet_3_to_1(foreground, background):
    ratio = _contrast(TOKENS[foreground], TOKENS[background])
    assert ratio >= 3, f"{foreground} on {background}: {ratio:.2f}"


def test_page_shows_confirmed_facts_only():
    """Disputed details stay in the private unconfirmed list, never on the page."""
    text = re.sub(r"<[^>]+>", " ", HTML)
    for disputed in ("Qafza", "Qafzeh", "Jul 2026", "Oct 2026", "Sep 2026", "Nov 2026", "Pending confirmation"):
        assert disputed not in text, disputed
    green = next(job for job in DATA["experience"] if job["org"] == "Green Circle for Cybersecurity")
    assert (green["role"], green["dates"]) == ("AI Engineering Intern", "2026")
    assert any("Green Circle: exact start and end months" in item for item in [*DATA["unconfirmed"], *DATA.get("resolved_for_release", {})])
