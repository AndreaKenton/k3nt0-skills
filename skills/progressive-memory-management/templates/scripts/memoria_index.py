#!/usr/bin/env python3
"""memoria_index — genera gli indici *derivati* della memoria del progetto.

Nessun indice si scrive a mano: si ricava dai file e si riscrive fra i marcatori. Due
destinazioni:

  * `AGENTS.md`          -> mappa dei capitoli (`<memoria>/*.md`), dal loro frontmatter
                            `leggi_quando` + `parole_chiave` (livello L1, in coda a L0);
  * `docs/ADR/README.md` -> indice delle decisioni (solo se il file esiste).

Gli indici generati **non contengono mai dati volatili** (date, conteggi, stime di token):
cambierebbero a ogni modifica e invaliderebbero il prefisso in prompt cache. Se un frontmatter
introduce un dato volatile, lo script si ferma con un errore invece di propagarlo.

Rileva da solo la cartella memoria: `memoria/` oppure `manuale/`.

Uso:
    python scripts/memoria_index.py            # (ri)genera gli indici
    python scripts/memoria_index.py --check    # non scrive: esce 1 se sono disallineati
    python scripts/memoria_index.py --print    # stampa gli indici senza scrivere
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "AGENTS.md"
ADR_README = ROOT / "docs" / "ADR" / "README.md"
SCRIPT_PATTERN = "{{VERSION}}"          # versione del pacchetto che ha generato lo script
MEM_CANDIDATES = ("memoria", "manuale")
INIZIO = "<!-- INDICE:INIZIO (generato: non modificare a mano) -->"
FINE = "<!-- INDICE:FINE -->"
ADR_INIZIO = "<!-- ADR:INIZIO (generato: non modificare a mano) -->"
ADR_FINE = "<!-- ADR:FINE -->"
VOLATILI = (
    (re.compile(r"\d{4}-\d{2}-\d{2}"), "una data"),
    (re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b"), "una data"),
    (re.compile(r"(?:~|≈|circa)\s*[\d.,]+\s*(?:tok|token)\b", re.I), "una stima di token"),
    (re.compile(r"[\d.,]+\s*tok\b|\btoken stimat", re.I), "una stima di token"),
)


def memoria_dir() -> Path:
    for nome in MEM_CANDIDATES:
        cand = ROOT / nome
        if cand.is_dir():
            return cand
    raise SystemExit(f"nessuna cartella memoria trovata in {ROOT} (attesa `memoria/` o `manuale/`)")


def frontmatter(path: Path) -> dict[str, str]:
    m = re.match(r"^---\n(.*?)\n---\n", path.read_text(encoding="utf8"), re.S)
    if not m:
        return {}
    dati: dict[str, str] = {}
    for riga in m.group(1).splitlines():
        if ":" in riga:
            k, v = riga.split(":", 1)
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            dati[k.strip()] = v
    return dati


def cella(valore: str) -> str:
    """Testo di una cella: una riga sola, senza `|` che rompono la tabella."""
    return " ".join(valore.split()).replace("|", "/").strip() or "—"


def capitoli() -> list[tuple[str, dict[str, str]]]:
    return [(f.name, frontmatter(f))
            for f in sorted(memoria_dir().glob("*.md"))
            if not f.name.lower().startswith("readme")]


def tabella_capitoli() -> str:
    righe = ["| capitolo | leggi quando · parole chiave |", "|---|---|"]
    for nome, fm in capitoli():
        righe.append(f"| `{nome}` | {cella(fm.get('leggi_quando', '—'))} · "
                     f"{cella(fm.get('parole_chiave', '—'))} |")
    return "\n".join(righe)


def adr_files() -> list[Path]:
    cartella = ADR_README.parent
    if not cartella.is_dir():
        return []
    return [f for f in sorted(cartella.glob("*.md"))
            if f.name != ADR_README.name and "template" not in f.name.lower()]


def adr_meta(path: Path) -> tuple[str, str, str]:
    fm = frontmatter(path)
    m = re.search(r"(?m)^#\s+(?:ADR[-\s]?(\d+)\s*[—:-]\s*)?(.+?)\s*$",
                  path.read_text(encoding="utf8"))
    titolo_h1 = m.group(2) if m else path.stem
    numero = fm.get("numero") or (m.group(1) if m and m.group(1) else "NNN")
    return str(numero), cella(fm.get("stato", "—")), cella(fm.get("titolo") or titolo_h1)


def tabella_adr() -> str:
    righe = ["| ADR | stato | titolo |", "|---|---|---|"]
    for f in adr_files():
        numero, stato, titolo = adr_meta(f)
        righe.append(f"| `{f.name}` ({numero}) | {stato} | {titolo} |")
    return "\n".join(righe)


def verifica_stabile(tabella: str, dove: str) -> None:
    for rx, cosa in VOLATILI:
        m = rx.search(tabella)
        if m:
            raise SystemExit(
                f"{dove}: l'indice conterrebbe {cosa} («{m.group(0)}»). "
                "Gli indici derivati devono restare stabili fra le sessioni (prompt cache): "
                "togli il dato volatile dal frontmatter."
            )


def blocco(inizio: str, fine: str, tabella: str) -> str:
    return f"{inizio}\n\n{tabella}\n\n{fine}"


def aggiorna(path: Path, inizio: str, fine: str, tabella: str) -> str | None:
    """Ritorna il testo atteso, o None se il file non esiste."""
    if not path.exists():
        return None
    testo = path.read_text(encoding="utf8")
    if inizio not in testo or fine not in testo:
        raise SystemExit(f"marcatori assenti in {path}: attesi {inizio!r} … {fine!r}")
    i = testo.index(inizio)
    j = testo.index(fine) + len(fine)
    return testo[:i] + blocco(inizio, fine, tabella) + testo[j:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verifica soltanto (esce 1 se gli indici vanno rigenerati)")
    ap.add_argument("--print", dest="stampa", action="store_true",
                    help="stampa gli indici senza scrivere nulla")
    args = ap.parse_args()

    t_cap = tabella_capitoli()
    verifica_stabile(t_cap, "mappa dei capitoli")
    t_adr = tabella_adr()
    verifica_stabile(t_adr, "indice delle decisioni")

    if args.stampa:
        print(t_cap)
        if ADR_README.exists():
            print()
            print(t_adr)
        return 0

    attesi: list[tuple[Path, str]] = []
    testo_agents = aggiorna(AGENTS, INIZIO, FINE, t_cap)
    if testo_agents is None:
        raise SystemExit(f"{AGENTS} assente: la mappa della memoria vive lì")
    attesi.append((AGENTS, testo_agents))
    testo_adr = aggiorna(ADR_README, ADR_INIZIO, ADR_FINE, t_adr)
    if testo_adr is not None:
        attesi.append((ADR_README, testo_adr))

    if args.check:
        vecchi = [p.name for p, atteso in attesi if atteso != p.read_text(encoding="utf8")]
        if vecchi:
            print(f"INDICI NON AGGIORNATI ({', '.join(vecchi)}): "
                  "esegui  python scripts/memoria_index.py")
            return 1
        print(f"indici coerenti ({len(capitoli())} capitoli, {len(adr_files())} decisioni)")
        return 0

    scritti = []
    for path, atteso in attesi:
        if atteso != path.read_text(encoding="utf8"):
            path.write_text(atteso, encoding="utf8", newline="\n")
            scritti.append(path.name)
    if scritti:
        print(f"indici aggiornati: {', '.join(scritti)} "
              f"({len(capitoli())} capitoli, {len(adr_files())} decisioni)")
    else:
        print("indici gia' allineati (nessuna scrittura: prefisso byte-stabile)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
