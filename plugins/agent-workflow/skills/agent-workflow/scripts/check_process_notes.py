#!/usr/bin/env python3
"""Cek catatan proses kerja di file produk sebelum commit (agent-workflow, sejak v3.22).

Skill agent-workflow memasang skrip ini ke handoff/tools/check_process_notes.py. File produk (kode, test, README, docs/)
hanya memuat isi teknis. Catatan proses kerja ditulis di handoff/ (task, report, register NOTES): siapa menulis,
memutuskan, atau mengecek; sesi dan model agen; kutipan dan persetujuan user; tinjauan internal; bahasa dokumen; tautan
sesi atau Artifact; larangan untuk agen; nomor task, report, atau item ROADMAP. Catatan seperti itu tidak berguna bagi
pembaca kode, ikut ter-push, dan di repo tim terbaca anggota yang tidak memakai alur agen.

Temuan diawali satu kata:
- PROCESS: frasa proses kerja, mis. "ditulis head", "keputusan user", "sesi diskusi", "tinjauan internal",
  "keterangan berbahasa Indonesia", "reviewed by the head agent", tautan claude.ai, model Claude beserta effort-nya,
  dan kutipan user (`user: "..."`) di komentar atau dokumen;
- REF: nomor task/report/item (TASK-012, REPORT-012, SPIKE-03, R-FIX-01) di semua file produk, dan rujukan lapisan agen
  (handoff/, ROADMAP §3, ROADMAP R4, NOTES.md, register NOTES, SKILL-FEEDBACK, BOARD.md, *-handoff.md) bila handoff/
  tidak ter-track di repo ini (lapisan agen privat). Di repo yang memuat handoff/, rujukan itu tautan yang berjalan.

File produk = file teks di luar lapisan agen. Lapisan agen: handoff/ di root; folder instruksi agen (.claude/, .agents/,
.agent/, .cursor/, .windsurf/, .clinerules); CLAUDE.md, CLAUDE.local.md, AGENTS.md, GEMINI.md, CONVENTIONS.md; NOTES.md,
NOTES_ARCHIVE.md, ROADMAP.md, dan SKILL-FEEDBACK.md di root (LITE). Lockfile, file minified, file biner, dan file
> 2 MB dilewati.

Pemakaian (dari root project):
  python handoff/tools/check_process_notes.py --staged                   # baris tambahan di diff ter-stage
  python handoff/tools/check_process_notes.py --staged --message "<pesan commit>"
  python handoff/tools/check_process_notes.py --worktree                 # baris tambahan terhadap HEAD + file baru
  python handoff/tools/check_process_notes.py --worktree --message <file pesan>   # blok commit yang diserahkan ke user
  python handoff/tools/check_process_notes.py --all [--summary]          # isi utuh file produk ter-track (audit)
  python handoff/tools/check_process_notes.py docs src/main.py           # isi utuh file atau folder tertentu

--staged dan --worktree hanya memeriksa baris yang ditambah atau diubah, jadi isi lama tidak menghalangi commit. Baris
lama yang diubah ikut dicek, sehingga catatan prosesnya dibuang sekalian.
--message (teks, path file, atau - untuk stdin): PROCESS selalu, REF hanya bila lapisan agen privat, karena di repo yang
memuat handoff/ nomor task memang tempatnya di pesan commit. Bersama --staged/--worktree, pesan tidak dicek bila diff
tidak memuat file produk (commit lapisan agen). Baris komentar git di file pesan commit (COMMIT_EDITMSG, hook
commit-msg) dan trailer (Co-Authored-By:, Signed-off-by:, "Generated with ...") tidak dicek; atribusi diatur setelan tool.
Di dalam repo handoff/ yang terpisah (lapisan agen privat dengan git sendiri) semua file adalah lapisan agen.

Penyesuaian per project, dibawa dari salinan lama saat upgrade seperti SECRET_FILES di check_secrets.py:
- EXCLUDE: pola path tambahan yang bukan file produk (mis. "graphify-out/"), juga lewat --exclude;
- ALLOW: regex teks yang memang isi produk walau mirip catatan proses (mis. r"permintaan user" bila "user" berarti
  pengguna aplikasi). Bagian baris yang cocok dibuang sebelum dicek; sisa barisnya tetap dicek.

Exit code: 0 = bersih, 1 = ada temuan, 2 = salah pakai.
"""
import argparse
import fnmatch
import glob
import os
import re
import subprocess
import sys
from pathlib import Path

# Diisi per project saat dipasang (relatif terhadap root repo), mis. EXCLUDE = ["graphify-out/"].
EXCLUDE = []
# Regex teks yang memang isi produk, mis. ALLOW = [r"permintaan user"].
ALLOW = []

AGEN_FOLDER = {".claude", ".agents", ".agent", ".cursor", ".windsurf", ".clinerules"}  # di kedalaman mana pun
AGEN_NAMA = {"claude.md", "claude.local.md", "agents.md", "gemini.md", "conventions.md"}  # nama file di mana pun
AGEN_ROOT = {"notes.md", "notes_archive.md", "roadmap.md", "skill-feedback.md"}  # file di root (LITE)
LEWATI_FOLDER = {".git", "node_modules", ".venv", "venv", "__pycache__", ".pio", "build", "dist", ".next"}
LOCKFILE = {"package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "pipfile.lock",
            "cargo.lock", "composer.lock", "gemfile.lock", "go.sum", "uv.lock"}
LEWATI_AKHIRAN = (".min.js", ".min.css", ".map", ".lock")
DOKUMEN = {".md", ".markdown", ".txt", ".rst", ".adoc"}
# Baris pola (bukan komentar) di file ignore menulis path lapisan agen apa adanya (mis. handoff/logs/TASK-0*.log), jadi
# REF tidak dicek di sana selama handoff/ ikut repo. Di lapisan agen privat, path itu sendiri bocoran.
FILE_IGNORE = {".gitignore", ".gitattributes", ".dockerignore", ".npmignore", ".prettierignore", ".eslintignore"}
MAKS_UKURAN = 2 * 1024 * 1024

PERAN = r"(?-i:head|executor|eksekutor)"  # huruf kecil: "HEAD" git dan <head> HTML bukan peran
TANGGAL = r"(?=.*\b20\d\d-[01]\d-[0-3]\d\b)"
# (label, keterangan, regex, hanya bila lapisan agen privat)
POLA = [
    ("PROCESS", "siapa menulis atau mengubah", re.compile(
        r"\bdi(?:tulis|buat|susun|perbarui|ubah|ganti|cek|verifikasi|pindah(?:kan)?|koreksi|tambahkan|usulkan|laporkan|"
        r"tinjau|kerjakan)\s+(?:oleh\s+)?(?:sesi\s+)?(?:" + PERAN + r"|(?-i:agen))\b", re.I), False),
    ("PROCESS", "keputusan atau catatan peran", re.compile(
        r"\b(?:keputusan|rekomendasi|usul(?:an)?|rujukan|patch|triase|catatan|hipotesis|tinjauan|koreksi|temuan|"
        r"analisis)\s+(?:sesi\s+)?" + PERAN + r"\b", re.I), False),
    ("PROCESS", "keputusan atau persetujuan user", re.compile(
        r"\b(?:keputusan|jawaban|pertanyaan|kata|menurut)\s+(?-i:user)\b|\batas\s+permintaan\s+(?-i:user)\b|"
        r"\b(?:disetujui|diputuskan|ditolak|diminta)\s+(?:oleh\s+)?(?-i:user)\b", re.I), False),
    ("PROCESS", "pembagian peran", re.compile(
        r"\b(?:milik|oleh|untuk|ke|dari)\s+(?:sesi\s+)?" + PERAN + r"\b|\b(?:jangan|tidak boleh)\s+(?:\w+\s+){0,2}"
        r"(?:oleh\s+)?(?-i:executor|eksekutor)\b|\b(?-i:executor|eksekutor)\s+(?:tidak boleh|jangan)\b", re.I), False),
    ("PROCESS", "sesi agen", re.compile(
        r"\bsesi\s+(?-i:head|diskusi|executor|eksekutor|samping|SPIKE|rancangan)\b|"
        r"\b(?-i:head|executor|side)\s+session\b", re.I), False),
    ("PROCESS", "tinjauan internal", re.compile(
        r"\b(?:tinjauan|diskusi|rapat)\s+internal\b|\binternal\s+(?:review|discussion)\b", re.I), False),
    ("PROCESS", "atribusi AI", re.compile(
        r"Co-Authored-By:|Generated with \[?Claude|\U0001F916 Generated|"
        r"\b(?:file|berkas|dokumen|kode|modul|test|skrip)\s+ini\s+(?:di(?:tulis|buat|susun|hasilkan))\s+(?:oleh|dengan)\s+"
        r"(?:AI|Claude|Gemini|ChatGPT|Copilot|LLM)\b|"
        r"\b(?:this|the)\s+(?:file|document|code|module|test|script)\s+(?:was\s+|is\s+)?(?:written|generated|created|"
        r"drafted)\s+(?:by|with)\s+(?:AI|Claude|Gemini|ChatGPT|Copilot|an?\s+LLM)\b", re.I), False),
    ("PROCESS", "model agen atau tautan sesi", re.compile(
        r"\b(?:Claude|Opus|Sonnet|Haiku|Fable)\b[^|\n]{0,20}\((?:low|medium|high|xhigh|max)\)|"
        r"claude\.ai/(?:artifact|code|chat|share|project)s?/|\b(?-i:head|executor) agent\b|\bagent-workflow\s+v\d", re.I),
     False),
    ("PROCESS", "bahasa dokumen", re.compile(
        r"\b(?:keterangan|dokumen\s+ini|prosa)\s+(?:ditulis\s+)?(?:dalam\s+)?(?:ber)?bahasa\s+(?:Indonesia|Inggris)\b|"
        r"\b(?:this\s+document|prose)\s+(?:is\s+)?(?:written\s+)?in\s+(?:English|Indonesian)\b", re.I), False),
    ("PROCESS", "siapa menulis atau memutuskan", re.compile(
        r"\b(?:written|drafted|reviewed|checked|verified|decided|approved|updated|changed)\s+by\s+(?:the\s+)?"
        r"(?-i:head|executor)(?:\s+(?:agent|session))?(?=\s*(?:$|[.,;:)\]|]|\s(?:on|at|in|for)\b))|"
        r"^" + TANGGAL + r".*?(?:\buser(?:'s)?\s+(?:decision|approval|request)\b|"
        r"\b(?:approved|decided|requested|confirmed)\s+by\s+(?:the\s+)?user\b)", re.I), False),
    ("REF", "nomor task/report/item", re.compile(r"\b(?:TASK|REPORT|SPIKE)-\d+[A-Za-z]?\b|\bR-[A-Z]{2,}-\d+"), False),
    ("REF", "rujukan lapisan agen", re.compile(
        r"\bhandoff/|\bSKILL-FEEDBACK\b|\bBOARD\.md\b|\bregister NOTES\b|"
        r"\b(?:ROADMAP|NOTES)(?:\.md\b|\s*§|\s+[A-Z]{1,4}-?\d+)|-handoff\.md\b"), True),
]
# Kutipan user (format bukti `user: "..."`) hanya dihitung di dokumen atau sesudah penanda komentar: di kode,
# `user: "..."` lazim sebagai data (objek JS, docker-compose).
KUTIP_USER = re.compile(r"\buser\s*:\s*[\"“]")
KOMENTAR = re.compile(r"//|#|/\*|^\s*\*|<!--|(?:^|\s)--\s|\"\"\"|'''")
TRAILER = re.compile(r"^\s*(?:Co-Authored-By|Signed-off-by|Reviewed-by|Acked-by)\s*:|Generated with \[?Claude Code|"
                     r"^\s*\U0001F916 Generated", re.I)
PETUNJUK = {
    "PROCESS": "tulis ulang sebagai isi teknis. Siapa menulis, memutuskan, atau mengecek, sesi, model, kutipan user, "
               "tinjauan internal, dan bahasa dokumen dicatat di handoff/ (report, register NOTES).",
    "REF": "hapus nomor task/report/item{rujukan} dari file produk; nomor task cukup ditulis di task dan report{pesan}.",
}


def siapkan_output():
    """Konsol Windows (cp1252) tidak boleh membuat skrip crash; output ke pipa/agen memakai UTF-8."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace") if s.isatty() else s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def git(root, *args):
    r = subprocess.run(["git", "-C", str(root), "-c", "core.quotepath=false", *args], capture_output=True)
    return r.returncode, r.stdout.decode("utf-8", errors="replace")


def root_repo():
    try:
        rc, out = git(Path.cwd(), "rev-parse", "--show-toplevel")
    except OSError:
        return Path.cwd(), False
    return (Path(out.strip()), True) if rc == 0 and out.strip() else (Path.cwd(), False)


def lapisan_agen(rel):
    bagian = [p.lower() for p in rel.replace("\\", "/").split("/") if p and p != "."]
    if not bagian:
        return False
    if (len(bagian) > 1 and bagian[0] == "handoff") or (len(bagian) == 1 and bagian[0] in AGEN_ROOT):
        return True
    return any(p in AGEN_FOLDER for p in bagian) or bagian[-1] in AGEN_NAMA


def dikecualikan(rel, pola):
    rel = rel.replace("\\", "/")
    for p in pola:
        p = p.replace("\\", "/")
        p = p[2:] if p.startswith("./") else p
        if any(c in p for c in "*?["):
            if fnmatch.fnmatch(rel, p):
                return True
        elif rel == p.rstrip("/") or rel.startswith(p.rstrip("/") + "/"):
            return True
    return False


def bukan_teks_produk(rel):
    nama = rel.replace("\\", "/").rsplit("/", 1)[-1].lower()
    return nama in LOCKFILE or nama.endswith(LEWATI_AKHIRAN)


def jenis(rel):
    return "doc" if Path(rel).suffix.lower() in DOKUMEN else "code"


def unquote(p):
    """Path bertanda kutip gaya C dari keluaran git (karakter kontrol, kutip, garis miring terbalik)."""
    if not (len(p) >= 2 and p[0] == p[-1] == '"'):
        return p
    s, out, i = p[1:-1], bytearray(), 0
    esc = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            if re.match(r"[0-7]{3}", s[i + 1:i + 4]):
                out.append(int(s[i + 1:i + 4], 8))
                i += 4
                continue
            out.append(esc.get(s[i + 1], ord(s[i + 1]) & 0xFF))
            i += 2
            continue
        out += s[i].encode("utf-8")
        i += 1
    return out.decode("utf-8", errors="replace")


def baris_tambahan(root, *args):
    """{path: [(nomor baris, teks)]} untuk baris yang ditambah di diff. Isi hunk dihitung dari kepala @@, karena baris
    tambahan yang diawali "++ " tampil sebagai "+++ " seperti kepala file."""
    rc, out = git(root, "diff", *args, "-U0", "--no-color", "--no-ext-diff", "--diff-filter=ACMR")
    if rc != 0:
        return None
    hasil, cur, no, sisa_hapus, sisa_tambah = {}, None, 0, 0, 0
    for b in out.split("\n"):
        if sisa_hapus or sisa_tambah:
            if b.startswith("+"):
                if cur is not None:
                    hasil[cur].append((no, b[1:].rstrip("\r")))
                no += 1
                sisa_tambah -= 1
            elif b.startswith("-"):
                sisa_hapus -= 1
            continue
        if b.startswith("+++ "):
            p = unquote(b[4:].rstrip("\t"))
            cur = None if p == "/dev/null" else (p[2:] if p.startswith("b/") else p)
            if cur is not None:
                hasil.setdefault(cur, [])
        elif b.startswith("@@"):
            m = re.match(r"@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", b)
            if m:
                sisa_hapus = int(m.group(1)) if m.group(1) is not None else 1
                no = int(m.group(2))
                sisa_tambah = int(m.group(3)) if m.group(3) is not None else 1
    return hasil


def isi_file(path):
    """[(nomor baris, teks)] atau None untuk file biner, terlalu besar, atau tidak terbaca."""
    try:
        if path.stat().st_size > MAKS_UKURAN:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:8192]:
        return None
    return [(i, b.rstrip("\r")) for i, b in enumerate(data.decode("utf-8", errors="replace").split("\n"), 1)]


def ls_files(root, *args):
    rc, out = git(root, "ls-files", "-z", *args)
    return [p for p in out.split("\0") if p] if rc == 0 else []


def jelajah(folder):
    for dp, dns, fns in os.walk(folder):
        dns[:] = [d for d in dns if d not in LEWATI_FOLDER]
        for f in fns:
            yield Path(dp) / f


def relatif(root, p):
    try:
        return Path(os.path.abspath(p)).relative_to(Path(os.path.abspath(root))).as_posix()
    except ValueError:
        return Path(p).as_posix()


def kumpulkan_path(root, di_git, paths):
    """File dari argumen path (file, folder, atau glob), relatif terhadap root."""
    hasil = []
    for a in paths:
        calon = glob.glob(a, recursive=True) if any(c in a for c in "*?[") else [a]
        for c in calon:
            if os.path.isdir(c):
                if di_git:
                    rel = relatif(root, c)
                    hasil += ls_files(root, "--cached", "--others", "--exclude-standard", "--", rel or ".")
                else:
                    hasil += [relatif(root, f) for f in jelajah(c)]
            elif os.path.isfile(c):
                hasil.append(relatif(root, c))
            else:
                print(f"WARNING: {a} tidak ada; dilewati.")
    return list(dict.fromkeys(hasil))


def cek_baris(teks, kind, privat, ref, allow):
    """Daftar (label, keterangan, posisi) untuk satu baris."""
    for rx in allow:
        teks = rx.sub(lambda m: " " * len(m.group(0)), teks)  # panjang tetap, supaya posisi cuplikan tidak bergeser
    hasil = []
    for label, ket, rx, hanya_privat in POLA:
        if (label == "REF" and not ref) or (hanya_privat and not privat):
            continue
        m = rx.search(teks)
        if m:
            hasil.append((label, ket, m.start()))
    m = KUTIP_USER.search(teks)
    if m and (kind == "doc" or KOMENTAR.search(teks[:m.start()])):
        hasil.append(("PROCESS", "kutipan user", m.start()))
    return hasil


def cuplikan(teks, posisi):
    """Potongan baris di sekitar temuan pertama, supaya temuan di ujung baris tabel yang panjang tetap terlihat."""
    mulai = max(0, posisi - 50)
    return ("…" if mulai else "") + teks[mulai:mulai + 150].strip()


def baca_pesan(arg):
    """[(nomor baris, teks)] dari --message, tanpa komentar git (file pesan commit) dan trailer."""
    if arg == "-":
        teks, file_git = sys.stdin.read(), False
    elif os.path.isfile(arg):
        p = Path(arg)
        teks = p.read_text(encoding="utf-8", errors="replace")
        file_git = p.name == "COMMIT_EDITMSG" or ".git" in p.resolve().parts
    else:
        teks, file_git = arg, False
    hasil = []
    for i, b in enumerate(teks.split("\n"), 1):
        b = b.rstrip("\r")
        if file_git and b.startswith("#"):
            if ">8" in b:
                break  # garis gunting `git commit -v`: diff di bawahnya bukan pesan
            continue
        if not TRAILER.search(b):
            hasil.append((i, b))
    return hasil


def main():
    ap = argparse.ArgumentParser(description="Cek catatan proses kerja di file produk (PROCESS) dan rujukan task atau "
                                             "lapisan agen (REF).")
    ap.add_argument("paths", nargs="*", help="file, folder, atau pola glob (isi utuh)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--staged", action="store_true", help="baris tambahan di diff ter-stage")
    mode.add_argument("--worktree", action="store_true", help="baris tambahan terhadap HEAD, ditambah file baru yang belum ter-track")
    mode.add_argument("--all", action="store_true", help="isi utuh semua file produk ter-track")
    ap.add_argument("--message", help="pesan commit atau deskripsi PR: teks, path file, atau - untuk stdin")
    ap.add_argument("--exclude", action="append", default=[], help="path atau pola glob tambahan yang bukan file produk (bisa berulang)")
    ap.add_argument("--summary", action="store_true", help="jumlah temuan per file, bukan per baris")
    a = ap.parse_args()
    siapkan_output()
    diff = a.staged or a.worktree
    if not (diff or a.all or a.paths or a.message is not None) or ((diff or a.all) and a.paths):
        ap.print_usage()
        print("Pilih satu: --staged, --worktree, --all, atau path; --message boleh sendiri atau bersama mode diff.")
        return 2
    try:
        allow = [re.compile(p, re.I) for p in ALLOW]
    except re.error as e:
        print(f"ERROR: regex ALLOW tidak valid: {e}")
        return 2
    root, di_git = root_repo()
    if diff and not di_git:
        print("ERROR: --staged dan --worktree butuh repo git.")
        return 2
    if di_git and root.name.lower() == "handoff":
        print("OK: repo ini lapisan agen (handoff/ dengan git sendiri); tidak ada file produk yang dicek.")
        return 0
    ada_handoff = (root / "handoff").is_dir()
    privat = di_git and ada_handoff and not ls_files(root, "--", "handoff")
    pola_kecuali = EXCLUDE + a.exclude

    unit, dilewati = {}, 0  # {path: [(no, teks)]}
    if diff:
        if a.staged:
            unit = baris_tambahan(root, "--cached")
        else:
            punya_head = git(root, "rev-parse", "--verify", "-q", "HEAD")[0] == 0
            unit = baris_tambahan(root, "HEAD") if punya_head else baris_tambahan(root, "--cached")
            if unit is not None:
                for rel in ls_files(root, "--others", "--exclude-standard"):
                    isi = isi_file(root / rel)
                    if isi is not None:
                        unit[rel] = isi
        if unit is None:
            print("ERROR: git diff gagal.")
            return 2
    elif a.all or a.paths:
        if a.all:
            daftar = ls_files(root) if di_git else [relatif(root, f) for f in jelajah(root)]
        else:
            daftar = kumpulkan_path(root, di_git, a.paths)
        for rel in daftar:
            if lapisan_agen(rel) or dikecualikan(rel, pola_kecuali) or bukan_teks_produk(rel):
                dilewati += 1
                continue
            isi = isi_file(root / rel)
            if isi is None:
                dilewati += 1
                continue
            unit[rel] = isi
    produk = {rel: isi for rel, isi in unit.items()
              if not (lapisan_agen(rel) or dikecualikan(rel, pola_kecuali) or bukan_teks_produk(rel))}
    if diff:
        dilewati = len(unit) - len(produk)

    temuan = []  # (lokasi, label-set, teks keluaran)
    per_file = {}
    for rel in sorted(produk):
        kind = jenis(rel)
        ignore = not privat and Path(rel).name.lower() in FILE_IGNORE
        for no, teks in produk[rel]:
            pola_ignore = ignore and not teks.lstrip().startswith("#")
            hasil = cek_baris(teks, kind, privat, not pola_ignore, allow)
            if hasil:
                temuan.append((rel, no, hasil, teks))
    pesan_dicek = False
    if a.message is not None:
        if diff and not produk:
            print("Pesan tidak dicek: diff tidak memuat file produk (commit lapisan agen).")
        else:
            pesan_dicek = True
            for no, teks in baca_pesan(a.message):
                hasil = cek_baris(teks, "doc", privat, privat, allow)
                if hasil:
                    temuan.append(("message", no, hasil, teks))

    n_proses = sum(1 for t in temuan if any(h[0] == "PROCESS" for h in t[2]))
    n_ref = sum(1 for t in temuan if any(h[0] == "REF" for h in t[2]))
    for rel, no, hasil, teks in temuan:
        per_file.setdefault(rel, [0, 0])
        per_file[rel][0] += any(h[0] == "PROCESS" for h in hasil)
        per_file[rel][1] += any(h[0] == "REF" for h in hasil)
        if not a.summary:
            label = ", ".join(dict.fromkeys(f"{h[0]} ({h[1]})" for h in hasil))
            print(f"{rel}:{no}: {label} | {cuplikan(teks, min(h[2] for h in hasil))}")
    if a.summary and per_file:
        urut = sorted(per_file.items(), key=lambda kv: (-(kv[1][0] + kv[1][1]), kv[0]))
        for rel, (p, r) in urut[:25]:
            print(f"{rel}: {p} PROCESS, {r} REF")
        if len(urut) > 25:
            print(f"... dan {len(urut) - 25} file lain")
    if privat:
        lapisan = "lapisan agen privat (handoff/ tidak ter-track): rujukan handoff/ ikut dicek"
    else:
        lapisan = "rujukan handoff/ tidak dicek: handoff/ ikut repo atau tidak ada"
    sumber = " + ".join(([f"{len(produk)} file produk"] if (diff or a.all or a.paths) else [])
                        + (["pesan"] if pesan_dicek else [])) or "tidak ada yang"
    lewat = f", {dilewati} file lapisan agen/dikecualikan/bukan teks dilewati" if dilewati else ""
    print(f"{sumber} dicek{lewat}: {n_proses} PROCESS, {n_ref} REF ({lapisan}).")
    if temuan:
        if n_proses:
            print("PROCESS: " + PETUNJUK["PROCESS"])
        if n_ref:
            print("REF: " + PETUNJUK["REF"].format(rujukan=" dan rujukan handoff/" if privat else "",
                                                  pesan="" if privat else ", serta pesan commit"))
        print("Teks yang memang isi produk (mis. \"user\" = pengguna aplikasi) ditambahkan ke ALLOW di skrip ini; "
              "path yang bukan file produk ke EXCLUDE atau --exclude.")
    return 1 if temuan else 0


if __name__ == "__main__":
    sys.exit(main())
