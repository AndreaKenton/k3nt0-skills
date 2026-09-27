---
name: progressive-memory-management
description: Memoria di progetto a livelli (L0-L3) come wiki autoconsistente: scaffold, retrofit non distruttivo di un progetto esistente, diagnosi della coerenza, indici derivati e prefisso stabile per la prompt cache. Agnostica rispetto ad agente e modello, senza strumenti né estensioni. Usa quando crei un progetto, quando la sua memoria cresce o va riorganizzata, o quando risulta disallineata.
---

# Progressive Memory Management (memoria di progetto L0-L3)

Skill **agnostica** rispetto ad agente e modello e **senza dipendenze**: nessuna estensione,
nessun tool, nessun servizio. È un pattern di buone pratiche più due script Python (`init`/
`migrate`/`check` e gli indici derivati) che li applicano. I template stanno in `../templates`,
gli script in `scripts/`: la cartella si copia ovunque.

La memoria di progetto è una **wiki autoconsistente**: l'agente la interroga in modo mirato e la
mantiene mentre lavora; gli indici sono derivati dai file, quindi la gerarchia non può andare
fuori sincrono senza che la verifica lo dica.

## Quando usarla

| situazione | comando |
|---|---|
| **Nuovo progetto**: appena crei la cartella, prima di scrivere codice | `init` |
| **Progetto esistente**: la memoria è un file unico, un diario, o non esiste | `migrate` |
| **La memoria è cresciuta** (monolite, capitoli oltre soglia) | `migrate`, poi spezza |
| **Diagnosi** (cosa manca, cosa è disallineato) | `check` |
| La **memoria è disallineata** (indice vecchio, link rotti, duplicati) | `check` → ripara |

## CLI

Dalla cartella di questa skill:

```bash
python scripts/manage_memory.py <comando> "<cartella>" [opzioni]
```

| comando | cosa fa |
|---|---|
| `init <cartella>` | scheletro completo (progetto nuovo) |
| `migrate <cartella>` | aggiunge **solo** ciò che manca (non distruttivo: non sovrascrive mai) |
| `check <cartella>` | diagnosi del pattern; esce **0** se è completo e coerente |
| `version` | versione del pacchetto |
| `<cartella>` | **auto**: `init` se non c'è nulla, altrimenti `migrate` |

| opzione | effetto |
|---|---|
| `--with-pi` | aggiunge gli adattatori per pi (`.pi/skills`, `.pi/prompts`, `.pi/extensions`) |
| `--refresh-scripts` | `migrate`: riporta `scripts/memoria_{index,check}.py` alla versione del pacchetto |
| `--refresh-generated` | `migrate`: come sopra + i file generati del pattern (contratto della wiki, indice e template delle decisioni) |
| `--dry-run` | anteprima: mostra i file senza scriverli (`init`/`migrate`) |
| `--nome <nome>` | nome logico se la cartella non è `<NNN>_<nome>` |
| `-h`, `--help` | aiuto |

```bash
# nuovo progetto (scheletro agent-agnostico: AGENTS.md, <memoria>/, docs/ADR/, scripts/)
python scripts/manage_memory.py init "C:/percorsi/022_nome_progetto"

# retrofit non distruttivo di un progetto esistente
python scripts/manage_memory.py migrate "C:/percorsi/019_progetto_esistente"

# diagnosi (0 = pattern completo e coerente)
python scripts/manage_memory.py check "C:/percorsi/021_progetto"

# anteprima · con adattatori pi
python scripts/manage_memory.py "C:/percorsi/023_nome" --dry-run
python scripts/manage_memory.py init "C:/percorsi/024" --with-pi
```

## Cosa genera

| File | Ruolo | Agnostico? |
|---|---|---|
| `AGENTS.md` | L0: regole (stabili) + mappa della memoria (derivata, in coda) | sì |
| `<memoria>/README.md` | il contratto della wiki: livelli, invarianti, manutenzione | sì |
| `<memoria>/00_STATO.md`, `97_CRONACA.md` | L2 stato durevole (letto a ogni sessione), L3 cronologia | sì |
| `docs/ADR/000-template.md`, `docs/ADR/README.md` | schede delle decisioni + indice derivato | sì |
| `scripts/memoria_index.py` | rigenera la mappa in `AGENTS.md` e l'indice delle decisioni | sì |
| `scripts/memoria_check.py` | verifica gli invarianti (I1–I11): deve uscire **0** | sì |
| `.pi/skills/<slug>-memoria/`, `.pi/prompts/`, `.pi/extensions/` | adattatori per pi, **opzionali** | **no** (`--with-pi`) |

Su un altro agente sostituisci `AGENTS.md` con la convenzione equivalente (`CLAUDE.md`,
`.cursor/rules`, …): la sostanza — regole stabili + mappa derivata + capitoli on demand — non
cambia.

## Perché si mantiene da sola

Quattro proprietà, tutte senza tooling:

1. **Gli indici sono derivati**, mai scritti a mano: `memoria_index.py` li ricava dal frontmatter
   dei capitoli e dal frontmatter delle decisioni. Non possono divergere dai file: o sono
   allineati, o la verifica lo dice.
2. **La verifica è un cancello**: `memoria_check.py` esce non-zero su indice vecchio, capitolo
   orfano, link rotto, frontmatter mancante, titolo o paragrafo duplicato, capitolo oltre
   soglia, L0 non stabile. La regola in L0 è: *non chiudere il task*.
3. **Il contratto sta nel progetto**: `<memoria>/README.md` dichiara livelli, invarianti e il
   ciclo LEGGI → SCRIVI → VERIFICA → RIPARA, quindi vale anche senza questa skill (che serve
   solo a creare e diagnosticare).
4. **Il prefisso è stabile**: L0 è byte-stabile fra sessioni e fra i task della stessa sessione
   (niente date, contatori, stime di token), le regole stanno **prima** della mappa e i capitoli
   — che si possono modificare quanto serve — non sono nel prefisso. Così la cache resta valida
   e i token riletti da cache costano molto meno degli input token nuovi (indicativamente
   10–30× meno, secondo il provider).

## Organizzare la memoria (spazio e tempo)

- **Sottocartella autonoma** → le sue regole in un file di contesto *locale*, non nella radice
  (pi: `AGENTS.md`/`AGENTS.override.md`; Claude Code: `CLAUDE.md`; Cursor: `.cursor/rules`).
- **Capacità mono-progetto** → nel progetto, non fra le capacità globali dell'agente; nell'indice
  globale restano le regole trasversali.
- **Esplorazione ampia** → in un contesto isolato che riporta solo un riassunto (su pi:
  sub-agente di sola lettura), non nel contesto principale.
- **Tempo**: `00_STATO.md` sopravvive ai riassunti del contesto, la chat no; gli archivi si
  citano, non si scandiscono; le descrizioni delle capacità si cambiano **in blocco** perché
  stanno nel prefisso in cache.

## Dove nasce una regola (per chi mantiene questo pacchetto)

| la regola… | va in |
|---|---|
| deve valere **dentro** i progetti (presenti e futuri) | `templates/**` |
| riguarda come **costruire/diagnosticare** il pattern | `SKILL.md`, `README.md` |
| deve essere **verificabile** | `templates/scripts/memoria_check.py` |
| è specifica di **un agente o di un modello** | fuori dal pacchetto (adattatore, es. `--with-pi`) |

Una regola scritta in due posti è una regola che divergerà: è il modo in cui una skill di
memoria invecchia.

## `migrate`: cosa fa e cosa non fa

Non sovrascrive **mai** un file esistente. In `migrate`:

- se `AGENTS.md` esiste ma non ha i marcatori della mappa, **li inserisce** (sotto un titolo
  «Mappa della memoria», o in coda);
- riconosce la cartella memoria esistente (`memoria/` **o** `manuale/`) e lavora su quella,
  senza crearne una seconda;
- aggiunge il rimando agli strumenti (indici, verifica, decisioni) **prima** della mappa;
- ai capitoli senza frontmatter aggiunge un segnaposto `leggi_quando`/`parole_chiave`
  (`DA COMPILARE`);
- crea solo script, template ADR e indice delle decisioni che mancano;
- poi esegue `memoria_index.py`.

Non fa: **non** aggiorna il testo delle regole di un `AGENTS.md` già scritto (le regole di una
versione nuova vanno unite a mano) e non riorganizza i contenuti. Il contenuto è lavoro
dell'agente: `check` dice cosa manca e cosa è disallineato.

## Dopo l'esecuzione

1. Compila i capitoli segnaposto (cerca `DA COMPILARE`).
2. `python scripts/memoria_check.py` deve uscire **0**.
3. Con `--with-pi`: apri l'agente nel progetto e concedi il **project trust** (serve per
   `.pi/**`).

## Versioning

`VERSION` contiene la versione del pacchetto; i progetti la annotano in `<memoria>/README.md`
e gli script generati la dichiarano in `SCRIPT_PATTERN`. `check` confronta le tre cose e dice,
per ogni progetto:

- versione del pattern annotata e versione del blocco regole in L0 → se sono vecchie, le regole
  vanno **unite a mano** (mai riscritte d'ufficio: potrebbero essere state adattate);
- versione degli script generati → `migrate --refresh-scripts` li riporta alla versione
  corrente (opt-in: sovrascrive quei due file e nient'altro);
- versione del **contratto della wiki** (`<memoria>/README.md`) → `migrate --refresh-generated`
  riporta script e file generati del pattern alla versione corrente. In nessun caso vengono
  toccati L0, `00_STATO.md`, `97_CRONACA.md`, i capitoli e le schede ADR.

Vedi `CHANGELOG.md`.
