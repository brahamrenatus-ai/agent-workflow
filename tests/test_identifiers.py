"""Uji pengenal berbahasa Inggris (v3.20) dan kata keluaran alat (v3.20.1): protokol lama dan baru dikenali `check_version.py`.

Fixture dibuat dari teks penuh template tanpa tag, jadi penanda teks hanya terpenuhi oleh teksnya:
- protokol bernama baru (template apa adanya): tanpa kandidat patch, versi efektif = versi penanda tertinggi;
- protokol bernama lama (pengenal template dikembalikan ke nama sebelum v3.20, salinan `check_evidence.py` tanpa
  status NONE): tepat penanda v3.20 yang menjadi kandidat, dan penanda lama yang memuat pengenal tetap dikenali
  lewat nama lamanya;
- protokol berkata keluaran lama (kata keluaran alat di instruksi dan salinan alat dikembalikan ke kata sebelum
  v3.20.1): tepat penanda v3.20.1 yang menjadi kandidat.
Juga dicek: `SKILL.md` dan `references/` tanpa nama dan kata lama, kecuali tabel padanan v3.20 dan v3.20.1 dan blok
penanda changelog.
Pemakaian: python -X utf8 tests/test_identifiers.py <folder skill>"""
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
SKILL = Path(sys.argv[1]).resolve()
CEK = SKILL / "scripts" / "check_version.py"
ok = True


def cek(cond, msg, out=""):
    global ok
    print(("OK    " if cond else "FAIL  ") + msg)
    if not cond and out:
        print("      " + out.replace("\n", "\n      "))
    ok = ok and cond


cl = (SKILL / "references" / "changelog.md").read_text(encoding="utf-8")
if "## v3.20 " not in cl:
    print("SKIP  uji pengenal: skill sebelum v3.20")
    print("\nRESULT: ALL OK")
    sys.exit(0)

# Padanan v3.20 (lama, baru). Uji ini salah satu dari sedikit tempat nama lama boleh ditulis.
PADANAN = [
    ("TIDAK DIUJI", "UNTESTED"), ("TIDAK YAKIN", "UNSURE"), ("TIDAK ADA", "NONE"), ("DITEMUKAN", "FOUND"),
    ("TUNGGU-USER", "WAIT-USER"), ("STRUKTUR", "STRUCTURE"), ("FAKTA", "FACT"),
    ("TINGGI", "HIGH"), ("SEDANG", "MEDIUM"), ("RENDAH", "LOW"),
    ("WAJIB", "REQUIRED"), ("STANDAR", "STANDARD"), ("SELERA", "PREFERENCE"),
    ("GAGAL", "FAIL"), ("HIPOTESIS", "HYPOTHESIS"), ("USULAN", "PROPOSAL"),
    ("BELUM", "TODO"), ("SEBAGIAN", "PARTIAL"), ("PARKIR", "PARKED"),
]


def kata(k):
    # huruf besar saja; nama file STRUCTURE.md/STRUKTUR.md bukan pengenal
    return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(k) + r"(?![A-Za-z0-9_])(?!\.md)")


LAMA = [(kata(baru), lama) for lama, baru in PADANAN]
POLA_LAMA = re.compile("|".join(kata(lama).pattern for lama, _ in PADANAN))
# Kata keluaran alat sebelum v3.20.1 (padanan di changelog §v3.20.1; GAGAL sudah ada di PADANAN).
POLA_KELUARAN = re.compile("|".join(kata(k).pattern for k in (
    "AMAN", "BESAR", "RAPIKAN", "TIDAK DIKETAHUI", "PESAN", "GALAT", "JADWAL", "BATAL", "SELESAI", "MASALAH",
    "PERINGATAN", "LOLOS")))
# Kata keluaran di teks protokol dikembalikan ke kata sebelum v3.20.1 menurut konteksnya di template.
KELUARAN_PROTOKOL = [(r"`LARGE`", "`BESAR`"), (r"`TIDY`", "`RAPIKAN`"), (r"`MESSAGE`", "`PESAN`"), (r"`ERROR`", "`GALAT`"),
                     (r"\bmenulis ERROR\b", "menulis GALAT"), (r"\b(setiap|ada|0) ERROR\b", r"\1 MASALAH")]
# Salinan alat sebelum v3.20.1: kata pembuka lama, tanpa pencarian cadangan yang melewati log yang diabaikan git.
KELUARAN_ALAT = {
    "check_evidence.py": [(r"def log_bersama", "def log_semua"), (r'"ERROR"', '"MASALAH"'), (r'"WARNING"', '"PERINGATAN"')],
    "context_size.py": [(r"\bLARGE\b", "BESAR"), (r"\bTIDY\b", "RAPIKAN"), (r"\bUNKNOWN\b", "TIDAK DIKETAHUI")],
    "orca_wait.py": [(r"\bMESSAGE\b", "PESAN"), (r"\bERROR\b", "GALAT")],
    "head_restart.py": [(r"\bSCHEDULED\b", "JADWAL"), (r"\bERROR\b", "GALAT"), (r"\bCANCELLED\b", "BATAL")],
    "check_secrets.py": [(r"\bWARNING:", "PERINGATAN:")],
}
SISA_KELUARAN = re.compile(r"\b(ERROR|WARNING|LARGE|TIDY|MESSAGE|SCHEDULED|UNKNOWN)\b")


def ke_lama(teks):
    for rx, lama in LAMA:
        teks = rx.sub(lama, teks)
    return teks


def ganti(teks, aturan):
    for pola, lama in aturan:
        teks = re.sub(pola, lama, teks)
    return teks


tp = (SKILL / "references" / "templates.md").read_text(encoding="utf-8")
TAG = re.compile(r"<!--\s*aw:[^>]*?-->")


def seksi(nama):
    return TAG.sub("", tp.split(f"### {nama} ")[1].split("\n### ")[0].split("\n## Penyesuaian")[0])


blok = re.search(r"```penanda\n(.*?)\n```", cl, re.S).group(1)
baris = [l.split(None, 2) for l in blok.splitlines() if l.strip() and not l.lstrip().startswith("#")]
kunci = lambda v: tuple(int(x) for x in v.split("."))  # noqa: E731
versi = sorted({r[0] for r in baris}, key=kunci)
v320 = {r[1] for r in baris if r[0] == "3.20"}
v3201 = {r[1] for r in baris if r[0] == "3.20.1"}
sebelum = [v for v in versi if kunci(v) < (3, 20)][-1]
sebelum_3201 = [v for v in versi if kunci(v) < (3, 20, 1)][-1]


def isi(teks, ver):
    return (teks.replace("{{TOOL_HEAD}}", "Claude Code").replace("{{TOOL_EXECUTOR}}", "Claude Code")
            .replace("{{PATH_HEAD}}", ".claude/skills/demo-head/SKILL.md").replace("{{VERSI_SKILL}}", ver))


def buat(root, lama, keluaran_lama=False):
    ver = sebelum if lama else (sebelum_3201 if keluaran_lama else versi[-1])
    ubah = ke_lama if lama else ((lambda t: ganti(t, KELUARAN_PROTOKOL)) if keluaran_lama else (lambda t: t))
    f = {
        ".claude/skills/demo-head/SKILL.md": seksi("T1"),
        ".claude/skills/demo-executor/SKILL.md": seksi("T2a"),
        "handoff/README.md": seksi("T3"),
        "handoff/ROADMAP.md": seksi("T4"),
        "handoff/NOTES.md": seksi("T5"),
        "handoff/reports/REPORT_TEMPLATE.md": seksi("T6"),
        "handoff/STRUCTURE.md": seksi("T9"),
        "handoff/PROMPT_EXECUTOR.md": "Model: demo (high). Kamu adalah executor demo.\n",
    }
    for rel, teks in f.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(ubah(isi(teks, ver)), encoding="utf-8")
    (root / ".env").write_text("API_TOKEN=abcdefghijklmnop1234\n", encoding="utf-8")
    (root / "web").mkdir()
    (root / "web/index.html").write_text("<!doctype html><title>demo</title>\n", encoding="utf-8")
    (root / "handoff/tools").mkdir(parents=True, exist_ok=True)
    for s in ("record.py", "check_evidence.py", "check_secrets.py", "screenshot.py", "orca_wait.py", "context_size.py", "head_restart.py"):
        shutil.copy(SKILL / "scripts" / s, root / "handoff/tools" / s)
    if lama:  # salinan check_evidence.py sebelum v3.20 belum mengenal status NONE
        p = root / "handoff/tools/check_evidence.py"
        p.write_text(p.read_text(encoding="utf-8").replace('"NONE"', '"TIDAK ADA"'), encoding="utf-8")
    if keluaran_lama:
        for s, aturan in KELUARAN_ALAT.items():
            p = root / "handoff/tools" / s
            p.write_text(ganti(p.read_text(encoding="utf-8"), aturan), encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, capture_output=True)


def jalan(root):
    r = subprocess.run([sys.executable, str(CEK)], cwd=root, capture_output=True, text=True, encoding="utf-8")
    out = r.stdout + r.stderr
    return r.returncode, out, set(re.findall(r"^  - ([A-Z0-9-]+) \(", out, re.M))


tmp = Path(tempfile.mkdtemp(prefix="cek_pengenal_"))
try:
    cek(v320 == {"N14", "N15", "N16", "N17", "N18", "N19", "Y17"}, f"penanda v3.20: N14–N19 dan Y17 ({sorted(v320)})")
    a = tmp / "baru"
    buat(a, lama=False)
    rc, out, hilang = jalan(a)
    cek(rc == 0 and not hilang and f"Versi efektif: v{versi[-1]}" in out,
        f"protokol bernama baru tanpa tag: tanpa kandidat patch, versi efektif v{versi[-1]}", out)
    cek("file secret lokal: ada | UI: ada" in out and "| Orca: ada" in out, "fixture memakai syarat @bila_secret, @bila_ui, dan @bila_orca", out)
    readme_baru = (a / "handoff/README.md").read_text(encoding="utf-8")
    cek(POLA_LAMA.search(readme_baru) is None, "README protokol baru tanpa nama lama")

    b = tmp / "lama"
    buat(b, lama=True)
    rc, out, hilang = jalan(b)
    cek(rc == 1 and hilang == v320, f"protokol bernama lama: tepat penanda v3.20 yang jadi kandidat ({sorted(hilang)})", out)
    cek(f"Versi efektif: v{sebelum}" in out, f"protokol bernama lama: versi efektif v{sebelum}", out)
    readme = (b / "handoff/README.md").read_text(encoding="utf-8")
    cek("| STRUKTUR |" in readme and "| FAKTA | Daftar pertanyaan" in readme and "berformat SEDANG" in readme,
        "fixture lama memuat nama lama yang dicari penanda S2, L1, E3")
    for pid in ("S2", "E3", "L1", "L2", "L3", "Y3"):
        spec = next((r[2] for r in baris if r[1] == pid), "")
        cek("||" in spec and POLA_LAMA.search(spec.split("||")[0]) and not POLA_LAMA.search(spec.split("||")[1]),
            f"penanda {pid} menerima nama lama dan baru ({spec.strip()})")

    ada_3201 = "## v3.20.1 " in cl
    if ada_3201:
        cek(v3201 == {"N20", "N21", "Y18", "Y19", "Y20", "Y21", "Y22"}, f"penanda v3.20.1: N20, N21, Y18–Y22 ({sorted(v3201)})")
        c = tmp / "keluaran_lama"
        buat(c, lama=False, keluaran_lama=True)
        sisa = {rel: SISA_KELUARAN.findall((c / rel).read_text(encoding="utf-8"))
                for rel in (".claude/skills/demo-head/SKILL.md", ".claude/skills/demo-executor/SKILL.md", "handoff/README.md")}
        cek(not any(sisa.values()), f"fixture berkata keluaran lama tanpa kata keluaran baru ({sisa})")
        rc, out, hilang = jalan(c)
        cek(rc == 1 and hilang == v3201, f"protokol berkata keluaran lama: tepat penanda v3.20.1 yang jadi kandidat ({sorted(hilang)})", out)
        cek(re.search(rf"^Versi efektif: v{re.escape(sebelum_3201)} ", out, re.M) is not None,
            f"protokol berkata keluaran lama: versi efektif v{sebelum_3201}", out)
    else:
        print("SKIP  uji kata keluaran alat: skill sebelum v3.20.1")

    # Teks skill: nama dan kata lama hanya di tabel padanan (v3.20, v3.20.1) dan blok penanda changelog.
    for rel in ["SKILL.md"] + sorted(f"references/{p.name}" for p in (SKILL / "references").glob("*.md")):
        t = (SKILL / rel).read_text(encoding="utf-8")
        if rel.endswith("changelog.md"):
            for judul in ("## v3.20 ", "## v3.20.1 "):
                v = t.split(judul)[1].split("\n## ")[0] if judul in t else ""
                tabel = v.split("| Lama | Baru |")[1].split("\n\n")[0] if "| Lama | Baru |" in v else ""
                t = t.replace(tabel, "") if tabel else t
            t = t.replace(blok, "")
        temuan = [m.group(0) for m in POLA_LAMA.finditer(t)]
        if ada_3201:
            temuan += [m.group(0) for m in POLA_KELUARAN.finditer(t)]
        cek(not temuan, f"{rel} tanpa nama{' dan kata keluaran' if ada_3201 else ''} lama di luar tabel padanan dan blok penanda ({temuan[:5]})")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("\nRESULT:", "ALL OK" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
