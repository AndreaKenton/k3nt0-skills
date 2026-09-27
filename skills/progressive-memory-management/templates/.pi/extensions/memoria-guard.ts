/**
 * Memoria Guard — guardia di coerenza per la memoria stratificata del progetto.
 *
 * Fa due cose, entrambe non invasive:
 *
 * 1. `session_start`: lancia `scripts/memoria_check.py` e notifica l'esito.
 *    Se la memoria e' incoerente (link rotti, indici disallineati, frontmatter
 *    mancante, token fuori soglia) l'agente lo sa subito, a costo zero di
 *    contesto: il check gira in un processo separato e non entra nel prompt.
 *
 * 2. `turn_end`: se durante il turno sono stati modificati file sotto `memoria/`
 *    o `docs/ADR/` ma NON `memoria/00_STATO.md`, avvisa una volta per sessione
 *    che lo stato probabilmente va aggiornato.
 *
 * Non inietta nulla nel system prompt e non riscrive nessun payload: la prompt
 * cache resta intatta. I marker di attivazione sono la presenza della cartella
 * `memoria/` e di `scripts/memoria_check.py`.
 *
 * Uso: copiare in `.pi/extensions/` del progetto (richiede project trust).
 */

import * as fs from "node:fs";
import * as path from "node:path";
import { spawnSync } from "node:child_process";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const MEM_DIR = "{{MEMDIR}}";
const CHECK_SCRIPT = path.join("scripts", "memoria_check.py");
const INDEX_SCRIPT = path.join("scripts", "memoria_index.py");
const STATE_FILE = path.join("{{MEMDIR}}", "00_STATO.md");
const WATCHED = ["{{MEMDIR}}", path.join("docs", "ADR")];

function newestMtime(dir: string, skip?: string): number {
	let newest = 0;
	let entries: fs.Dirent[];
	try {
		entries = fs.readdirSync(dir, { withFileTypes: true });
	} catch {
		return 0;
	}
	for (const e of entries) {
		const full = path.join(dir, e.name);
		if (e.isDirectory()) {
			newest = Math.max(newest, newestMtime(full, skip));
		} else if (e.isFile() && e.name.endsWith(".md")) {
			if (skip && path.resolve(full) === path.resolve(skip)) continue;
			try {
				newest = Math.max(newest, fs.statSync(full).mtimeMs);
			} catch {
				/* ignora */
			}
		}
	}
	return newest;
}

function findPython(cwd: string): string {
	const venv = process.platform === "win32"
		? path.join(cwd, ".venv", "Scripts", "python.exe")
		: path.join(cwd, ".venv", "bin", "python");
	return fs.existsSync(venv) ? venv : "python";
}

export default function memoriaGuard(pi: ExtensionAPI) {
	let memoriaPresent = false;
	let warnedThisSession = false;
	let lastCheckTurn = -99;

	pi.on("session_start", async (_event, ctx) => {
		memoriaPresent = fs.existsSync(path.join(ctx.cwd, MEM_DIR));
		warnedThisSession = false;
		lastCheckTurn = -99;

		if (!memoriaPresent || !fs.existsSync(path.join(ctx.cwd, CHECK_SCRIPT))) {
			return;
		}

		const res = spawnSync(findPython(ctx.cwd), [CHECK_SCRIPT], {
			cwd: ctx.cwd,
			encoding: "utf8",
		});

		if (res.error) {
			ctx.ui.notify(`memoria-guard: impossibile eseguire ${CHECK_SCRIPT}`, "warning");
			return;
		}

		const out = `${res.stdout ?? ""}${res.stderr ?? ""}`.trim();

		if (res.status === 0) {
			const last = out.split("\n").filter(Boolean).pop() ?? "nessun errore";
			ctx.ui.notify(`Memoria coerente — ${last}`, "info");
		} else {
			const errors = out
				.split("\n")
				.filter((l) => l.includes("ERR"))
				.slice(0, 5)
				.join(" | ");
			ctx.ui.notify(`Memoria INCOERENTE — ${errors || (out.split("\n").pop() ?? "")}`, "error");
		}
	});

	pi.on("turn_end", async (event, ctx) => {
		if (!memoriaPresent || warnedThisSession) return;
		// Non ripetere il check a ogni turno: solo ogni 4 turni.
		if (event.turnIndex - lastCheckTurn < 4) return;
		lastCheckTurn = event.turnIndex;

		const statePath = path.join(ctx.cwd, STATE_FILE);
		const stateMtime = fs.existsSync(statePath) ? fs.statSync(statePath).mtimeMs : 0;

		let touched = 0;
		for (const rel of WATCHED) {
			const full = path.join(ctx.cwd, rel);
			const newest = rel === MEM_DIR ? newestMtime(full, statePath) : newestMtime(full);
			if (newest > stateMtime) touched++;
		}

		if (touched > 0) {
			warnedThisSession = true;
			ctx.ui.notify(
				`memoria-guard: capitoli modificati ma ${STATE_FILE} no — aggiorna lo stato, ` +
					`poi \`python ${INDEX_SCRIPT}\` e \`python ${CHECK_SCRIPT}\` (devono uscire 0)`,
				"warning",
			);
		}
	});
}
