#!/usr/bin/env python3
"""memoria_index — genera l'indice della memoria dentro AGENTS.md.

L'indice NON si scrive a mano: si ricava dal frontmatter dei capitoli
(`memoria/*.md` -> `parole_chiave`, `leggi_quando`) e viene riscritto fra i
marcatori in AGENTS.md. Cosi' l'indice resta coerente con i capitoli e il file
di ingresso e' byte-stabile fra le sessioni (prompt caching).

Rileva da solo la cartella memoria: `memoria/` oppure `manuale/`.

Uso:
    python scripts/memoria_index.py            # aggiorna l'indice in AGENTS.md
    python scripts/memoria_index.py --check    # non scrive: esce 1 se l'indice e' vecchio
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "AGENTS.md"
INIZIO = "<!-- INDICE:INIZIO (generato: non modificare a mano) -->"
FINE = "<!-- INDICE:FINE -->"


def memoria_dir() -> Path:
    for nome in ("memoria", "manuale"):
        cand = ROOT / nome
        if cand.is_dir():
            return cand
    raise SystemExit(f"nessuna cartella memoria trovata in {ROOT} (attesa `memoria/` o `manuale/`)")


def frontmatter(path: Path) -> dict:
    testo = path.read_text(encoding="utf8")
    m = re.match(r"^---\n(.*?)\n---\n", testo, re.S)
    if not m:
        return {}
    dati = {}
    for riga in m.group(1).splitlines():
        if ":" in riga:
            k, v = riga.split(":", 1)
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            dati[k.strip()] = v
    return dati


def capitoli() -> list[tuple[str, dict]]:
    out = []
    for f in sorted(memoria_dir().glob("*.md")):
        if f.name.lower().startswith("readme"):
            continue
        out.append((f.name, frontmatter(f)))
    return out


def tabella() -> str:
    """Indice compatto: due colonne, nome del capitolo senza path ripetuto."""
    righe = ["| capitolo | leggi quando · parole chiave |", "|---|---|"]
    for nome, fm in capitoli():
        leggi = fm.get("leggi_quando", "—")
        kw = fm.get("parole_chiave", "—")
        righe.append(f"| `{nome}` | {leggi} · {kw} |")
    return "\n".join(righe)


def blocco() -> str:
    return f"{INIZIO}\n\n{tabella()}\n\n{FINE}"


def aggiorna(testo: str) -> str:
    nuovo = blocco()
    if INIZIO in testo and FINE in testo:
        i = testo.index(INIZIO)
        j = testo.index(FINE) + len(FINE)
        return testo[:i] + nuovo + testo[j:]
    raise SystemExit(f"marcatori dell'indice assenti in {AGENTS}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="verifica soltanto (esce 1 se l'indice e' da rigenerare)")
    args = ap.parse_args()

    testo = AGENTS.read_text(encoding="utf8")
    atteso = aggiorna(testo)
    if args.check:
        if atteso != testo:
            print("INDICE NON AGGIORNATO: esegui  python scripts/memoria_index.py")
            return 1
        print(f"indice coerente ({len(capitoli())} capitoli)")
        return 0
    if atteso == testo:
        print("indice gia' aggiornato (nessuna modifica al file: byte-stabile)")
        return 0
    AGENTS.write_text(atteso, encoding="utf8")
    print(f"indice aggiornato in {AGENTS.name} ({len(capitoli())} capitoli)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
