---
name: agent-prefix-hygiene
description: Igiene del prefisso dell'agente: cosa tenere nel file sempre in contesto, cosa mettere in una capacità on demand, stabilità delle description (prompt cache), capacità mono-progetto, esplorazione in contesto isolato, verifica di budget e coerenza con prefix_check.py. Usa quando aggiungi o riorganizzi regole, skill o comandi globali, cambi una description, o il prefisso cresce.
---

# Igiene del prefisso dell'agente

Vale per l'**installazione** dell'agente — il file che viene caricato a ogni sessione e il
catalogo delle sue capacità on demand — non per un singolo progetto: per la memoria *dentro un
progetto* c'è la skill `progressive-memory-management`.

Ogni agente ha due superfici sempre presenti: un **file di contesto** (regole + indice) e le
**description** delle capacità on demand. Tutto il resto si carica quando serve. Questa skill
tiene quelle due superfici piccole, stabili e coerenti.

## Regole

1. **Nel file sempre caricato solo regole e indice** — niente procedure, cronaca, date,
   contatori o stime di token: un byte diverso invalida la prompt cache di tutte le sessioni.
   Tienilo entro il budget (indicativamente 1.000 token) e mettilo sotto verifica.
2. **Le procedure stanno nelle capacità on demand** — la `description` è l'unica parte sempre in
   contesto: tra 80 e 400 caratteri (sotto non instrada, sopra pesa). Se una sezione del file
   sempre caricato spiega *come fare qualcosa*, il suo posto è una capacità, e nel file resta la
   riga che dice **quando** caricarla.
3. **La mappa è derivata, non scritta a mano** — l'indice delle capacità si genera dai file e si
   verifica: una capacità che esiste ma non è dichiarata è invisibile all'agente, una dichiarata
   che non esiste è un riferimento morto.
4. **Le description si cambiano in blocco** — cambiarne una cambia il prefisso e invalida la
   cache di tutte le sessioni. Le capacità che non devono auto-attivarsi si filtrano (allowlist /
   prefissi nascosti), non si cancellano.
5. **Una capacità di un solo progetto sta nel progetto** — così la sua description non entra nel
   prefisso di tutti gli altri progetti; globali restano le regole trasversali.
6. **Esplorazione ampia in un contesto isolato** — per capire un'area vasta non riempire il
   contesto principale: usa una sessione o un processo separato che riporti solo un riassunto
   (1-2k token invece di decine di migliaia).
7. **Sottocartelle autonome → contesto locale** — le regole di un sottosistema stanno nella sua
   cartella, in un file di contesto locale: valgono quando si lavora lì e non gonfiano la radice.
8. **Lo stato durevole sta nei file** — i riassunti del contesto (compaction) non sono memoria:
   ciò che deve sopravvivere a una sessione lunga va scritto in un file, non nella conversazione.

## Verifica

```bash
python scripts/prefix_check.py --l0 <file-sempre-caricato> \
    --capabilities <cartella-delle-capacità> --budget 1000
```

Esce **0** se: ogni file sempre caricato è stabile (nessun volatile) e il totale sta entro
budget; la mappa derivata, se c'è, sta **dopo** le regole; ogni capacità ha una description entro
i limiti; nessuna capacità orfana o dichiarata e assente. `--strict` trasforma gli avvisi in
errori; `--hash` stampa l'impronta dei file, da confrontare fra sessioni.

## Dove sta cosa, in ogni agente

| pezzo | pi | Claude Code | Cursor / altri |
|---|---|---|---|
| file sempre caricato | `AGENTS.md` | `CLAUDE.md` | `.cursor/rules/*.mdc` |
| capacità on demand | `.pi/skills/*/SKILL.md` | skill/comandi dell'agente | regole con glob |
| scorciatoie utente | `.pi/prompts/*.md` | comandi slash | — |
| verifica automatica | `.pi/extensions/*.ts` | hook | — |

Le regole non cambiano: cambia solo dove si mettono i file.
