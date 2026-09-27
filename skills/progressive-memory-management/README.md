# progressive-memory-management

Skill **agnostica** per la **gestione della memoria nei progetti** con agenti di coding
(pi, Claude Code, Cursor, …) e modelli generici. Copia e condividi l'intera cartella: tutto
ciò che serve sta qui.

## Perché

Un file di memoria unico e gigantesco viene ricaricato a ogni richiesta, spreca token e
**peggiora la precisione** (le regole utili finiscono sepolte nella cronaca). La skill applica
la *progressive disclosure* a 4 livelli:

| Livello | Contenuto | Costo |
|---|---|---|
| L0 | `AGENTS.md`: regole di ingaggio, stabile, senza date | sempre |
| L1 | tabella-indice dentro `AGENTS.md` (generata) | sempre |
| L2 | capitoli `memoria/NN_*.md` con frontmatter `leggi_quando`/`parole_chiave` | on demand |
| L3 | `97_CRONACA.md`, `docs/ADR/`, archivi | raro |

Il file L0 resta **byte-stabile** fra le sessioni (nessuna data, nessun contatore): è il
prefisso che i provider tengono in prompt cache.

## Struttura

```
progressive-memory-management/
├── SKILL.md                     # istruzioni per l'agente
├── README.md                    # questo file
├── scripts/
│   └── manage_memory.py         # init / migrate / check / auto
└── templates/                   # ciò che viene copiato nel progetto
    ├── AGENTS.md.tmpl
    ├── memoria/{00_STATO,97_CRONACA,README}.md
    ├── docs/ADR/000-template.md
    ├── scripts/{memoria_index,memoria_check}.py
    └── .pi/{skills,prompts,extensions}/…   # extra opzionali (pi)
```

## CLI

Dalla cartella della skill:

```bash
python scripts/manage_memory.py <comando> "<cartella>" [opzioni]
```

| comando | effetto |
|---|---|
| `init <cartella>` | crea lo scheletro completo (progetto nuovo) |
| `migrate <cartella>` | aggiunge solo ciò che manca (progetto esistente, non distruttivo) |
| `check <cartella>` | diagnosi; esce **0** se il pattern è completo e coerente |
| `<cartella>` | **auto**: `init` se non c'è nulla, altrimenti `migrate` |

| opzione | effetto |
|---|---|
| `--core-only` | salta `.pi/**` → scheletro **agent-agnostico** |
| `--dry-run` | anteprima: mostra i file senza scriverli (`init`/`migrate`) |
| `--nome <nome>` | nome logico se la cartella non è `<NNN>_<nome>` |
| `-h`, `--help` | aiuto |

### Esempi

```bash
python scripts/manage_memory.py init    "C:/percorsi/022_nome"
python scripts/manage_memory.py migrate "C:/percorsi/019_progetto_esistente"
python scripts/manage_memory.py check   "C:/percorsi/021_progetto"
python scripts/manage_memory.py         "C:/percorsi/023_nome"          # auto
python scripts/manage_memory.py init    "C:/percorsi/024" --dry-run
python scripts/manage_memory.py init    "C:/percorsi/025" --core-only
```

## Uso con agenti diversi

- `AGENTS.md`, `memoria/`, `docs/ADR/` e i due script Python sono **agent-agnostici**.
- **pi**: la skill si installa nella cartella utente (`~/.pi/agent/skills/`) o come pacchetto;
  gli extra `.pi/**` sono risorse protette (richiedono il trust).
- **Claude Code / altri**: copia/collega la skill nella cartella skills del tuo agente; per la
  memoria di progetto usa `--core-only` e adatta `AGENTS.md` alla convenzione attesa
  (es. `CLAUDE.md`, `.cursor/rules`).
- **Senza agente**: lo script è autonomo (solo Python 3.10+; usa `tiktoken` se presente,
  altrimenti stima i token).

## Comandi utili (dentro il progetto)

```bash
python scripts/memoria_index.py     # rigenera l'indice dentro AGENTS.md
python scripts/memoria_check.py     # coerenza + budget: deve uscire 0
```
