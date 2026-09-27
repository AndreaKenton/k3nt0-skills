---
name: progressive-memory-management
description: Gestione della memoria di progetto a livelli (L0-L3, progressive disclosure) per agenti e modelli generici — init di un nuovo progetto (AGENTS.md con indice derivato, memoria/, ADR, script di verifica) o migrazione non distruttiva di uno esistente. Usa quando crei un nuovo progetto o converti/riorganizzi la memoria di uno esistente.
---

# Progressive Memory Management (memoria di progetto L0-L3)

Skill **agnostica**: nessuna dipendenza da un agente o da un modello specifico. È composta da
istruzioni (`SKILL.md`), uno script Python e template. Lo script vive in `scripts/` e trova i
template in `../templates` (percorsi relativi alla skill), quindi la cartella si può copiare
ovunque.

## Quando usarla

- **All'inizio di un nuovo progetto**: esegui `init` appena crei la cartella, prima di
  scrivere codice (la memoria nasce insieme al progetto).
- **Su un progetto esistente senza il pattern**: esegui `migrate`.
- **Per diagnosi**: `check` dice se il pattern è presente e coerente.

## CLI (riferimento)

Dalla cartella di questa skill:

```bash
python scripts/manage_memory.py <comando> "<cartella>" [opzioni]
```

(se non sei nella cartella della skill, usa il percorso completo: `<skill-dir>/scripts/manage_memory.py`)

| comando | cosa fa |
|---|---|
| `init <cartella>` | crea lo scheletro completo di un progetto nuovo |
| `migrate <cartella>` | aggiunge **solo** ciò che manca a un progetto esistente (non distruttivo) |
| `check <cartella>` | diagnosi; esce **0** se il pattern è completo e coerente |
| `<cartella>` (senza comando) | **auto**: `init` se non c'è nulla, altrimenti `migrate` |

| opzione | effetto |
|---|---|
| `--core-only` | salta gli extra `.pi/**`: crea solo la parte **agent-agnostica** (`AGENTS.md`, `memoria/`, `docs/ADR/`, script) |
| `--dry-run` | mostra i file che creerebbe, senza scrivere (`init`/`migrate`) |
| `--nome <nome>` | nome logico se la cartella non è `<NNN>_<nome>` |
| `-h`, `--help` | stampa l'aiuto |

Esempi:

```bash
# nuovo progetto
python scripts/manage_memory.py init "C:/percorsi/022_nome_progetto"

# migrazione di un esistente (non distruttiva)
python scripts/manage_memory.py migrate "C:/percorsi/019_progetto_esistente"

# diagnosi (0 = pattern completo e coerente)
python scripts/manage_memory.py check "C:/percorsi/021_progetto"

# auto + anteprima + scheletro solo agnostico (senza extra di pi)
python scripts/manage_memory.py "C:/percorsi/023_nome" --dry-run
python scripts/manage_memory.py init "C:/percorsi/024" --core-only
```

## Cosa genera

| File | Ruolo | Agnostico? |
|---|---|---|
| `AGENTS.md` | L0: regole + indice generato (byte-stabile) | sì |
| `memoria/00_STATO.md`, `97_CRONACA.md` | L2 stato durevole, L3 cronologia | sì |
| `memoria/README.md` | come è organizzata la memoria (non indicizzato) | sì |
| `docs/ADR/000-template.md` | modello per le decisioni | sì |
| `scripts/memoria_index.py` | rigenera l'indice dentro `AGENTS.md` | sì |
| `scripts/memoria_check.py` | coerenza + budget (deve uscire **0**) | sì |
| `.pi/skills/<slug>-memoria/SKILL.md` | procedura di progetto | **extra** (pi) |
| `.pi/prompts/{mem.md,nuovo-adr.md}` | scorciatoie `/mem`, `/nuovo-adr` | **extra** (pi) |
| `.pi/extensions/memoria-guard.ts` | controllo automatico | **extra** (pi) |

Con `--core-only` gli extra `.pi/**` non vengono creati. Su un altro agente, sostituisci
`AGENTS.md`/gli extra con la convenzione equivalente (es. `CLAUDE.md`, `.cursor/rules`, …):
la sostanza (regole + indice + capitoli on demand) non cambia.

## `migrate`: cosa fa e cosa non fa

È **non distruttivo**: non sovrascrive mai un file esistente. In `migrate`:

- se l'`AGENTS.md` esiste ma non ha i marcatori, **li inserisce** (sotto un titolo `Indice`, o
  in coda) e aggiunge un rimando alla skill di progetto (solo senza `--core-only`);
- rileva la cartella memoria esistente (`memoria/` **o** `manuale/`) e lavora su quella, senza
  crearne una seconda;
- ai capitoli **senza frontmatter** aggiunge un segnaposto `leggi_quando`/`parole_chiave`
  (`DA COMPILARE`): il contenuto va poi compilato dall'agente/utente;
- crea solo gli script/skill/prompt che mancano.

Poi esegue `memoria_index.py`. Il contenuto (cosa scrivere nei capitoli, come rinominare le
cartelle) resta lavoro dell'agente.

## Dopo l'esecuzione

1. Se usi pi: gli extra `.pi/**` sono risorse protette e richiedono il **project trust**.
2. Compila i capitoli segnaposto (cerca `DA COMPILARE`).
3. `python scripts/memoria_check.py` deve uscire **0**.
