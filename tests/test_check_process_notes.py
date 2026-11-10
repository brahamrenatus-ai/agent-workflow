"""Uji scripts/check_process_notes.py pada repo palsu: frasa proses (PROCESS) dan rujukan task atau lapisan agen (REF)
di file produk; mode --all, --staged, --worktree, --message, dan path; handoff/ ikut repo vs lapisan agen privat;
EXCLUDE/ALLOW; dan teks yang mirip catatan proses tetapi lazim di produk (HEAD git, <head> HTML, executor thread pool,
`user: "..."` sebagai data, alur persetujuan pengguna aplikasi). Argumen: folder skill."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

SKILL = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "plugins/agent-workflow/skills/agent-workflow"
SKRIP = SKILL / "scripts" / "check_process_notes.py"
hasil = []


def cek(nama, cond, info=""):
    hasil.append(bool(cond))
    print(("OK    " if cond else "FAIL  ") + nama)
    if not cond and info:
        print("      " + str(info).replace("\n", "\n      "))


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.name=uji", "-c", "user.email=uji@example.com",
                           "-c", "core.autocrlf=false", *a], capture_output=True, text=True, encoding="utf-8")


def jalan(cwd, *a, skrip=SKRIP, stdin=None):
    r = subprocess.run([sys.executable, str(skrip), *a], cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       input=stdin)
    return r.returncode, r.stdout + r.stderr


def tulis(root, files):
    for rel, isi in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(isi if isinstance(isi, bytes) else isi.encode("utf-8"))


def temuan(out):
    """{'file:baris': label} dari keluaran per baris."""
    return {m.group(1): m.group(2) for m in re.finditer(r"^(.+?:\d+): (.+?) \| ", out, re.M)}


PRODUK = {
    "src/app.js": ("// Ditulis head; executor tidak boleh mengubah file ini.\n"   # 1 PROCESS
                   "const batas = 1; // TASK-012: batas dinaikkan\n"             # 2 REF
                   "// struktur folder: lihat handoff/STRUCTURE.md\n"            # 3 REF hanya bila privat
                   "const h = document.querySelector('head');\n"                 # 4 bersih
                   "const cfg = { user: \"hello world\" };\n"                     # 5 bersih (data)
                   "// user: \"terlalu ramai\"\n"                                # 6 PROCESS (kutipan user di komentar)
                   "// Pesanan dikirim setelah disetujui user\n"                 # 7 PROCESS (dipakai uji ALLOW)
                   "export default cfg;\n"),
    "src/run.py": ("loop.run_in_executor(None, fn)  # bandingkan dengan HEAD git\n"
                   "patch = git('diff', 'HEAD')\n"),
    "docs/api.md": ("# API\n"
                    "| Bahasa | Keterangan berbahasa Indonesia; identifier tetap berbahasa Inggris |\n"   # 2 PROCESS
                    "| Language | Python |\n"                                                        # 3 bersih
                    "| `message` | Untuk developer, berbahasa Inggris |\n"                            # 4 bersih
                    "Disusun sesi diskusi atas permintaan user.\n"                                   # 5 PROCESS
                    "Rancangan visual: https://claude.ai/artifact/abc123\n"                          # 6 PROCESS
                    "The order must be approved by the user before shipping.\n"                     # 7 bersih
                    "Reviewed by the head agent.\n"                                                  # 8 PROCESS
                    "Approved by the head of finance.\n"                                             # 9 bersih
                    "Lingkup ada di ROADMAP §3.\n"                                                   # 10 REF hanya bila privat
                    "| 0.2 | 2026-11-10 | Tinjauan internal: aturan retry |\n"                         # 11 PROCESS
                    "Dokumen ini ditulis dalam bahasa Inggris.\n"                                    # 12 PROCESS
                    "Field `user` diisi pengguna; permintaan user divalidasi di server.\n"),         # 13 bersih
    "deploy/compose.yml": "services:\n  app:\n    user: \"1000:1000\"\n",
    "web/index.html": "<!doctype html><html><head><title>x</title></head></html>\n",
    ".gitignore": "handoff/logs/TASK-0*.log\n# log uji lokal (TASK-012)\n",            # 1 REF hanya bila privat, 2 REF
    "package-lock.json": "{\"resolved\": \"https://example.com/TASK-120.tgz\"}\n",         # lockfile dilewati
    "assets/logo.png": b"\x89PNG\x00\x00TASK-120 ditulis head",                         # biner dilewati
}
LAPISAN = {
    "handoff/README.md": "TASK-012 ditulis head, keputusan user.\n",
    "handoff/tools/x.py": "# TASK-012 ditulis head\n",
    ".claude/skills/demo-head/SKILL.md": "Ditulis head. Lihat handoff/ROADMAP.md dan TASK-012.\n",
    "CLAUDE.md": "Head: handoff/. TASK-012.\n",
    "src/sub/AGENTS.md": "keputusan user: TASK-012\n",
}
UMUM = {"src/app.js:1": "PROCESS", "src/app.js:2": "REF", "src/app.js:6": "PROCESS", "src/app.js:7": "PROCESS",
        "docs/api.md:2": "PROCESS", "docs/api.md:5": "PROCESS", "docs/api.md:6": "PROCESS", "docs/api.md:8": "PROCESS",
        "docs/api.md:11": "PROCESS", "docs/api.md:12": "PROCESS", ".gitignore:2": "REF"}
PRIVAT = {"src/app.js:3": "REF", "docs/api.md:10": "REF", ".gitignore:1": "REF"}


def label_cocok(dapat, harap):
    """Setiap lokasi yang diharapkan ada dengan label itu, dan tidak ada lokasi lain."""
    salah = [f"{k}: harap {v}, dapat {dapat.get(k)}" for k, v in harap.items() if v not in (dapat.get(k) or "")]
    lebih = sorted(set(dapat) - set(harap))
    return not salah and not lebih, "; ".join(salah) + (f" | lebih: {lebih}" if lebih else "")


tmp = Path(tempfile.mkdtemp(prefix="uji_cek_proses_"))
try:
    if not SKRIP.is_file():
        cek("scripts/check_process_notes.py ada", False, str(SKRIP))
        print("\nRESULT: SOME FAILED")
        raise SystemExit(1)

    # ---------- T1: handoff/ ikut repo, --all ----------
    a = tmp / "bersama"
    a.mkdir()
    git(a, "init", "-q")
    tulis(a, {**PRODUK, **LAPISAN})
    git(a, "add", "-A")
    git(a, "commit", "-qm", "awal")
    rc, out = jalan(a, "--all")
    dapat = temuan(out)
    ok, info = label_cocok(dapat, UMUM)
    cek("T1 --all (handoff/ ikut repo): frasa proses dan nomor task ditandai, rujukan handoff/ tidak", ok, info + "\n" + out)
    cek("T1 exit 1 dan ringkasan menyebut jumlah", rc == 1 and "9 PROCESS, 2 REF" in out and "handoff/ ikut repo" in out, out)
    cek("T1 lapisan agen (handoff/, .claude/, CLAUDE.md, AGENTS.md bersarang), lockfile, dan biner dilewati",
        not any(k.split(":")[0] in LAPISAN or k.startswith(("package-lock", "assets/")) for k in dapat), out)
    cek("T1 teks produk yang mirip (HEAD git, <head>, executor thread pool, user: \"...\" data, compose) tidak ditandai",
        not any(k.startswith(("src/run.py", "deploy/", "web/")) for k in dapat) and "src/app.js:4" not in dapat
        and "src/app.js:5" not in dapat, out)
    cek("T1 petunjuk perbaikan dicetak", "PROCESS: tulis ulang sebagai isi teknis" in out and "REF: hapus nomor task" in out
        and "ALLOW" in out, out)
    rc, out = jalan(a, "--all", "--summary")
    cek("T1 --summary: jumlah per file, bukan per baris", rc == 1 and "src/app.js: 3 PROCESS, 1 REF" in out
        and "docs/api.md: 6 PROCESS, 0 REF" in out and not temuan(out), out)
    rc, out = jalan(a, "docs", "src/run.py")
    cek("T1 path (folder + file): hanya isi path itu", rc == 1 and set(temuan(out)) == {k for k in UMUM if k.startswith("docs/")}, out)

    # ---------- T2: lapisan agen privat (handoff/ tidak ter-track) ----------
    b = tmp / "privat"
    b.mkdir()
    git(b, "init", "-q")
    tulis(b, {**PRODUK, **{k: v for k, v in LAPISAN.items() if k.startswith("handoff/")}})
    (b / ".git" / "info").mkdir(parents=True, exist_ok=True)
    (b / ".git" / "info" / "exclude").write_text("handoff/\n", encoding="utf-8")
    git(b, "add", "-A")
    git(b, "commit", "-qm", "awal")
    rc, out = jalan(b, "--all")
    ok, info = label_cocok(temuan(out), {**UMUM, **PRIVAT})
    cek("T2 --all (lapisan agen privat): rujukan handoff/, ROADMAP §, dan pola ignore handoff/ ikut ditandai", ok, info + "\n" + out)
    cek("T2 ringkasan menyebut lapisan agen privat", "lapisan agen privat" in out, out)

    # ---------- T3: --staged dan --worktree hanya baris tambahan ----------
    s = tmp / "staged"
    shutil.copytree(a, s)
    tulis(s, {
        "src/app.js": PRODUK["src/app.js"].replace("const batas = 1; // TASK-012: batas dinaikkan",
                                                   "const batas = 2; // TASK-012: batas dinaikkan lagi")
                      + "// keputusan user: batas 5\n",
        "docs/catatan.txt": "awal\n++ catatan TASK-120\n+++ ditulis head\n",
        "docs/with space.md": "Diperbarui head.\n",
    })
    git(s, "add", "-A")
    tulis(s, {"src/run.py": PRODUK["src/run.py"] + "# hipotesis head: belum diukur\n",
              "src/baru.py": "x = 1\n# TASK-121 belum selesai\n"})
    rc, out = jalan(s, "--staged")
    harap = {"src/app.js:2": "REF", "src/app.js:9": "PROCESS", "docs/catatan.txt:2": "REF",
             "docs/catatan.txt:3": "PROCESS", "docs/with space.md:1": "PROCESS"}
    ok, info = label_cocok(temuan(out), harap)
    cek("T3 --staged: baris tambahan dan baris lama yang diubah, nomor baris benar, isi lama tidak", ok, info + "\n" + out)
    cek("T3 --staged: baris berawalan '++ ' dan path berspasi terbaca", "docs/catatan.txt:2" in out and "docs/with space.md:1" in out, out)
    rc, out = jalan(s, "--worktree")
    harap.update({"src/run.py:3": "PROCESS", "src/baru.py:2": "REF"})
    ok, info = label_cocok(temuan(out), harap)
    cek("T3 --worktree: ditambah perubahan belum di-stage dan file baru yang belum ter-track", ok, info + "\n" + out)
    git(s, "add", "-A")
    git(s, "commit", "-qm", "dua")
    rc, out = jalan(s, "--staged")
    cek("T3 --staged tanpa perubahan: exit 0", rc == 0 and "0 PROCESS, 0 REF" in out, out)
    tulis(s, {"handoff/NOTES.md": "keputusan user 2026-11-10: TASK-012 lolos triase head\n"})
    git(s, "add", "-A")
    rc, out = jalan(s, "--staged", "--message", "handoff: triase TASK-012, keputusan user")
    cek("T3 commit lapisan agen: diff tanpa file produk, pesan tidak dicek, exit 0",
        rc == 0 and "Pesan tidak dicek" in out, out)

    # ---------- T4: --message ----------
    rc, out = jalan(a, "--message", "fix: batas login (TASK-012)")
    cek("T4 pesan di repo yang memuat handoff/: nomor task boleh", rc == 0, out)
    rc, out = jalan(a, "--message", "fix: patch triase head atas batas login")
    cek("T4 pesan dengan frasa proses ditandai", rc == 1 and "message:1: PROCESS" in out, out)
    rc, out = jalan(b, "--message", "fix: batas login (TASK-012, ROADMAP R4)")
    cek("T4 pesan di lapisan agen privat: nomor task dan item ROADMAP ditandai", rc == 1 and "message:1: REF" in out, out)
    msg = b / ".git" / "COMMIT_EDITMSG"
    msg.write_text("feat: kontrak API\n\nKontrak memuat amplop error.\n\n"
                   "Co-Authored-By: Asisten <noreply@example.com>\n"
                   "# On branch dev/TASK-012-kontrak\n# Changes to be committed:\n#\tmodified:   docs/TASK-012.md\n"
                   "# ------------------------ >8 ------------------------\n+// ditulis head\n", encoding="utf-8")
    rc, out = jalan(b, "--message", str(msg))
    cek("T4 file pesan commit: komentar git, garis gunting, dan trailer tidak dicek", rc == 0 and "0 PROCESS, 0 REF" in out, out)
    pr = tmp / "pr.md"
    pr.write_text("## Ringkasan\nTambah kontrak API.\n\nDicek head (TASK-012).\n\n"
                  "\U0001F916 Generated with [Claude Code](https://claude.com/claude-code)\n", encoding="utf-8")
    rc, out = jalan(b, "--message", str(pr))
    cek("T4 deskripsi PR: baris proses ditandai di nomor barisnya, baris atribusi tidak", rc == 1
        and "message:4: PROCESS" in out and "REF" in out and "message:6" not in out, out)
    rc, out = jalan(b, "--message", "-", stdin="docs: rapikan kontrak\n\nsesi diskusi memutuskan format\n")
    cek("T4 --message - membaca stdin", rc == 1 and "message:3: PROCESS" in out, out)
    tulis(b, {"src/app.js": PRODUK["src/app.js"] + "// batas baru\n"})
    rc, out = jalan(b, "--worktree", "--message", "feat: batas baru (TASK-012)")
    cek("T4 --worktree --message (blok commit untuk user): perubahan dan pesan dicek bersama",
        rc == 1 and "message:1: REF" in out and "file produk + pesan dicek" in out, out)
    git(b, "checkout", "--", "src/app.js")

    # ---------- T5: EXCLUDE, ALLOW, --exclude ----------
    e = tmp / "kecuali"
    shutil.copytree(a, e)
    tulis(e, {"generated/out.txt": "TASK-120 ditulis head\n"})
    alat = e / "handoff" / "tools" / "check_process_notes.py"
    alat.parent.mkdir(parents=True, exist_ok=True)
    isi = SKRIP.read_text(encoding="utf-8")
    cek("T5 skrip punya EXCLUDE = [] dan ALLOW = []", "\nEXCLUDE = []\n" in isi and "\nALLOW = []\n" in isi)
    alat.write_bytes(isi.replace("\nEXCLUDE = []\n", "\nEXCLUDE = [\"generated/\"]\n")
                     .replace("\nALLOW = []\n", "\nALLOW = [r\"disetujui user\"]\n").encode("utf-8"))
    git(e, "add", "-A")
    rc, out = jalan(e, "--all", skrip=alat)
    dapat = temuan(out)
    cek("T5 EXCLUDE melewati generated/ dan ALLOW membuang teks yang memang isi produk",
        "generated/out.txt:1" not in dapat and "src/app.js:7" not in dapat and "src/app.js:1" in dapat, out)
    tulis(e, {"src/x.js": "// Pesanan dikirim setelah disetujui user (TASK-120)\n"})
    rc, out = jalan(e, "src/x.js", skrip=alat)
    cek("T5 ALLOW hanya membuang bagian yang cocok: nomor task di baris yang sama tetap ditandai",
        temuan(out).get("src/x.js:1") == "REF (nomor task/report/item)", out)
    rc, out = jalan(e, "--all", "--exclude", "generated/", "--exclude", "docs/*.md")
    dapat = temuan(out)
    cek("T5 --exclude (folder dan glob) dari baris perintah", not any(k.startswith(("generated/", "docs/api.md")) for k in dapat)
        and "src/app.js:1" in dapat, out)

    # ---------- T6: repo handoff/ terpisah, folder tanpa git, salah pakai ----------
    h = tmp / "tim"
    h.mkdir()
    git(h, "init", "-q")
    tulis(h, {"src/a.py": "x = 1\n", "handoff/tasks/TASK-012-x.md": "ditulis head\n"})
    git(h / "handoff", "init", "-q")
    git(h / "handoff", "add", "-A")
    rc, out = jalan(h / "handoff", "--staged", "--message", "TASK-012 ditulis head")
    cek("T6 di dalam repo handoff/ terpisah: lapisan agen, exit 0", rc == 0 and "lapisan agen" in out, out)
    rc, out = jalan(h, "--all")
    cek("T6 repo tim dengan handoff/ ber-git sendiri dianggap lapisan agen privat", rc == 0 and "lapisan agen privat" in out, out)
    n = tmp / "tanpa_git"
    tulis(n, {"README.md": "Lihat TASK-012.\n", "node_modules/x/a.js": "// TASK-012\n"})
    rc, out = jalan(n, "--all")
    cek("T6 folder tanpa git: --all menjelajah folder, node_modules dilewati",
        rc == 1 and set(temuan(out)) == {"README.md:1"}, out)
    rc, out = jalan(n, "--staged")
    cek("T6 --staged di luar git: exit 2", rc == 2, out)
    rc, out = jalan(a)
    cek("T6 tanpa mode: exit 2", rc == 2, out)
    rc, out = jalan(a, "--all", "docs")
    cek("T6 --all bersama path: exit 2", rc == 2, out)
    k = tmp / "kosong"
    k.mkdir()
    git(k, "init", "-q")
    tulis(k, {"a.md": "awal\n", "b.md": "sesi head memutuskan format\n"})
    git(k, "add", "a.md")
    rc, out = jalan(k, "--worktree")
    cek("T6 --worktree di repo tanpa commit: perubahan ter-stage dan file baru tetap dicek",
        rc == 1 and set(temuan(out)) == {"b.md:1"}, out)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\nRESULT: {'ALL OK' if all(hasil) and hasil else 'SOME FAILED'} ({sum(hasil)}/{len(hasil)})")
sys.exit(0 if all(hasil) and hasil else 1)
