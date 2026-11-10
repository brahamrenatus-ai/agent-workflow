"""Uji fungsional scripts/brief.py (v3.23) dengan project palsu: bagian kecil utuh, bagian besar dipendekkan
(baris tertutup disembunyikan, baris lain dipotong dengan nomor baris), §1 dan §2 ROADMAP selalu utuh, task per
status, LITE, --full/--all, dan file yang tidak berubah.
Pemakaian: python -X utf8 tests/test_brief.py <folder skill>"""
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".claude/skills/agent-workflow").resolve()
SKRIP = SKILL / "scripts" / "brief.py"
ok = True
n_cek = 0


def cek(cond, msg, out=""):
    global ok, n_cek
    n_cek += 1
    print(("OK    " if cond else "FAIL  ") + msg)
    if not cond and out:
        print("      " + out[:1500].replace("\n", "\n      "))
    ok = ok and cond


def jalankan(cwd, *args):
    r = subprocess.run([sys.executable, "-X", "utf8", str(SKRIP), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=60, cwd=cwd)
    return r.returncode, r.stdout + r.stderr


def tulis(path, teks, crlf=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if crlf:
        teks = teks.replace("\n", "\r\n")
    path.write_bytes(teks.encode("utf-8"))


PANJANG = "alasan panjang " * 160  # ±2400 karakter

ROADMAP = "\n".join([
    "# ROADMAP Contoh",
    "> Milik head.",
    "",
    "## 1. Tertunda untuk Sesi Head Berikutnya",
    "- SERAH-TERIMA-AWAL " + "keadaan terkini " * 500,
    "- SERAH-TERIMA-AKHIR",
    "## 2. Fokus Saat Ini (maks. 2 jalur)",
    "- Jalur A: sinkronisasi",
    "## 3. Backlog",
    "| ID | Jenis | Item | Sumber | Status (cek kode: fungsi + `file:baris`) |",
    "|---|---|---|---|---|",
    "| R1 | FIX | BARIS-TERBUKA-PENDEK | audit | TODO |",
    "| R2 | FIX | BARIS-SELESAI-1 " + PANJANG + " | audit | DONE (`src/a.c:10`) |",
    "| R3 | FEATURE | BARIS-SELESAI-2 | user | **DONE** 2026-01-02 |",
    "| R4 | FEATURE | BARIS-TERBUKA-PANJANG " + PANJANG + " | user | PARTIAL: tersisa uji |",
    "| R5 | FIX | BARIS-MENUNGGU | audit | TODO (sesudah R2 DONE) |",
    "| R6 | SPIKE | BARIS-PARKIR | user | PARKED: buka bila ada data baru |",
    "| R7 | FIX | BARIS-SELESAI-3 | audit | ~~DONE~~ selesai |",
    "| R8 | FIX | BARIS-PIPA `a \\| b` " + PANJANG + " | audit | TASK-004 |",
    "| R9 | FIX | BARIS-PIPA-2 `x \\| y` " + PANJANG + " | DONE sebagian menurut audit | TODO |",
    "### Selesai",
    "| Item | Bukti |",
    "|---|---|",
    "| ARSIP-SELESAI-1 | REPORT-001 |",
    "| ARSIP-SELESAI-2 | REPORT-002 |",
    "## 5. Tugas User",
    "| ID | Tindakan | Kenapa | Cara verifikasi | Status |",
    "|---|---|---|---|---|",
    "| U1 | TUGAS-KECIL | perlu | lihat | selesai 2026-01-03 |",
    "## 7. Kotak Usulan",
    "| Tanggal | Asal | Usulan | Keputusan | Alasan |",
    "|---|---|---|---|---|",
    "| 2026-01-01 | REPORT-001 | USUL-DITERIMA " + PANJANG + " | Diterima → R4 | cocok |",
    "| 2026-01-02 | REPORT-002 | USUL-DITOLAK " + PANJANG + " | tolak | mahal |",
    "| 2026-01-03 | REPORT-003 | USUL-TERBUKA " + PANJANG + " | | |",
    "| 2026-01-04 | REPORT-003 | USUL-PARKIR " + PANJANG + " | **parkir** | nanti |",
    "| 2026-01-05 | REPORT-004 | USUL-TERIMAKASIH " + PANJANG + " | terimakasih, dibahas dulu | - |",
    "## 8. Pertanyaan Terbuka",
    "- Apakah port 8080 boleh dipakai?",
    "",
])

NOTES = "\n".join([
    "# NOTES Contoh",
    "## 1. Arsitektur & Aturan Inti",
    "- Satu layanan, satu basis data.",
    "## 3. Register Keputusan",
    "| Tanggal | Keputusan | Oleh | Alasan | Opsi ditolak | Buka ulang jika |",
    "|---|---|---|---|---|---|",
] + ["| 2026-01-%02d | KEPUTUSAN-%02d pakai antrean | user | %s | ditolak: polling | beban naik |" % (i, i, PANJANG)
     for i in range(1, 21)] + [
    "| 2026-02-01 | Tolak polling, KEPUTUSAN-TOLAK | user | hemat | - | beban turun |",
    "",
    "```",
    "## bukan judul, hanya isi blok kode",
    "```",
    "- BARIS-SESUDAH-PAGAR " + PANJANG,
    "## 5. Anomali Terbuka",
    "- ANOMALI-KECIL",
    "",
])


def task(status, triase=None):
    baris = ["# TASK: contoh", f"- Jenis: FIX · Roadmap: R1 · Status: {status} · Butuh executor: MEDIUM"]
    baris.append("- Triase head: " + (triase or "(diisi head setelah verifikasi: lolos <tanggal> / koreksi → TASK-NNN)"))
    baris += ["## Langkah", "1. Ubah `Status: IN_PROGRESS` saat mulai."]
    return "\n".join(baris) + "\n"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    cek(SKRIP.is_file(), "scripts/brief.py ada")
    tmp = Path(tempfile.mkdtemp(prefix="aw_brief_"))
    try:
        p = tmp / "proj"
        h = p / "handoff"
        tulis(h / "ROADMAP.md", ROADMAP)
        tulis(h / "NOTES.md", NOTES)
        tulis(h / "tasks" / "TASK-001-smoke.md", task("DONE", "lolos 2026-01-01"))
        tulis(h / "tasks" / "TASK-002-lama.md", task("DONE"))
        tulis(h / "tasks" / "TASK-003-fix.md", task("DONE", "koreksi → TASK-004"))
        tulis(h / "tasks" / "TASK-004-fix.md", task("DONE"))
        tulis(h / "tasks" / "TASK-004B-adhoc.md", task("BLOCKED"))
        tulis(h / "tasks" / "TASK-005-fitur.md", task("IN_PROGRESS"))
        tulis(h / "tasks" / "TASK-010-fitur.md", task("OPEN"))
        sebelum = {f: sha(h / f) for f in ("ROADMAP.md", "NOTES.md")}
        kode, out = jalankan(p)
        baris = out.split("\n")
        cek(kode == 0 and baris[0].startswith("BRIEF: "), "keluar 0 dan baris pertama diawali BRIEF", out[:400])
        cek("ROADMAP.md" in baris[0] and "->" in baris[0] and "NOTES.md" in baris[0], "BRIEF menyebut ukuran sebelum dan sesudah", baris[0])
        cek(baris[1].startswith("TASKS: 7 file, terakhir TASK-010"), "TASKS: jumlah file dan nomor terakhir menurut angka", baris[1])
        cek("OPEN: TASK-010" in baris[1] and "IN_PROGRESS: TASK-005" in baris[1] and "BLOCKED: TASK-004B" in baris[1],
            "TASKS: task per status dari baris header, bukan dari teks langkah", baris[1])
        cek("DONE belum ditriase: TASK-004" in baris[1] and "TASK-002" not in baris[1],
            "TASKS: hanya task DONE tanpa tanda sesudah task bertanda terakhir; templat kosong bukan tanda", baris[1])
        cek("SERAH-TERIMA-AWAL" in out and "SERAH-TERIMA-AKHIR" in out and not any(b.startswith("[L5]") for b in baris),
            "ROADMAP §1 dicetak utuh walau lebih besar dari batas")
        cek("BARIS-TERBUKA-PENDEK" in out and "BARIS-MENUNGGU" in out and "BARIS-PARKIR" in out,
            "baris terbuka, PARKED, dan TODO yang menyebut DONE di tengah sel tetap tampil")
        cek("BARIS-SELESAI-1" not in out and "BARIS-SELESAI-2" not in out and "BARIS-SELESAI-3" not in out,
            "baris berstatus DONE (polos, tebal, dicoret) disembunyikan")
        cek("ARSIP-SELESAI-1" not in out and "ARSIP-SELESAI-2" not in out and "### Selesai" in out,
            "isi sub-bagian Selesai disembunyikan, judulnya tetap")
        potong = [b for b in baris if "BARIS-TERBUKA-PANJANG" in b]
        cek(len(potong) == 1 and potong[0].startswith("[L15] | R4 ") and "…(+" in potong[0] and len(potong[0]) < 260,
            "baris panjang dipotong dan diawali nomor baris file aslinya", "\n".join(potong)[:400])
        asli = ROADMAP.split("\n")
        cek(asli[14].startswith("| R4 | FEATURE | BARIS-TERBUKA-PANJANG"), "nomor baris [L15] menunjuk baris yang sama di file")
        cek(any(b.startswith("[L19] | R8 ") for b in baris) and any(b.startswith("[L20] | R9 ") for b in baris),
            "pipa ter-escape di sel tidak menggeser kolom Status: baris terbuka tetap tampil")
        cek("TUGAS-KECIL" in out, "bagian kecil dicetak utuh walau barisnya tertutup")
        cek("USUL-DITERIMA" not in out and "USUL-DITOLAK" not in out and "USUL-PARKIR" not in out,
            "usulan yang sudah diputuskan disembunyikan")
        cek("USUL-TERBUKA" in out and "USUL-TERIMAKASIH" in out, "usulan tanpa keputusan tetap tampil; awalan kata harus utuh")
        cek(all("KEPUTUSAN-%02d" % i in out for i in range(1, 21)),
            "baris register keputusan tidak disembunyikan walau punya kolom Keputusan dan sel berawalan 'ditolak'")
        cek(sum(1 for b in baris if b.startswith("[L") and "KEPUTUSAN-" in b) == 20, "baris register dipotong dengan nomor baris")
        cek("KEPUTUSAN-TOLAK" in out, "baris register yang sel Keputusan-nya berawalan 'Tolak' tetap tampil (bukan tabel usulan)")
        cek("## bukan judul, hanya isi blok kode" in out and "ANOMALI-KECIL" in out
            and any(b.startswith("[L") and "BARIS-SESUDAH-PAGAR" in b for b in baris), "judul di dalam blok kode tidak memecah bagian")
        catatan = [b for b in baris if b.startswith("[brief]")]
        cek(len(catatan) == 3 and "baris tertutup disembunyikan" in catatan[0] and "handoff/ROADMAP.md baris 9-" in catatan[0],
            "tiap bagian yang dipendekkan diberi catatan jumlah dan rentang baris", "\n".join(catatan))
        cek(len(out.encode("utf-8")) < 0.6 * sum(len((h / f).read_bytes()) for f in sebelum), "keluaran lebih kecil dari 60% file asli")
        cek(all(sha(h / f) == v for f, v in sebelum.items()), "file ROADMAP dan NOTES tidak berubah")

        kode, out = jalankan(p, "--full", "register")
        cek(kode == 0 and not any(b.startswith("[L") and "KEPUTUSAN-" in b for b in out.split("\n")) and "BARIS-SELESAI-1" not in out,
            "--full <teks> mencetak utuh bagian yang judulnya cocok saja")
        kode, out = jalankan(p, "--all")
        cek(kode == 0 and "BARIS-SELESAI-1" in out and "[L" not in out and "semua bagian utuh" in out.split("\n")[0],
            "--all mencetak semua bagian utuh", out[:300])
        kode, out = jalankan(p, "--limit", "0", "--cut", "60")
        cek(kode == 0 and "SERAH-TERIMA-AKHIR" in out and any(b.startswith("[L") and "Apakah port" not in b for b in out.split("\n")),
            "--limit dan --cut dipakai; §1 ROADMAP tetap utuh")
        kode, out = jalankan(p, "handoff/NOTES.md")
        cek(kode == 0 and "ROADMAP.md" not in out.split("\n")[0] and "KEPUTUSAN-01" in out, "file bisa disebut sendiri")
        kode, out = jalankan(p, "tidak-ada.md")
        cek(kode == 2 and out.startswith("ERROR:"), "file yang tidak ada: ERROR, keluar 2", out[:200])
        kode, out = jalankan(p, "--cut", "5")
        cek(kode == 2 and out.startswith("ERROR:"), "--cut terlalu kecil ditolak", out[:200])

        # CRLF: hasil sama dengan LF
        q = tmp / "crlf"
        tulis(q / "handoff" / "ROADMAP.md", ROADMAP, crlf=True)
        tulis(q / "handoff" / "NOTES.md", NOTES, crlf=True)
        kode, out_crlf = jalankan(q)
        kode2, out_lf = jalankan(p)
        badan = lambda t: [b for b in t.split("\n")[1:] if not b.startswith("TASKS")]  # noqa: E731
        cek(kode == 0 and "\r" not in out_crlf and badan(out_crlf) == badan(out_lf), "file CRLF memberi isi yang sama tanpa CR")

        # LITE: NOTES dan ROADMAP di root, tanpa handoff/tasks
        lite = tmp / "lite"
        tulis(lite / "ROADMAP.md", ROADMAP)
        tulis(lite / "NOTES.md", NOTES)
        kode, out = jalankan(lite)
        cek(kode == 0 and "===== ROADMAP.md =====" in out and "TASKS" not in out, "LITE: file di root, tanpa baris TASKS", out[:300])

        # Skrip di handoff/tools dijalankan dari subfolder: root dicari dari lokasi skrip
        salinan = h / "tools" / "brief.py"
        salinan.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(SKRIP, salinan)
        (p / "src").mkdir()
        r = subprocess.run([sys.executable, "-X", "utf8", str(salinan)], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60, cwd=p / "src")
        cek(r.returncode == 0 and r.stdout.startswith("BRIEF: ") and "TASKS: 7 file" in r.stdout,
            "salinan di handoff/tools menemukan root project dari lokasinya", (r.stdout + r.stderr)[:300])

        kosong = tmp / "kosong"
        kosong.mkdir()
        kode, out = jalankan(kosong)
        cek(kode == 2 and out.startswith("ERROR:"), "tanpa file keadaan: ERROR, keluar 2", out[:200])

        # Protokol berbahasa Inggris
        en = tmp / "en"
        tulis(en / "handoff" / "ROADMAP.md", "\n".join([
            "# ROADMAP", "## 3. Backlog", "| ID | Type | Item | Source | Status |", "|---|---|---|---|---|",
            "| R1 | FIX | ROW-OPEN " + PANJANG * 6 + " | audit | TODO |",
            "| R2 | FIX | ROW-CLOSED " + PANJANG * 6 + " | audit | DONE |",
            "### Done", "| Item | Evidence |", "|---|---|", "| ARCHIVED-ROW | REPORT-001 |",
            "## 7. Proposal Box", "| Date | From | Proposal | Decision | Reason |", "|---|---|---|---|---|",
            "| 2026-01-01 | REPORT-001 | PROPOSAL-REJECTED " + PANJANG * 6 + " | Rejected | cost |",
            "| 2026-01-02 | REPORT-002 | PROPOSAL-OPEN " + PANJANG * 6 + " | | |", ""]))
        tulis(en / "handoff" / "tasks" / "TASK-001-x.md", "# TASK-001\n- Type: FIX · Status: DONE\n- Head triage: passed 2026-01-01\n")
        tulis(en / "handoff" / "tasks" / "TASK-002-x.md", "# TASK-002\n- Type: FIX · Status: DONE\n- Head triage: (filled by head)\n")
        kode, out = jalankan(en)
        cek(kode == 0 and "ROW-OPEN" in out and "ROW-CLOSED" not in out and "ARCHIVED-ROW" not in out
            and "PROPOSAL-REJECTED" not in out and "PROPOSAL-OPEN" in out, "judul kolom dan sub-bagian berbahasa Inggris dikenali", out[:400])
        cek("DONE belum ditriase: TASK-002" in out.split("\n")[1], "tanda triase berbahasa Inggris dikenali", out.split("\n")[1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"RESULT: {'ALL OK' if ok else 'SOME FAILED'} ({n_cek} cek)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
