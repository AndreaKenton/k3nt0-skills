#!/usr/bin/env python3
"""prefix_check — igiene del prefisso di un agente: budget, stabilità, capacità, coerenza.

Agnostico: non sa nulla di un agente in particolare. Gli si dice **quali** file vengono caricati
sempre (`--l0`) e **dove** stanno le capacità on demand (`--capabilities`), e verifica gli
invarianti dell'igiene del prefisso.

Controlli
  1. ogni file sempre caricato è stabile: nessuna data, orario, riferimento temporale o stima di
     token (un byte diverso invalida la prompt cache di tutte le sessioni);
  2. il prefisso (somma dei file `--l0`) sta entro `--budget`;
  3. la mappa derivata, se presente fra i marcatori, sta **dopo** le regole: così aggiornarla non
     invalida il blocco stabile;
  4. ogni capacità ha frontmatter con `name` e `description` entro `--desc-min`/`--desc-max`
     caratteri (la description è l'unica parte sempre in contesto);
  5. ogni capacità trovata è **dichiarata** nel file sempre caricato (una capacità non dichiarata
     è invisibile all'agente) e ogni nome dichiarato esiste (un nome senza file è un riferimento
     morto) — avvisi, che `--strict` trasforma in errori;
  6. stampa il costo: prefisso fisso (file + description), contenuto on demand e confronto con una
     memoria monolitica.

Uso
    python prefix_check.py --l0 AGENTS.md --capabilities ~/.pi/agent/skills --budget 1000
    python prefix_check.py --l0 AGENTS.md --l0 CLAUDE.md --capabilities .claude/skills -v
    python prefix_check.py --l0 AGENTS.md --capabilities ~/.pi/agent/skills --strict
    python prefix_check.py --l0 AGENTS.md --ignore grill-me --capabilities .pi/skills
    python prefix_check.py --l0 AGENTS.md --hash

Esce 0 se tutto regge, 1 se c'è almeno un errore (o un avviso, con `--strict`).
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

BUDGET_DEFAULT = 1000
DESC_MIN_DEFAULT = 80
DESC_MAX_DEFAULT = 400
CAP_FILE = "SKILL.md"
MARKER_MAPPA = "<!-- INDICE:INIZIO"
VOLATILI = (
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "una data"),
    (re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b"), "una data"),
    (re.compile(r"\b\d{1,2}:\d{2}\b"), "un orario"),
    (re.compile(r"\b(?:oggi|ieri|domani|ultima sessione)\b", re.I), "un riferimento temporale"),
    # Stime di token (`~1.200 token`, `1234 tok`), non i tassi: `tok/s` è un'unità di velocità.
    (re.compile(r"(?:~|≈|circa)\s*[\d.,]+\s*(?:tok|token)\b(?!\s*/)", re.I), "una stima di token"),
    (re.compile(r"[\d.,]+\s*tok\b(?!\s*/)|\btoken stimat", re.I), "una stima di token"),
)
NOME_DICHIARATO = re.compile(r"(?m)^\|\s*`([\w.-]+)`\s*\|")


def stima_token(testo: str) -> int:
    try:
        import tiktoken
        return len(tiktoken.get_encoding("o200k_base").encode(testo))
    except Exception:
        return round(len(testo.encode("utf8")) / 4)          # stima prudente


def frontmatter(path: Path) -> dict[str, str]:
    """Frontmatter YAML semplice: `chiave: valore`, con scalari `>` / `|` su più righe."""
    m = re.match(r"^---\n(.*?)\n---\n", path.read_text(encoding="utf8"), re.S)
    if not m:
        return {}
    righe = m.group(1).splitlines()
    dati: dict[str, str] = {}
    i = 0
    while i < len(righe):
        riga = righe[i]
        if ":" in riga and not riga[:1].isspace():
            chiave, valore = riga.split(":", 1)
            valore = valore.strip()
            if valore in (">", "|", ">-", "|-", ">+", "|+"):
                i += 1
                pezzi = []
                while i < len(righe) and (not righe[i].strip() or righe[i][:1].isspace()):
                    pezzi.append(righe[i].strip())
                    i += 1
                valore = " ".join(p for p in pezzi if p)
            elif len(valore) >= 2 and valore[0] == valore[-1] and valore[0] in "\"'":
                valore = valore[1:-1]
            dati[chiave.strip()] = valore
        i += 1
    return dati


def capacita(cartelle: list[Path]) -> list[tuple[str, Path, str]]:
    """(nome, file, description) delle capacità on demand trovate.

    Convenzione Agent Skills: una cartella per capacità con dentro `SKILL.md`. Se una cartella
    non ne contiene nessuna, si contano i `*.md` con frontmatter `description` (capacità
    "piatta": regole, comandi).
    """
    trovate: list[tuple[str, Path, str]] = []
    for cartella in cartelle:
        if not cartella.is_dir():
            continue
        skill = sorted(cartella.glob(f"*/{CAP_FILE}"))
        if skill:
            for f in skill:
                fm = frontmatter(f)
                trovate.append((fm.get("name") or f.parent.name, f, fm.get("description", "")))
            continue
        for f in sorted(cartella.glob("*.md")):
            if f.name.lower().startswith(("readme", "changelog")):
                continue
            fm = frontmatter(f)
            if fm.get("description"):
                trovate.append((fm.get("name") or f.stem, f, fm["description"]))
    return trovate


def main() -> int:
    ap = argparse.ArgumentParser(description="Verifica l'igiene del prefisso di un agente.")
    ap.add_argument("--l0", action="append", default=[], required=True,
                    help="file caricato a ogni sessione (ripetibile)")
    ap.add_argument("--capabilities", action="append", default=[],
                    help="cartella delle capacità on demand (ripetibile)")
    ap.add_argument("--ignore", action="append", default=[],
                    help="capacità che non devono comparire nella mappa (ripetibile)")
    ap.add_argument("--budget", type=int, default=BUDGET_DEFAULT,
                    help=f"token massimi per la somma dei file --l0 (default {BUDGET_DEFAULT})")
    ap.add_argument("--desc-min", type=int, default=DESC_MIN_DEFAULT)
    ap.add_argument("--desc-max", type=int, default=DESC_MAX_DEFAULT)
    ap.add_argument("--strict", action="store_true", help="anche gli avvisi fanno fallire")
    ap.add_argument("--hash", action="store_true",
                    help="stampa l'impronta dei file --l0 (confronto fra sessioni)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    testi: list[tuple[Path, str]] = []
    for p in args.l0:
        path = Path(p).expanduser()
        if not path.is_file():
            print(f"ERR  file sempre caricato assente: {path}")
            return 1
        testi.append((path, path.read_text(encoding="utf8")))

    if args.hash:
        for path, testo in testi:
            print(f"{path.name}  sha256={hashlib.sha256(testo.encode('utf8')).hexdigest()[:16]}  "
                  f"{stima_token(testo)} token  {len(testo)} byte")
        return 0

    problemi: list[str] = []
    avvisi: list[str] = []
    ok: list[str] = []
    ignorate = set(args.ignore)

    # 1 · stabilità dei file sempre caricati
    volatili = 0
    for path, testo in testi:
        for rx, cosa in VOLATILI:
            m = rx.search(testo)
            if m:
                problemi.append(f"{path.name} contiene {cosa} («{m.group(0)}»): rompe la "
                                "stabilità del prefisso in cache")
                volatili += 1
    if not volatili:
        ok.append(f"{len(testi)} file sempre caricati, stabili (nessun volatile)")

    # 2 · budget del prefisso
    n_l0 = sum(stima_token(t) for _, t in testi)
    if n_l0 > args.budget:
        problemi.append(f"prefisso = {n_l0} token (> budget {args.budget}): sposta procedure e "
                        "dettagli nelle capacità on demand")
    else:
        ok.append(f"prefisso = {n_l0} token (budget {args.budget})")

    # 3 · la mappa derivata in coda alle regole
    for path, testo in testi:
        if MARKER_MAPPA in testo and "## Regole" in testo:
            if testo.index(MARKER_MAPPA) < testo.index("## Regole"):
                avvisi.append(f"{path.name}: la mappa derivata sta prima delle regole — mettila in "
                              "coda, così aggiornarla non invalida il blocco stabile")

    # 4 · capacità: frontmatter e description
    trovate_tutte = capacita([Path(c).expanduser() for c in args.capabilities])
    da_verificare = [(n, f, d) for n, f, d in trovate_tutte if n not in ignorate]
    tot_desc = 0
    tot_corpi = 0
    for nome, f, desc in da_verificare:
        tot_corpi += stima_token(f.read_text(encoding="utf8"))
        if not frontmatter(f).get("name") or not desc:
            problemi.append(f"capacità {nome}: frontmatter senza `name`/`description`")
            continue
        tot_desc += stima_token(desc)
        if len(desc) > args.desc_max:
            problemi.append(f"capacità {nome}: description di {len(desc)} caratteri "
                            f"(> {args.desc_max}): sta sempre nel prefisso fisso")
        elif len(desc) < args.desc_min:
            avvisi.append(f"capacità {nome}: description di {len(desc)} caratteri "
                          f"(< {args.desc_min}): troppo vaga per far scattare il routing")
    if da_verificare and not any("description" in p for p in problemi):
        ok.append(f"{len(da_verificare)} capacità con description entro i limiti")
    if ignorate:
        ok.append(f"fuori dalla mappa per scelta: {', '.join(sorted(ignorate))}")

    # 5 · dichiarate vs trovate
    dichiarate = {n for _, testo in testi for n in NOME_DICHIARATO.findall(testo)}
    trovate = {nome for nome, _, _ in trovate_tutte}
    orfane = sorted(trovate - dichiarate - ignorate)
    morte = sorted(dichiarate - trovate)
    if orfane:
        avvisi.append("capacità presenti ma non dichiarate nel file sempre caricato: "
                      + ", ".join(orfane) + " (l'agente non sa che esistono)")
    if morte:
        avvisi.append("nomi dichiarati senza una capacità corrispondente: " + ", ".join(morte))
    if not orfane and not morte and trovate:
        ok.append(f"mappa coerente ({len(dichiarate)} nomi dichiarati, {len(trovate)} capacità)")

    # 6 · esito
    if args.verbose:
        for riga in ok:
            print(f"  OK  {riga}")
    for riga in avvisi:
        print(f"  AVV {riga}")
    if problemi:
        print("PREFISSO DA SISTEMARE:")
        for riga in problemi:
            print(f"  ERR {riga}")
        return 1
    if args.strict and avvisi:
        print("PREFISSO CON AVVISI (--strict): risolvili o togli --strict")
        return 1
    on_demand = tot_corpi - tot_desc
    fisso = n_l0 + tot_desc
    print(f"prefisso sano · fisso {fisso} token ({n_l0} file + {tot_desc} di "
          f"{len(da_verificare)} description) · on demand {on_demand} token")
    print(f"  con una memoria monolitica il prefisso sarebbe {fisso + on_demand} token "
          f"→ risparmio {on_demand} token/sessione · {len(avvisi)} avvisi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
