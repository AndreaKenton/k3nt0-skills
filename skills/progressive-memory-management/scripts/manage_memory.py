#!/usr/bin/env python3
"""manage_memory — memoria di progetto a livelli L0-L3: init, migrazione, diagnosi.

Pacchetto autonomo e portabile: questo script vive in `scripts/` della skill e trova i
template in `../templates`. Non dipende da un agente, da un modello né da estensioni: copia la
cartella della skill dove vuoi.

Il progetto generato è **agent-agnostico** (AGENTS.md, `<memoria>/`, docs/ADR, due script
Python). Gli adattatori per un agente specifico (per pi: `.pi/**`) sono **opzionali** e si
aggiungono con `--with-pi`.

COMANDI
    init    <cartella>    crea lo scheletro completo di un progetto nuovo
    migrate <cartella>    aggiunge SOLO cio' che manca a un progetto esistente
                          (non distruttivo: non sovrascrive mai un file)
    check   <cartella>    diagnosi; esce 0 se il pattern e' completo e coerente
    version               stampa la versione del pacchetto
    <cartella>            senza comando: AUTO (init se non c'e' nulla, altrimenti migrate)

OPZIONI
    --with-pi      aggiunge gli adattatori per pi (.pi/skills, .pi/prompts, .pi/extensions)
    --refresh-scripts  aggiorna scripts/memoria_{index,check}.py alla versione del pacchetto
                   (migrate: opt-in; non tocca L0 né la memoria)
    --refresh-generated  come sopra + i file generati del pattern (contratto della wiki,
                   indice e template delle decisioni): mai L0, mai i contenuti del progetto
    --dry-run      mostra i file che creerebbe, senza scrivere (init/migrate)
    --nome <nome>  nome logico se la cartella non e' <NNN>_<nome>
    -h, --help     questo aiuto

ESEMPI
    python manage_memory.py init    "C:/percorsi/022_nome"
    python manage_memory.py migrate "C:/percorsi/019_progetto_esistente"
    python manage_memory.py check   "C:/percorsi/021_progetto"
    python manage_memory.py         "C:/percorsi/023_nome"                 # auto
    python manage_memory.py init    "C:/percorsi/024" --dry-run
    python manage_memory.py init    "C:/percorsi/025" --with-pi
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
COMANDI = ("init", "migrate", "check", "version")
INIZIO = "<!-- INDICE:INIZIO (generato: non modificare a mano) -->"
FINE = "<!-- INDICE:FINE -->"
MARKER_REGOLE = "<!-- REGOLE-DEL-PATTERN"
FRONTMATTER_MIN = (
    "---\n"
    'leggi_quando: "DA COMPILARE — quando serve leggere questo capitolo"\n'
    'parole_chiave: "DA COMPILARE"\n'
    "---\n\n"
)
USAGE = (__doc__ or "").strip()


def versione_pacchetto() -> str:
    f = PKG / "VERSION"
    try:
        return f.read_text(encoding="utf8").strip() or "0.0.0"
    except OSError:
        return "0.0.0"


VERSION = versione_pacchetto()
PATTERN_VERSION = "v2"                # generazione del pattern (marker in AGENTS.md);
                                      # indipendente dalla versione del pacchetto


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
    """Inserisce i marcatori della mappa in un AGENTS.md esistente. True se modificato."""
    testo = agents.read_text(encoding="utf8")
    if INIZIO in testo:
        return False
    blocco = f"{INIZIO}\n\n{FINE}"
    m = re.search(r"(?m)^(#{1,6}\s+[Mm]appa della memoria\s*|#{1,6}\s+[Ii]ndice\s*)$", testo)
    if m:
        testo = testo[: m.end()] + "\n\n" + blocco + testo[m.end():]
    else:
        testo = testo.rstrip() + "\n\n## Mappa della memoria\n\n" + blocco + "\n"
    agents.write_text(testo, encoding="utf8", newline="\n")
    return True


def assicura_procedure(agents: Path, slug: str, with_pi: bool) -> bool:
    """Aggiunge il rimando agli strumenti/memoria se manca. True se modificato."""
    testo = agents.read_text(encoding="utf8")
    if f"{slug}-memoria" in testo or "memoria_check" in testo:
        return False
    righe = [
        "\n## Strumenti\n",
        "",
        "- **Memoria**: `<memoria>/README.md` — come è organizzata e come si mantiene.",
        "- **Indici derivati**: `scripts/memoria_index.py` (rigenera mappa e decisioni) · "
        "`scripts/memoria_check.py` (verifica: **deve uscire 0**).",
        "- **Decisioni**: `docs/ADR/` (parti da `docs/ADR/000-template.md`).",
    ]
    if with_pi:
        righe.insert(2, f"- **Capacità di progetto**: `.pi/skills/{slug}-memoria/SKILL.md`.")
    testo = testo.rstrip() + "\n" + "\n".join(righe) + "\n"
    # le regole stanno prima della mappa: se i marcatori ci sono, inserisci sopra
    if INIZIO in testo and testo.index("## Strumenti") > testo.index(INIZIO):
        sezione = testo[testo.index("\n## Strumenti"):]
        testo = testo[: testo.index("\n## Strumenti")].rstrip() + "\n"
        i = testo.index(INIZIO)
        testo = testo[:i] + sezione.strip() + "\n\n" + testo[i:]
    agents.write_text(testo, encoding="utf8", newline="\n")
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


def procedure(slug: str, memname: str, with_pi: bool) -> str:
    righe = [
        "## Strumenti",
        "",
        f"- **Memoria**: `{memname}/README.md` — livelli, invarianti, contratto di manutenzione.",
        "- **Indici derivati**: `scripts/memoria_index.py` (mappa in `AGENTS.md` + indice delle "
        "decisioni) ·",
        "  `scripts/memoria_check.py` (verifica la coerenza: **deve uscire 0**).",
        "- **Decisioni**: `docs/ADR/` — parti da `docs/ADR/000-template.md`.",
    ]
    if with_pi:
        righe.append(
            f"- **Capacità di progetto**: `.pi/skills/{slug}-memoria/SKILL.md` — leggila quando "
            "aggiorni la memoria."
        )
        righe.append("- **Scorciatoie**: `.pi/prompts/` (`mem`, `nuovo-adr`).")
    return "\n".join(righe)


def versione_progetto(target: Path, memname: str | None) -> str | None:
    if not memname:
        return None
    wiki = target / memname / "README.md"
    if not wiki.exists():
        return None
    m = re.search(r"pacchetto[^\n]{0,12}?([0-9][0-9A-Za-z.\-]*)",
                  wiki.read_text(encoding="utf8"), re.I)
    return m.group(1) if m else None


def versione_script(target: Path, script: str = "memoria_check.py") -> str | None:
    f = target / "scripts" / script
    if not f.exists():
        return None
    m = re.search(r'(?m)^SCRIPT_PATTERN\s*=\s*["\']([^"\']+)', f.read_text(encoding="utf8"))
    return m.group(1) if m else None


def script_presente(target: Path) -> bool:
    return (target / "scripts" / "memoria_check.py").exists()


def regole_pattern(agents_testo: str) -> str | None:
    m = re.search(r"<!--\s*REGOLE-DEL-PATTERN:\s*(v?[\d.]+)", agents_testo)
    return m.group(1) if m else None


def generati(memname: str, docs: bool) -> list[tuple[str, str]]:
    """Coppie (template, destinazione) dei file *generati dal pacchetto*."""
    coppie = [("scripts/memoria_index.py", "scripts/memoria_index.py"),
              ("scripts/memoria_check.py", "scripts/memoria_check.py")]
    if docs:
        coppie += [("memoria/README.md.tmpl", f"{memname}/README.md"),
                   ("docs/ADR/README.md.tmpl", "docs/ADR/README.md"),
                   ("docs/ADR/000-template.md.tmpl", "docs/ADR/000-template.md")]
    return coppie


def aggiorna_generati(target: Path, valori: dict[str, str], docs: bool) -> list[str]:
    """Opt-in: riporta i file generati alla versione del pacchetto (mai i contenuti)."""
    aggiornati = []
    for src_rel, dst_rel in generati(valori["MEMDIR"], docs):
        src = TEMPLATES / src_rel
        dst = target / dst_rel
        if not src.exists():
            continue
        nuovo = rendi(src.read_text(encoding="utf8"), valori)
        if dst.exists() and dst.read_text(encoding="utf8") == nuovo:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(nuovo, encoding="utf8", newline="\n")
        aggiornati.append(dst_rel)
    return aggiornati


def check(target: Path) -> int:
    stato = rileva(target)
    memname = stato["memdir"]
    agents_testo = (target / "AGENTS.md").read_text(encoding="utf8") if stato["agents"] else ""
    v_script = versione_script(target)
    stato_script = v_script or ("senza versione" if script_presente(target) else "assenti")
    print(f"pacchetto: {VERSION} · pattern nel progetto: {versione_progetto(target, memname) or 'assente'} "
          f"· script: {stato_script} · regole: {regole_pattern(agents_testo) or 'non riconosciute'}")
    print(f"AGENTS.md: {'si' if stato['agents'] else 'no'} "
          f"(mappa: {'si' if stato['markers'] else 'no'})")
    print(f"cartella memoria: {memname or 'assente'}")
    for rel in ("scripts/memoria_index.py", "scripts/memoria_check.py",
                "docs/ADR/000-template.md", "docs/ADR/README.md"):
        print(f"{rel}: {'si' if (target / rel).exists() else 'no'}")
    print(f".pi/** (adattatore opzionale): {'si' if (target / '.pi').is_dir() else 'no'}")
    mancanti = [r for r in ("AGENTS.md", "scripts/memoria_index.py", "scripts/memoria_check.py")
                if not (target / r).exists()]
    if not memname:
        mancanti.append("cartella memoria (memoria/ o manuale/)")
    if mancanti:
        print("pattern incompleto: " + ", ".join(mancanti) + "  →  esegui migrate")
        return 1
    if MARKER_REGOLE not in agents_testo:
        print("nota: AGENTS.md non riconosciuto come blocco regole del pattern — le regole nuove "
              "vanno unite a mano (migrate non sovrascrive)")
    elif (regole_pattern(agents_testo) or "").lstrip("v") != PATTERN_VERSION.lstrip("v"):
        print(f"nota: regole del pattern {regole_pattern(agents_testo)} in AGENTS.md, attese "
              f"{PATTERN_VERSION} — allinea a mano da templates/AGENTS.md.tmpl")
    v_pattern = versione_progetto(target, memname)
    if v_pattern and v_pattern != VERSION:
        print(f"nota: contratto della wiki ({memname}/README.md) della versione {v_pattern} — "
              f"`migrate --refresh-generated` lo riporta a {VERSION} (o allinealo a mano)")
    if v_script and v_script != VERSION:
        print(f"nota: scripts/memoria_*.py generati dal pacchetto {v_script} — "
              "`migrate --refresh-scripts` li riporta a " + VERSION)
    elif not v_script and script_presente(target):
        print("nota: scripts/memoria_*.py senza dichiarazione di versione (pacchetto precedente) — "
              "`migrate --refresh-scripts` li porta a " + VERSION)
    check_script = target / "scripts" / "memoria_check.py"
    sys.stdout.flush()
    return subprocess.run([sys.executable, str(check_script)], cwd=str(target)).returncode


def esegui(target: Path, modo: str, nome: str | None, with_pi: bool, dry_run: bool,
           refresh_scripts: bool = False, refresh_generated: bool = False) -> int:
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
        "VERSION": VERSION,
        "PROCEDURE": procedure(slug, memname, with_pi),
    }

    if not dry_run:
        target.mkdir(parents=True, exist_ok=True)

    creati: list[str] = []
    saltati: list[str] = []
    for src in sorted(p for p in TEMPLATES.rglob("*") if p.is_file() and da_copiare(p)):
        rel = destinazione(src.relative_to(TEMPLATES), slug, memname)
        if not with_pi and rel.parts[0] == ".pi":
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
                azioni.append("AGENTS.md: marcatori della mappa inseriti")
            if assicura_procedure(agents, slug, with_pi):
                azioni.append("AGENTS.md: sezione Strumenti aggiunta")
        memdir = target / memname
        if memdir.is_dir():
            n = aggiungi_frontmatter(memdir)
            if n:
                azioni.append(f"{memname}/: frontmatter aggiunto a {n} capitoli")
        if refresh_scripts or refresh_generated:
            for rel in aggiorna_generati(target, valori, docs=refresh_generated):
                azioni.append(f"{rel}: aggiornato alla versione {VERSION}")

    for rel in creati:
        print(f"  + {rel}")
    for rel in saltati:
        print(f"  = {rel} (esistente, non toccato)")
    for az in azioni:
        print(f"  ~ {az}")

    verbo = "da creare" if dry_run else "creati"
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
    if with_pi:
        print(f'  1. project trust: apri l\'agente in "{target}" e concedi il trust '
              "(serve per .pi/**)")
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
    if comando == "version":
        print(f"progressive-memory-management {VERSION}")
        return 0

    target: str | None = None
    nome: str | None = None
    with_pi = False
    dry_run = False
    refresh_scripts = False
    refresh_generated = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help"):
            print(USAGE)
            return 0
        if a == "--with-pi":
            with_pi = True
        elif a == "--refresh-scripts":
            refresh_scripts = True
        elif a == "--refresh-generated":
            refresh_generated = True
        elif a == "--core-only":
            print("nota: `--core-only` non serve più: lo scheletro è agent-agnostico per "
                  "default (usa `--with-pi` per aggiungere gli adattatori di pi)")
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
    return esegui(target_path, modo, nome, with_pi, dry_run, refresh_scripts, refresh_generated)


if __name__ == "__main__":
    sys.exit(main())
