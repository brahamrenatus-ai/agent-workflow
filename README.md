# agent-workflow

A Claude Code skill that sets up, audits, and upgrades a **two-agent development workflow** for any project:

- **Head** (planner): keeps direction, triages reports, decides, designs, writes tasks, and verifies. Usually your strongest model.
- **Executor** (implementer): implements, measures, runs long jobs, and writes reports. Often a cheaper model or a local LLM.

The two roles talk through files in the repo (`handoff/tasks`, `handoff/reports`, `NOTES`, `ROADMAP`), and the protocol is tuned to the **capacity of the executor model** instead of one size for all. The skill writes real files into your project (role instructions, protocol, roadmap, checks), not generic advice.

> The skill text is written in **Indonesian**; file, script, and option names, identifiers such as modes, task types, capacity levels, and statuses, and the words that open script results are English. Files it generates follow the language you use with the agent. Rule tags and tool keywords keep the bundled scripts working in any language (see [Language](#language)).

## Why

Every rule targets a failure that two-agent workflows tend to repeat; the skill's *Pelajaran* (lessons) section explains each one. For example:

- A head that only reacts to the latest report digs into one anomaly forever, and most tasks become re-measurements instead of fixes.
- Reports said "passed" with evidence that did not match the saved logs. Rules alone did not stop it; scripts now check every quote and status.
- A cheap executor was promoted, then failed its first harder task twice. Promotion now needs evidence in the target format plus a probation period.
- UI tasks passed their tests while the screens were wrong (buttons too small, tabs off-screen). Visual criteria are now checked from screenshots.
- A second session re-ran a finished task and overwrote the first session's evidence logs. Executors now stop on tasks that are not `OPEN`, and the log wrapper refuses to overwrite logs of finished tasks.
- A trial of launching executors through [Orca](https://github.com/stablyai/orca) looked successful, but Orca's "Full access" setting had started the executor with `--dangerously-skip-permissions`, and a standby Claude Code terminal sat at the bypass-mode consent dialog. The head now checks the launcher's permission setting and reads the model from the launch receipt, not from the request.
- A head waiting on an Orca worker was still woken by every worker heartbeat: its wait listened for some message types only, and Orca types a notice into the coordinator's terminal for every other type. Each wake re-read the head's whole context, and the head treated it as normal. The head now waits with a bundled script that acknowledges heartbeats itself, and records gaps like this in `handoff/SKILL-FEEDBACK.md` so they reach the next upgrade.
- Reports passed even though a test command had been run 8 times with 7 failures, and a test tool printed `20/20` but exited 1; both facts sat in the provenance log that nothing checked. The evidence checker now warns on both.
- Decisions handed over from a separate discussion or design session tend to be recorded as written, so line references that have moved and estimates written as facts reach the decision register. The head now checks each handed-over row like a report before recording it.
- Agents left notes about their own work in product files: test headers naming the role that wrote them, comments citing task numbers or the user's decision, design documents with session names and links, and a document-language line in the API contract of a team repo. Product files now carry technical content only, and a script checks the added lines before each commit.
- Having the head suggest `/clear` kept its context small, but the user then had to type it over and over. A head in an Orca terminal can now start its own fresh session when the user allows it. Testing the cancel path found that text the user was typing got sent along with `/clear`, so it was fixed before release.

## What it does

| Mode | When | Result |
|---|---|---|
| BOOTSTRAP | Project has no head/executor protocol | Head + executor instructions, `handoff/` folder, verified initial ROADMAP, file-structure map, first SMOKE task |
| AUDIT | Existing agent setup feels rigid, the project stalls, tools or models changed, or the protocol is older than the skill | Evidence-based diagnosis, then (after approval) minimal patches. Includes an **upgrade path** driven by version markers |
| LITE | Small project, one tool, no request for two agents | One `<prefix>-dev` skill + ROADMAP + NOTES |
| STRUCTURE | You only want the project's file structure checked | Structure map with findings labelled REQUIRED / STANDARD / PREFERENCE |

Executor capacity has three levels: HIGH, MEDIUM, and LOW. Each level changes how tasks are written, how much design freedom the executor gets, and how deeply the head verifies. A new model can be placed with a 15-minute **calibration test** scored by a script.

Capacity is tracked **per model**, so one project can use several executor models across tools (for example Gemini Flash in Antigravity for routine work, Claude in Claude Code for harder tasks). The head picks the model for each task: the cheapest one whose capacity is enough, following the user's preference order, and writes the reason in the task. With **Orca**, the head also launches that model itself (`orca orchestration worker-start`), waits for `worker_done`, and still triages the report from files; see `references/orca.md`. Tool-permission prompts and usage-limit dialogs only show in the worker terminal, so the head reads it between waits, and Claude workers run under the head session's own Claude account. While a worker runs, the head waits with `orca_wait.py` in the background instead of waking every few minutes (each wake re-reads its whole context), or keeps working in another part of the codebase.

**Side sessions** (optional, since v3.21) are separate sessions for discussion, Q&A, or design work with you, so long conversations do not fill the head's context. A side session writes no tasks and changes no code: it hands your decisions to the head in `handoff/<role>-handoff.md` (your words, rejected options, the basis with `file:line` quotes, and the impact), and the head checks each row like a report before recording it. See `references/side-session.md`. Any agent in this workflow also tests your own decisions the way it tests its recommendations: if the evidence favours another option, it says so once, with that evidence, and the decision stays yours.

### Bundled scripts

| Script | Copied into the project | Purpose |
|---|---|---|
| `record.py` | yes (`handoff/tools/`) | Runs a command, saves its output byte-for-byte as an evidence log, and records provenance (command, exit code, SHA-256) in `handoff/logs/provenance.jsonl`. `--result` registers files the command wrote (glob patterns allowed); logs of finished tasks are not overwritten without `--overwrite`. |
| `check_evidence.py` | yes | Checks a report against its evidence: every `file:line` quote (also quotes in prose such as the Anomalies section), every OK against its expected value, log provenance (including logs overwritten by a different command, commands repeated until they passed, OK rows that cite a log whose command failed, and logs produced from temporary scripts), that each acceptance criterion has a row, and that expected values copied from a task's data-table template were not changed. `--at <commit>` / `--at-report` check old reports against the files as they were. Reads Indonesian or English reports. |
| `check_secrets.py` | yes, if the project has local secret files | Finds secrets in files before commit by pattern and by the actual values from your local secret files, without printing them. `--staged`, `--redact`. |
| `screenshot.py` | yes, if the project has a web UI | Screenshots a page at target screen sizes using real device emulation through the Chrome DevTools Protocol, and reports the page width and any element that sticks out of the screen (exit 1 if so). `--offline` blocks every host except localhost and the page's own host (so a device web UI still loads); `--allow-host` keeps more hosts reachable. |
| `context_size.py` | yes (`handoff/tools/`) | Reads the context size of the Claude Code session that runs it, from that session's own transcript (`CLAUDE_CODE_SESSION_ID`). Above 200k tokens (`--limit`) it prints `LARGE`, and the head suggests `/clear` plus its skill to the user: the model cannot clear itself, and auto-compact keeps only the first 5,000 tokens of each skill. It also prints `TIDY` when the hand-off section of the ROADMAP grows past 8 KB (`--handoff-limit`), because every new session re-reads it. |
| `check_process_notes.py` | yes (`handoff/tools/`) | Flags process notes in product files before commit: who wrote, decided, or checked something, agent sessions and models, user quotes and approvals, internal reviews, document-language lines, session links, and task/report/item numbers, plus `handoff/` references when the agent layer is kept out of the repo. Checks only added lines (`--staged`, `--worktree`), commit messages and PR descriptions (`--message`), or whole files for audits (`--all --summary`). |
| `check_diff.py` | yes (`handoff/tools/`) | Reports facts about the added lines of a change, read-only: names used but defined nowhere in the code or in the change, unused imports, calls through a string key (`obj['name']()`), and (only with `--docs`) names in Markdown code spans that exist nowhere in the code. A run with no changed files in the chosen mode says so. Comments, strings, and regex literals are skipped; library members are not checked; languages that are not parsed are listed as not checked. Modes: `--worktree` (default), `--staged`, `--commit`, `--range`, `--json`. |
| `brief.py` | yes (`handoff/tools/`) | Prints the head's start-of-session reading: ROADMAP and NOTES with large sections shortened (closed table rows hidden, long rows cut and prefixed with their line number), plus tasks by status and DONE tasks that still lack a triage mark. Files are not modified; `--full <text>` prints a section whole. |
| `orca_wait.py` | yes, if the head launches executors through Orca | Waits for Orca worker messages in the background without waking the head: acknowledges heartbeat-only batches itself, drops Orca's keepalive frames, and exits on any other message (`MESSAGE`), an error (`ERROR`), or after 36 minutes (`TIMEOUT`, with each dispatch's last heartbeat). |
| `head_restart.py` | yes, if the head launches executors through Orca | Starts a fresh head session in the same Orca terminal, when you allow it in the project README: waits for the head's turn to end, gives a 30-second grace period, then types `/clear` and the head skill. It cancels if you type or send anything during the grace period. |
| `check_version.py` | no (run from the skill folder, in the project root or with its path as the argument) | Compares the project's protocol with the changelog markers, reports the effective version and the patches still missing. |
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

The skill is written in Indonesian, with English file, script, and option names (since v3.12) and English identifiers (since v3.20): mode and task types (`STRUCTURE`, `FACT`, ...), capacity levels (`HIGH`/`MEDIUM`/`LOW`), structure labels (`REQUIRED`/`STANDARD`/`PREFERENCE`), criterion statuses (`OK`/`FAIL`/`UNTESTED`; `FOUND`/`NONE`/`UNSURE` for fact-finding tasks), roadmap statuses (`TODO`/`PARTIAL`/`PARKED`/`WAIT-USER`), and the `HYPOTHESIS:`/`PROPOSAL:` labels. Since v3.20.1 the word that opens each script result is English as well: `context_size.py` prints `OK`/`LARGE`/`TIDY`/`UNKNOWN`, `orca_wait.py` `MESSAGE`/`TIMEOUT`/`ERROR`, `head_restart.py` `SCHEDULED`/`ERROR`, and `check_evidence.py` labels its findings `ERROR`/`WARNING`; the explanation after that word stays Indonesian. Identifiers stay the same in every protocol language; the scripts still accept the older Indonesian names, and the mapping is in the changelog (v3.12, v3.20, and v3.20.1). Generated files follow your language. Two mechanisms keep the scripts language-independent:

- **Rule tags.** Every rule in the templates carries an HTML comment such as `<!-- aw: Z1 -->`. Tags are copied with the rule, invisible when rendered, and `check_version.py` recognises rules by their tag, so a protocol written in any language can still be upgraded.
- **Tool keywords.** Words the scripts parse (report headings, Data table columns, evidence forms) are written either in Indonesian or English, e.g. `Self-check`, `Expected`/`Observed`/`Evidence`, `count(file, "pattern")`. The full table is in `references/templates.md` (*Kata kunci alat*).

## Versioning and upgrades

The skill version is in `SKILL.md` and `references/changelog.md`. Each version lists the rules it adds to projects, with target file, patch method, and a marker. A generated `handoff/README.md` records the skill version it was built with. To upgrade a project, run the skill in AUDIT mode: it runs `check_version.py`, patches only the missing rules, keeps your own rules and local script patches, and asks before committing. The head records gaps it finds in the skill (wrong or missing rules, checks that missed a problem, wasted time or tokens, its own slips the protocol did not prevent) in `handoff/SKILL-FEEDBACK.md`, where a side session may add a line too; the upgrade reads that file and marks each entry handled or declined.

## Development

```
python tests/run_tests.py
```

This runs a structure check (frontmatter, version consistency, every changelog marker present in the templates and tagged in every template variant, LF line endings) and functional tests of every script in temporary projects. CI runs the same on Linux, Windows, and macOS. Tests that need Chrome or Orca are skipped when those are not installed; `test_orca_cli.py` checks every `orca` command and option written in the skill against the installed Orca's `--help`.

When adding a rule that ends up in project files: add a row to the version's table in `references/changelog.md`, a marker in the `penanda` block, the rule text in every template variant that produces the target file, and the `<!-- aw: ID -->` tag on that line. Bump the version in `SKILL.md`, the changelog, and `plugins/agent-workflow/.claude-plugin/plugin.json` together.

The tests above check the scripts and the rule text, not how a model behaves with the skill loaded. `plugins/agent-workflow/evals/` holds a small [`claude plugin eval`](https://code.claude.com/docs/en/plugin-evals) suite for that: the skill must fire on a natural planner/executor complaint, stay out of an unrelated coding request, and, in an audit, run `check_version.py` and report before changing anything. Run it before a release, not in CI, because every run is a real model call on your account:

```
claude plugin eval plugins/agent-workflow --tag trigger --trust-plugin
claude plugin eval plugins/agent-workflow --tag shell --scaffold --allow-tools Bash Edit Write --trust-plugin
```

The `shell` case needs Bash, which Claude Code only grants where it has a sandbox backend (macOS, Linux, WSL); on native Windows the run is refused before any model call.

## Bahasa Indonesia

Skill ini memasang, mengaudit, dan meng-upgrade alur kerja dua agen, yaitu head (perencana) dan executor (pelaksana), untuk project apa pun. Protokolnya disetel ke kapasitas model executor. Isi skill berbahasa Indonesia; file yang dibuat untuk project mengikuti bahasa user. Pasang lewat `/plugin marketplace add brahamrenatus-ai/agent-workflow` lalu `/plugin install agent-workflow@agent-workflow`, atau salin `plugins/agent-workflow/skills/agent-workflow/` ke `~/.claude/skills/agent-workflow/`. Mulai dari `SKILL.md`; riwayat versi ada di `references/changelog.md`.

## License

[MIT](LICENSE)
