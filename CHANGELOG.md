# Changelog

Versioni del bundle di skill `k3nt0-skills` (tag `v*` → release con un archivio per skill).
La versione di ogni singola skill è nel suo `VERSION`/`CHANGELOG.md`, accanto a `SKILL.md`.

## 0.2.1

`skills/progressive-memory-management` **0.2.1** (generazione del pattern `v2`).

- Corretto un **falso positivo** nella rilevazione dei dati volatili: `tok/s` (unità di velocità,
  es. `108 tok/s`) era scambiato per una stima di token e bloccava `memoria_index.py` su progetti
  che parlano di prestazioni. Ora le stime (`~1.200 token`, `1234 tok`, `token stimati`) sono
  rifiutate e i tassi (`tok/s`) passano.

## 0.2.0

`skills/progressive-memory-management` **0.2.0** (generazione del pattern `v2`).

- La memoria di progetto diventa una **wiki autoconsistente**: contratto di manutenzione
  (LEGGI → SCRIVI → VERIFICA → RIPARA) e invarianti **I1–I11** dichiarati in `<memoria>/README.md`.
- **Indice derivato anche per le decisioni** (`docs/ADR/README.md`), oltre alla mappa in `AGENTS.md`.
- Regole di L0 al pattern v2: lettura mirata, indici derivati come cancello di fine task, L0 come
  prefisso in cache (niente date, contatori o stime di token; regole **prima** della mappa),
  procedure fuori da L0, aggiornamento della memoria durante il lavoro, soglie di capitolo.
- Verifica più forte (`memoria_check.py`): duplicati di titoli e paragrafi, numerazione e stato
  delle decisioni, budget di `00_STATO.md`, ordine regole→mappa; più `--strict`, `--hash` e
  avvisi separati dagli errori.
- Gli indici **rifiutano** i dati volatili (date, stime di token) invece di propagarli nel prefisso.
- Scaffold **agent-agnostico per default**: gli adattatori per pi (`.pi/**`) si aggiungono con
  `--with-pi`.
- Versioning del pacchetto: `VERSION`, `CHANGELOG.md`, `pacchetto:` nella wiki e `SCRIPT_PATTERN`
  negli script; `check` diagnostica le versioni e `migrate --refresh-scripts` /
  `--refresh-generated` riallineano i file generati (mai L0, mai i contenuti del progetto).
- `migrate` resta **non distruttivo**: non sovrascrive mai un file esistente.

## 0.1.0

Prima pubblicazione del bundle: `skills/progressive-memory-management` **0.1.0** (pattern `v1`).
`init` / `migrate` / `check`, livelli L0–L3, `memoria_index.py` (mappa a due colonne, niente stime
di token), `memoria_check.py` (coerenza e soglie), adattatori pi.
