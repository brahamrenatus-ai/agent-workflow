"""Uji check_version.py v3.10: penanda dikenali lewat tag <!-- aw: ID --> walau teks protokol bukan bahasa Indonesia,
syarat @bila_ui, (sejak v3.11) syarat @bila_orca, dan (sejak v3.12) penanda nama lama `tiada~`. Fixture dibuat dari template skill: setiap baris dibuang teksnya, hanya tag yang disisakan,
lalu diberi teks pengisi berbahasa Inggris. Dengan begitu satu-satunya jalan penanda teks terpenuhi adalah tag.
Pemakaian: python -X utf8 tests/test_check_version_tags.py <folder skill>"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(sys.argv[1]).resolve()
CEK = SKILL / "scripts" / "check_version.py"
ok = True


def cek(cond, msg, out=""):
    global ok
    print(("OK    " if cond else "GAGAL ") + msg)
    if not cond and out:
        print("      " + out.replace("\n", "\n      "))
    ok = ok and cond


if "def punya_tag" not in CEK.read_text(encoding="utf-8"):
    print("LEWAT uji tag: check_version.py versi lama")
    print("\nHASIL: SEMUA OK")
    sys.exit(0)

tp = (SKILL / "references" / "templates.md").read_text(encoding="utf-8")
TAG = re.compile(r"<!--\s*aw:[^>]*?-->")


def seksi(nama):
    return tp.split(f"### {nama} ")[1].split("\n### ")[0].split("\n## Penyesuaian")[0]


def hanya_tag(nama, dengan_tag=True):
    """Isi template tanpa teks berbahasa Indonesia: tiap baris diganti teks Inggris pengisi, ditambah tag-nya bila ada."""
    keluar = []
    for b in seksi(nama).splitlines():
        tags = TAG.findall(b) if dengan_tag else []
        keluar.append(("lorem ipsum rule text " + " ".join(tags)).strip())
    return "\n".join(keluar) + "\n"


def buat(root, executor="T2a", dengan_tag=True, ui=True):
    f = {
        ".claude/skills/demo-head/SKILL.md": hanya_tag("T1", dengan_tag),
        f".claude/skills/demo-executor/SKILL.md": hanya_tag(executor, dengan_tag),
        "handoff/ROADMAP.md": hanya_tag("T4", dengan_tag),
        "handoff/NOTES.md": hanya_tag("T5", dengan_tag),
        "handoff/reports/REPORT_TEMPLATE.md": hanya_tag("T6", dengan_tag),
        "handoff/STRUCTURE.md": hanya_tag("T9", dengan_tag),
        "handoff/PROMPT_EXECUTOR.md": "Run the task.\n" + ("<!-- aw: M3 -->\n" if dengan_tag else ""),
        "handoff/README.md": ("# Handoff demo\n> Created with agent-workflow v3.10\n- **Head:** `.claude/skills/demo-head/SKILL.md` · tool: Claude Code\n"
                              "## Executor Profile\n- Tool: Claude Code\n" + hanya_tag("T3", dengan_tag)),
        ".env": "API_TOKEN=abcdefghijklmnop1234\n",
        "src/main.py": "print('hi')\n",
    }
    if ui:
        f["web/index.html"] = "<!doctype html><title>demo</title>\n"
    for rel, isi in f.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(isi, encoding="utf-8")
    for s in ("record.py", "check_evidence.py", "check_secrets.py", "screenshot.py", "orca_wait.py", "context_size.py"):
        (root / "handoff/tools").mkdir(parents=True, exist_ok=True)
        if (SKILL / "scripts" / s).is_file():  # screenshot.py ada sejak v3.10.1, orca_wait.py sejak v3.16, context_size.py sejak v3.17
            shutil.copy(SKILL / "scripts" / s, root / "handoff/tools" / s)
    subprocess.run(["git", "init", "-q"], cwd=root, capture_output=True)


def jalan(root):
    r = subprocess.run([sys.executable, str(CEK)], cwd=root, capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


versi = re.search(r"\*\*Versi skill: (\d+(?:\.\d+)*)\.\*\*", (SKILL / "SKILL.md").read_text(encoding="utf-8")).group(1)
tmp = Path(tempfile.mkdtemp(prefix="cekversi_tag_"))
try:
    a = tmp / "inggris"
    buat(a)
    rc, out = jalan(a)
    cek(rc == 0 and f"Versi efektif: v{versi}" in out and "Kandidat patch" not in out,
        f"protokol tanpa teks Indonesia, hanya tag: versi efektif v{versi}, tanpa kandidat patch", out)
    cek("file secret lokal: ada | UI: ada" in out, "syarat @bila_secret dan @bila_ui terdeteksi (.env, web/index.html)", out)

    b = tmp / "rendah"
    buat(b, executor="T2b")
    rc, out = jalan(b)
    cek(rc == 0 and f"Versi efektif: v{versi}" in out, "varian RENDAH (T2b sebagai brief executor): semua penanda executor dikenali lewat tag", out)

    c = tmp / "tanpa_tag"
    buat(c, dengan_tag=False)
    rc, out = jalan(c)
    hilang = set(re.findall(r"^  - ([A-Z0-9-]+) \(", out, re.M))
    cek(rc == 1 and {"B2", "V3-1", "X2", "Z1", "I1"} <= hilang and "Versi efektif: di bawah" in out,
        "pembanding tanpa tag: penanda teks hilang (yang memenuhi di uji pertama memang tag)", out)
    cek(not ({"B1", "C1", "Y1", "Y2", "Y5", "Y7", "Z2", "Y6", "K1", "K2"} & hilang),
        "penanda netral bahasa (file ada, nama fungsi skrip, tool tercatat) tetap terpenuhi tanpa tag", out)

    d = tmp / "tanpa_ui"
    buat(d, ui=False)
    for rel in (".claude/skills/demo-head/SKILL.md", ".claude/skills/demo-executor/SKILL.md", "handoff/README.md"):
        p = d / rel
        p.write_text(re.sub(r"\b(I1|I2|I3)\b", "XX", p.read_text(encoding="utf-8")), encoding="utf-8")
    rc, out = jalan(d)
    cek(rc == 0 and "UI: tidak ada" in out and f"Versi efektif: v{versi}" in out,
        "project tanpa UI: I1–I3 n/a walau aturannya tidak ada", out)
    (d / "handoff/logs").mkdir(parents=True)
    (d / "handoff/logs/dasbor.html").write_text("<html></html>\n", encoding="utf-8")
    rc, out = jalan(d)
    cek("UI: tidak ada" in out, "file HTML di handoff/ (log) tidak membuat project dianggap ber-UI", out)
    (d / "package.json").write_text('{"dependencies": {"react": "^19.0.0"}}\n', encoding="utf-8")
    rc, out = jalan(d)
    cek("UI: ada" in out and rc == 1 and "I1" in out, "package.json dengan react: project ber-UI, I1–I3 jadi kandidat", out)

    if "def root_repo(folder" in CEK.read_text(encoding="utf-8"):  # path project sebagai argumen sejak v3.15
        def jalan_dari(cwd, *args):
            r = subprocess.run([sys.executable, str(CEK), *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8")
            return r.returncode, r.stdout, r.stderr

        rc0, out0 = jalan(a)
        rc, out, err = jalan_dari(tmp, str(a / "handoff"))
        cek(rc == rc0 and out == out0, "path project sebagai argumen (dari folder lain, menunjuk subfolder project): hasil sama dengan dijalankan di root", out + err)
        rc, out, err = jalan_dari(a, "--root", str(b))
        cek(rc == 2 and "tidak dikenal" in err and "Root:" not in out, "opsi tidak dikenal: exit 2, tidak diam-diam memeriksa folder kerja", out + err)
        rc, out, err = jalan_dari(a, str(tmp / "tidak-ada"))
        cek(rc == 2 and "tidak ada" in err, "path yang tidak ada: exit 2", out + err)

    e = tmp / "id_mirip"
    buat(e)
    p = e / ".claude/skills/demo-executor/SKILL.md"
    p.write_text(p.read_text(encoding="utf-8").replace("Z1", "Z10"), encoding="utf-8")
    rc, out = jalan(e)
    cek(rc == 1 and re.search(r"^  - Z1 \(", out, re.M), "tag dicocokkan per ID utuh (Z10 bukan Z1)", out)

    if "def ada_orca" in CEK.read_text(encoding="utf-8"):  # syarat @bila_orca ada sejak v3.11
        rc, out = jalan(a)
        cek("| Orca: tidak ada" in out, "protokol tanpa kata Orca: syarat @bila_orca tidak terpenuhi", out)
        f = tmp / "orca"
        buat(f)
        p = f / "handoff/README.md"
        p.write_text(p.read_text(encoding="utf-8") + "- Executors are launched by the head through Orca.\n", encoding="utf-8")
        rc, out = jalan(f)
        cek(rc == 0 and "| Orca: ada" in out and f"Versi efektif: v{versi}" in out,
            "README menyebut Orca, aturan Orca bertag: syarat terpenuhi dan D4–D6 dikenali lewat tag", out)
        for rel in (".claude/skills/demo-head/SKILL.md", ".claude/skills/demo-executor/SKILL.md", "handoff/README.md"):
            p = f / rel
            p.write_text(re.sub(r"\b(D4|D5|D6)\b", "XX", p.read_text(encoding="utf-8")), encoding="utf-8")
        rc, out = jalan(f)
        hilang = set(re.findall(r"^  - ([A-Z0-9-]+) \(", out, re.M))
        cek(rc == 1 and hilang == {"D4", "D5", "D6"}, "project memakai Orca tanpa aturan Orca: tepat D4, D5, D6 jadi kandidat", out)
        g = tmp / "orca_di_head"
        buat(g)
        p = g / ".claude/skills/demo-head/SKILL.md"
        p.write_text(p.read_text(encoding="utf-8") + "Dispatch executors with ORCA.\n", encoding="utf-8")
        rc, out = jalan(g)
        cek(rc == 0 and "| Orca: ada" in out, "kata Orca di instruksi head juga memenuhi syarat (tanpa peka huruf besar-kecil)", out)
        p = g / "handoff/README.md"
        p.write_text(p.read_text(encoding="utf-8") + "- Model orcanet-7b; whales: orcas.\n", encoding="utf-8")
        p = g / ".claude/skills/demo-head/SKILL.md"
        p.write_text(p.read_text(encoding="utf-8").replace("ORCA", "orcanet"), encoding="utf-8")
        rc, out = jalan(g)
        cek("| Orca: tidak ada" in out, "kata yang hanya memuat 'orca' (orcanet, orcas) tidak dihitung", out)
    if "tiada~" in CEK.read_text(encoding="utf-8"):  # penanda nama lama ada sejak v3.12
        n = tmp / "nama_lama"
        buat(n)
        for lama, baru in (("cek_bukti.py", "check_evidence.py"), ("catat.py", "record.py"),
                           ("cek_secret.py", "check_secrets.py"), ("foto_tampilan.py", "screenshot.py")):
            (n / "handoff/tools" / baru).rename(n / "handoff/tools" / lama)
        (n / "handoff/STRUCTURE.md").rename(n / "handoff/STRUKTUR.md")
        (n / "handoff/logs").mkdir(parents=True, exist_ok=True)
        (n / "handoff/logs/asal.jsonl").write_text("", encoding="utf-8")
        rc, out = jalan(n)
        hilang = set(re.findall(r"^  - ([A-Z0-9-]+) \(", out, re.M))
        cek(rc == 1 and hilang == {"N2", "N3", "N4", "N5", "N6", "N8"},
            "project bernama lama: tepat N2–N6 dan N8 jadi kandidat; penanda versi lama tetap dikenali lewat nama lama", out)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("\nHASIL:", "SEMUA OK" if ok else "ADA YANG GAGAL")
sys.exit(0 if ok else 1)
