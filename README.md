# agent-workflow

A Claude Code skill that sets up, audits, and upgrades a **two-agent development workflow** for any project:

- **Head** (planner): keeps direction, triages reports, decides, designs, writes tasks, and verifies. Usually your strongest model.
- **Executor** (implementer): implements, measures, runs long jobs, and writes reports. Often a cheaper model or a local LLM.

The two roles talk through files in the repo (`handoff/tasks`, `handoff/reports`, `NOTES`, `ROADMAP`), and the protocol is tuned to the **capacity of the executor model** instead of one size for all. The skill writes real files into your project (role instructions, protocol, roadmap, checks), not generic advice.

> The skill text is written in **Indonesian**; file, script, and option names are English. Files it generates follow the language you use with the agent. Rule tags and tool keywords keep the bundled scripts working in any language (see [Language](#language)).

## Why

Every rule comes from a failure seen in real projects, recorded in the skill's *Pelajaran* (lessons) section. For example:

- A head that only reacts to the latest report digs into one anomaly forever: about 30 of 42 tasks in one firmware project were re-measurements.
- Reports said "passed" with evidence that did not match the saved logs. Rules alone did not stop it; scripts now check every quote and status.
- A cheap executor was promoted, then failed its first harder task twice. Promotion now needs evidence in the target format plus a probation period.
- UI tasks passed their tests while the screens were wrong (buttons too small, tabs off-screen). Visual criteria are now checked from screenshots.
- A second session re-ran a finished task and overwrote the first session's evidence logs. Executors now stop on tasks that are not `OPEN`, and the log wrapper refuses to overwrite logs of finished tasks.
- A trial of launching executors through [Orca](https://github.com/stablyai/orca) looked successful, but Orca's "Full access" setting had started the executor with `--dangerously-skip-permissions`, and a standby Claude Code terminal sat at the bypass-mode consent dialog. The head now checks the launcher's permission setting and reads the model from the launch receipt, not from the request.

## What it does

| Mode | When | Result |
|---|---|---|
| BOOTSTRAP | Project has no head/executor protocol | Head + executor instructions, `handoff/` folder, verified initial ROADMAP, file-structure map, first SMOKE task |
| AUDIT | Existing agent setup feels rigid, the project stalls, tools or models changed, or the protocol is older than the skill | Evidence-based diagnosis, then (after approval) minimal patches. Includes an **upgrade path** driven by version markers |
| LITE | Small project, one tool, no request for two agents | One `<prefix>-dev` skill + ROADMAP + NOTES |
| STRUKTUR | You only want the project's file structure checked | Structure map with findings labelled required / standard / taste |

Executor capacity has three levels (TINGGI/SEDANG/RENDAH, i.e. high/medium/low). Each level changes how tasks are written, how much design freedom the executor gets, and how deeply the head verifies. A new model can be placed with a 15-minute **calibration test** scored by a script.

Capacity is tracked **per model**, so one project can use several executor models across tools (for example Gemini Flash in Antigravity for routine work, Claude in Claude Code for harder tasks). The head picks the model for each task: the cheapest one whose capacity is enough, following the user's preference order, and writes the reason in the task. With **Orca**, the head also launches that model itself (`orca orchestration worker-start`), waits for `worker_done`, and still triages the report from files; see `references/orca.md`. Tool-permission prompts and usage-limit dialogs only show in the worker terminal, so the head reads it between waits, and Claude workers run under the head session's own Claude account.

### Bundled scripts

| Script | Copied into the project | Purpose |
|---|---|---|
| `record.py` | yes (`handoff/tools/`) | Runs a command, saves its output byte-for-byte as an evidence log, and records provenance (command, exit code, SHA-256) in `handoff/logs/provenance.jsonl`. `--result` registers files the command wrote (glob patterns allowed); logs of finished tasks are not overwritten without `--overwrite`. |
| `check_evidence.py` | yes | Checks a report against its evidence: every `file:line` quote, every OK against its expected value, log provenance, and that each acceptance criterion has a row. `--at <commit>` / `--at-report` check old reports against the files as they were. Reads Indonesian or English reports. |
| `check_secrets.py` | yes, if the project has local secret files | Finds secrets in files before commit by pattern and by the actual values from your local secret files, without printing them. `--staged`, `--redact`. |
| `screenshot.py` | yes, if the project has a web UI | Screenshots a page at target screen sizes using real device emulation through the Chrome DevTools Protocol, and reports the page width and any element that sticks out of the screen (exit 1 if so). `--offline` blocks every host except localhost. |
| `check_version.py` | no (run from the skill folder) | Compares the project's protocol with the changelog markers, reports the effective version and the patches still missing. |
| `calibrate.py` | no | Builds and scores the calibration test for a new executor model. |

All scripts use only the Python standard library. `screenshot.py` also needs Chrome, Chromium, or Edge.

> Why not `chrome --headless --window-size=375,812 --screenshot`? Desktop Chrome lays the page out at least ~500 px wide even when the window is narrower, then crops the picture. Buttons look cut off on "phone width" when they actually fit, or the other way round. This skill shipped that mistake once (see changelog v3.10.1).

## Install

Requirements: Python 3.9+ and git; Chrome, Chromium, or Edge for UI screenshots.

**As a Claude Code plugin** (this repo is a plugin marketplace):

```
/plugin marketplace add brahamrenatus-ai/agent-workflow
/plugin install agent-workflow@agent-workflow
```

Then ask in plain words ("set up a head/executor workflow for this project", "audit my agent setup") or run `/agent-workflow:agent-workflow`.

**As a plain skill:** copy `plugins/agent-workflow/skills/agent-workflow/` to `~/.claude/skills/agent-workflow/` (all projects) or `<project>/.claude/skills/agent-workflow/` (one project). Invoke with `/agent-workflow`.

**Other agent tools** (Antigravity, Cline, Codex, Gemini CLI, …): give the tool `SKILL.md` together with the `references/` and `scripts/` folders.

## Language

The skill is written in Indonesian, with English file, script, and option names (since v3.12; the scripts still accept the older Indonesian names). Generated files follow your language. Two mechanisms keep the scripts language-independent:

- **Rule tags.** Every rule in the templates carries an HTML comment such as `<!-- aw: Z1 -->`. Tags are copied with the rule, invisible when rendered, and `check_version.py` recognises rules by their tag, so a protocol written in any language can still be upgraded.
- **Tool keywords.** Words the scripts parse (report headings, Data table columns, statuses) are written either in Indonesian or English, e.g. `Self-check`, `Expected`/`Observed`/`Evidence`, `PASS`/`FAIL`/`NOT TESTED`. The full table is in `references/templates.md` (*Kata kunci alat*).

## Versioning and upgrades

The skill version is in `SKILL.md` and `references/changelog.md`. Each version lists the rules it adds to projects, with target file, patch method, and a marker. A generated `handoff/README.md` records the skill version it was built with. To upgrade a project, run the skill in AUDIT mode: it runs `check_version.py`, patches only the missing rules, keeps your own rules and local script patches, and asks before committing.

## Development

```
python tests/run_tests.py
```

This runs a structure check (frontmatter, version consistency, every changelog marker present in the templates and tagged in every template variant, LF line endings) and functional tests of every script in temporary projects. CI runs the same on Linux, Windows, and macOS. Tests that need Chrome or Orca are skipped when those are not installed; `test_orca_cli.py` checks every `orca` command and option written in the skill against the installed Orca's `--help`.

When adding a rule that ends up in project files: add a row to the version's table in `references/changelog.md`, a marker in the `penanda` block, the rule text in every template variant that produces the target file, and the `<!-- aw: ID -->` tag on that line. Bump the version in `SKILL.md`, the changelog, and `plugins/agent-workflow/.claude-plugin/plugin.json` together.

## Bahasa Indonesia

Skill ini memasang, mengaudit, dan meng-upgrade alur kerja dua agen, yaitu head (perencana) dan executor (pelaksana), untuk project apa pun. Protokolnya disetel ke kapasitas model executor. Isi skill berbahasa Indonesia; file yang dibuat untuk project mengikuti bahasa user. Pasang lewat `/plugin marketplace add brahamrenatus-ai/agent-workflow` lalu `/plugin install agent-workflow@agent-workflow`, atau salin `plugins/agent-workflow/skills/agent-workflow/` ke `~/.claude/skills/agent-workflow/`. Mulai dari `SKILL.md`; riwayat versi ada di `references/changelog.md`.

## License

[MIT](LICENSE)
