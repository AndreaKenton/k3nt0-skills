#!/usr/bin/env python3
"""memoria_check — coerenza e leggerezza della memoria del progetto (deve uscire 0).

Controlla, in ordine:
  1. ogni capitolo della cartella memoria ha frontmatter `leggi_quando` e `parole_chiave`;
  2. l'indice in AGENTS.md e' quello derivato dai capitoli (memoria_index --check);
  3. ogni capitolo e' citato nell'indice e viceversa (nessun orfano, nessun link rotto);
  4. AGENTS.md e' stabile e minimale: nessuna data/timestamp e token entro il budget;
  5. dimensione dei capitoli entro le soglie (6000 token: spezzare; 8000: vietato);
  6. nessun titolo di sezione duplicato fra capitoli (una cosa, un posto);
  7. i link relativi a file del repo esistono;
  8. le skill in .pi/skills/ hanno frontmatter valido e una `description` breve.

Rileva da solo la cartella memoria: `memoria/` oppure `manuale/`.

Uso:
    python scripts/memoria_check.py         # esce 0 se tutto coerente
    python scripts/memoria_check.py -v      # elenca anche i controlli superati
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "AGENTS.md"
SKILLS = ROOT / ".pi" / "skills"
SOGLIA_AVVISO = 6000
SOGLIA_ERRORE = 8000
BUDGET_L0 = 900          # token: oltre, AGENTS.md va alleggerito (procedure -> skill)
DESC_MAX = 400           # caratteri della description di una skill
DESC_MIN = 80            # sotto, la description non fa scattare il routing
VOLATILE = [r"\b\d{4}-\d{2}-\d{2}\b", r"\b\d{2}/\d{2}/\d{4}\b",
            r"\boggi\b", r"\bieri\b", r"\bultima sessione\b", r"\b\d{1,2}:\d{2}\b"]


def memoria_dir() -> Path:
    for nome in ("memoria", "manuale"):
        cand = ROOT / nome
        if cand.is_dir():
            return cand
    raise SystemExit(f"nessuna cartella memoria trovata in {ROOT}")


def stima_token(testo: str) -> int:
    try:
        import tiktoken
        return len(tiktoken.get_encoding("o200k_base").encode(testo))
    except Exception:
        return round(len(testo.encode("utf8")) / 4)   # stima prudente


def frontmatter(path: Path) -> dict:
    m = re.match(r"^---\n(.*?)\n---\n", path.read_text(encoding="utf8"), re.S)
    if not m:
        return {}
    return {k.strip(): v.strip() for riga in m.group(1).splitlines()
            if ":" in riga for k, v in [riga.split(":", 1)]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    problemi: list[str] = []
    ok: list[str] = []
    agents = AGENTS.read_text(encoding="utf8")
    capitoli = sorted(memoria_dir().glob("*.md"))
    rilevanti = [f for f in capitoli if not f.name.lower().startswith("readme")]

    # 1 · frontmatter completo
    for f in rilevanti:
        fm = frontmatter(f)
        for campo in ("leggi_quando", "parole_chiave"):
            if not fm.get(campo):
                problemi.append(f"{f.name}: frontmatter senza `{campo}`")
    if not problemi:
        ok.append(f"frontmatter completo su {len(rilevanti)} capitoli")

    # 2 · indice derivato
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "memoria_index.py"),
                        "--check"], capture_output=True, text=True, cwd=str(ROOT))
    (ok if r.returncode == 0 else problemi).append(
        "indice in AGENTS.md coerente con i capitoli" if r.returncode == 0
        else "indice non aggiornato: esegui scripts/memoria_index.py")

    # 3 · nessun capitolo orfano e nessun riferimento a capitoli inesistenti
    for f in rilevanti:
        if f.name not in agents:
            problemi.append(f"{f.name}: non citato in AGENTS.md")
    for citato in set(re.findall(r"\b(\d\d_[\w-]+\.md)\b", agents)):
        if not (memoria_dir() / citato).exists():
            problemi.append(f"AGENTS.md cita {memoria_dir().name}/{citato} che non esiste")
    if not any("non citato" in p for p in problemi):
        ok.append("nessun capitolo orfano, nessun riferimento a capitoli inesistenti")

    # 4 · stabilita' e leggerezza del prefisso
    for pat in VOLATILE:
        m = re.search(pat, agents)
        if m:
            problemi.append(f"AGENTS.md contiene un elemento volatile ({m.group(0)}): "
                            "rompe la stabilita' del prefisso in cache")
    n_l0 = stima_token(agents)
    if n_l0 > BUDGET_L0:
        problemi.append(f"AGENTS.md = {n_l0} token (> budget {BUDGET_L0}): sposta le "
                        "procedure nella skill o nei capitoli")
    if not any("volatile" in p or "budget" in p for p in problemi):
        ok.append(f"AGENTS.md stabile e minimale ({n_l0} token, budget {BUDGET_L0})")

    # 5 · dimensione dei capitoli
    tot_l2 = 0
    for f in rilevanti:
        t = stima_token(f.read_text(encoding="utf8"))
        tot_l2 += t
        if t > SOGLIA_ERRORE:
            problemi.append(f"{f.name}: {t} token (> {SOGLIA_ERRORE}): va spezzato")
        elif t > SOGLIA_AVVISO:
            problemi.append(f"{f.name}: {t} token (> {SOGLIA_AVVISO}): da spezzare a breve")

    # 6 · titoli duplicati fra capitoli
    titoli: dict[str, str] = {}
    for f in rilevanti:
        for h in re.findall(r"(?m)^#{2,3} (.+)$", f.read_text(encoding="utf8")):
            h = h.strip()
            if h in titoli and titoli[h] != f.name:
                problemi.append(f"titolo «{h}» presente in {titoli[h]} e {f.name} "
                                "(una cosa, un posto)")
            titoli[h] = f.name
    if not any("una cosa, un posto" in p for p in problemi):
        ok.append(f"nessun titolo duplicato ({len(titoli)} sezioni)")

    # 7 · link interni esistenti
    da_controllare = [AGENTS, *rilevanti]
    readme = ROOT / "README.md"
    if readme.exists():
        da_controllare.append(readme)
    for f in da_controllare:
        for link in re.findall(r"\]\((?!https?:)([^)#]+)\)", f.read_text(encoding="utf8")):
            if not (ROOT / link).exists() and not (f.parent / link).exists():
                problemi.append(f"{f.name}: link rotto -> {link}")
    if not any("link rotto" in p for p in problemi):
        ok.append("tutti i link interni risolvono")

    # 8 · skill: frontmatter valido, description breve
    tot_desc = 0
    tot_skill = 0
    presenti = []
    if SKILLS.exists():
        for d in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
            skill_file = d / "SKILL.md"
            if not skill_file.exists():
                continue
            presenti.append(d.name)
            testo = skill_file.read_text(encoding="utf8")
            tot_skill += stima_token(testo)
            fm = frontmatter(skill_file)
            if not fm.get("name") or not fm.get("description"):
                problemi.append(f"skill {d.name}: frontmatter senza name/description")
                continue
            tot_desc += stima_token(fm["description"])
            if len(fm["description"]) > DESC_MAX:
                problemi.append(f"skill {d.name}: description di {len(fm['description'])} "
                                f"caratteri (> {DESC_MAX}): sta sempre nel prefisso fisso")
            elif len(fm["description"]) < DESC_MIN:
                problemi.append(f"skill {d.name}: description troppo corta "
                                "per far scattare il routing")
        for o in (s for s in presenti if s not in agents):
            problemi.append(f"skill {o} non citata in AGENTS.md")
    if presenti and not any("skill" in p for p in problemi):
        ok.append(f"skill: {len(presenti)} valide e citate in AGENTS.md")

    if args.verbose:
        for riga in ok:
            print(f"  OK  {riga}")
    if problemi:
        print("MEMORIA INCOERENTE:")
        for p in problemi:
            print(f"  ERR {p}")
        return 1

    fisso = n_l0 + tot_desc
    mono = n_l0 + tot_l2 + tot_skill
    print(f"memoria coerente · prefisso fisso {fisso} token "
          f"(AGENTS.md {n_l0} + description skill {tot_desc})")
    print(f"  on demand: {tot_l2} token in {len(rilevanti)} capitoli · "
          f"{tot_skill} token di skill; monolite equivalente = {mono} token "
          f"→ risparmio {mono - fisso} token a sessione")
    return 0


if __name__ == "__main__":
    sys.exit(main())
