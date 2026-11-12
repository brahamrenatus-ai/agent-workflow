"""Uji scripts/check_diff.py pada repo palsu (git sementara): fakta tentang baris baru sebuah perubahan.

Tiap sumber tanda palsu punya fixture sendiri dan harus nol tanda: isi string regex Python, anggota URL dan objek
pustaka di JS, isi literal regex JS, spread `...NAMA`, `import type` dan impor TS tanpa ekstensi, id yang didefinisikan
di baris baru file lain pada perubahan yang sama, dan dokumen yang ditulis sebelum kodenya (satu baris INFO).
Tanda benar per golongan: properti karangan, impor tak terpakai, `obj['delete'](`, `var(--x)` tanpa definisi, impor
relatif yang hilang, nilai prop komponen, field dokumen karangan, panggilan Python tanpa definisi (kelas CSS tanpa
aturan gaya tidak ditandai: NO-STYLE tidak lolos gerbang); juga
lapisan agen dilewati kecuali handoff/tools/, `not checked`, mode --commit/--range/--staged, kode keluar, dan --json.
DOC dan baris INFO dokumen hanya dengan --docs (tanpanya satu baris hitungan, `docs_hidden`, di luar hitungan akhir);
perubahan kosong memberi baris "No changed files to check" dan `"files": 0`, `"mode"` di setiap --json.
Argumen: folder skill. Fixture juga bisa diimpor (FALSE_POSITIVES, BASE) tanpa menjalankan uji."""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 and __name__ == "__main__" else \
    Path(__file__).resolve().parent.parent / "plugins/agent-workflow/skills/agent-workflow"
SCRIPT = SKILL / "scripts" / "check_diff.py"

# Small project committed as the base of every fixture.
BASE = {
    "src/api.js": ("export function loadRows(client) {\n"
                   "  return client.rows.map((row) => ({ id: row.id, weight_avg_g: row.weight_avg_g, label: row.label }));\n"
                   "}\n"),
    "src/theme.ts": ("export const BASE_STYLE = { color: 'black' };\n"
                     "export const ACCENT = 'red';\n"
                     "export type Tone = 'plain' | 'strong';\n"),
    "src/types.ts": "export interface Row {\n  id: number;\n  label: string;\n}\n",
    "src/styles.css": (":root { --bg: white; }\n"
                       ".card { background: var(--bg); }\n"
                       ".card-title { font-weight: bold; }\n"),
    "src/Button.jsx": ("export function Button({ tone, children }) {\n"
                       "  const cls = tone === 'strong' ? 'card-title' : tone === 'plain' ? 'card' : '';\n"
                       "  return <button className={cls}>{children}</button>;\n"
                       "}\n"),
    "src/state.js": "export const isActive = (x) => Boolean(x);\nexport const itemCount = (rows) => rows.length;\n",
    "lib/date.js": ("function formatDate(d) {\n  return d.toISOString();\n}\n"
                    "function shiftDay(d, n) {\n  return new Date(d.getTime() + n * 86400000);\n}\n"
                    "module.exports = { formatDate, shiftDay };\n"),
    "tools/report.py": "import re\n\n\ndef item_count(rows):\n    return len(rows)\n",
    "docs/api.md": ("# API\n\n"
                    "`loadRows` returns rows with `weight_avg_g` and `label`.\n"
                    "Helpers: `formatDate`, `shiftDay`, `isActive`, `itemCount`, and `item_count` in the report tool.\n"),
    ".gitignore": "node_modules/\n",
}

# False-positive sources: each change must give no mark at all (and an INFO line where stated).
FALSE_POSITIVES = [
    {"id": "py-regex-string", "src": "(a) Python regex string",
     "change": {"tools/report.py": BASE["tools/report.py"] + (
         "\n\nEXIT_RE = re.compile(r\"\\bterminate_job(\\s|$)\")\n\n\n"
         "def is_exit(line):\n    return bool(EXIT_RE.search(line))\n")},
     "proto_name": "bterminate_job"},
    {"id": "js-library-members", "src": "(d) URL and library members",
     "change": {"src/origin.js": ("import { createClient } from 'some-sdk';\n\n"
                                  "export function isLocal(origin) {\n"
                                  "  let parsed;\n"
                                  "  try {\n"
                                  "    parsed = new URL(origin);\n"
                                  "  } catch (err) {\n"
                                  "    return String(err.details || '');\n"
                                  "  }\n"
                                  "  const client = createClient();\n"
                                  "  const state = client.connectionState;\n"
                                  "  return parsed.hostname === 'localhost' && parsed.protocol === 'http:' && state;\n"
                                  "}\n"),
                "src/store.js": ("import { createClient } from 'some-sdk';\n\n"
                                 "const db = createClient();\n\n"
                                 "function table(name) {\n"
                                 "  return db.from(name);\n"
                                 "}\n\n"
                                 "export async function addItem(item) {\n"
                                 "  const { data, error: errItem } = await table('items').insert(item).select().single();\n"
                                 "  if (errItem) return errItem.details || errItem.hint;\n"
                                 "  return data;\n"
                                 "}\n")},
     "proto_name": "hostname"},
    {"id": "js-regex-literal", "src": "(a) JS regex literal",
     "change": {"test/render.test.js": ("import { loadRows } from '../src/api.js';\n\n"
                                        "test('render', () => {\n"
                                        "  const html = String(loadRows({ rows: [] }));\n"
                                        "  expect(html).not.toMatch(/\\.panelWidgetB\\b/);\n"
                                        "});\n")},
     "proto_name": "panelWidgetB"},
    {"id": "js-spread", "src": "spread ...NAME",
     "change": {"src/view.js": ("import { BASE_STYLE } from './theme';\n\n"
                                "export const panelStyle = { ...BASE_STYLE, padding: 4 };\n")},
     "proto_name": "BASE_STYLE"},
    {"id": "ts-import-type", "src": "(e) import type + TS path without extension",
     "change": {"src/table.ts": ("import type { Row } from './types';\n"
                                 "import { ACCENT } from './theme';\n\n"
                                 "export function rowLabel(row: Row): string {\n"
                                 "  return `${row.label} ${ACCENT}`;\n"
                                 "}\n")},
     "proto_name": "./types"},
    {"id": "same-change-id", "src": "(b) id defined on a new line of another file",
     "change": {"src/Header.jsx": "export function Header() {\n  return <h2 id=\"today-title\">Today</h2>;\n}\n",
                "src/Today.jsx": ("import { Header } from './Header';\n\n"
                                  "export function Today() {\n"
                                  "  return (\n"
                                  "    <section aria-labelledby=\"today-title\">\n"
                                  "      <Header />\n"
                                  "    </section>\n"
                                  "  );\n"
                                  "}\n")},
     "proto_name": "today-title"},
    {"id": "doc-before-code", "src": "(c) document written before its code", "info": 1,
     "change": {"docs/contract.md": ("# Order contract (planned)\n\n"
                                     "`POST /orders` accepts `order_ref`, `buyer_name`, `ship_window`, `pay_method`, "
                                     "and `promo_code`; it returns `order_state` and `eta_hours`.\n")},
     "proto_name": "order_ref"},
]

# One change with a true positive for every class, plus files that must not be checked.
TRUE_POSITIVES = {
    "src/detail.js": ("import { formatDate, shiftDay } from '../lib/date';\n\n"
                      "export function showRow(row, client) {\n"
                      "  const when = formatDate(row.label);\n"
                      "  const avg = row.weight_avg_gram;\n"
                      "  client['delete']();\n"
                      "  return `${when} ${avg}`;\n"
                      "}\n\n"
                      "export const later = async () => formatDate(new Date());\n"),
    "src/extra.js": "import { helper } from './missing-helper';\n\nexport const extra = helper();\n",
    "src/styles.css": BASE["src/styles.css"] + (
        ".card-note { color: var(--text-strong); border-color: var(--edge, gray); background: var(--bg); }\n"),
    "src/Page.jsx": ("import { Button } from './Button';\n\n"
                     "export const Page = () => <Button tone=\"ghostly\">Go</Button>;\n"),
    "src/Card.jsx": ("export const Card = () => (\n"
                     "  <div className=\"card card-ghost\">\n"
                     "    <span className=\"hook-only\" style={{ color: 'red' }}>x</span>\n"
                     "  </div>\n"
                     ");\n"),
    "docs/api.md": BASE["docs/api.md"] + "- `ghost_field` is returned next to `weight_avg_g`.\n",
    "tools/report.py": BASE["tools/report.py"] + (
        "\n\nimport os.path as osp\nfrom os import path, sep\n\n\ndef total(rows):\n"
        "    return path.join(*rows) + summarize_rows(rows) + f\"{sep}\"\n"),
    "firmware/main.cpp": "int main() { return ghostCall(); }\n",
    "handoff/tasks/TASK-001.md": "Add `ghost_task_field` to the API.\n",
    ".claude/hooks/check.js": "export const x = (o) => o.notThere;\n",
    "handoff/tools/check_ui.py": "def run():\n    return undefined_helper_call()\n",
}
TP_EXPECT = {
    ("UNDEFINED", "weight_avg_gram"), ("UNUSED-IMPORT", "shiftDay"), ("DYNAMIC-CALL", "delete"),
    ("UNDEFINED", "./missing-helper"), ("UNDEFINED", "--text-strong"), ("UNDEFINED", "ghostly"),
    ("DOC", "ghost_field"), ("UNDEFINED", "summarize_rows"),
    ("UNUSED-IMPORT", "osp"),
    ("UNDEFINED", "undefined_helper_call"),
}


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=test", "-c", "user.email=test@example.com",
                           "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false", *a],
                          capture_output=True, text=True, encoding="utf-8")


def write(root, files):
    for rel, text in files.items():
        p = Path(root) / rel
        if text is None:
            if p.exists():
                p.unlink()
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode("utf-8"))


def make_repo(root, change=None, base=None):
    """Base committed; `change` left as uncommitted worktree changes (edits and new files)."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init", "-q")
    write(root, BASE if base is None else base)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "base")
    if change:
        write(root, change)
    return root


def run(cwd, *args, script=None):
    r = subprocess.run([sys.executable, str(script or SCRIPT), *args], cwd=str(cwd), capture_output=True, text=True,
                       encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


def run_json(cwd, *args, script=None):
    rc, out = run(cwd, "--json", *args, script=script)
    try:
        return rc, json.loads(out), out
    except ValueError:
        return rc, None, out


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    results = []

    def check(name, cond, info=""):
        results.append(bool(cond))
        print(("OK    " if cond else "FAIL  ") + name)
        if not cond and info:
            print("      " + str(info).replace("\n", "\n      ")[:3000])

    tmp = Path(tempfile.mkdtemp(prefix="check_diff_"))
    try:
        # 1. false-positive sources: no marks (INFO lines only with --docs)
        for fx in FALSE_POSITIVES:
            repo = make_repo(tmp / fx["id"], fx["change"])
            rc, j, out = run_json(repo, "--docs")
            ok = rc == 0 and j is not None and j["marks"] == [] and len(j["info"]) == fx.get("info", 0)
            rc, jb, outb = run_json(repo)
            ok_bare = rc == 0 and jb is not None and jb["marks"] == [] and jb["info"] == [] and jb.get("docs_hidden") == 0
            check(f"no mark: {fx['src']} [{fx['id']}]", ok and ok_bare, out + "\n" + outb)

        # 2. true positives in one worktree change (--docs: every class)
        tp = make_repo(tmp / "tp", TRUE_POSITIVES)
        rc, j, out = run_json(tp, "--docs")
        got = {(m["class"], m["name"]) for m in j["marks"]} if j else set()
        check("--json: version 1 with mode, files, marks, info, not_checked, docs_hidden",
              rc == 0 and j is not None and j.get("version") == 1 and j.get("mode") == "worktree" and j.get("files") == 9
              and isinstance(j.get("marks"), list) and isinstance(j.get("info"), list)
              and isinstance(j.get("not_checked"), dict) and j.get("docs_hidden") == 0, out)
        rc, jb, outb = run_json(tp)
        got_bare = {(m["class"], m["name"]) for m in jb["marks"]} if jb else set()
        check("--json without --docs: no DOC mark, docs_hidden 1, other marks unchanged",
              rc == 0 and jb is not None and got_bare == {x for x in TP_EXPECT if x[0] != "DOC"}
              and jb.get("docs_hidden") == 1 and jb.get("files") == 9, outb)
        for cls, name in sorted(TP_EXPECT):
            check(f"mark {cls} {name}", (cls, name) in got, out)
        extra = got - TP_EXPECT
        check("no other marks (no NO-STYLE, var() with fallback, async arrow, f-string use, agent layer)", not extra,
              f"extra: {sorted(extra)}\n{out}")
        files = {m["file"] for m in j["marks"]} if j else set()
        check("agent layer skipped, handoff/tools/ checked",
              not any(f.startswith((".claude/", "handoff/tasks/")) for f in files) and "handoff/tools/check_ui.py" in files, out)
        check("not checked: .cpp listed", j is not None and j["not_checked"].get(".cpp") == 1, out)
        mk = [m for m in j["marks"] if m["name"] == "weight_avg_gram"] if j else []
        check("mark has file, line, and line text",
              mk and mk[0]["file"] == "src/detail.js" and mk[0]["line"] == 5 and mk[0]["text"] == "const avg = row.weight_avg_gram;", mk)
        rc, out = run(tp, "--docs")
        check("text output: `<CLASS> <name> <file>:<line> | <text>` and final count line, exit 0 with marks",
              rc == 0 and re.search(r"^UNDEFINED weight_avg_gram src/detail\.js:5 \| const avg = row\.weight_avg_gram;$", out, re.M)
              and re.search(r"^DOC ghost_field docs/api\.md:5 \| ", out, re.M)
              and re.search(r"^not checked: \.cpp 1 file$", out, re.M) and "--docs to list" not in out
              and out.rstrip().splitlines()[-1] == f"CHECK-DIFF: {len(TP_EXPECT)} marks in 7 files", out)
        rc, out = run(tp)
        check("text output without --docs: no DOC mark line, one count line, DOC left out of the final count",
              rc == 0 and not re.search(r"^DOC ", out, re.M)
              and len(re.findall(r"^DOC: 1 name in changed docs not found in code \(run with --docs to list them\)$", out, re.M)) == 1
              and out.rstrip().splitlines()[-1] == f"CHECK-DIFF: {len(TP_EXPECT) - 1} marks in 6 files", out)

        # 3. --commit / --range / --staged / clean worktree
        git(tp, "add", "-A")
        git(tp, "commit", "-q", "-m", "change")
        rc, j2, out = run_json(tp, "--commit", "HEAD", "--docs")
        got2 = {(m["class"], m["name"]) for m in j2["marks"]} if j2 else set()
        check("--commit HEAD: same marks as the worktree run (tree read from git)", rc == 0 and got2 == got
              and j2.get("mode") == "commit" and j2.get("files") == 9, out)
        rc, j3, out = run_json(tp, "--range", "HEAD~1..HEAD", "--docs")
        check("--range HEAD~1..HEAD: same marks", rc == 0 and j3 is not None and j3.get("mode") == "range"
              and {(m["class"], m["name"]) for m in j3["marks"]} == got, out)
        write(tp, {"src/detail.js": None, "src/state.js": None})  # the commit's tree is used, not the folder
        rc, j4, out = run_json(tp, "--commit", "HEAD", "--docs")
        check("--commit reads the tree of the commit, not the working folder",
              rc == 0 and j4 is not None and {(m["class"], m["name"]) for m in j4["marks"]} == got, out)
        git(tp, "checkout", "-q", "--", ".")
        rc, out = run(tp)
        check("clean worktree: 0 marks", rc == 0 and out.rstrip().splitlines()[-1] == "CHECK-DIFF: 0 marks in 0 files", out)
        write(tp, {"src/late.js": "export const late = (r) => r.ghost_late;\n",
                   "src/later.js": "export const later = (r) => r.ghost_later;\n"})
        git(tp, "add", "src/late.js")
        rc, j5, out = run_json(tp, "--staged")
        check("--staged: only the staged file", rc == 0 and j5 is not None and j5.get("mode") == "staged"
              and j5.get("files") == 1 and {m["name"] for m in j5["marks"]} == {"ghost_late"}, out)
        rc, j6, out = run_json(tp, "src/later.js")
        check("path argument limits the checked files", rc == 0 and j6 is not None
              and {m["name"] for m in j6["marks"]} == {"ghost_later"}, out)

        # 4. exit codes
        nogit = tmp / "nogit"
        nogit.mkdir()
        rc, out = run(nogit)
        check("outside git: exit 2", rc == 2 and "ERROR" in out, out)
        rc, out = run(tp, "--commit", "no-such-ref")
        check("unknown commit: exit 2", rc == 2 and "ERROR" in out, out)
        rc, out = run(tp, "--staged", "--commit", "HEAD")
        check("two modes: exit 2", rc == 2, out)

        # 5. overflow: a class with more marks than the limit is cut with its count
        names = [f"known_name_{k}" for k in range(40)]
        many = dict(BASE)
        many["src/names.js"] = "".join(f"export const {n} = {k};\n" for k, n in enumerate(names))
        many["docs/names.md"] = "# Names\n\n" + "".join(f"- `{n}`\n" for n in names)
        ov = make_repo(tmp / "overflow", {"docs/names.md": many["docs/names.md"] + "".join(f"- `ghost_name_{k}`\n" for k in range(30))}, many)
        rc, out = run(ov, "--docs")
        check("overflow: 25 DOC lines + `DOC ... 5 more`", rc == 0 and len(re.findall(r"^DOC ghost_name_", out, re.M)) == 25
              and re.search(r"^DOC \.\.\. 5 more", out, re.M) and "CHECK-DIFF: 30 marks in 1 files" in out, out)

        # 5b. DOC only with --docs: a change whose only absent name is in a doc
        dc = make_repo(tmp / "doc-only", {"docs/api.md": BASE["docs/api.md"] + "- `phantom_total` is returned too.\n"})
        rc, out = run(dc)
        check("doc-only change without --docs: no `DOC ` line, one count line, final count 0, no zero-change line",
              rc == 0 and not re.search(r"^DOC ", out, re.M)
              and re.findall(r"^DOC: .*$", out, re.M) == ["DOC: 1 name in changed docs not found in code (run with --docs to list them)"]
              and "No changed files" not in out and out.rstrip().splitlines()[-1] == "CHECK-DIFF: 0 marks in 0 files", out)
        rc, out = run(dc, "--docs")
        check("doc-only change with --docs: the DOC mark is listed and counted",
              rc == 0 and re.search(r"^DOC phantom_total docs/api\.md:5 \| - `phantom_total` is returned too\.$", out, re.M)
              and "--docs to list" not in out and out.rstrip().splitlines()[-1] == "CHECK-DIFF: 1 marks in 1 files", out)
        rc, jb, outb = run_json(dc)
        rc2, jd, outd = run_json(dc, "--docs")
        check("doc-only change --json: DOC absent and docs_hidden 1 without --docs; listed and docs_hidden 0 with --docs",
              rc == 0 and rc2 == 0 and jb is not None and jd is not None and jb["marks"] == [] and jb.get("docs_hidden") == 1
              and jb.get("files") == 1 and [(m["class"], m["name"]) for m in jd["marks"]] == [("DOC", "phantom_total")]
              and jd.get("docs_hidden") == 0, outb + "\n" + outd)

        # 5c. zero-change run: says so, names --commit/--range, exit 0
        cl = make_repo(tmp / "clean")
        rc, out = run(cl)
        lines = out.rstrip().splitlines()
        check("clean repo, --worktree: explicit zero-change line naming --commit/--range, then the 0 count, exit 0",
              rc == 0 and len(lines) >= 2 and lines[-2] == ("No changed files to check in --worktree mode; if the change is "
                                                            "already committed, use --commit <C> or --range A..B.")
              and lines[-1] == "CHECK-DIFF: 0 marks in 0 files", out)
        rc, j, out = run_json(cl)
        check("clean repo --json: mode worktree, files 0, no marks", rc == 0 and j is not None and j.get("mode") == "worktree"
              and j.get("files") == 0 and j["marks"] == [] and j.get("docs_hidden") == 0, out)
        rc, out = run(cl, "--staged")
        check("clean repo, --staged: zero-change line names the mode", rc == 0
              and "No changed files to check in --staged mode; if the change is already committed" in out, out)
        write(cl, {"handoff/tasks/TASK-002.md": "Agent layer only.\n"})
        rc, j, out = run_json(cl)
        check("agent-layer-only change counts as no changed file", rc == 0 and j is not None and j.get("files") == 0, out)
        rc, out = run(cl, "--commit", "HEAD")
        check("--commit with only checked files: no zero-change line", rc == 0 and "No changed files" not in out, out)

        # 6. read-only: git index untouched
        idx = tp / ".git" / "index"
        before = idx.stat().st_mtime_ns
        run(tp)
        run(tp, "--commit", "HEAD")
        check("read-only: .git/index not rewritten", idx.stat().st_mtime_ns == before)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\nRESULT: {'ALL OK' if all(results) and results else 'SOME FAILED'} ({sum(results)}/{len(results)})")
    return 0 if all(results) and results else 1


if __name__ == "__main__":
    sys.exit(main())
