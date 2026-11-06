#!/usr/bin/env python3
"""Build the light Palio plumbing overlay: search index, win chart, related-page strips.

Does not push, does not fetch new images, and does not invent crest files.
Counts victories only from Orlando's own pages in this copy.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from html import escape, unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CONTRADE = [
    {
        "slug": "aquila",
        "name": "Aquila",
        "profile": "17aquila.htm",
        "wins_page": "vittoriecontradeaquila.htm",
        "crest": "stemminoaquila74.gif",
        "aliases": ("AQUILA",),
    },
    {
        "slug": "bruco",
        "name": "Bruco",
        "profile": "17bruco.htm",
        "wins_page": "vittoriecontradebruco.htm",
        "crest": "stemminobruco74.gif",
        "aliases": ("BRUCO",),
    },
    {
        "slug": "chiocciola",
        "name": "Chiocciola",
        "profile": "17chiocciola.htm",
        "wins_page": "vittoriecontradechiocciola.htm",
        "crest": "stemminochiocciola74.gif",
        "aliases": ("CHIOCCIOLA",),
    },
    {
        "slug": "civetta",
        "name": "Civetta",
        "profile": "17civetta.htm",
        "wins_page": "vittoriecontradecivetta.htm",
        "crest": "stemminoCIVETTA74.gif",
        "aliases": ("CIVETTA",),
    },
    {
        "slug": "drago",
        "name": "Drago",
        "profile": "17drago.htm",
        "wins_page": "vittoriecontradedrago.htm",
        "crest": "stemminoDRAGO74.gif",
        "aliases": ("DRAGO",),
    },
    {
        "slug": "giraffa",
        "name": "Giraffa",
        "profile": "17giraffa.htm",
        "wins_page": "vittoriecontradegiraffa.htm",
        "crest": "stemminoGIRAFFA74.gif",
        "aliases": ("GIRAFFA",),
    },
    {
        "slug": "istrice",
        "name": "Istrice",
        "profile": "17istrice.htm",
        "wins_page": "vittoriecontradeistrice.htm",
        "crest": "stemminoISTRICE74.gif",
        "aliases": ("ISTRICE",),
    },
    {
        "slug": "leocorno",
        "name": "Leocorno",
        "profile": "17leocorno.htm",
        "wins_page": "vittoriecontradeleocorno.htm",
        "crest": "stemminoLEOCORNO74.gif",
        "aliases": ("LEOCORNO",),
    },
    {
        "slug": "lupa",
        "name": "Lupa",
        "profile": "17lupa.htm",
        "wins_page": "vittoriecontradelupa.htm",
        "crest": "stemminoLUPA74.gif",
        "aliases": ("LUPA",),
    },
    {
        "slug": "nicchio",
        "name": "Nicchio",
        "profile": "17nicchio.htm",
        "wins_page": "vittoriecontradenicchio.htm",
        "crest": "stemminoNICCHIO74.gif",
        "aliases": ("NICCHIO",),
    },
    {
        "slug": "oca",
        "name": "Oca",
        "profile": "17oca.htm",
        "wins_page": "vittoriecontradeoca.htm",
        "crest": "stemminoOCA74.gif",
        "aliases": ("OCA",),
    },
    {
        "slug": "onda",
        "name": "Onda",
        "profile": "17onda.htm",
        "wins_page": "vittoriecontradeonda.htm",
        "crest": "stemminoONDA74.gif",
        "aliases": ("ONDA",),
    },
    {
        "slug": "pantera",
        "name": "Pantera",
        "profile": "17pantera.htm",
        "wins_page": "vittoriecontradepantera.htm",
        "crest": "stemminoPANTERA75.png",
        "aliases": ("PANTERA",),
    },
    {
        "slug": "selva",
        "name": "Selva",
        "profile": "17selva.htm",
        "wins_page": "vittoriecontradeselva.htm",
        "crest": "stemminoSELVA74.gif",
        "aliases": ("SELVA",),
    },
    {
        "slug": "tartuca",
        "name": "Tartuca",
        "profile": "17tartuca.htm",
        "wins_page": "vittoriecontradetartuca.htm",
        "crest": "stemminoTARTUCA74.gif",
        "aliases": ("TARTUCA",),
    },
    {
        "slug": "torre",
        "name": "Torre",
        "profile": "17torre.htm",
        "wins_page": "vittoriecontradetorre.htm",
        "crest": "stemminoTORRE74.gif",
        "aliases": ("TORRE",),
    },
    {
        "slug": "valdimontone",
        "name": "Valdimontone",
        "profile": "17montone.htm",
        "wins_page": "vittoriecontradevaldimontone.htm",
        "crest": "stemminovaldiMONTONE74.gif",
        "aliases": ("VALDIMONTONE", "VALDI MONTONE", "VAL DI MONTONE", "MONTONE"),
    },
]

ALIAS_TO_SLUG = {}
for row in CONTRADE:
    for alias in row["aliases"]:
        ALIAS_TO_SLUG[alias] = row["slug"]
SLUG = {row["slug"]: row for row in CONTRADE}

FANTINI_INDEXES = [
    ("dizionarioaf.htm", "Fantini A-F (cognome)"),
    ("dizionariogo.htm", "Fantini G-O (cognome)"),
    ("dizionariopz.htm", "Fantini P-Z (cognome)"),
    ("dizionariosoprannomiaf.htm", "Fantini A-F (soprannome)"),
    ("dizionariosoprannomigo.htm", "Fantini G-O (soprannome)"),
    ("dizionariosoprannomipz.htm", "Fantini P-Z (soprannome)"),
]
HORSE_INDEXES = [
    ("cavalli900ter.htm", "Cavalli 1900-1939"),
    ("cavalli900bis.htm", "Cavalli 1945-1999"),
    ("cavalli2000bis.htm", "Cavalli dal 2000"),
]

MARKER_START = b"<!-- palio-plumbing -->"
MARKER_END = b"<!-- /palio-plumbing -->"
SEARCH_START = b"<!-- palio-plumbing-search -->"
SEARCH_END = b"<!-- /palio-plumbing-search -->"
SEARCH_SNIPPET = (
    b"<!-- palio-plumbing-search -->"
    b'[<a href="cerca.htm" title="Cerca nel sito">CERCA NEL SITO</a>] '
    b"<!-- /palio-plumbing-search -->"
)
SKIP_INDEX_NAMES = {
    "search-index.json",
    "related-map.json",
    "plumbing.css",
    "plumbing-cerca.js",
}
HREF_RE = re.compile(
    r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
    flags=re.I | re.S,
)
ALBO_RE = re.compile(
    r'<a\s+[^>]*href=["\'](sch[^"\']+)["\'][^>]*>(.*?)</a>([^<]{0,100})',
    flags=re.I | re.S,
)


def decode_bytes(data: bytes) -> str:
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1", "replace")


def read_text(path: Path) -> str:
    return decode_bytes(path.read_bytes())


def file_index() -> dict[str, list[str]]:
    idx: dict[str, list[str]] = {}
    for p in ROOT.iterdir():
        if p.is_file():
            idx.setdefault(p.name.lower(), []).append(p.name)
    return idx


def resolve_name(name: str, idx: dict[str, list[str]]) -> str | None:
    raw = name.split("?")[0].split("#")[0].split("/")[-1]
    if not raw:
        return None
    direct = ROOT / raw
    if direct.is_file():
        return direct.name
    cands = idx.get(raw.lower(), [])
    if not cands:
        return None
    for cand in cands:
        if cand == raw:
            return cand
    return cands[0]


def extract_hrefs(html: str) -> list[tuple[str, str]]:
    out = []
    for href, inner in HREF_RE.findall(html):
        text = unescape(re.sub(r"<[^>]+>", " ", inner))
        text = re.sub(r"\s+", " ", text).strip()
        out.append((href, text))
    return out


HREF_ATTR_RE = re.compile('\\bhref=["\']([^"\']+)["\']', flags=re.I)


def unique_sch_links(html: str, idx: dict[str, list[str]]) -> list[str]:
    found = []
    seen = set()
    for href in HREF_ATTR_RE.findall(html):
        base = href.split("?")[0].split("#")[0].split("/")[-1]
        if not re.match(r"sch\d{4}", base, re.I):
            continue
        resolved = resolve_name(base, idx) or base
        key = resolved.lower()
        if key not in seen:
            seen.add(key)
            found.append(resolved)
    return found


def visible_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style|noscript)\b[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<!--.*?-->", " ", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    html = unescape(html).replace("\xa0", " ")
    return re.sub(r"\s+", " ", html).strip()


def page_title(html: str, fallback: str) -> str:
    match = re.search(r"(?is)<title[^>]*>(.*?)</title>", html)
    if not match:
        return fallback
    title = unescape(re.sub(r"<[^>]+>", " ", match.group(1)))
    title = re.sub(r"\s+", " ", title).strip()
    return title or fallback


def is_palio_year(name: str) -> bool:
    return bool(re.match(r"sch\d{4}", name, re.I)) and name.lower().endswith((".htm", ".html"))


def parse_albo(idx: dict[str, list[str]]) -> tuple[list[dict], dict[str, str], Counter]:
    html = read_text(ROOT / "vittorie.htm")
    order = []
    winners = {}
    counts = Counter()
    seen = set()
    alias_names = sorted(ALIAS_TO_SLUG, key=len, reverse=True)
    for href, inner, after in ALBO_RE.findall(html):
        resolved = resolve_name(href, idx)
        if not resolved:
            continue
        label = unescape(re.sub(r"<[^>]+>", " ", inner))
        label = re.sub(r"\s+", " ", label).strip()
        date_label = re.split(r"\s+-\s+", label, maxsplit=1)[0].strip() or label
        blob = (label + " " + after).upper()
        slug = None
        for alias in alias_names:
            if re.search(r"\b" + re.escape(alias) + r"\b", blob):
                slug = ALIAS_TO_SLUG[alias]
                break
        key = resolved.lower()
        if (
            slug
            and "RINVIATO" not in blob
            and "ANNULLATO" not in blob
            and "NON DISPUTATO" not in blob
            and key not in seen
        ):
            winners[key] = slug
            counts[slug] += 1
        if key not in seen:
            seen.add(key)
            order.append({"file": resolved, "label": date_label, "winner": slug})
    return order, winners, counts


def count_wins_from_contrada_pages(idx: dict[str, list[str]]) -> dict[str, list[str]]:
    wins = {}
    for row in CONTRADE:
        path = ROOT / row["wins_page"]
        if not path.is_file():
            wins[row["slug"]] = []
            continue
        wins[row["slug"]] = unique_sch_links(read_text(path), idx)
    return wins


def collect_linked_pages(sources, idx, predicate):
    found = {}
    for filename, _label in sources:
        path = ROOT / filename
        if not path.is_file():
            continue
        for href, _text in extract_hrefs(read_text(path)):
            base = href.split("?")[0].split("#")[0].split("/")[-1]
            if not predicate(base):
                continue
            resolved = resolve_name(base, idx)
            if resolved and resolved not in found:
                found[resolved] = filename
    return found


def elision(name: str) -> str:
    if name in {"Aquila", "Oca", "Onda", "Istrice"}:
        return f"dell'{name}"
    return f"della {name}"


def a_tag(href: str, label: str) -> str:
    return f'<a href="{escape(href, quote=True)}">{escape(label, quote=False)}</a>'


def related_html(links, extra=None) -> bytes:
    sep = " · "
    parts = [
        "<!-- palio-plumbing -->",
        '<link rel="stylesheet" href="plumbing.css">',
        '<aside class="pp-related">',
        '<p class="pp-kicker">Pagine collegate</p>',
        '<p class="pp-links">' + sep.join(a_tag(href, text) for href, text in links) + "</p>",
    ]
    if extra:
        parts.append(
            '<p class="pp-links pp-more">'
            + sep.join(a_tag(href, text) for href, text in extra)
            + "</p>"
        )
    parts.append("</aside>")
    parts.append("<!-- /palio-plumbing -->")
    return ("\n".join(parts) + "\n").encode("utf-8")


def inject_bytes(data: bytes, snippet: bytes, start: bytes, end: bytes) -> bytes:
    if start in data and end in data:
        start_at = data.find(start)
        end_at = data.find(end, start_at)
        if start_at != -1 and end_at != -1:
            return data[:start_at] + snippet + data[end_at + len(end) :]
    low = data.lower()
    body = low.rfind(b"</body")
    if body != -1:
        return data[:body] + snippet + data[body:]
    html = low.rfind(b"</html")
    if html != -1:
        return data[:html] + snippet + data[html:]
    if not data.endswith(b"\n"):
        data += b"\n"
    return data + snippet


def write_if_changed(path: Path, data: bytes) -> bool:
    if path.is_file() and path.read_bytes() == data:
        return False
    path.write_bytes(data)
    return True


def inject_file(path: Path, snippet: bytes) -> bool:
    original = path.read_bytes()
    updated = inject_bytes(original, snippet, MARKER_START, MARKER_END)
    if updated == original:
        return False
    path.write_bytes(updated)
    return True


def add_home_search_link(filename: str) -> bool:
    path = ROOT / filename
    data = path.read_bytes()
    if SEARCH_START in data and SEARCH_END in data:
        start_at = data.find(SEARCH_START)
        end_at = data.find(SEARCH_END, start_at)
        updated = data[:start_at] + SEARCH_SNIPPET + data[end_at + len(SEARCH_END) :]
    else:
        lower = data.lower()
        pos = lower.find(b'<a href="contatti.htm"')
        if pos == -1:
            raise SystemExit(f"Could not find CONTATTI link in {filename}")
        updated = data[:pos] + SEARCH_SNIPPET + data[pos:]
    if updated == data:
        return False
    path.write_bytes(updated)
    return True


def build_search_index() -> tuple[int, int]:
    pages = []
    for path in sorted(ROOT.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_file():
            continue
        if path.name in SKIP_INDEX_NAMES:
            continue
        if path.suffix.lower() not in {".htm", ".html"}:
            continue
        if path.stat().st_size > 2_000_000:
            continue
        html = read_text(path)
        title = page_title(html, path.name)
        text = visible_text(html)
        if title and text.startswith(title):
            text = text[len(title):].strip(" -–|:;")
        snippet = text[:160].strip()
        if snippet and len(text) > 160 and " " in snippet:
            snippet = snippet.rsplit(" ", 1)[0] + "…"
        pages.append([path.name, title, snippet])
    payload = json.dumps({"pages": pages}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    out = ROOT / "search-index.json"
    write_if_changed(out, payload)
    return len(pages), out.stat().st_size


def build_chart(win_map: dict[str, list[str]], albo_counts: Counter) -> list[str]:
    rows = [(contrada, len(win_map.get(contrada["slug"], []))) for contrada in CONTRADE]
    rows.sort(key=lambda item: (-item[1], item[0]["name"]))
    max_wins = max((count for _contrada, count in rows), default=1) or 1
    bars = []
    notes = []
    for contrada, count in rows:
        albo = albo_counts.get(contrada["slug"], 0)
        width = round(100.0 * count / max_wins, 2)
        bars.append(
            '<div class="pp-row">'
            f'<a class="pp-name" href="{escape(contrada["wins_page"], quote=True)}">'
            f'<img src="{escape(contrada["crest"], quote=True)}" alt="" width="28" height="28">'
            f'{escape(contrada["name"])}</a>'
            f'<div class="pp-bar-track"><div class="pp-bar" style="width:{width}%"></div></div>'
            f'<span class="pp-count">{count}</span></div>'
        )
        if albo and albo != count:
            notes.append(
                f"{contrada['name']}: {count} nella pagina delle vittorie ({contrada['wins_page']}), "
                f"{albo} nell'albo d'oro (vittorie.htm)."
            )
    cite_items = [
        '<li><a href="vittoriecontrade.htm">vittoriecontrade.htm</a> — indice delle vittorie per Contrada</li>'
    ]
    for contrada, count in rows:
        cite_items.append(
            f'<li><a href="{escape(contrada["wins_page"], quote=True)}">{escape(contrada["wins_page"])}</a>'
            f' — {escape(contrada["name"])}: {count} schede di Palio distinte</li>'
        )
    cite_items.append(
        '<li><a href="vittorie.htm">vittorie.htm</a> — albo d\'oro dal 1633 '
        "(controllo: stesso totale di 674 vittorie assegnate)</li>"
    )
    note_html = ""
    if notes:
        note_html = (
            '<p class="pp-note"><b>Nota sul controllo con l\'albo d\'oro.</b> '
            + " ".join(escape(note) for note in notes)
            + " Il grafico usa il conteggio delle pagine di vittoria per Contrada.</p>"
        )
    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>Vittorie per Contrada — grafico (copia Palio di Siena)</title>
<meta name="robots" content="noindex">
<meta name="description" content="Grafico delle vittorie per Contrada ricavato dalle pagine di Orlando Papei in questa copia.">
<link rel="stylesheet" href="plumbing.css">
</head>
<body class="pp-page" link="#2f4f2f">
<p class="pp-banner">
<a href="index.htm"><img src="banner-paliosiena.jpg" width="100" height="100" alt="Il Palio di Siena" title="Torna all'indice"></a>
</p>
<p class="pp-nav"><a href="index.htm">Indice</a> · <a href="cerca.htm">Cerca nel sito</a> · <a href="vittoriecontrade.htm">Vittorie per Contrada</a> · <a href="vittorie.htm">Albo d'oro</a></p>
<div class="pp-wrap">
<h1>Vittorie per Contrada</h1>
<p class="pp-lead">Conteggio delle schede di Palio (collegamenti unici a pagine <code>sch…</code>) presenti in ciascuna pagina delle vittorie di Contrada di questa copia. Nessun dato esterno. Gli stemmini sono quelli già nel sito (<code>stemmino*74.gif</code> e <code>stemminoPANTERA75.png</code>).</p>
<div class="pp-chart">
{''.join(bars)}
</div>
{note_html}
<div class="pp-cite">
<p><b>Fonti (pagine di Orlando Papei in questa copia)</b></p>
<ul>
{''.join(cite_items)}
</ul>
<p>Copia di consultazione, uso non commerciale.</p>
</div>
</div>
</body>
</html>
"""
    write_if_changed(ROOT / "vittorie-contrade-grafico.htm", html.encode("utf-8"))
    return notes


def date_from_filename(name: str) -> str:
    match = re.match(r"sch(\d{4})\.(\d{1,2})\.(\d{1,2})\.", name, re.I)
    if match:
        return f"{int(match.group(2))}.{int(match.group(3))}.{match.group(1)}"
    match = re.match(r"sch(\d{4})\.(\d{1,2})\.", name, re.I)
    if match:
        return f"{match.group(2)}/{match.group(1)}"
    match = re.match(r"sch(\d{4})([a-z]+)", name, re.I)
    if match:
        return f"{match.group(2)} {match.group(1)}"
    match = re.match(r"sch(\d{4})", name, re.I)
    if match:
        return match.group(1)
    return name


def build_related_targets(idx, albo_order, albo_winners, win_map):
    targets = {}
    other_contrade = [(contrada["profile"], contrada["name"]) for contrada in CONTRADE]
    for contrada in CONTRADE:
        main = [
            ("le_17_contrade.htm", "Le 17 Contrade"),
            (contrada["wins_page"], f"Vittorie {elision(contrada['name'])}"),
            ("vittorie-contrade-grafico.htm", "Grafico delle vittorie"),
            ("vittorie.htm", "Albo d'oro"),
            ("cerca.htm", "Cerca nel sito"),
        ]
        extras = [item for item in other_contrade if item[0] != contrada["profile"]]
        targets[contrada["profile"]] = (main, extras)
        vic_main = [
            (contrada["profile"], f"Profilo {elision(contrada['name'])}"),
            ("le_17_contrade.htm", "Le 17 Contrade"),
            ("vittorie-contrade-grafico.htm", "Grafico delle vittorie"),
            ("vittorie.htm", "Albo d'oro"),
            ("cerca.htm", "Cerca nel sito"),
        ]
        targets[contrada["wins_page"]] = (vic_main, extras)

    fantini = collect_linked_pages(
        FANTINI_INDEXES,
        idx,
        lambda base: base.lower().startswith("sc") and base.lower().endswith((".htm", ".html")),
    )
    source_labels = dict(FANTINI_INDEXES)
    for page, source in fantini.items():
        targets[page] = (
            [
                ("fantini_schede.htm", "Schede dei fantini"),
                (source, source_labels.get(source, source)),
                ("cerca.htm", "Cerca nel sito"),
            ],
            [],
        )

    horses = collect_linked_pages(
        HORSE_INDEXES,
        idx,
        lambda base: (
            base.lower().endswith((".htm", ".html"))
            and not is_palio_year(base)
            and base.lower() not in {"index.htm", "index.html"}
        ),
    )
    horse_labels = dict(HORSE_INDEXES)
    for page, source in horses.items():
        targets[page] = (
            [
                ("cavalli_alfabetico.htm", "I cavalli dal 1900"),
                (source, horse_labels.get(source, source)),
                ("cerca.htm", "Cerca nel sito"),
            ],
            [],
        )

    listed_by = {}
    for slug, files in win_map.items():
        for filename in files:
            listed_by.setdefault(filename.lower(), slug)

    order_files = [item["file"] for item in albo_order]
    order_labels = {item["file"].lower(): item["label"] for item in albo_order}
    position = {name.lower(): i for i, name in enumerate(order_files)}

    for path in ROOT.iterdir():
        if not path.is_file() or not is_palio_year(path.name):
            continue
        page = path.name
        links = [("vittorie.htm", "Albo d'oro dal 1633")]
        key = page.lower()
        if key in position:
            index = position[key]
            insert_at = 0
            if index > 0:
                prev = order_files[index - 1]
                plabel = order_labels.get(prev.lower()) or date_from_filename(prev)
                links.insert(insert_at, (prev, f"Palio precedente ({plabel})"))
                insert_at += 1
            if index + 1 < len(order_files):
                nxt = order_files[index + 1]
                nlabel = order_labels.get(nxt.lower()) or date_from_filename(nxt)
                links.insert(insert_at, (nxt, f"Palio successivo ({nlabel})"))
        slug = albo_winners.get(key) or listed_by.get(key)
        if slug and slug in SLUG:
            info = SLUG[slug]
            links.append((info["profile"], f"Contrada vittoriosa: {info['name']}"))
            links.append((info["wins_page"], f"Vittorie {elision(info['name'])}"))
        links.append(("vittorie-contrade-grafico.htm", "Grafico delle vittorie"))
        links.append(("cerca.htm", "Cerca nel sito"))
        targets[page] = (links, [])

    return targets


def main() -> None:
    idx = file_index()
    for row in CONTRADE:
        if not (ROOT / row["profile"]).is_file():
            raise SystemExit(f"Missing contrada page {row['profile']}")
        if not (ROOT / row["wins_page"]).is_file():
            raise SystemExit(f"Missing wins page {row['wins_page']}")
        if not (ROOT / row["crest"]).is_file():
            raise SystemExit(f"Missing allowed crest {row['crest']}")

    albo_order, albo_winners, albo_counts = parse_albo(idx)
    win_map = count_wins_from_contrada_pages(idx)
    notes = build_chart(win_map, albo_counts)
    page_count, index_size = build_search_index()
    targets = build_related_targets(idx, albo_order, albo_winners, win_map)

    changed = 0
    for filename, (links, extra) in targets.items():
        path = ROOT / filename
        if not path.is_file():
            continue
        if inject_file(path, related_html(links, extra or None)):
            changed += 1

    home_changed = 0
    for home in ("index.htm", "INDEX.htm"):
        if (ROOT / home).is_file() and add_home_search_link(home):
            home_changed += 1

    print("search_pages", page_count)
    print("search_index_bytes", index_size)
    print("related_targets", len(targets))
    print("related_files_written", changed)
    print("home_search_links", home_changed)
    print("albo_palii_listed", len(albo_order))
    print("albo_assigned_wins", sum(albo_counts.values()))
    print("contrada_page_wins", {slug: len(files) for slug, files in win_map.items()})
    print("contrada_page_total", sum(len(files) for files in win_map.values()))
    print("chart_notes", notes)


if __name__ == "__main__":
    main()
