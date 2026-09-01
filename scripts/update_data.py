#!/usr/bin/env python3
"""
Descarrega l'agenda de partits de Hoquei Patins des del backend de la FECAPA
(sidgad) i la converteix en un fitxer data.json compacte que consumeix
l'aplicació web (index.html).

Aquest script s'executa automàticament cada dia mitjançant GitHub Actions
(.github/workflows/update-data.yml), però també es pot executar a mà:

    python3 scripts/update_data.py

Si la petició o el parsing fallen, el script acaba amb un error (exit code 1)
i NO sobreescriu el data.json existent, per evitar deixar l'app sense dades
si la FECAPA canvia alguna cosa del seu backend.
"""

import datetime
import json
import re
import sys
import urllib.request

URL = "https://server2.sidgad.es/fecapa/00_fecapa_agenda_1.php"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.hoqueipatins.fecapa.cat/ag/",
    "Origin": "https://www.hoqueipatins.fecapa.cat",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}

# Si en algun moment la FECAPA comença a exigir paràmetres addicionals al
# POST (per exemple un identificador de temporada), afegeix-los aquí tal com
# apareguin a la pestanya "Payload" de les eines de desenvolupador del
# navegador, per exemple: {"temporada": "26"}
POST_PARAMS = {}


def fetch_html():
    body = "&".join(f"{k}={v}" for k, v in POST_PARAMS.items()).encode("utf-8")
    req = urllib.request.Request(URL, data=body, headers=HEADERS, method="POST")
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    # El backend serveix Windows-1252 / UTF-8 segons el dia; provem totes dues.
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def extract_select(html, select_id):
    m = re.search(r'id="%s"' % re.escape(select_id), html)
    if not m:
        return ""
    sel_start = html.rfind("<select", 0, m.start())
    sel_end = html.find("</select>", m.start())
    return html[sel_start:sel_end]


def parse_options(html):
    return [
        (v, t.strip())
        for v, t in re.findall(r'<option value="(-?\d+)">([^<]*)</option>', html)
    ]


ROW_RE = re.compile(
    r'<tr class="fila_agenda[^"]*" fecha="(-?\d+)" club1="(\d*)" club2="(\d*)" '
    r'pista="(\d+)" param_game="([^"]*)">'
    r'\s*<td><div style="font-size: 12px; padding-left: 5px;">\s*([^<]*?)\s*</div>\s*</td>'
    r'\s*<td[^>]*>\s*(\d{2}/\d{2}/\d{4})\s*</td>'
    r'\s*<td[^>]*>\s*(\d{2}:\d{2})?\s*</td>'
    r'\s*<td width="20"></td>\s*<td>([^<]*)</td>'
    r'\s*<td width="20"></td>\s*<td>([^<]*)</td>'
    r'\s*<td[^>]*>\s*([^<]*?)\s*</td>'
    r'\s*<td class="tabla_standard_less_mini">\s*([^<]*?)\s*</td>',
    re.DOTALL,
)


def parse_matches(html):
    matches = []
    for m in ROW_RE.finditer(html):
        fecha, club1, club2, pista, param_game, comp, date, time, home, away, score, venue = m.groups()
        matches.append(
            {
                "comp": comp.strip(),
                "date": date,
                "time": time or "",
                "home": home.strip(),
                "away": away.strip(),
                "score": score.strip(),
                "venue": venue.strip(),
                "club1": club1,
                "club2": club2,
            }
        )
    return matches


SUFFIX_RE = re.compile(r'\s+[A-F](\s*)$')  # treu la lletra final d'equip filial (" A", " B"...)


def derive_club_labels(matches):
    """
    Calcula, per a cada club, el nom que la gent reconeixeria de veritat.

    El registre oficial de clubs de la FECAPA de vegades fa servir una raó
    social diferent del nom amb què l'equip juga habitualment (per exemple,
    el club 727 hi consta com "COMUNIDAD LA SALLE BONANOVA" però els seus
    equips surten sempre com "SE La Salle Bonanova"). Per evitar que el
    filtre de club sigui confús, fem servir el nom que apareix de debò als
    partits (traient la lletra final que distingeix els equips filials A/B/C…
    i quedant-nos amb la variant més freqüent).
    """
    names_by_id = {}
    for m in matches:
        for cid, name in ((m["club1"], m["home"]), (m["club2"], m["away"])):
            if not cid:
                continue
            names_by_id.setdefault(cid, __import__("collections").Counter())
            base = SUFFIX_RE.sub("", name).strip()
            base = re.sub(r"\s{2,}", " ", base)
            if base:
                names_by_id[cid][base] += 1

    return {cid: counter.most_common(1)[0][0] for cid, counter in names_by_id.items()}


def build_dataset(html):
    matches = parse_matches(html)
    if len(matches) < 100:
        # Salvaguarda: si de sobte n'hi ha molt poques, probablement el
        # backend ha canviat de format o ha retornat una pàgina d'error.
        raise RuntimeError(
            f"Nomes s'han trobat {len(matches)} partits: sembla que el format "
            "de resposta ha canviat. Revisa el regex del parser."
        )

    clubs_html = extract_select(html, "agenda_club_select")
    club_name_by_id = {v: n for v, n in parse_options(clubs_html) if v != "0"}
    derived_labels = derive_club_labels(matches)

    comps = sorted({m["comp"] for m in matches})
    venues = sorted({m["venue"] for m in matches})
    comp_idx = {c: i for i, c in enumerate(comps)}
    venue_idx = {v: i for i, v in enumerate(venues)}

    appearing_ids = set()
    for m in matches:
        if m["club1"]:
            appearing_ids.add(m["club1"])
        if m["club2"]:
            appearing_ids.add(m["club2"])

    clubs_out = sorted(
        (
            [int(cid), derived_labels.get(cid, club_name_by_id.get(cid, cid))]
            for cid in appearing_ids
        ),
        key=lambda x: x[1],
    )

    compact_matches = []
    for m in matches:
        compact_matches.append(
            [
                comp_idx[m["comp"]],
                m["date"],
                m["time"],
                m["home"],
                m["away"],
                m["score"],
                venue_idx[m["venue"]],
                int(m["club1"]) if m["club1"] else 0,
                int(m["club2"]) if m["club2"] else 0,
            ]
        )

    return {
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
        "comps": comps,
        "venues": venues,
        "clubs": clubs_out,
        "matches": compact_matches,
    }


def main():
    try:
        html = fetch_html()
        dataset = build_dataset(html)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR actualitzant les dades: {exc}", file=sys.stderr)
        sys.exit(1)

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, separators=(",", ":"))

    print(f"OK: {len(dataset['matches'])} partits, generat {dataset['generated']}")


if __name__ == "__main__":
    main()
