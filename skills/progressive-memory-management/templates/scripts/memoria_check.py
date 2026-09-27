#!/usr/bin/env python3
"""memoria_check — la memoria del progetto deve essere autoconsistente (esce 0).

È il cancello di fine task. Non modifica nulla: se trova un disallineamento lo dice e dice
cosa eseguire. Gli invarianti verificati sono quelli dichiarati in `<memoria>/README.md`.

  I1  struttura: `AGENTS.md` con i marcatori della mappa; cartella memoria; `00_STATO.md` e
      `97_CRONACA.md` presenti e con frontmatter;
  I2  ogni capitolo ha frontmatter `leggi_quando` + `parole_chiave`;
  I3  gli indici derivati sono allineati ai file (delega a `memoria_index.py --check`);
  I4  nessun capitolo orfano, nessun riferimento a capitoli inesistenti, nessun link rotto;
  I5  L0 stabile e minimale: niente date/contatori/stime di token, entro budget, regole prima
      della mappa;
  I6  capitoli entro soglia (6000 token: spezzare; 8000: vietato) e `00_STATO.md` corto;
  I7  nessun titolo duplicato fra capitoli (una cosa, un posto);
  I8  nessun paragrafo identico fra i file della memoria (>= 40 parole) — escape: una riga
      `<!-- duplicato-ok -->`;
  I9  decisioni: numerazione unica, stato valido, titolo coerente col numero;
  I10 capacità on demand locali (`.pi/skills/*/SKILL.md`), se presenti: frontmatter valido;
  I11 il file della wiki dichiara la versione del pacchetto (`pacchetto:`).

Rileva da solo la cartella memoria: `memoria/` oppure `manuale/`.

Uso:
    python scripts/memoria_check.py            # esce 0 se la memoria è coerente
    python scripts/memoria_check.py -v         # elenca anche i controlli superati
    python scripts/memoria_check.py --strict   # anche gli avvisi fanno fallire
    python scripts/memoria_check.py --hash     # impronta di L0: confrontala fra sessioni
"""
from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS = ROOT / "AGENTS.md"
SKILLS = ROOT / ".pi" / "skills"
SCRIPT_PATTERN = "{{VERSION}}"          # versione del pacchetto che ha generato lo script
MEM_CANDIDATES = ("memoria", "manuale")
SOGLIA_AVVISO = 6000
SOGLIA_ERRORE = 8000
BUDGET_L0 = 1200            # token: oltre, L0 va alleggerito (procedure e dettagli altrove).
                            # 1200 e non 1000 perché la mappa cresce con i capitoli: è il
                            # prezzo del ToC, e va lasciato margine alle regole.
BUDGET_STATO = 1200         # token: `00_STATO.md` si legge a ogni sessione
DESC_MIN = 80               # caratteri: sotto, la descrizione non fa scattare il routing
DESC_MAX = 400              # caratteri: la descrizione sta sempre nel prefisso
PAROLE_MIN_DUP = 40         # parole: sotto, due paragrafi uguali sono normali
STATI_ADR = ("proposta", "accettata", "superata")
MARKER_REGOLE = "<!-- REGOLE-DEL-PATTERN"
ESCAPE_DUP = re.compile(r"(?m)^<!--\s*duplicato-ok\s*-->\s*$")
VOLATILI = (
    (re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "una data"),
    (re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b"), "una data"),
    (re.compile(r"\b\d{1,2}:\d{2}\b"), "un orario"),
    (re.compile(r"\b(?:oggi|ieri|domani|ultima sessione)\b", re.I), "un riferimento temporale"),
    (re.compile(r"(?:~|≈|circa)\s*[\d.,]+\s*(?:tok|token)\b(?!\s*/)", re.I), "una stima di token"),
    (re.compile(r"[\d.,]+\s*tok\b(?!\s*/)|\btoken stimat", re.I), "una stima di token"),
)


def memoria_dir() -> Path:
    for nome in MEM_CANDIDATES:
        cand = ROOT / nome
        if cand.is_dir():
            return cand
    raise SystemExit(f"nessuna cartella memoria trovata in {ROOT} (attesa `memoria/` o `manuale/`)")


def stima_token(testo: str) -> int:
    try:
        import tiktoken
        return len(tiktoken.get_encoding("o200k_base").encode(testo))
    except Exception:
        return round(len(testo.encode("utf8")) / 4)      # stima prudente


def frontmatter(testo: str) -> dict[str, str]:
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


def senza_rumore(testo: str) -> str:
    """Toglie frontmatter e blocchi di codice: restano titoli, prosa e tabelle."""
    testo = re.sub(r"^---\n.*?\n---\n", "", testo, flags=re.S)
    return re.sub(r"(?ms)^```.*?^```\s*$", "", testo)


def titoli(testo: str) -> list[str]:
    return [re.sub(r"\s+", " ", h).strip()
            for h in re.findall(r"(?m)^#{2,3}\s+(.+)$", senza_rumore(testo))]


def paragrafi(testo: str) -> list[str]:
    fuori = []
    for blocco in re.split(r"\n\s*\n", senza_rumore(testo)):
        riga = re.sub(r"(?m)^[\s>]*[-*+|#\d.]+\s*", "", blocco)
        riga = re.sub(r"[`*_\[\]()>|]", " ", riga)
        riga = re.sub(r"\s+", " ", riga).strip().lower()
        if riga.startswith("---") or len(riga.split()) < PAROLE_MIN_DUP:
            continue
        fuori.append(riga)
    return fuori


def adr_files() -> list[Path]:
    cartella = ROOT / "docs" / "ADR"
    if not cartella.is_dir():
        return []
    return [f for f in sorted(cartella.glob("*.md"))
            if f.name != "README.md" and "template" not in f.name.lower()]


def adr_numero(path: Path, fm: dict[str, str]) -> str | None:
    if fm.get("numero"):
        return str(fm["numero"]).zfill(3)
    m = re.search(r"(\d{3})", path.name)
    return m.group(1) if m else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--strict", action="store_true", help="anche gli avvisi fanno fallire")
    ap.add_argument("--hash", action="store_true",
                    help="stampa l'impronta di AGENTS.md (confronto fra sessioni)")
    args = ap.parse_args()

    if args.hash:
        if not AGENTS.exists():
            print(f"{AGENTS} assente")
            return 1
        testo = AGENTS.read_text(encoding="utf8")
        print(f"AGENTS.md  sha256={hashlib.sha256(testo.encode('utf8')).hexdigest()[:16]}  "
              f"{stima_token(testo)} token  {len(testo)} byte")
        return 0

    problemi: list[str] = []
    avvisi: list[str] = []
    ok: list[str] = []

    # ---------------------------------------------------------------- I1 struttura
    if not AGENTS.exists():
        print(f"ERR  {AGENTS.name} assente: il pattern non è applicato")
        return 1
    agents = AGENTS.read_text(encoding="utf8")
    memdir = memoria_dir()
    stato_file = memdir / "00_STATO.md"
    cronaca_file = memdir / "97_CRONACA.md"
    if "<!-- INDICE:INIZIO" not in agents or "<!-- INDICE:FINE -->" not in agents:
        problemi.append(f"{AGENTS.name}: mancano i marcatori della mappa "
                        "(`<!-- INDICE:INIZIO … -->` / `<!-- INDICE:FINE -->`)")
    for f in (stato_file, cronaca_file):
        if not f.exists():
            problemi.append(f"{f.relative_to(ROOT).as_posix()}: assente")
        elif not frontmatter(f.read_text(encoding="utf8")):
            problemi.append(f"{f.name}: frontmatter `leggi_quando`/`parole_chiave` assente")
    if MARKER_REGOLE not in agents:
        avvisi.append(f"{AGENTS.name}: blocco regole del pattern non riconosciuto "
                      f"(atteso {MARKER_REGOLE} v2 -->): unisci a mano le regole v2")
    if not problemi:
        ok.append(f"struttura presente ({memdir.name}/, 00_STATO, 97_CRONACA)")

    capitoli = [f for f in sorted(memdir.glob("*.md")) if not f.name.lower().startswith("readme")]
    testi = {f: f.read_text(encoding="utf8") for f in capitoli}

    # ---------------------------------------------------------------- I2 frontmatter
    senza_fm = []
    for f, testo in testi.items():
        fm = frontmatter(testo)
        for campo in ("leggi_quando", "parole_chiave"):
            if not fm.get(campo):
                problemi.append(f"{f.name}: frontmatter senza `{campo}`")
                senza_fm.append(f)
        if not re.match(r"^\d\d_", f.name):
            avvisi.append(f"{f.name}: nome senza numero progressivo (`NN_nome.md`)")
    if not senza_fm:
        ok.append(f"frontmatter completo su {len(capitoli)} capitoli")

    # ---------------------------------------------------------------- I3 indici derivati
    index_script = ROOT / "scripts" / "memoria_index.py"
    if not index_script.exists():
        problemi.append("scripts/memoria_index.py assente: gli indici non sono derivabili")
    else:
        r = subprocess.run([sys.executable, str(index_script), "--check"],
                           capture_output=True, text=True, cwd=str(ROOT))
        if r.returncode == 0:
            ok.append("indici derivati allineati ai file")
        else:
            problemi.append((r.stdout.strip() or "indici non allineati")
                            + "  →  python scripts/memoria_index.py")

    # ---------------------------------------------------------------- I4 integrità
    orfani = [f.name for f in capitoli if f.name not in agents]
    if orfani:
        problemi.append("capitoli non citati nella mappa di AGENTS.md: " + ", ".join(orfani))
    for citato in sorted(set(re.findall(r"\b(\d\d_[\w.-]+\.md)\b", agents))):
        if not (memdir / citato).exists():
            problemi.append(f"{AGENTS.name} cita {memdir.name}/{citato} che non esiste")
    da_scandire = [AGENTS, *capitoli, memdir / "README.md"]
    for extra in (ROOT / "README.md", ROOT / "docs" / "ADR" / "README.md"):
        if extra.exists():
            da_scandire.append(extra)
    for f in da_scandire:
        if not f.exists():
            continue
        for link in re.findall(r"\]\(\s*<?(?!https?:|mailto:|#)([^\s)>#]+)", f.read_text(encoding="utf8")):
            if not (ROOT / link).exists() and not (f.parent / link).exists():
                problemi.append(f"{f.name}: link rotto → {link}")
    if not any("non citati" in p or "link rotto" in p or "che non esiste" in p for p in problemi):
        ok.append("nessun capitolo orfano, nessun link rotto")

    # ---------------------------------------------------------------- I5 stabilità di L0
    for rx, cosa in VOLATILI:
        m = rx.search(agents)
        if m:
            problemi.append(f"{AGENTS.name} contiene {cosa} («{m.group(0)}»): rompe la "
                            "stabilità del prefisso in cache")
    n_l0 = stima_token(agents)
    if n_l0 > BUDGET_L0:
        problemi.append(f"{AGENTS.name} = {n_l0} token (> budget {BUDGET_L0}): sposta "
                        "procedure e dettagli nei capitoli")
    if "<!-- INDICE:INIZIO" in agents and "## Regole" in agents:
        if agents.index("<!-- INDICE:INIZIO") < agents.index("## Regole"):
            avvisi.append("in AGENTS.md la mappa sta prima delle regole: mettila in coda, "
                          "così aggiornarla non invalida il blocco delle regole")
    if not any("volatile" in p or "stabilità" in p or "budget" in p for p in problemi):
        ok.append(f"L0 stabile e minimale ({n_l0} token, budget {BUDGET_L0})")

    # ---------------------------------------------------------------- I6 soglie
    tot_l2 = 0
    for f, testo in testi.items():
        t = stima_token(testo)
        tot_l2 += t
        if t > SOGLIA_ERRORE:
            problemi.append(f"{f.name}: {t} token (> {SOGLIA_ERRORE}): va spezzato in più capitoli")
        elif t > SOGLIA_AVVISO:
            problemi.append(f"{f.name}: {t} token (> {SOGLIA_AVVISO}): da spezzare a breve")
    if stato_file.exists():
        t_stato = stima_token(stato_file.read_text(encoding="utf8"))
        if t_stato > BUDGET_STATO:
            avvisi.append(f"00_STATO.md = {t_stato} token (> {BUDGET_STATO}): è letto a ogni "
                          "sessione, sposta i dettagli nei capitoli tematici")
    if not any("spezzato" in p or "spezzare" in p for p in problemi):
        ok.append(f"{len(capitoli)} capitoli entro soglia ({tot_l2} token in L2)")

    # ---------------------------------------------------------------- I7 titoli duplicati
    visti: dict[str, str] = {}
    dup_titoli = 0
    for f, testo in testi.items():
        for h in titoli(testo):
            if h in visti and visti[h] != f.name:
                problemi.append(f"titolo «{h}» in {visti[h]} e {f.name} (una cosa, un posto)")
                dup_titoli += 1
            visti[h] = f.name
    if not dup_titoli:
        ok.append(f"nessun titolo duplicato ({len(visti)} sezioni)")

    # ---------------------------------------------------------------- I8 paragrafi duplicati
    dove: dict[str, tuple[str, str]] = {}
    dup_para = 0
    testi_dup = dict(testi)
    wiki_file = memdir / "README.md"
    if wiki_file.exists():
        testi_dup[wiki_file] = wiki_file.read_text(encoding="utf8")
    for f, testo in testi_dup.items():
        if ESCAPE_DUP.search(testo):
            continue
        for p in paragrafi(testo):
            chiave = hashlib.sha1(p.encode("utf8")).hexdigest()
            if chiave in dove and dove[chiave][0] != f.name:
                altro, estratto = dove[chiave]
                problemi.append(f"paragrafo identico in {altro} e {f.name} («{estratto[:60]}…»): "
                                "tieni una copia sola, o metti una riga `<!-- duplicato-ok -->`")
                dup_para += 1
            dove[chiave] = (f.name, p)
    if not dup_para:
        ok.append("nessun paragrafo duplicato fra i file della memoria")

    # ---------------------------------------------------------------- I9 decisioni (ADR)
    adrs = adr_files()
    if adrs:
        numeri = Counter()
        for f in adrs:
            testo = f.read_text(encoding="utf8")
            fm = frontmatter(testo)
            numero = adr_numero(f, fm)
            if numero is None:
                avvisi.append(f"{f.name}: numero dell'ADR non deducibile (atteso `ADR-NNN_*`)")
            else:
                numeri[numero] += 1
            if not fm:
                avvisi.append(f"{f.name}: scheda senza frontmatter (numero/stato/titolo)")
            elif fm.get("stato") and fm["stato"].lower() not in STATI_ADR:
                avvisi.append(f"{f.name}: stato «{fm['stato']}» non previsto "
                              f"({', '.join(STATI_ADR)})")
            if numero and f"ADR-{numero}" not in senza_rumore(testo):
                avvisi.append(f"{f.name}: il titolo non contiene «ADR-{numero}»")
        for numero, n in sorted(numeri.items()):
            if n > 1:
                problemi.append(f"numero di ADR {numero} usato {n} volte")
        if not any("numero di ADR" in p for p in problemi):
            ok.append(f"{len(adrs)} decisioni numerate correttamente")
    else:
        avvisi.append("docs/ADR/: nessuna decisione registrata")

    # ---------------------------------------------------------------- I10 capacità on demand
    if SKILLS.is_dir():
        presenti = []
        for d in sorted(p for p in SKILLS.iterdir() if p.is_dir()):
            skill_file = d / "SKILL.md"
            if not skill_file.exists():
                continue
            presenti.append(d.name)
            fm = frontmatter(skill_file.read_text(encoding="utf8"))
            if not fm.get("name") or not fm.get("description"):
                problemi.append(f"capacità {d.name}: frontmatter senza name/description")
                continue
            lung = len(fm["description"])
            if lung > DESC_MAX:
                problemi.append(f"capacità {d.name}: description di {lung} caratteri "
                                f"(> {DESC_MAX}): sta sempre nel prefisso fisso")
            elif lung < DESC_MIN:
                avvisi.append(f"capacità {d.name}: description di {lung} caratteri: "
                              "troppo vaga per far scattare il routing")
        if presenti and not any("description" in p for p in problemi):
            ok.append(f"capacità on demand: {len(presenti)} valide")

    # ---------------------------------------------------------------- I11 versione pacchetto
    wiki = memdir / "README.md"
    if wiki.exists() and "pacchetto" not in wiki.read_text(encoding="utf8").lower():
        avvisi.append(f"{memdir.name}/README.md: manca la versione del pacchetto "
                      "(`pacchetto: <versione>`): serve a capire quanto è vecchio il pattern")

    # ---------------------------------------------------------------- esito
    if args.verbose:
        for riga in ok:
            print(f"  OK  {riga}")
    for riga in avvisi:
        print(f"  AVV {riga}")
    if problemi:
        print("MEMORIA DA RIPARARE:")
        for riga in problemi:
            print(f"  ERR {riga}")
        return 1
    if args.strict and avvisi:
        print("MEMORIA CON AVVISI (--strict): risolvili o togli --strict")
        return 1
    print(f"memoria autoconsistente · L0 {n_l0} token (budget {BUDGET_L0}) · "
          f"L2 {tot_l2} token in {len(capitoli)} capitoli · {len(adrs)} decisioni · "
          f"{len(avvisi)} avvisi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
