#!/usr/bin/env python3
"""Build the LingXiFox Apps static site with no third-party dependencies."""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
CONTENT = ROOT / "content"
ASSETS = ROOT / "assets"
SITE_URL = "https://apps.lingxifox.cn"
SITE_NAME = "LingXiFox Apps"
ISSUES_URL = "https://github.com/LingXiFox/LingXiStyle/issues"
REPO_URL = "https://github.com/LingXiFox/apps-site"
TODAY = date(2026, 11, 13)

sys.path.insert(0, str(CONTENT))
import zh_hans  # noqa: E402
import zh_hant  # noqa: E402
import en  # noqa: E402
import ja  # noqa: E402

LANGS = [zh_hans.LANG, zh_hant.LANG, en.LANG, ja.LANG]
PAGE_ORDER = ["home", "texel", "privacy", "support"]
PAGE_REL = {
    "home": "",
    "texel": "texel",
    "privacy": "texel/privacy",
    "support": "texel/support",
}
PAGE_PRIORITY = {"home": "1.0", "texel": "0.9", "privacy": "0.6", "support": "0.7"}

ICONS = {
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "arrow-up-right": '<path d="M7 17 17 7M8 7h9v9"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "chevron": '<path d="m6 9 6 6 6-6"/>',
    "device": '<rect x="7" y="2.5" width="10" height="19" rx="2.5"/><path d="M11 18.5h2"/>',
    "layers": '<path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 16 9 5 9-5"/>',
    "shield": '<path d="M12 3 5 6v6c0 4.5 3 7.5 7 9 4-1.5 7-4.5 7-9V6l-7-3Z"/>',
    "lock": '<rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/>',
    "queue": '<path d="M4 6h16M4 12h10M4 18h13"/>',
    "spark": '<path d="m12 3 1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3Z"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
    "save": '<path d="M12 3v12m0 0 4-4m-4 4-4-4"/><path d="M5 21h14"/>',
    "user-off": '<circle cx="9" cy="8" r="3.5"/><path d="M3 20c0-3.3 2.7-6 6-6 1.6 0 3 .6 4 1.6"/><path d="m16 16 5 5m0-5-5 5"/>',
    "eye-off": '<path d="M3 3l18 18"/><path d="M10.6 10.6a2 2 0 0 0 2.8 2.8"/><path d="M9.4 5.2A10.5 10.5 0 0 1 12 5c5 0 9 4.5 9 7a11.5 11.5 0 0 1-2.4 3.6"/><path d="M6.2 6.2C4.2 7.6 3 9.7 3 12c0 2.5 4 7 9 7 1.4 0 2.7-.3 3.9-.9"/>',
}

FLOW_ICONS = ["search", "spark", "shield", "save"]


def esc(value: str) -> str:
    return html.escape(str(value), quote=True)


def icon(name: str, cls: str = "") -> str:
    body = ICONS[name]
    klass = f"icon {cls}".strip()
    return (
        f'<svg class="{klass}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true" focusable="false">{body}</svg>'
    )


def page_path(lang: dict, page: str) -> str:
    rel = PAGE_REL[page]
    prefix = lang["prefix"]
    if not rel:
        return f"{prefix}/" if prefix else "/"
    return f"{prefix}/{rel}/"


def page_output(page_path_value: str) -> Path:
    clean = page_path_value.strip("/")
    if not clean:
        return DIST / "index.html"
    return DIST / clean / "index.html"


def nav_items(lang: dict, current: str) -> str:
    labels = lang["nav"]
    items = []
    for page in PAGE_ORDER:
        href = page_path(lang, page)
        active = ' class="is-active" aria-current="page"' if page == current else ""
        items.append(f'<a href="{esc(href)}"{active}>{esc(labels[page])}</a>')
    items.append(
        f'<a href="{esc(ISSUES_URL)}" rel="noopener">{esc(labels["github"])}'
        f'<span class="external-mark" aria-hidden="true">↗</span></a>'
    )
    return "".join(items)


def lang_switch(lang: dict, current: str) -> str:
    rows = []
    for other in LANGS:
        href = page_path(other, current)
        is_current = other["code"] == lang["code"]
        aria = ' aria-current="true"' if is_current else ""
        rows.append(
            f'<a href="{esc(href)}" hreflang="{esc(other["html_lang"])}" '
            f'lang="{esc(other["html_lang"])}"{aria}>'
            f'{esc(other["name"])}</a>'
        )
    return (
        '<details class="lang-switch">'
        f'<summary aria-label="{esc(lang["common"]["language"])}: {esc(lang["name"])}">'
        f'<span>{esc(lang["label"])}</span>{icon("chevron", "chevron")}</summary>'
        f'<div class="lang-menu" role="group" aria-label="{esc(lang["common"]["language"])}">'
        + "".join(rows)
        + "</div></details>"
    )


def header(lang: dict, current: str) -> str:
    nav = nav_items(lang, current)
    return f"""
<header class="site-header">
  <div class="header-inner">
    <a class="brand" href="{esc(page_path(lang, 'home'))}" aria-label="LingXiFox Apps">
      <span class="brand-mark" aria-hidden="true">LX</span>
      <span class="brand-word">LingXiFox<span class="brand-dot">.</span>apps</span>
    </a>
    <nav class="desktop-nav" aria-label="Primary">{nav}</nav>
    <div class="header-actions">
      {lang_switch(lang, current)}
      <details class="mobile-menu">
        <summary aria-label="{esc(lang['common']['menu'])}"><span class="menu-lines" aria-hidden="true"><i></i><i></i></span></summary>
        <nav class="mobile-nav" aria-label="Mobile">{nav}</nav>
      </details>
    </div>
  </div>
</header>"""


def footer(lang: dict) -> str:
    f = lang["footer"]
    n = lang["nav"]
    return f"""
<footer class="site-footer">
  <div class="footer-inner">
    <div class="footer-brand">
      <a class="brand" href="{esc(page_path(lang, 'home'))}" aria-label="LingXiFox Apps">
        <span class="brand-mark" aria-hidden="true">LX</span>
        <span class="brand-word">LingXiFox<span class="brand-dot">.</span>apps</span>
      </a>
      <p>{esc(f['tagline'])}</p>
    </div>
    <div class="footer-col">
      <h2>{esc(f['explore'])}</h2>
      <a href="{esc(page_path(lang, 'texel'))}">Texel</a>
      <a href="{esc(page_path(lang, 'privacy'))}">{esc(n['privacy'])}</a>
      <a href="{esc(page_path(lang, 'support'))}">{esc(n['support'])}</a>
    </div>
    <div class="footer-col">
      <h2>{esc(f['resources'])}</h2>
      <a href="{esc(REPO_URL)}" rel="noopener">{esc(f['github'])}<span class="external-mark" aria-hidden="true">↗</span></a>
      <a href="{esc(ISSUES_URL)}" rel="noopener">{esc(lang['common']['github_issues'])}<span class="external-mark" aria-hidden="true">↗</span></a>
    </div>
    <div class="footer-col footer-contact">
      <h2>{esc(f['contact'])}</h2>
      <p>{esc(f['contact_body'])}</p>
      <a class="text-link" href="{esc(ISSUES_URL)}" rel="noopener">{esc(lang['common']['github_issues'])} {icon('arrow-up-right')}</a>
    </div>
  </div>
  <div class="footer-bottom">
    <p>{esc(f['rights'])}</p>
    <p>{esc(f['note'])}</p>
  </div>
</footer>"""


def head(lang: dict, page: str, title: str, desc: str, noindex: bool = False, json_ld: dict | None = None) -> str:
    canonical = SITE_URL + page_path(lang, page)
    alternates = []
    for other in LANGS:
        alternates.append(
            f'<link rel="alternate" hreflang="{esc(other["html_lang"])}" '
            f'href="{esc(SITE_URL + page_path(other, page))}">'
        )
    alternates.append(
        f'<link rel="alternate" hreflang="x-default" href="{esc(SITE_URL + page_path(LANGS[0], page))}">'
    )
    og_locales = [
        f'<meta property="og:locale:alternate" content="{esc(other["og_locale"])}">'
        for other in LANGS
        if other["code"] != lang["code"]
    ]
    robots = '<meta name="robots" content="noindex, follow">' if noindex else '<meta name="robots" content="index, follow, max-image-preview:large">'
    ld = ""
    if json_ld:
        ld = (
            '<script type="application/ld+json">'
            + json.dumps(json_ld, ensure_ascii=False, separators=(",", ":"))
            + "</script>"
        )
    return f"""<!doctype html>
<html lang="{esc(lang['html_lang'])}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{robots}
<link rel="canonical" href="{esc(canonical)}">
{''.join(alternates)}
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(SITE_NAME)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="og:image" content="{esc(SITE_URL)}/assets/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="{esc(lang['og_locale'])}">
{''.join(og_locales)}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{esc(SITE_URL)}/assets/og.png">
<meta name="theme-color" content="#FBFBFD" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0B0B0F" media="(prefers-color-scheme: dark)">
<link rel="icon" href="/assets/icon-32.png" sizes="32x32" type="image/png">
<link rel="icon" href="/assets/icon-192.png" sizes="192x192" type="image/png">
<link rel="apple-touch-icon" href="/assets/icon-180.png">
<link rel="manifest" href="/assets/site.webmanifest">
<link rel="stylesheet" href="/assets/styles.css">
{ld}
</head>
<body class="page-{page}">
<a class="skip-link" href="#main">{esc(lang['common']['skip'])}</a>
<div class="grain" aria-hidden="true"></div>
{header(lang, page)}
<main id="main">
"""


def close_page(lang: dict) -> str:
    return f"""
</main>
{footer(lang)}
</body>
</html>
"""


def home_body(lang: dict) -> str:
    h = lang["home"]
    values = "".join(
        f'<article class="value-card"><div class="value-icon">{icon(name)}</div>'
        f'<h3>{esc(item["title"])}</h3><p>{esc(item["body"])}</p></article>'
        for name, item in zip(("device", "layers", "shield"), h["values"])
    )
    chips = "".join(f'<span class="chip">{esc(chip)}</span>' for chip in h["chips"])
    return f"""
<section class="hero home-hero">
  <div class="container hero-grid">
    <div class="hero-copy">
      <p class="eyebrow">{esc(h['eyebrow'])}</p>
      <h1>{h['title']}</h1>
      <p class="lead">{esc(h['lead'])}</p>
      <div class="actions">
        <a class="button primary" href="{esc(page_path(lang, 'texel'))}">{esc(h['primary'])} {icon('arrow')}</a>
        <a class="button secondary" href="{esc(page_path(lang, 'privacy'))}">{esc(h['secondary'])}</a>
      </div>
      <p class="status-line"><span class="status-dot" aria-hidden="true"></span>{esc(h['status'])}</p>
    </div>
    <div class="hero-art home-art" aria-hidden="true">
      <div class="glow glow-one"></div>
      <div class="glow glow-two"></div>
      <div class="showcase">
        <div class="showcase-head">
          <img src="/assets/texel-icon.png" alt="" width="56" height="56">
          <div><strong>Texel</strong><span>{esc(lang['texel']['subtitle'])}</span></div>
          <span class="live-dot"></span>
        </div>
        <div class="showcase-visual">
          <span class="grain-swatch"></span>
          <span class="visual-label">HEIC</span>
        </div>
        <div class="showcase-foot">
          <span>{esc(lang['common']['local_badge'])}</span>
          <span>{esc(lang['common']['no_upload_badge'])}</span>
        </div>
      </div>
      <div class="float-badge badge-a">{esc(lang['common']['heic_badge'])}</div>
      <div class="float-badge badge-b">5 / day</div>
    </div>
  </div>
</section>

<section class="section">
  <div class="container">
    <div class="section-head">
      <p class="eyebrow">{esc(h['values_title'])}</p>
      <h2>{esc(h['values_lead'])}</h2>
    </div>
    <div class="value-grid">{values}</div>
  </div>
</section>

<section class="section product-section">
  <div class="container">
    <a class="product-card" href="{esc(page_path(lang, 'texel'))}">
      <div class="product-icon"><img src="/assets/texel-icon.png" alt="" width="96" height="96"></div>
      <div class="product-copy">
        <p class="eyebrow">{esc(h['product_eyebrow'])}</p>
        <h2>{esc(h['product_heading'])}</h2>
        <p class="product-tagline">{esc(h['product_tagline'])}</p>
        <p>{esc(h['product_body'])}</p>
        <div class="chip-row">{chips}</div>
      </div>
      <span class="product-arrow" aria-hidden="true">{icon('arrow-up-right')}</span>
    </a>
  </div>
</section>

<section class="section">
  <div class="container">
    <div class="note-card">
      <p class="eyebrow">{esc(h['more_title'])}</p>
      <p>{esc(h['more_body'])}</p>
    </div>
  </div>
</section>"""


def art_for(feature: dict) -> str:
    art = feature["art"]
    if art == "stack":
        return """
<div class="art-stack">
  <div class="layer layer-3"><span>Styles</span></div>
  <div class="layer layer-2"><span>EXIF</span></div>
  <div class="layer layer-1"><span>HDR</span></div>
  <div class="layer-base"><span>HEIC</span><small>original</small></div>
</div>"""
    if art == "local":
        local_tags = feature.get("art_tags", ["On-device", "Keychain"])
        return f"""
<div class="art-local">
  <div class="phone">
    <div class="phone-notch"></div>
    <div class="phone-screen">
      <div class="lock-badge">{icon('lock')}</div>
      <strong>0</strong>
      <div class="phone-lines"><i></i><i></i><i></i></div>
    </div>
  </div>
  <div class="art-tag tag-a">{esc(local_tags[0])}</div>
  <div class="art-tag tag-b">{esc(local_tags[1])}</div>
</div>"""
    if art == "queue":
        return f"""
<div class="art-queue">
  <div class="queue-row"><span class="queue-index">1</span><div class="queue-bar p100"><i></i></div><span class="queue-state done">{icon('check')}</span></div>
  <div class="queue-row"><span class="queue-index">2</span><div class="queue-bar p64"><i></i></div><span class="queue-state active"></span></div>
  <div class="queue-row"><span class="queue-index">3</span><div class="queue-bar p28"><i></i></div><span class="queue-state"></span></div>
  <div class="queue-caption">iCloud · 9</div>
</div>"""
    tags = feature.get("art_tags", [])
    tag_html = "".join(f'<span>{esc(tag)}</span>' for tag in tags)
    return f"""
<div class="art-privacy">
  <div class="shield-ring">{icon('shield')}</div>
  <div class="privacy-tags">{tag_html}</div>
</div>"""


def texel_body(lang: dict) -> str:
    t = lang["texel"]
    stats = "".join(
        f'<div class="stat"><span class="stat-value">{esc(item["value"])}</span>'
        f'<span class="stat-label">{esc(item["label"])}</span></div>'
        for item in t["stats"]
    )
    features = []
    for index, feature in enumerate(t["features"]):
        bullets = "".join(
            f'<li>{icon("check")}<span>{esc(bullet)}</span></li>' for bullet in feature["bullets"]
        )
        reverse = " reverse" if index % 2 else ""
        features.append(
            f'<article class="feature{reverse}">'
            f'<div class="feature-copy"><p class="kicker">{esc(feature["kicker"])}</p>'
            f'<h2>{esc(feature["title"])}</h2><p>{esc(feature["body"])}</p>'
            f'<ul class="check-list">{bullets}</ul></div>'
            f'<div class="feature-art">{art_for(feature)}</div></article>'
        )
    specs = "".join(
        f'<div class="spec-row"><dt>{esc(item["label"])}</dt><dd>{esc(item["value"])}</dd></div>'
        for item in t["specs"]
    )
    flow_labels = t.get("flow", ["Inspect", "Convert", "Verify", "Save"])
    flow = "".join(
        f'<div class="flow-step"><span class="flow-icon">{icon(FLOW_ICONS[i])}</span>'
        f'<span>{esc(label)}</span></div>'
        for i, label in enumerate(flow_labels)
    )
    faq = "".join(
        f'<details class="faq-item"><summary>{esc(item["q"])}<span class="faq-plus" aria-hidden="true"></span></summary>'
        f'<div class="faq-answer"><p>{esc(item["a"])}</p></div></details>'
        for item in t["faq"]
    )
    meta = "".join(f'<span class="chip">{esc(item)}</span>' for item in t["meta"])
    return f"""
<section class="hero product-hero">
  <div class="container hero-grid">
    <div class="hero-copy">
      <p class="eyebrow">{esc(t['eyebrow'])}</p>
      <h1>{esc(t['title'])} <span class="title-sub">{esc(t['subtitle'])}</span></h1>
      <p class="lead">{esc(t['lead'])}</p>
      <p class="status-line"><span class="status-dot" aria-hidden="true"></span>{esc(t['status'])}</p>
      <div class="actions">
        <a class="button primary" href="{esc(page_path(lang, 'support'))}">{esc(t['cta_primary'])} {icon('arrow')}</a>
        <a class="button secondary" href="{esc(page_path(lang, 'privacy'))}">{esc(t['cta_secondary'])}</a>
      </div>
      <div class="chip-row meta-row">{meta}</div>
    </div>
    <div class="hero-art product-art" aria-hidden="true">
      <div class="icon-halo"></div>
      <img class="product-icon-large" src="/assets/texel-icon.png" alt="" width="320" height="320">
      <div class="orbit-ring"></div>
      <span class="float-chip chip-hdr">HDR</span>
      <span class="float-chip chip-exif">EXIF</span>
      <span class="float-chip chip-styles">Styles</span>
    </div>
  </div>
</section>

<section class="stats-band">
  <div class="container stats-grid">{stats}</div>
</section>

<section class="section">
  <div class="container feature-list">{''.join(features)}</div>
</section>

<section class="section">
  <div class="container split-head">
    <div><p class="eyebrow">{esc(t['specs_title'])}</p><h2>{esc(t['specs_lead'])}</h2></div>
    <p class="split-note">{esc(t['compat_body'])}</p>
  </div>
  <div class="container">
    <dl class="spec-grid">{specs}</dl>
  </div>
</section>

<section class="section">
  <div class="container">
    <div class="flow-card">
      <div class="flow-copy"><h2>{esc(t['compat_title'])}</h2></div>
      <div class="flow">{flow}</div>
    </div>
  </div>
</section>

<section class="section">
  <div class="container pricing-wrap">
    <div class="section-head">
      <p class="eyebrow">Pro</p>
      <h2>{esc(t['pricing_title'])}</h2>
      <p>{esc(t['pricing_body'])}</p>
    </div>
    <div class="pricing-grid">
      <article class="price-card">
        <p class="price-label">{esc(t['pricing_free_title'])}</p>
        <p class="price-value">5 <small>/ day</small></p>
        <p>{esc(t['pricing_free_body'])}</p>
      </article>
      <article class="price-card featured">
        <p class="price-label">{esc(t['pricing_pro_title'])}</p>
        <p class="price-value">∞</p>
        <p>{esc(t['pricing_pro_body'])}</p>
        <a class="text-link" href="{esc(page_path(lang, 'support'))}">{esc(lang['common']['read_support'])} {icon('arrow')}</a>
      </article>
    </div>
    <p class="fine-print">{esc(t['pricing_note'])}</p>
  </div>
</section>

<section class="section">
  <div class="container faq-wrap">
    <div class="section-head"><p class="eyebrow">FAQ</p><h2>{esc(t['faq_title'])}</h2></div>
    <div class="faq-list">{faq}</div>
  </div>
</section>

<section class="section">
  <div class="container">
    <div class="final-card">
      <div><p class="eyebrow">Texel</p><h2>{esc(t['final_title'])}</h2><p>{esc(t['final_body'])}</p></div>
      <a class="button primary" href="{esc(page_path(lang, 'support'))}">{esc(t['final_cta'])} {icon('arrow')}</a>
    </div>
  </div>
</section>"""


def doc_body(lang: dict, page: str, body_html: str) -> str:
    data = lang[page]
    toc = ""
    if page == "privacy":
        toc = "".join(f'<a href="#{esc(s["id"])}">{esc(s["title"])}</a>' for s in data["sections"])
    else:
        toc = f'<a href="#quick-start">{esc(data["quick_title"])}</a><a href="#faq">{esc(data["faq_title"])}</a><a href="#contact">{esc(data["contact_title"])}</a>'
    return f"""
<section class="page-hero">
  <div class="container narrow">
    <p class="eyebrow">Texel · {'Legal' if page == 'privacy' else 'Support'}</p>
    <h1>{esc(data['title'])}</h1>
    <p class="updated">{esc(data.get('updated', ''))}</p>
    <p class="lead">{esc(data['intro'])}</p>
  </div>
</section>
<section class="section doc-section">
  <div class="container doc-layout">
    <nav class="toc" aria-label="On this page">{toc}</nav>
    <div class="doc-content">{body_html}</div>
  </div>
</section>"""


def privacy_body(lang: dict) -> str:
    p = lang["privacy"]
    sections = "".join(
        f'<section class="doc-block" id="{esc(s["id"])}"><h2>{esc(s["title"])}</h2>{s["html"]}</section>'
        for s in p["sections"]
    )
    body = f"""
<div class="summary-box"><p>{esc(p['summary'])}</p></div>
{sections}
<aside class="contact-card" id="contact-card">
  <h2>{esc(p['contact_title'])}</h2>
  <p>{esc(p['contact_body'])}</p>
  <a class="button primary" href="{esc(ISSUES_URL)}" rel="noopener">{esc(p['contact_cta'])} {icon('arrow-up-right')}</a>
</aside>"""
    return doc_body(lang, "privacy", body)


def support_body(lang: dict) -> str:
    s = lang["support"]
    steps = "".join(
        f'<article class="step-card"><span class="step-number">{i:02d}</span>'
        f'<h3>{esc(step["title"])}</h3><p>{esc(step["body"])}</p></article>'
        for i, step in enumerate(s["steps"], 1)
    )
    faq = "".join(
        f'<details class="faq-item"><summary>{esc(item["q"])}<span class="faq-plus" aria-hidden="true"></span></summary>'
        f'<div class="faq-answer"><p>{esc(item["a"])}</p></div></details>'
        for item in s["faq"]
    )
    diag = "".join(f"<li>{esc(item)}</li>" for item in s["diag_items"])
    body = f"""
<section class="doc-block" id="quick-start">
  <h2>{esc(s['quick_title'])}</h2>
  <p>{esc(s['quick_lead'])}</p>
</section>
<div class="step-grid">{steps}</div>
<section class="doc-block" id="faq">
  <h2>{esc(s['faq_title'])}</h2>
  <div class="faq-list">{faq}</div>
</section>
<aside class="contact-card" id="contact">
  <h2>{esc(s['contact_title'])}</h2>
  <p>{esc(s['contact_body'])}</p>
  <h3>{esc(s['diag_title'])}</h3>
  <ul class="diag-list">{diag}</ul>
  <a class="button primary" href="{esc(ISSUES_URL)}" rel="noopener">{esc(s['contact_cta'])} {icon('arrow-up-right')}</a>
</aside>"""
    return doc_body(lang, "support", body)


def build_page(lang: dict, page: str) -> None:
    meta = lang["meta"]
    title = meta[f"{page}_title"]
    desc = meta[f"{page}_desc"]
    if page == "home":
        body = home_body(lang)
        json_ld = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "LingXiFox",
            "url": SITE_URL,
            "logo": SITE_URL + "/assets/texel-icon.png",
            "sameAs": [REPO_URL],
        }
    elif page == "texel":
        body = texel_body(lang)
        json_ld = {
            "@context": "https://schema.org",
            "@type": "SoftwareApplication",
            "name": "Texel",
            "alternateName": "纹粒",
            "applicationCategory": "PhotographyApplication",
            "operatingSystem": "iOS 18 or later",
            "description": desc,
            "url": SITE_URL + page_path(lang, "texel"),
            "image": SITE_URL + "/assets/texel-icon.png",
            "author": {"@type": "Organization", "name": "LingXiFox", "url": SITE_URL},
            "inLanguage": lang["html_lang"],
        }
    elif page == "privacy":
        body = privacy_body(lang)
        json_ld = None
    else:
        body = support_body(lang)
        json_ld = None
    document = head(lang, page, title, desc, json_ld=json_ld) + body + close_page(lang)
    out = page_output(page_path(lang, page))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(document, encoding="utf-8")


def build_not_found() -> None:
    lang = LANGS[0]
    title = "404 — LingXiFox Apps"
    desc = "The requested page could not be found."
    body = f"""
<section class="notfound">
  <div class="container narrow">
    <p class="eyebrow">404</p>
    <h1>{esc(lang['notfound']['title'])}</h1>
    <p class="lead">{esc(lang['notfound']['body'])}</p>
    <p class="lead">The requested page could not be found. It may have moved, or the link may be outdated.</p>
    <div class="actions">
      <a class="button primary" href="/">{esc(lang['notfound']['cta'])} {icon('arrow')}</a>
      <a class="button secondary" href="/en/">English home</a>
    </div>
  </div>
</section>"""
    document = head(lang, "home", title, desc, noindex=True) + body + close_page(lang)
    (DIST / "404.html").write_text(document, encoding="utf-8")


def build_support_files() -> None:
    urls = []
    for page in PAGE_ORDER:
        for lang in LANGS:
            loc = SITE_URL + page_path(lang, page)
            urls.append(
                f"  <url><loc>{esc(loc)}</loc><lastmod>{TODAY.isoformat()}</lastmod>"
                f"<changefreq>monthly</changefreq><priority>{PAGE_PRIORITY[page]}</priority></url>"
            )
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls)
        + "\n</urlset>\n"
    )
    (DIST / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (DIST / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n\nSitemap: " + SITE_URL + "/sitemap.xml\n",
        encoding="utf-8",
    )
    (DIST / "_headers").write_text(
        """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  X-Frame-Options: DENY
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
  Cross-Origin-Opener-Policy: same-origin

/assets/*
  Cache-Control: public, max-age=86400
""",
        encoding="utf-8",
    )
    manifest = {
        "name": SITE_NAME,
        "short_name": "LingXiFox",
        "description": "Local tools for real photos.",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#FBFBFD",
        "theme_color": "#E8A13A",
        "icons": [
            {"src": "/assets/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/assets/icon-512.png", "sizes": "512x512", "type": "image/png"},
        ],
    }
    (DIST / "assets" / "site.webmanifest").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


class LinkParser(html.parser.HTMLParser if False else object):
    pass


def validate() -> None:
    from html.parser import HTMLParser

    class Parser(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.links: list[str] = []
            self.has_h1 = False
            self.has_title = False
            self.has_desc = False
            self.lang = ""

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            attrs_dict = dict(attrs)
            if tag == "html":
                self.lang = attrs_dict.get("lang", "") or ""
            if tag == "h1":
                self.has_h1 = True
            if tag == "title":
                self.has_title = True
            if tag == "meta" and attrs_dict.get("name") == "description":
                self.has_desc = bool(attrs_dict.get("content"))
            if tag in ("a", "link", "img", "script") and attrs_dict.get("href"):
                self.links.append(attrs_dict["href"] or "")
            if tag in ("img", "script") and attrs_dict.get("src"):
                self.links.append(attrs_dict["src"] or "")

    errors: list[str] = []
    pages = list(DIST.rglob("*.html"))
    for path in pages:
        parser = Parser()
        parser.feed(path.read_text(encoding="utf-8"))
        rel = path.relative_to(DIST)
        if not parser.lang:
            errors.append(f"{rel}: missing html lang")
        if not parser.has_h1:
            errors.append(f"{rel}: missing h1")
        if not parser.has_title:
            errors.append(f"{rel}: missing title")
        if not parser.has_desc and path.name != "404.html":
            errors.append(f"{rel}: missing meta description")
        for link in parser.links:
            if link.startswith("#") or link.startswith("mailto:") or link.startswith("https://") or link.startswith("http://"):
                continue
            if link.startswith("/"):
                target = DIST / link.lstrip("/")
                if link.endswith("/"):
                    target = target / "index.html"
                if not target.exists():
                    errors.append(f"{rel}: broken link {link}")
            else:
                errors.append(f"{rel}: unexpected relative link {link}")
    text = "".join(p.read_text(encoding="utf-8") for p in pages)
    if re.search(r"<[A-Z_]{3,}>", text):
        errors.append("placeholder-like token found")
    if "@" in re.sub(r"https?://[^\s\"']+", "", text):
        # URLs can contain @; only flag simple email-like strings outside URLs.
        if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text):
            errors.append("email-like string found")
    if errors:
        print("Validation failed:")
        for error in errors:
            print(" -", error)
        raise SystemExit(1)
    print(f"Validated {len(pages)} HTML pages: links, lang, title, description, h1, no placeholders.")


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    (DIST / "assets").mkdir(parents=True)
    for asset in ASSETS.iterdir():
        if asset.is_file():
            shutil.copy2(asset, DIST / "assets" / asset.name)
    for lang in LANGS:
        for page in PAGE_ORDER:
            build_page(lang, page)
    build_not_found()
    build_support_files()
    validate()
    print(f"Built {len(list(DIST.rglob('*.html')))} pages into {DIST}")


if __name__ == "__main__":
    main()
