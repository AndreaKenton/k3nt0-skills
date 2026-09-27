# agent-prefix-hygiene

**Igiene del prefisso dell'agente.** Le regole per tenere piccolo, stabile e coerente ciò che
l'agente vede a ogni sessione — il file di contesto (regole + indice) e le `description` delle
capacità on demand — più uno script che le verifica su percorsi arbitrari.

- **Agnostico**: `prefix_check.py` non sa nulla di un agente in particolare; gli si dicono i file
  sempre caricati (`--l0`) e le cartelle delle capacità (`--capabilities`).
- **Senza dipendenze**: Python 3.10+ (usa `tiktoken` se presente, altrimenti stima i token).
- **Verificabile**: budget, stabilità, lunghezza delle description, mappa dichiarata/trovata,
  ordine regole→mappa derivata.

## Perché

Ogni agente ha due superfici sempre presenti: un **file di contesto** e le **description** del suo
catalogo di capacità. Il resto si carica on demand. Quelle due superfici:

- costano a **ogni** richiesta: i token riletti da cache costano molto meno degli input token
  nuovi (indicativamente 10–30× meno, secondo il provider), quindi conviene tenerle ferme;
- cambiano la **cache di tutte le sessioni** quando cambiano di un byte: una data, un contatore o
  una stima di token dentro il file sempre caricato invalidano il prefisso;
- sono la **mappa** con cui l'agente decide cosa caricare: una capacità non dichiarata è
  invisibile, un nome dichiarato senza file è un riferimento morto.

## Regole (riassunto)

1. Nel file sempre caricato solo regole e indice: niente procedure, cronaca, date, contatori o
   stime di token; entro il budget (indicativamente 1.000 token).
2. Le procedure stanno nelle capacità on demand; la `description` (80–400 caratteri) è l'unica
   parte sempre in contesto, il corpo si carica quando serve.
3. La mappa è **derivata** dai file e verificata, non scritta a mano.
4. Le `description` si cambiano **in blocco**: una alla volta invalida la cache di tutte le sessioni.
5. Una capacità di un solo progetto sta nel progetto, non fra quelle globali.
6. Esplorazione ampia in un **contesto isolato** che riporta solo un riassunto.
7. Sottocartelle autonome → file di contesto **locale** nella sottocartella.
8. Lo stato durevole sta nei **file**, non nei riassunti del contesto.

## CLI

```bash
python scripts/prefix_check.py --l0 <file> [--l0 <altro>] \
    [--capabilities <cartella>] [--ignore <nome>] \
    [--budget 1000] [--desc-min 80] [--desc-max 400] \
    [--strict] [--hash] [-v]
```

| opzione | effetto |
|---|---|
| `--l0 <file>` | file caricato a ogni sessione (ripetibile; obbligatorio) |
| `--capabilities <cartella>` | cartella delle capacità on demand (ripetibile) |
| `--ignore <nome>` | capacità che non deve comparire nella mappa (invocata a mano) |
| `--budget` | token massimi per la **somma** dei file `--l0` (default 1000) |
| `--desc-min` / `--desc-max` | limiti della `description` in caratteri (default 80 / 400) |
| `--strict` | anche gli avvisi fanno fallire |
| `--hash` | impronta dei file `--l0`, da confrontare fra sessioni |

### Esempi

```bash
# pi (agente con file AGENTS.md e skill in .pi/skills)
python scripts/prefix_check.py --l0 ~/.pi/agent/AGENTS.md \
    --capabilities ~/.pi/agent/skills --budget 1000 \
    --ignore grilling --ignore grill-me --ignore skill-visibility --strict -v

# un progetto con più file di contesto (globale + progetto) e capacità locali
python scripts/prefix_check.py --l0 AGENTS.md --l0 ~/.claude/CLAUDE.md \
    --capabilities .pi/skills --budget 1400

# confronto dell'impronta fra due sessioni
python scripts/prefix_check.py --l0 AGENTS.md --hash
```

## Cosa verifica

| controllo | esito |
|---|---|
| data / orario / «oggi», «ieri» / stima di token nei file `--l0` | **errore** (rompe la cache) |
| somma dei file `--l0` oltre `--budget` | **errore** |
| capacità senza `name`/`description`; `description` oltre `--desc-max` | **errore** |
| mappa derivata prima delle regole | avviso |
| `description` sotto `--desc-min` (non instrada) | avviso |
| capacità presente ma non dichiarata nella mappa | avviso |
| nome dichiarato senza capacità corrispondente | avviso |

Gli avvisi diventano errori con `--strict`. In coda il costo: prefisso fisso (file +
description), contenuto on demand e confronto con una memoria monolitica.

## Con agenti diversi

| pezzo | pi | Claude Code | Cursor / altri |
|---|---|---|---|
| file sempre caricato | `AGENTS.md` | `CLAUDE.md` | `.cursor/rules/*.mdc` |
| capacità on demand | `.pi/skills/*/SKILL.md` | skill/comandi dell'agente | regole con glob |
| scorciatoie utente | `.pi/prompts/*.md` | comandi slash | — |
| verifica automatica | `.pi/extensions/*.ts` | hook | — |

La skill è autocontenuta: copia la cartella dove l'agente cerca le sue capacità, oppure invoca lo
script direttamente.

## Versioni

`VERSION` e `CHANGELOG.md` in questa cartella. Per la memoria *dentro un progetto* (livelli
L0-L3, indici derivati, `init`/`migrate`/`check`) vedi la skill `progressive-memory-management`.
