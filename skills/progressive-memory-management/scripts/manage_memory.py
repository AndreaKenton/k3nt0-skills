#!/usr/bin/env python3
"""manage_memory — memoria di progetto a livelli L0-L3: init, migrazione, diagnosi.

Pacchetto autonomo e portabile: questo script vive in `scripts/` della skill e trova
i template in `../templates`. Non dipende da `~/.pi/agent`: puoi copiare la cartella
della skill ovunque (anche su un altro agente/modello).

COMANDI
    init    <cartella>    crea lo scheletro completo di un progetto nuovo
    migrate <cartella>    aggiunge SOLO cio' che manca a un progetto esistente
                          (non distruttivo: non sovrascrive mai un file)
    check   <cartella>    diagnosi; esce 0 se il pattern e' completo e coerente
    <cartella>            senza comando: AUTO (init se non c'e' nulla, altrimenti migrate)

OPZIONI
    --core-only    salta i file .pi/** (parte agent-agnostica per agenti non-pi)
    --dry-run      mostra i file che creerebbe, senza scrivere (init/migrate)
    --nome <nome>  nome logico se la cartella non e' <NNN>_<nome>
    -h, --help     questo aiuto

ESEMPI
    python manage_memory.py init    "C:/percorsi/022_nome"
    python manage_memory.py migrate "C:/percorsi/019_progetto_esistente"
    python manage_memory.py check   "C:/percorsi/021_progetto"
    python manage_memory.py         "C:/percorsi/023_nome"        # auto
    python manage_memory.py init    "C:/percorsi/024" --dry-run
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve()
PKG = SCRIPT.parent.parent                       # cartella della skill
TEMPLATES = PKG / "templates"
RENAME_DIR = "PROJECT-memoria"                   # -> <slug>-memoria
MEM_CANDIDATES = ("memoria", "manuale")
COMANDI = ("init", "migrate", "check")
INIZIO = "<!-- INDICE:INIZIO (generato: non modificare a mano) -->"
FINE = "<!-- INDICE:FINE -->"
FRONTMATTER_MIN = (
    "---\n"
    'leggi_quando: "DA COMPILARE — quando serve leggere questo capitolo"\n'
    'parole_chiave: "DA COMPILARE"\n'
    "---\n\n"
)
USAGE = (__doc__ or "").strip()


def slugify(nome: str) -> str:
    s = re.sub(r"[^0-9a-zA-Z]+", "-", nome).strip("-").lower()
    return s or "progetto"


def parse_target(target: Path, forzato: str | None) -> tuple[str, str]:
    m = re.match(r"^(\d{2,4})[_-](.+)$", target.name)
    if m:
        return m.group(1), m.group(2)
    if forzato:
        return "000", forzato
    raise SystemExit(
        f"il nome cartella «{target.name}» non e' <NNN>_<nome>: usa --nome <nome> per forzare"
    )


def rendi(testo: str, valori: dict[str, str]) -> str:
    for k, v in valori.items():
        testo = testo.replace("{{" + k + "}}", v)
    return testo


def da_copiare(p: Path) -> bool:
    if "__pycache__" in p.parts:
        return False
    return p.suffix not in (".pyc", ".pyo")


def destinazione(rel: Path, slug: str, memname: str) -> Path:
    parti = []
    for i, p in enumerate(rel.parts):
        if p == RENAME_DIR:
            parti.append(f"{slug}-memoria")
        elif i == 0 and p == "memoria":
            parti.append(memname)
        else:
            parti.append(p)
    rel2 = Path(*parti)
    if rel2.name.endswith(".tmpl"):
        rel2 = rel2.with_name(rel2.name[: -len(".tmpl")])
    return rel2


def rileva(target: Path) -> dict:
    agents = target / "AGENTS.md"
    memdir = None
    for nome in MEM_CANDIDATES:
        if (target / nome).is_dir():
            memdir = nome
            break
    markers = agents.exists() and INIZIO in agents.read_text(encoding="utf8")
    return {"agents": agents.exists(), "markers": markers, "memdir": memdir}


def aggancia_indice(agents: Path) -> bool:
    """Inserisce i marcatori dell'indice in un AGENTS.md esistente. True se modificato."""
    testo = agents.read_text(encoding="utf8")
    if INIZIO in testo:
        return False
    blocco = f"{INIZIO}\n\n{FINE}"
    m = re.search(r"(?m)^(#{1,6}\s+[Ii]ndice\s*)$", testo)
    if m:
        testo = testo[: m.end()] + "\n\n" + blocco + testo[m.end():]
    else:
        testo = testo.rstrip() + "\n\n## Indice\n\n" + blocco + "\n"
    agents.write_text(testo, encoding="utf8", newline="\n")
    return True


def assicura_procedure(agents: Path, slug: str) -> bool:
    """Aggiunge un rimando alla skill di progetto se manca. True se modificato."""
    testo = agents.read_text(encoding="utf8")
    if f"{slug}-memoria" in testo:
        return False
    sezione = (
        "\n## Procedure\n\n"
        f"- Skill di progetto: `.pi/skills/{slug}-memoria/SKILL.md`.\n"
        "- Memoria: `scripts/memoria_index.py` (rigenera) · "
        "`scripts/memoria_check.py` (verifica, deve uscire 0).\n"
    )
    agents.write_text(testo.rstrip() + "\n" + sezione, encoding="utf8", newline="\n")
    return True


def aggiungi_frontmatter(memdir: Path) -> int:
    """Aggiunge un frontmatter segnaposto ai capitoli che ne sono privi. Ritorna quanti."""
    n = 0
    for f in sorted(memdir.glob("*.md")):
        if f.name.lower().startswith("readme"):
            continue
        testo = f.read_text(encoding="utf8")
        if testo.startswith("---\n"):
            continue
        f.write_text(FRONTMATTER_MIN + testo, encoding="utf8", newline="\n")
        n += 1
    return n


def procedure(slug: str, memname: str, core_only: bool) -> str:
    if core_only:
        return (
            "## Strumenti\n\n"
            "- **Indice**: `scripts/memoria_index.py` (rigenera) · "
            "`scripts/memoria_check.py` (verifica, deve uscire 0).\n"
            "- **Decisioni**: `docs/ADR/` (usa `docs/ADR/000-template.md`)."
        )
    return (
        "## Procedure e strumenti\n\n"
        f"- **Skill di progetto**: `.pi/skills/{slug}-memoria/SKILL.md` — leggila quando "
        "aggiorni la\n  memoria o aggiungi una decisione.\n"
        "- **Script**: `scripts/memoria_index.py` (rigenera l'indice) · "
        "`scripts/memoria_check.py`\n  (verifica, deve uscire 0).\n"
        "- **Decisioni**: `docs/ADR/` (nuovo ADR con `/nuovo-adr`) · **prompt**: `.pi/prompts/`."
    )


def check(target: Path) -> int:
    stato = rileva(target)
    print(f"AGENTS.md: {'si' if stato['agents'] else 'no'} "
          f"(marcatori indice: {'si' if stato['markers'] else 'no'})")
    print(f"cartella memoria: {stato['memdir'] or 'assente'}")
    for rel in ("scripts/memoria_index.py", "scripts/memoria_check.py",
                ".pi/extensions/memoria-guard.ts"):
        print(f"{rel}: {'si' if (target / rel).exists() else 'no'}")
    check_script = target / "scripts" / "memoria_check.py"
    if not check_script.exists():
        print("memoria_check.py assente: pattern incompleto")
        return 1
    return subprocess.run([sys.executable, str(check_script)], cwd=str(target)).returncode


def esegui(target: Path, modo: str, nome: str | None, core_only: bool, dry_run: bool) -> int:
    if not TEMPLATES.is_dir():
        raise SystemExit(f"template non trovati in {TEMPLATES}")
    nnn, nome_logico = parse_target(target, nome)
    slug = slugify(nome_logico)
    stato = rileva(target)
    memname = stato["memdir"] or "memoria"

    valori = {
        "NNN": nnn,
        "REPO": target.name,
        "SLUG": slug,
        "PROGETTO": nome_logico.replace("_", " ").strip(),
        "MEMDIR": memname,
        "PROCEDURE": procedure(slug, memname, core_only),
    }

    if not dry_run:
        target.mkdir(parents=True, exist_ok=True)

    creati: list[str] = []
    saltati: list[str] = []
    for src in sorted(p for p in TEMPLATES.rglob("*") if p.is_file() and da_copiare(p)):
        rel = destinazione(src.relative_to(TEMPLATES), slug, memname)
        if core_only and rel.parts[0] == ".pi":
            continue
        dst = target / rel
        etichetta = rel.as_posix()
        if dst.exists():
            saltati.append(etichetta)
            continue
        if dry_run:
            creati.append(etichetta)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(rendi(src.read_text(encoding="utf8"), valori),
                       encoding="utf8", newline="\n")
        creati.append(etichetta)

    azioni: list[str] = []
    if not dry_run and modo == "migrate":
        agents = target / "AGENTS.md"
        if agents.exists():
            if aggancia_indice(agents):
                azioni.append("AGENTS.md: marcatori indice inseriti")
            if not core_only and assicura_procedure(agents, slug):
                azioni.append("AGENTS.md: sezione Procedure aggiunta")
        memdir = target / memname
        if memdir.is_dir():
            n = aggiungi_frontmatter(memdir)
            if n:
                azioni.append(f"{memname}/: frontmatter aggiunto a {n} capitoli")

    for rel in creati:
        print(f"  + {rel}")
    for rel in saltati:
        print(f"  = {rel} (esistente, non toccato)")
    for az in azioni:
        print(f"  ~ {az}")

    verbo = "creerebbe" if dry_run else "creato"
    print(f"\n{modo} · progetto {target.name}: {len(creati)} file {verbo}, "
          f"{len(saltati)} saltati, {len(azioni)} modifiche")
    if dry_run:
        return 0

    idx = target / "scripts" / "memoria_index.py"
    if idx.exists():
        r = subprocess.run([sys.executable, str(idx)], cwd=str(target))
        if r.returncode != 0:
            print("ATTENZIONE: memoria_index.py e' uscito non-zero")
            return r.returncode

    print("\nProssimi passi:")
    if not core_only:
        print(f'  1. project trust: apri l\'agente in "{target}" e concedi il trust (serve per .pi/**)')
    print("  2. compila i capitoli segnaposto (cerca «DA COMPILARE»)")
    print(f'  3. python "{target / "scripts" / "memoria_check.py"}"   # deve uscire 0')
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(USAGE)
        return 0 if argv else 2

    comando = "auto"
    if argv[0] in COMANDI:
        comando = argv.pop(0)

    target: str | None = None
    nome: str | None = None
    core_only = False
    dry_run = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help"):
            print(USAGE)
            return 0
        if a == "--core-only":
            core_only = True
        elif a == "--dry-run":
            dry_run = True
        elif a == "--nome":
            i += 1
            if i >= len(argv):
                print("--nome richiede un valore\n\n" + USAGE, file=sys.stderr)
                return 2
            nome = argv[i]
        elif a.startswith("-"):
            print(f"opzione sconosciuta: {a}\n\n" + USAGE, file=sys.stderr)
            return 2
        elif target is None:
            target = a
        else:
            print("troppi argomenti\n\n" + USAGE, file=sys.stderr)
            return 2
        i += 1

    if target is None:
        print(USAGE, file=sys.stderr)
        return 2
    target_path = Path(target).expanduser().resolve()

    if comando == "check":
        return check(target_path)

    modo = comando
    if modo == "auto":
        stato = rileva(target_path)
        modo = "migrate" if (stato["agents"] or stato["memdir"]) else "init"
    return esegui(target_path, modo, nome, core_only, dry_run)


if __name__ == "__main__":
    sys.exit(main())
