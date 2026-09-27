# k3nt0-skills

Skill **agnostiche** per agenti di coding e modelli generici, nel formato
[Agent Skills](https://agentskills.io/specification): ogni skill è una cartella con un
`SKILL.md` (frontmatter `name` + `description`, poi le istruzioni) e, se serve, `scripts/` e
asset. Nessuna dipendenza da un agente o da un modello specifico.

## Skill incluse

| Skill | Cosa fa |
|---|---|
| [`progressive-memory-management`](skills/progressive-memory-management/) | Gestione della memoria di progetto a livelli **L0-L3** (progressive disclosure): `init` di un nuovo progetto o `migrate` non distruttiva di uno esistente, con `AGENTS.md`, capitoli `memoria/`, ADR e script di verifica. |

## Come si usa con qualsiasi agente

Il formato è quello portabile **Agent Skills**. Metti la cartella della skill dove il tuo
agente cerca le skill, oppure invoca lo script direttamente.

| Agente / contesto | Come |
|---|---|
| pi | `pi install git:github.com/AndreaKenton/k3nt0-skills` (pi scopre la cartella convenzionale `skills/`), oppure copia la skill in `~/.pi/agent/skills/` |
| Claude Code / altri | copia/collega la skill nella cartella skills del tuo agente |
| Qualsiasi | `python skills/<nome>/scripts/…` direttamente; i template sono in `skills/<nome>/templates/` |

Esempio (skill `progressive-memory-management`):

```bash
python skills/progressive-memory-management/scripts/manage_memory.py init    "<cartella>"
python skills/progressive-memory-management/scripts/manage_memory.py migrate "<cartella>"
python skills/progressive-memory-management/scripts/manage_memory.py check   "<cartella>"
```

Dettagli in [`skills/progressive-memory-management/README.md`](skills/progressive-memory-management/README.md).

## Scaricare una sola skill (senza il resto del repo)

Ogni skill è **autocontenuta**: puoi prenderne solo la cartella.

- **Release (un click)**: dalla pagina [Releases](../../releases) scarica
  `<nome-skill>.zip`. Gli archivi sono generati automaticamente a ogni tag
  (`.github/workflows/release-skills.yml`).
- **Sparse checkout** (git, solo quella cartella):

  ```bash
  git clone --filter=blob:none --sparse https://github.com/AndreaKenton/k3nt0-skills
  cd k3nt0-skills
  git sparse-checkout set skills/progressive-memory-management
  ```

- **Dallo ZIP del repo**: scarica il repo e copia `skills/<nome-skill>/`.

## Struttura

```
k3nt0-skills/
├── README.md
├── LICENSE
└── skills/
    └── progressive-memory-management/
        ├── SKILL.md
        ├── README.md
        ├── scripts/manage_memory.py
        └── templates/
```

## Aggiungere una nuova skill

1. Crea `skills/<nome>/SKILL.md` con frontmatter `name` + `description` (la `description` è
   ciò che l'agente mostra per instradare la skill).
2. Aggiungi eventuali `scripts/` e asset accanto a `SKILL.md`.
3. Aggiungi una riga nella tabella qui sopra.
4. Commit e push.

## Licenza

[MIT](LICENSE).
