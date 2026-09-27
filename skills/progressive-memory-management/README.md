# progressive-memory-management

**Memoria di progetto a livelli, come wiki autoconsistente.** Pattern di buone pratiche più due
script Python che lo applicano: `init` / `migrate` / `check`.

- **Agnostico**: nessun agente, nessun modello, nessun servizio richiesto. `AGENTS.md`,
  `<memoria>/`, `docs/ADR/` e gli script sono file normali.
- **Senza tooling**: nessuna estensione necessaria. Gli adattatori per pi (`.pi/**`) sono
  opzionali (`--with-pi`).
- **Autoconsistente**: gli indici sono *derivati* dai file e la coerenza è *verificata* da uno
  script. La gerarchia non può divergere in silenzio.
- **Non distruttivo**: su un progetto esistente aggiunge solo ciò che manca, non sovrascrive mai.

## Perché

Un file di memoria unico e gigantesco viene ricaricato a ogni richiesta, spreca token e
**peggiora la precisione** (le regole utili finiscono sepolte nella cronaca). La progressive
disclosure a 4 livelli risolve entrambe le cose:

| livello | contenuto | quando entra nel contesto |
|---|---|---|
| L0 | `AGENTS.md`: regole + mappa della memoria | sempre (è il prefisso in prompt cache) |
| L1 | la mappa in coda a `AGENTS.md`, generata | sempre (è dentro L0) |
| L2 | `<memoria>/NN_*.md` con frontmatter `leggi_quando` + `parole_chiave` | on demand, solo i capitoli pertinenti |
| L3 | `97_CRONACA.md`, `docs/ADR/`, archivi | raro, su richiesta |

L0 resta **byte-stabile** fra sessioni e fra i task della stessa sessione: niente date, niente
contatori, niente stime di token, e le regole stanno **prima** della mappa. I token riletti da
cache costano molto meno degli input token nuovi (indicativamente **10–30× meno**, secondo il
provider): un prefisso fermo è ciò che permette a una sessione lunga di non ripagare tutto il
contesto a ogni task. Vale anche per le **descrizioni** delle capacità dell'agente (skill,
comandi): stanno nel prefisso fisso, quindi si modificano **in blocco** e solo quando serve.

## Garanzie del pattern

| garanzia | meccanismo |
|---|---|
| memoria minima nel system prompt | budget su L0 (`memoria_check`), regole in L0 e tutto il resto on demand |
| lettura a livelli | L0 → mappa → solo i capitoli pertinenti; gli archivi non si scandiscono |
| gerarchia sempre aggiornata | `memoria_index.py` *deriva* la mappa e l'indice delle decisioni dai file |
| avviso di disallineamento | `memoria_check.py` esce non-zero: indice vecchio, orfani, link rotti, frontmatter mancante, duplicati, soglie, volatili in L0 |
| cache valida fra i task | prefisso stabile, regole prima della mappa; i capitoli (fuori dal prefisso) si modificano liberamente |
| progetti nuovi ed esistenti | `init` per lo scaffold, `migrate` non distruttivo, `check` per la diagnosi |
| niente tool o estensioni | due script Python standard; l'adattatore per un agente è opzionale |

## Struttura

```
progressive-memory-management/
├── SKILL.md                     # istruzioni per l'agente
├── README.md                    # questo file
├── CHANGELOG.md · VERSION
├── scripts/
│   └── manage_memory.py         # init / migrate / check / auto / version
└── templates/                   # ciò che viene copiato nel progetto
    ├── AGENTS.md.tmpl                        # L0: regole + mappa
    ├── memoria/{README,00_STATO,97_CRONACA}.md
    ├── docs/ADR/{000-template,README}.md      # decisioni + indice derivato
    ├── scripts/{memoria_index,memoria_check}.py
    └── .pi/{skills,prompts,extensions}/…      # adattatori opzionali (--with-pi)
```

## CLI

```bash
python scripts/manage_memory.py <comando> "<cartella>" [opzioni]
```

| comando | effetto |
|---|---|
| `init <cartella>` | scheletro completo (progetto nuovo) |
| `migrate <cartella>` | aggiunge solo ciò che manca (progetto esistente, non distruttivo) |
| `check <cartella>` | diagnosi del pattern; esce **0** se completo e coerente |
| `version` | versione del pacchetto |
| `<cartella>` | **auto**: `init` se non c'è nulla, altrimenti `migrate` |

| opzione | effetto |
|---|---|
| `--with-pi` | aggiunge gli adattatori pi (`.pi/**`) |
| `--refresh-scripts` | `migrate`: riporta `scripts/memoria_{index,check}.py` alla versione del pacchetto |
| `--refresh-generated` | `migrate`: come sopra + i file generati del pattern (contratto della wiki, indice e template delle decisioni) |
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
python scripts/manage_memory.py init    "C:/percorsi/025" --with-pi
```

## Comandi utili (dentro il progetto)

```bash
python scripts/memoria_index.py          # rigenera mappa + indice delle decisioni
python scripts/memoria_index.py --check  # solo verifica dell'allineamento (esce 1 se vecchio)
python scripts/memoria_check.py          # invarianti I1-I11: deve uscire 0
python scripts/memoria_check.py -v       # elenca anche i controlli superati
python scripts/memoria_check.py --strict # anche gli avvisi fanno fallire
python scripts/memoria_check.py --hash   # impronta di L0: confrontala fra sessioni
```

## Uso con agenti diversi

- `AGENTS.md`, `<memoria>/`, `docs/ADR/` e i due script Python sono **agent-agnostici**.
- **pi**: la skill sta nella cartella delle skill dell'utente; gli adattatori si aggiungono con
  `--with-pi` e richiedono il **project trust**.
- **Claude Code / altri**: copia o collega la skill dove l'agente cerca le sue capacità e adatta
  il nome del file L0 alla convenzione attesa (`CLAUDE.md`, `.cursor/rules`, …). Lo scheletro
  generato di default non contiene nulla di specifico.
- **Senza agente**: gli script sono autonomi (Python 3.10+; usa `tiktoken` se presente,
  altrimenti stima i token).
- Ciò che vale per un solo progetto — una procedura, una regola locale — vive **nel progetto**
  (es. `.pi/skills/`), non fra le capacità globali dell'agente: così la sua descrizione non
  entra nel prefisso di tutti gli altri progetti.
- **Sottocartelle autonome**: se un sottosistema ha regole proprie, mettile in un file di
  contesto *locale* (pi: `AGENTS.md` o `AGENTS.override.md` nella sottocartella; Claude Code:
  `CLAUDE.md`; Cursor: `.cursor/rules`): varrà quando si lavora lì dentro, senza gonfiare il
  file di radice.

Gli adattatori cambiano da agente ad agente; il pattern no — L0, la cartella della memoria, gli
indici derivati, gli invarianti e i due script restano gli stessi file:

| pezzo del pattern | pi | equivalenti altrove (esempi) |
|---|---|---|
| L0: regole + mappa | `AGENTS.md` | `CLAUDE.md`, `.cursor/rules/*.mdc`, … |
| procedura on demand | `.pi/skills/*/SKILL.md` | skill o regole dell'agente |
| scorciatoia utente | `.pi/prompts/*.md` (es. `/mem`) | comandi slash dell'agente |
| avviso automatico | `.pi/extensions/*.ts` (guardia) | hook equivalenti (avvio sessione, fine turno) |

## Il pacchetto

Il ciclo di vita è in `CHANGELOG.md`; la versione in `VERSION`. Ogni progetto dichiara la
versione del pattern in due punti che stanno **fuori** da L0 (`<memoria>/README.md` e
`SCRIPT_PATTERN` dentro gli script generati): `check` le confronta con l'installazione e dice
cosa è vecchio. Le **regole** in `AGENTS.md` non vengono mai riscritte d'ufficio (potrebbero
essere state adattate al progetto): la diagnosi lo segnala e l'agente le unisce a mano. Gli
**script** generati si riportano alla versione corrente con `migrate --refresh-scripts`; con
`--refresh-generated` si riportano anche i file generati del pattern (contratto della wiki,
indice e template delle decisioni). Mai L0, `00_STATO.md`, `97_CRONACA.md`, capitoli e ADR.
