# Changelog

Numerazione del **pacchetto** (questa cartella): la prima pubblicazione è la `0.2.0`. La
numerazione della **generazione del pattern** è indipendente e resta `v2` (marker
`<!-- REGOLE-DEL-PATTERN: v2 -->` in `AGENTS.md` e formato degli indici derivati).

## 0.2.1

Corretto un **falso positivo** nella rilevazione dei dati volatili: `tok/s` (unità di velocità,
es. `108 tok/s`) veniva scambiato per una stima di token e **bloccava la rigenerazione
dell'indice**. Ora le stime (`~1.200 token`, `1234 tok`, `token stimati`) restano rifiutate e i
tassi (`tok/s`) passano. Vale per `memoria_index.py` e `memoria_check.py`.

## 0.2.0

Il pattern diventa **una wiki autoconsistente agent-agnostica**, senza dipendenze da tool o
estensioni. Portato dentro il pacchetto ciò che di generale e astratto c'era nella skill
`memoria-progetti` di pi.

**Aggiunto**

- **Contratto di manutenzione** in `<memoria>/README.md`: ciclo LEGGI → SCRIVI → VERIFICA →
  RIPARA, tabella dei livelli, **invarianti I1–I11**, e la spiegazione di *cosa invalida la
  prompt cache e cosa no*.
- **Indice delle decisioni derivato**: `docs/ADR/README.md` con marcatori, generato da
  `memoria_index.py` insieme alla mappa in `AGENTS.md`; le schede ADR hanno un frontmatter
  (`numero`, `titolo`, `stato`, `data`, `supera`).
- **Regole portate in L0** (`templates/AGENTS.md.tmpl`): lettura mirata, indici derivati come
  cancello di fine task, L0 come prefisso in cache (niente date/contatori/**stime di token**,
  regole **prima** della mappa), procedure fuori da L0, aggiornamento della memoria durante il
  lavoro, un tema per capitolo con soglie.
- **Verifica più forte** (`memoria_check.py`): I1–I11, inclusi *paragrafi duplicati fra capitoli*
  (≥ 40 parole, escape `<!-- duplicato-ok -->`), numerazione e stato delle decisioni, ordine
  regole→mappa in L0, budget dedicato di `00_STATO.md`, `--strict` per gli avvisi, `--hash` per
  confrontare l'impronta di L0 fra sessioni.
- **Gli indici si rifiutano di contenere dati volatili**: `memoria_index.py` si ferma con un
  errore se un frontmatter porta date o stime di token, invece di propagarle nel prefisso.
- **Versioning**: `VERSION`, `CHANGELOG.md`, `pacchetto: <versione>` in `<memoria>/README.md` e
  `SCRIPT_PATTERN` negli script generati; `check` confronta le versioni del progetto con quella
  installata e `migrate --refresh-scripts` aggiorna i due script (opt-in, non tocca L0 né la
  memoria); `--refresh-generated` aggiorna anche i file generati del pattern (contratto della
  wiki, indice e template delle decisioni).
- **Principi portati nel core** (non più solo nell'adattatore pi o assenti): lettura mirata e
  archivi citati e non scanditi; esplorazione ampia in un contesto isolato; sottocartelle
  autonome con un file di contesto locale; `00_STATO.md` che sopravvive ai riassunti del
  contesto (compaction); descrizioni delle capacità da cambiare in blocco perché stanno nel
  prefisso in cache.
- **Regola di manutenzione del pacchetto** in `SKILL.md`: dove nasce una regola (template per i
  progetti, skill per il pattern, script per ciò che è verificabile, adattatore per ciò che è
  specifico di un agente).

**Cambiato**

- Lo scaffold è **agent-agnostico per default**: gli adattatori `.pi/**` (skill di progetto,
  prompt, estensione di guardia) si aggiungono con `--with-pi`; `--core-only` non serve più
  (accettato come no-op con una nota).
- `AGENTS.md` di progetto: le regole sono **prima** della mappa, così rigenerare la mappa non
  invalida il blocco delle regole nella cache.
- `migrate`: il rimando agli strumenti viene inserito **prima** della mappa e la diagnosi
  (`check`) segnala se il blocco regole è di una versione precedente (non lo riscrive).
- `00_STATO.md` diventa un **router** corto (budget ~1.000 token) verso i capitoli; la storia
  resta in `97_CRONACA.md` (tabella append-only).

**Non cambiato (per scelta)**

- `migrate` resta **non distruttivo**: non sovrascrive mai un file esistente e non riscrive le
  regole di un `AGENTS.md` già in uso.

## 0.1.0

Prima versione pubblicata (tag `v0.1.0` del bundle [`k3nt0-skills`](https://github.com/AndreaKenton/k3nt0-skills)):
`init` / `migrate` / `check`, livelli L0–L3, `memoria_index.py` (mappa in `AGENTS.md`, due
colonne, niente stime di token), `memoria_check.py` (coerenza e soglie), adattatori pi.
