"""Uji fungsional scripts/check_evidence.py pada project palsu. Pemakaian: python -X utf8 tests/test_check_evidence.py <path check_evidence.py>"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKRIP = Path(sys.argv[1]).resolve()
ok = True
LOG_A = """[23:41:35] [OLED_STAT] init=1 render_fail=0 last_ok_ms_ago=627 ka_err=0 bus_resets=0
[23:41:42] [OLED_STAGE] refresh err=0
[23:41:46] [OLED_STAGE] on err=255
[23:41:48] [OLED_STAGE] cfg err=255
[23:41:55] [OLED_STAT] init=1 render_fail=19 last_ok_ms_ago=19834 ka_err=1 bus_resets=3 fps=3.9
[23:42:10] [HEARTBEAT] up=60s heap=161848 fps=12.3
"""
LOG_B = "[10:00:00] [NET] rssi=-60 err=0\n[10:00:05] [SOAK] durasi=48,2 jam\n"


def cek(cond, msg, out=""):
    global ok
    print(("OK    " if cond else "FAIL  ") + msg)
    if not cond and out:
        print("      " + out.replace("\n", "\n      "))
    ok = ok and cond


def jalan(proj, isi, nama="REPORT-T.md"):
    p = proj / "handoff" / "reports" / nama
    p.write_text(isi, encoding="utf-8")
    r = subprocess.run([sys.executable, str(SKRIP), str(p.relative_to(proj))], cwd=proj, capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


TABEL = "| Kriteria | Harapan | Teramati | Bukti (file:baris) | Status |\n|---|---|---|---|---|\n"
tmp = Path(tempfile.mkdtemp(prefix="cekbukti_"))
try:
    proj = tmp / "proj"
    for d in ("handoff/reports", "handoff/logs/raw", "handoff/logs/lain"):
        (proj / d).mkdir(parents=True)
    (proj / "handoff/logs/a.log").write_text(LOG_A, encoding="utf-8")
    (proj / "handoff/logs/raw/b.log").write_text(LOG_B, encoding="utf-8")
    (proj / "handoff/logs/lain/c.log").write_text("[11:00:00] [NET] rssi=-61 err=0\n", encoding="utf-8")
    (proj / "handoff/logs/dup.log").write_text("x\n", encoding="utf-8")
    (proj / "handoff/logs/lain/dup.log").write_text("x\n", encoding="utf-8")

    baik = ("# REPORT-T\nPelaksana (model): Uji (high)\n\n## Data yang Diminta\n" + TABEL +
            "| refresh | err=0 | err=0 | `handoff/logs/a.log:2` | OK |\n"
            "| on | err=0 | err=255 | `handoff/logs/a.log:3` | GAGAL |\n"
            "| heap & fps | fps>=10 dan heap>100000 | heap=161848 fps=12.3 | `a.log:6` | OK |\n"
            "| soak | ≥ 47 jam | 48,2 jam | `handoff/logs/raw/b.log:2` | OK |\n"
            "| ka_err dua titik | ka_err<=1 | ka_err=1 | `handoff/logs/a.log:1, 5` | OK |\n"
            "| belum | - | - | - | TIDAK DIUJI |\n\n"
            "## Bukti Mentah\n```bukti\nhandoff/logs/a.log:3 | [OLED_STAGE] on err=255\nhandoff/logs/a.log:4 | cfg err=255\n```\n\n"
            "```\n[23:41:55] [OLED_STAT] init=1 render_fail=19 last_ok_ms_ago=19834 ka_err=1 bus_resets=3 fps=3.9\n"
            "handoff\\logs\\a.log:2:[23:41:42] [OLED_STAGE] refresh err=0\n```\n\n"
            "```powershell\nSelect-String -Path handoff/logs/a.log -Pattern \"OLED_STAGE\" | Select-Object LineNumber, Line\n```\n"
            "```\nLineNumber Line\n---------- ----\n         2 [23:41:42] [OLED_STAGE] refresh err=0\n         3 [23:41:46] [OLED_STAGE] on err=255\n```\n")
    rc, out = jalan(proj, baik)
    cek(rc == 0 and "0 ERROR" in out, "report yang benar: exit 0, 0 masalah", out)
    cek("Ringkas: 12 bukti dicek" in out, "semua bukti terhitung (tabel, blok bukti, blok log, grep -n, Select-String)", out)

    # Pola baris log karangan: blok kode berisi baris log yang tidak ada di file mana pun
    rc, out = jalan(proj, "Pelaksana (model): X\nLog: `handoff/logs/a.log`\n\n```\n[OLED_STAT] init=1 render_fail=0 last_ok_ms_ago=26 ka_err=4 bus_resets=133\n[OLED_STAGE] refresh err=0\n[OLED_STAGE] on err=0\n```\n")
    cek(rc == 1 and out.count("tidak ada di file log mana pun") == 2, "baris log karangan -> 2 masalah, baris asli lolos", out)

    rc, out = jalan(proj, "## Data\n" + TABEL + "| on | err=0 | err=255 | `handoff/logs/a.log:3` | OK |\n")
    cek(rc == 1 and "tidak memenuhi Harapan" in out, "OK yang bertentangan dengan Harapan -> masalah", out)
    rc, out = jalan(proj, "## Data\n" + TABEL + "| on | err=0 | err=0 | `handoff/logs/a.log:3` | OK |\n")
    cek(rc == 1 and "tidak terlihat di baris yang dirujuk" in out, "Teramati karangan (err=0 padahal baris berisi err=255) -> masalah", out)
    rc, out = jalan(proj, "## Data\n" + TABEL + "| on | err=0 | err=0 | lihat log di atas | OK |\n")
    cek(rc == 1 and "OK tanpa rujukan" in out, "OK tanpa rujukan file:baris -> masalah", out)
    rc, out = jalan(proj, "## Data\n" + TABEL + "| fps | fps>=15 | fps=12.3 | `a.log:6` | OK |\n")
    cek(rc == 1 and "tidak memenuhi Harapan" in out, "perbandingan angka fps>=15 vs 12.3 -> masalah", out)
    rc, out = jalan(proj, "## Data\n" + TABEL + "| refresh | err=0 | err=0 | `handoff/logs/a.log:2` | GAGAL |\n")
    cek(rc == 0 and "WARNING" in out and "padahal Teramati memenuhi" in out, "GAGAL yang memenuhi Harapan -> peringatan saja", out)

    rc, out = jalan(proj, "```bukti\nhandoff/logs/a.log:3 | [OLED_STAGE] on err=0\nhandoff/logs/a.log:99 | x\nhandoff/logs/zzz.log:1 | x\nhandoff/logs/<file>.log:<baris> | <kutipan persis>\n```\n")
    cek(rc == 1 and "tidak sama dengan isi baris" in out and "hanya 6 baris" in out and "zzz.log tidak ada" in out and "tidak berformat" in out,
        "blok bukti: kutipan salah, baris di luar file, file tidak ada, placeholder template -> masalah", out)
    rc, out = jalan(proj, "```bukti\ndup.log:1 | x\n```\n")
    cek(rc == 1 and "ambigu" in out, "nama file ambigu -> masalah", out)
    rc, out = jalan(proj, "```\nhandoff/logs/a.log:2:[23:41:42] [OLED_STAGE] refresh err=999\n```\n")
    cek(rc == 1 and "tidak sama dengan isi baris" in out, "output grep -n yang diubah -> masalah", out)
    rc, out = jalan(proj, "```powershell\nSelect-String -Path handoff/logs/a.log -Pattern x\n```\n```\nLineNumber Line\n---------- ----\n         3 [23:41:46] [OLED_STAGE] on err=0\n```\n")
    cek(rc == 1 and "a.log:3 tidak sama" in out, "tabel Select-String yang diubah -> masalah", out)
    rc, out = jalan(proj, "Log: `handoff/logs/a.log`\n```\n[11:00:00] [NET] rssi=-61 err=0\n```\n")
    cek(rc == 1 and "tidak ada di file yang dirujuk report" in out and "lain/c.log" in out, "baris yang hanya ada di file lain -> masalah, dengan petunjuk file-nya", out)
    rc, out = jalan(proj, "## Ringkasan\n- Semua tahap berhasil.\n- Build sukses (`handoff/logs/a.log:2`).\n\n```bukti\nhandoff/logs/a.log:2 | refresh err=0\n```\n")
    cek(rc == 0 and out.count("tanpa rujukan file:baris") == 1, "klaim berhasil tanpa rujukan -> peringatan; dengan rujukan -> tidak", out)
    rc, out = jalan(proj, "## Data\n" + TABEL +
                    "| ka_err | ka_err<=1 | ka_err=1 | `handoff/logs/a.log:1`, `:5` | OK |\n"
                    "| crash | =0 | 0 | hitung(handoff/logs/a.log, \"Guru Meditation\\|rst:0x\") | OK |\n")
    cek(rc == 0 and "0 ERROR" in out and "3 bukti dicek" in out, "rujukan lanjutan `:5` dan hitung() untuk kriteria '0 kemunculan' -> lolos", out)
    rc, out = jalan(proj, "## Data\n" + TABEL + "| crash | =0 | 0 | hitung(handoff/logs/a.log, \"Guru|rst:0x\") | OK |\n")
    cek(rc == 1 and "kolom, header" in out, "tanda | tanpa escape di sel -> masalah jumlah kolom, bukan baris terlewat", out)
    rc, out = jalan(proj, "## Data\n" + TABEL + "| stage | =2 | 2 | hitung(handoff/logs/a.log, \"OLED_STAGE\") | OK |\n"
                          "| rusak | =0 | 0 | hitung(handoff/logs/a.log, \"(\") | OK |\n")
    cek(rc == 1 and "3 baris di handoff/logs/a.log cocok" in out and "bukan regex yang valid" in out, "hitung() yang tidak cocok dan pola rusak -> masalah", out)
    (proj / "src").mkdir()
    (proj / "src/x.cpp").write_text("int a = 1;\nint b = 2;\nint c = 3;\n", encoding="utf-8")
    rc, out = jalan(proj, "```bukti\nhandoff/logs/a.log:2 | refresh err=0\n```\nSebelum perubahan:\n```\nsrc/x.cpp:3:int c = 999;\n```\n"
                          "```powershell\nSelect-String -Path src/x.cpp -Pattern int\n```\n```\nLineNumber Line\n---------- ----\n         1 int a = 0;\n```\n")
    cek(rc == 0 and "0 ERROR" in out, "kutipan grep/Select-String atas file kode dilewati (bisa versi sebelum perubahan)", out)
    rc, out = jalan(proj, "## Data\n" + TABEL + "| garis | hilang | hilang | user: \"garisnya sudah hilang\" | OK |\n"
                          "```bukti\nhandoff/logs/a.log:2 | refresh err=0\n```\n")
    cek(rc == 0 and "pengamatan user" in out, "bukti pengamatan user -> peringatan, bukan masalah", out)
    # v3.7: tabel task FAKTA, hitung() atas folder dan glob, bagian Periksa Diri
    FAKTA = "| No | Pertanyaan | Jawaban | Bukti | Status |\n|---|---|---|---|---|\n"
    rc, out = jalan(proj, "## Data\n" + FAKTA +
                    "| 1 | Di mana fps dicetak? | di baris HEARTBEAT | `handoff/logs/a.log:6` | DITEMUKAN |\n"
                    "| 2 | Ada crash di semua log? | tidak | hitung(handoff/logs, \"Guru Meditation\") | TIDAK ADA |\n"
                    "| 3 | Ada OLED_STAGE di kode? | tidak | hitung(src/**/*.cpp, \"OLED_STAGE\") | TIDAK ADA |\n"
                    "| 4 | Berapa deklarasi int di src? | 3 | hitung(src, \"int \") | DITEMUKAN |\n"
                    "| 5 | Siapa pemanggil X? | belum jelas | - | TIDAK YAKIN |\n"
                    "## Periksa Diri (sebelum DONE)\n- ok\n")
    cek(rc == 0 and "0 ERROR" in out and "4 bukti dicek" in out and "Periksa Diri" not in out,
        "tabel FAKTA: DITEMUKAN berujukan, TIDAK ADA lewat hitung folder/glob = 0, hitung = Jawaban, TIDAK YAKIN dilewati", out)
    rc, out = jalan(proj, "## Data\n" + FAKTA +
                    "| 1 | Ada OLED_STAGE di log a? | tidak | hitung(handoff/logs/a.log, \"OLED_STAGE\") | TIDAK ADA |\n"
                    "| 2 | Ada crash? | tidak | sudah dicari | TIDAK ADA |\n"
                    "| 3 | Di mana fps? | di log | lihat log | DITEMUKAN |\n"
                    "| 4 | Ada di folder hilang? | tidak | hitung(tidak/ada, \"x\") | TIDAK ADA |\n"
                    "| 5 | Ada di glob kosong? | tidak | hitung(src/**/*.zzz, \"x\") | TIDAK ADA |\n")
    cek(rc == 1 and "padahal 3 baris" in out and "butuh bukti `hitung" in out and "OK tanpa rujukan" in out
        and "tidak/ada tidak ada" in out and "tidak cocok dengan file apa pun" in out,
        "FAKTA salah: TIDAK ADA padahal ada, tanpa hitung, DITEMUKAN tanpa rujukan, lingkup hilang -> masalah", out)
    # v3.20: nama baru (FAIL, UNTESTED; task FACT: FOUND, NONE, UNSURE). Kasus di atas memakai nama lama, yang tetap diterima.
    rc, out = jalan(proj, "## Data\n" + FAKTA +
                    "| 1 | Di mana fps dicetak? | di baris HEARTBEAT | `handoff/logs/a.log:6` | FOUND |\n"
                    "| 2 | Ada crash di semua log? | tidak | hitung(handoff/logs, \"Guru Meditation\") | NONE |\n"
                    "| 3 | Siapa pemanggil X? | belum jelas | - | UNSURE |\n"
                    "## Periksa Diri (sebelum DONE)\n- ok\n")
    cek(rc == 0 and "0 ERROR" in out and "2 bukti dicek" in out, "v3.20 tabel FACT: FOUND berujukan, NONE lewat hitung = 0, UNSURE dilewati", out)
    rc, out = jalan(proj, "## Data\n" + FAKTA +
                    "| 1 | Ada OLED_STAGE di log a? | tidak | hitung(handoff/logs/a.log, \"OLED_STAGE\") | NONE |\n"
                    "| 2 | Ada crash? | tidak | sudah dicari | NONE |\n")
    cek(rc == 1 and "status NONE, padahal 3 baris" in out and "status NONE butuh bukti `hitung" in out,
        "v3.20 tabel FACT: NONE padahal ada, NONE tanpa hitung -> masalah", out)
    rc, out = jalan(proj, "## Data\n" + TABEL + "| refresh | err=0 | err=0 | `handoff/logs/a.log:2` | FAIL |\n"
                          "| on | err=0 | err=255 | `handoff/logs/a.log:3` | FAIL |\n| belum | - | - | - | UNTESTED |\n")
    cek(rc == 0 and out.count("status FAIL, padahal Teramati memenuhi") == 1, "v3.20 tabel Data: FAIL dan UNTESTED dikenali", out)
    rc, out = jalan(proj, "## Data\n" + TABEL + "| on | err=0 | err=255 | `handoff/logs/a.log:3` | OK |\n")
    cek(rc == 1 and "FAIL / UNTESTED (task FACT: UNSURE)" in out, "v3.20: saran perbaikan memakai nama baru", out)
    rc, out = jalan(proj, "```bukti\nhandoff/logs/a.log:2 | refresh err=0\n```\n")
    cek(rc == 0 and "tanpa bagian Periksa Diri" in out, "report DONE tanpa bagian Periksa Diri -> peringatan", out)
    rc, out = jalan(proj, "# REPORT\nStatus akhir: BLOCKED\nAlasan: port dipakai task lain.\n")
    cek(rc == 0, "report BLOCKED tanpa bukti -> tidak dianggap masalah", out)
    rc, out = jalan(proj, "# REPORT\nStatus akhir: DONE\nSemua OK.\n")
    cek(rc == 1 and "tidak ada bukti yang bisa dicek" in out, "report DONE tanpa bukti sama sekali -> masalah", out)
    r = subprocess.run([sys.executable, str(SKRIP), "handoff/reports/TIDAK-ADA.md"], cwd=proj, capture_output=True, text=True, encoding="utf-8")
    cek(r.returncode == 2, "report tidak ditemukan -> exit 2", r.stdout + r.stderr)

    # ---- v3.9: asal log (record.py), kutipan user karangan, kriteria K, angka tanpa rujukan ----
    if "def cek_asal" in SKRIP.read_text(encoding="utf-8"):
        rc, out = jalan(proj, baik)
        cek("record.py" not in out and "provenance.jsonl" not in out, "project tanpa provenance.jsonl: tidak ada pesan asal", out)
        CATAT = SKRIP.parent / "record.py"
        p2 = tmp / "proj2"
        (p2 / "handoff/reports").mkdir(parents=True)
        subprocess.run([sys.executable, str(CATAT), "handoff/logs/uji.log",
                        f'"{sys.executable}" -c "print(\'[10:00:00] [UJI] err=0\')"'], cwd=p2, capture_output=True)
        rep = ("# REPORT\n## Data yang Diminta\n" + TABEL + "| K1 uji | err=0 | err=0 | `handoff/logs/uji.log:1` | OK |\n\n"
               "## Periksa Diri\n- ok\n")
        rc, out = jalan(p2, rep, "REPORT-A.md")
        cek(rc == 0 and "tidak tercatat" not in out and "berubah setelah" not in out, "log dari record.py: asal cocok, tanpa temuan", out)
        lg = p2 / "handoff/logs/uji.log"
        lg.write_text(lg.read_text(encoding="utf-8") + "[10:00:01] [UJI] baris tambahan tangan\n", encoding="utf-8")
        rc, out = jalan(p2, rep, "REPORT-A.md")
        cek(rc == 1 and "berubah setelah dicatat" in out, "log diedit setelah dicatat record.py -> masalah", out)
        (p2 / "handoff/logs/tangan.log").write_text("[10:00:00] [UJI] err=0\n", encoding="utf-8")
        rc, out = jalan(p2, rep.replace("uji.log", "tangan.log"), "REPORT-B.md")
        cek(rc == 0 and "tidak tercatat" in out, "log tanpa catatan asal -> peringatan", out)
        r = subprocess.run([sys.executable, str(SKRIP), "--require-provenance", "handoff/reports/REPORT-B.md"], cwd=p2,
                           capture_output=True, text=True, encoding="utf-8")
        cek(r.returncode == 1 and "tidak tercatat" in r.stdout, "--require-provenance: log tanpa catatan asal -> masalah", r.stdout)

        # v3.12: catatan asal bernama lama (asal.jsonl) tetap dibaca, dan opsi lama tetap diterima
        if "ASAL_LAMA" in SKRIP.read_text(encoding="utf-8"):
            p3 = tmp / "proj_lama"
            shutil.copytree(p2, p3)
            (p3 / "handoff/logs/provenance.jsonl").rename(p3 / "handoff/logs/asal.jsonl")
            rc, out = jalan(p3, rep, "REPORT-A.md")
            cek(rc == 1 and "berubah setelah dicatat" in out, "project bernama lama: catatan asal dibaca dari asal.jsonl", out)
            r = subprocess.run([sys.executable, str(SKRIP), "--wajib-asal", "handoff/reports/REPORT-B.md"], cwd=p3,
                               capture_output=True, text=True, encoding="utf-8")
            cek(r.returncode == 1 and "tidak tercatat di handoff/logs/asal.jsonl" in r.stdout,
                "opsi lama --wajib-asal diterima; pesan menyebut file asal yang dipakai", r.stdout)
            r = subprocess.run([sys.executable, str(SKRIP), "--pada", "tidak-ada-123", "handoff/reports/REPORT-B.md"], cwd=p3,
                               capture_output=True, text=True, encoding="utf-8")
            cek("Commit tidak-ada-123 tidak ditemukan" in r.stdout + r.stderr, "opsi lama --pada diterima", r.stdout + r.stderr)
            if "NAMA_V312" in SKRIP.read_text(encoding="utf-8"):  # v3.12.1: kutipan report lama ke file yang berganti nama
                p4 = tmp / "proj_v3121"
                for sub in ("handoff/reports", "handoff/logs", "handoff/tools"):
                    (p4 / sub).mkdir(parents=True)
                (p4 / "handoff/logs/provenance.jsonl").write_text('{"file": "x", "sha256": "0"}\n', encoding="utf-8")
                (p4 / "handoff/tools/record.py").write_text("import sys\n", encoding="utf-8")
                rc, out = jalan(p4, "```bukti\nhandoff/logs/asal.jsonl:1 | sha256\n```\n", "REPORT-L.md")
                cek(rc == 0 and "0 ERROR" in out, "kutipan report lama ke asal.jsonl dibaca dari provenance.jsonl (isi sama)", out)
                rc, out = jalan(p4, "```bukti\nhandoff/tools/catat.py:1 | import sys\n```\n", "REPORT-M.md")
                cek(rc == 1 and "sejak v3.12 bernama handoff/tools/record.py" in out,
                    "kutipan report lama ke catat.py: masalah, dengan nama barunya dan saran --at-report", out)
        else:
            print("SKIP  uji v3.12: check_evidence.py versi lama")

        rep_user = ("# REPORT\n## Data yang Diminta\n" + TABEL +
                    "| K1 cek mata | Tombol ekspor mengunduh file CSV yang terbuka | Tombol ekspor mengunduh file CSV yang terbuka"
                    " | user: \"Tombol ekspor mengunduh file CSV yang terbuka\" | OK |\n"
                    "| K2 cek mata | Grafik tampil | grafik tampil | user: \"sudah saya coba, grafiknya tampil\" | OK |\n\n## Periksa Diri\n- ok\n")
        rc, out = jalan(proj, rep_user, "REPORT-U.md")
        cek(rc == 1 and "kutipan user sama dengan teks Harapan" in out and out.count("head yang memverifikasinya") == 1,
            "kutipan user = Harapan -> masalah; kutipan user asli -> peringatan", out)

        (proj / "handoff/tasks").mkdir(exist_ok=True)
        (proj / "handoff/tasks/TASK-K-uji.md").write_text(
            "# TASK-K\n## Kriteria terima\n| Kriteria | Harapan |\n|---|---|\n| K1 refresh | err=0 |\n"
            "| K2 on | err=255, lihat juga K9 |\n| K3 user: cek mata | layar terang |\n## Batasan\n- -\n", encoding="utf-8")
        rep_k = ("# REPORT-K\n## Data yang Diminta\n" + TABEL + "| K1 refresh | err=0 | err=0 | `handoff/logs/a.log:2` | OK |\n"
                 "| K2 on | err=255 | err=255 | `handoff/logs/a.log:3` | OK |\n\n## Periksa Diri\n- ok\n")
        rc, out = jalan(proj, rep_k, "REPORT-K.md")
        cek(rc == 1 and "kriteria K3" in out and "K9" not in out, "kriteria K3 tanpa baris di tabel Data -> masalah (K9 di tengah teks diabaikan)", out)
        rc, out = jalan(proj, rep_k.replace("\n\n## Periksa", "\n| K3 user: cek mata | layar terang | - | - | TIDAK DIUJI |\n\n## Periksa"),
                        "REPORT-K.md")
        cek(rc == 0 and "kriteria K" not in out, "semua kriteria K punya baris -> tanpa temuan kriteria", out)
        (proj / "handoff/tasks/TASK-L-uji.md").write_text("# TASK-L\n## Kriteria terima\n- build lulus\n- test lulus\n", encoding="utf-8")
        rc, out = jalan(proj, rep_k, "REPORT-L.md")
        cek(rc == 0 and "belum bernomor K1" in out, "kriteria task tanpa nomor K -> peringatan", out)

        rep_angka = (baik + "\n## Keputusan Implementasi\n- Latensi rata-rata panggilan 3–6 detik per panggilan.\n"
                     "- Jeda 1,5 detik sesuai `handoff/logs/a.log:2`.\n- Perkiraan durasi total 45 detik.\n")
        rc, out = jalan(proj, rep_angka, "REPORT-N.md")
        cek(rc == 0 and out.count("tanpa rujukan file:baris di baris ini") == 1 and "3–6 detik" in out,
            "angka bersatuan tanpa rujukan -> peringatan; dengan rujukan atau perkiraan -> tidak", out)
    else:
        print("SKIP  uji v3.9: check_evidence.py versi lama")

    # ---- v3.9.2: log yang hanya tercantum di output git status (Periksa Diri) bukan rujukan untuk cek asal ----
    if "STATUS_GIT" in SKRIP.read_text(encoding="utf-8"):
        p3 = tmp / "proj3"
        (p3 / "handoff/reports").mkdir(parents=True)
        subprocess.run([sys.executable, str(SKRIP.parent / "record.py"), "handoff/logs/TASK-9-regresi.log",
                        f'"{sys.executable}" -c "print(\'[10:00:00] [UJI] err=0\')"'], cwd=p3, capture_output=True)
        for nama in ("uji_a", "uji_b", "uji_c", "lama", "baru", "prosa", "tabel"):  # ditulis regresi_uji.py, bukan record.py
            (p3 / f"handoff/logs/TASK-9-{nama}.log").write_text(f"[10:00:05] [UJI] {nama} selesai err=0\n", encoding="utf-8")
        status = ("## Periksa Diri\n```\n  ?? handoff/logs/TASK-9-uji_a.log\n   M handoff/logs/TASK-9-uji_b.log\n"
                  "R  handoff/logs/TASK-9-lama.log -> handoff/logs/TASK-9-baru.log\n?? handoff/logs/TASK-9-tabel.log\n```\n"
                  "- `?? handoff/logs/TASK-9-uji_c.log`\n\n```\n[10:00:05] [UJI] uji_a selesai err=0\n```\n")
        rep = "# REPORT\n## Data yang Diminta\n" + TABEL + "| K1 uji | err=0 | err=0 | `handoff/logs/TASK-9-regresi.log:1` | OK |\n\n" + status
        rc, out = jalan(p3, rep, "REPORT-G.md")
        cek(rc == 0 and "tidak tercatat" not in out and "0 ERROR" in out,
            "log yang hanya tercantum di output git status (??, M, R ->, berbacktick) -> tanpa peringatan asal", out)
        cek("tidak ada di file yang dirujuk" not in out and "tidak ada di file log mana pun" not in out,
            "baris log dari file yang tercantum di git status tetap dicari seperti dulu (hanya cek asal yang berubah)", out)
        r = subprocess.run([sys.executable, str(SKRIP), "--require-provenance", "handoff/reports/REPORT-G.md"], cwd=p3,
                           capture_output=True, text=True, encoding="utf-8")
        cek(r.returncode == 0 and "tidak tercatat" not in r.stdout, "--require-provenance: log yang hanya di git status tidak menjadi masalah", r.stdout)
        rep2 = ("# REPORT\n## Data yang Diminta\n" + TABEL + "| K1 uji | err=0 | err=0 | `handoff/logs/TASK-9-regresi.log:1` | OK |\n"
                "| K2 tabel | err=0 | err=0 | `handoff/logs/TASK-9-tabel.log:1` | OK |\n\n"
                "A handoff/logs/TASK-9-prosa.log dibaca ulang sebelum report ditulis.\n\n" + status)
        rc, out = jalan(p3, rep2, "REPORT-H.md")
        cek(out.count("tidak tercatat") == 2 and "TASK-9-tabel.log tidak tercatat" in out and "TASK-9-prosa.log tidak tercatat" in out,
            "log yang juga dirujuk tabel, atau disebut di kalimat berawalan huruf status -> tetap diperingatkan", out)
    else:
        print("SKIP  uji v3.9.2: check_evidence.py versi lama")

    # ---- v3.10: report berbahasa Inggris, --at / --at-report untuk report lama, \approx LaTeX ----
    if "def glob_rx" in SKRIP.read_text(encoding="utf-8"):
        def jalan_arg(proj, *args):
            r = subprocess.run([sys.executable, str(SKRIP), *args], cwd=proj, capture_output=True, text=True, encoding="utf-8")
            return r.returncode, r.stdout + r.stderr

        p4 = tmp / "proj4"
        for d in ("handoff/reports", "handoff/tasks"):
            (p4 / d).mkdir(parents=True)
        subprocess.run([sys.executable, str(SKRIP.parent / "record.py"), "handoff/logs/run.log",
                        f'"{sys.executable}" -c "print(\'[10:00:00] [TEST] passed=12 failed=0\')"'], cwd=p4, capture_output=True)
        (p4 / "handoff/tasks/TASK-7-suite.md").write_text("# TASK-7\n## Acceptance criteria\n- K1 tests pass\n- K2 no errors\n## Steps\n", encoding="utf-8")
        TAB_EN = "| Criteria | Expected | Observed | Evidence | Status |\n|---|---|---|---|---|\n"
        en = ("# REPORT-7\n- Final status: DONE\n\n## Fact Summary\n- Ran the suite in 5 sec.\n- About 3 sec per test (estimate).\n\n"
              "## Data\n" + TAB_EN + "| K1 tests | failed=0 | failed=0 | `handoff/logs/run.log:1` | PASS |\n"
              "| K2 errors | =0 | 0 | count(handoff/logs/run.log, \"ERROR\") | PASS |\n\n"
              "```evidence\nhandoff/logs/run.log:1 | [TEST] passed=12\n```\n\n## Self-check\n- `check_evidence.py`: 0 problems.\n")
        rc, out = jalan(p4, en, "REPORT-7.md")
        cek(rc == 0 and "0 ERROR" in out and "Periksa Diri" not in out, "report berbahasa Inggris (Self-check, Criteria/Expected/Observed/Evidence, PASS, count, evidence): 0 masalah", out)
        cek(out.count("tanpa rujukan file:baris di baris ini") == 1 and "5 sec" in out, "Fact Summary: angka tanpa rujukan diberi peringatan; 'estimate' dianggap perkiraan", out)
        salah = en.replace("| K1 tests | failed=0 |", "| K1 tests | failed>0 |").replace("| K2 errors | =0 | 0 | count(handoff/logs/run.log, \"ERROR\") | PASS |\n", "")
        rc, out = jalan(p4, salah, "REPORT-7.md")
        cek(rc == 1 and "status OK, padahal" in out and "kriteria K2" in out, "bahasa Inggris: PASS yang melanggar Expected dan kriteria K2 yang hilang tertangkap", out)
        fakta = ("# REPORT-7\n## Answers\n| No | Question | Answer | Evidence | Status |\n|---|---|---|---|---|\n"
                 "| 1 | Any TEST line? | none | count(handoff/logs/run.log, \"TEST\") | NOT FOUND |\n| 2 | ? | ? | - | UNSURE |\n\n## Self-check\n")
        rc, out = jalan(p4, fakta, "REPORT-7.md")
        cek(rc == 1 and "status NONE, padahal 1 baris" in out, "NOT FOUND yang hitungannya > 0 adalah masalah; UNSURE tidak dicek", out)
        rc, out = jalan(p4, "# REPORT-7\n- Final status: BLOCKED\n", "REPORT-7.md")
        cek(rc == 0 and "kriteria K" not in out, "Final status: BLOCKED: kriteria dan bukti tidak dituntut", out)
        rc, out = jalan(p4, "# R\n## Ringkasan Fakta\n- 167 error / 2,8 jam $\\approx 59,6$ error/jam\n## Periksa Diri\n", "REPORT-L.md")
        cek("\"2,8 jam\"" in out, "`$\\approx$` LaTeX tidak dianggap tanda perkiraan", out)

        p5 = tmp / "proj5"
        for d in ("handoff/reports", "handoff/tasks", "src/sub"):
            (p5 / d).mkdir(parents=True)
        G = ["git", "-c", "user.name=uji", "-c", "user.email=uji@example.com", "-c", "core.autocrlf=false"]
        subprocess.run(["git", "init", "-q"], cwd=p5, capture_output=True)
        (p5 / "src/sub/app.py").write_text("x = 1\n", encoding="utf-8")
        (p5 / "handoff/tasks/TASK-8-nilai.md").write_text("# TASK-8\n## Kriteria terima\n- K1 nilai x\n- K2 satu baris\n", encoding="utf-8")
        subprocess.run([sys.executable, str(SKRIP.parent / "record.py"), "handoff/logs/TASK-8-uji.log",
                        f'"{sys.executable}" -c "print(\'[09:00:00] [UJI] x=1\')"'], cwd=p5, capture_output=True)
        lama = ("# REPORT-8\n## Data yang Diminta\n" + TABEL + "| K1 nilai | x = 1 | x = 1 | `src/sub/app.py:1` | OK |\n"
                "| K2 satu baris | =1 | 1 | hitung(src/**/*.py, \"x = 1\") | OK |\n"
                "| K2 log | x=1 | x=1 | `handoff/logs/TASK-8-uji.log:1` | OK |\n\n## Periksa Diri\n- ok\n")
        (p5 / "handoff/reports/REPORT-8.md").write_text(lama, encoding="utf-8")
        subprocess.run(G + ["add", "-A"], cwd=p5, capture_output=True)
        subprocess.run(G + ["commit", "-q", "-m", "report"], cwd=p5, capture_output=True)
        c1 = subprocess.run(["git", "rev-parse", "HEAD"], cwd=p5, capture_output=True, text=True).stdout.strip()
        (p5 / "src/sub/app.py").write_text("x = 2\n", encoding="utf-8")
        subprocess.run(G + ["commit", "-q", "-am", "kode berubah"], cwd=p5, capture_output=True)
        rc, out = jalan_arg(p5, "handoff/reports/REPORT-8.md")
        cek(rc == 1 and "tidak terlihat di baris yang dirujuk" in out and "0 baris di src/**/*.py" in out,
            "tanpa --at: kutipan kode lama terbaca salah setelah kode berubah", out)
        rc, out = jalan_arg(p5, "--at", c1[:10], "handoff/reports/REPORT-8.md")
        cek(rc == 0 and "0 ERROR" in out and f"pada commit {c1[:8]}" in out, "--at <commit>: kutipan dan hitung(src/**/*.py) dicocokkan dengan isi file pada commit itu", out)
        rc, out = jalan_arg(p5, "--at-report", "handoff/reports/REPORT-*.md")
        cek(rc == 0 and "0 ERROR" in out and f"pada commit {c1[:8]}" in out, "--at-report (argumen glob): commit terakhir yang mengubah report dipakai", out)
        rc, out = jalan_arg(p5, "--at", "bukan-commit", "handoff/reports/REPORT-8.md")
        cek(rc == 2 and "tidak ditemukan" in out, "--at dengan commit yang tidak ada: exit 2", out)
        (p5 / "handoff/reports/REPORT-9.md").write_text("# REPORT-9\n" + TABEL.replace("Bukti (file:baris)", "Bukti") +
                                                         "| K1 | x = 2 | x = 2 | `src/sub/app.py:1` | OK |\n\n## Periksa Diri\n", encoding="utf-8")
        rc, out = jalan_arg(p5, "--at-report", "handoff/reports/REPORT-9.md")
        cek(rc == 0 and "belum di-commit" in out, "--at-report: report yang belum di-commit dicek terhadap working tree", out)
        (p5 / "handoff/logs/TASK-8-uji.log").write_text("[09:00:00] [UJI] x=9\n", encoding="utf-8")
        rc, out = jalan_arg(p5, "--at", c1, "handoff/reports/REPORT-8.md")
        cek(rc == 0, "--at: log dibaca dari commit, jadi perubahan log di working tree tidak memengaruhi", out)
        rc, out = jalan_arg(p5, "handoff/reports/REPORT-8.md")
        cek("berubah setelah dicatat" in out, "tanpa --at: log yang diedit di working tree tetap tertangkap", out)
    else:
        print("SKIP  uji v3.10: check_evidence.py versi lama")

    # ---- v3.15: kutipan di prosa, nomor baris seperti grep, log ditimpa perintah lain, templat tabel Data ----
    if "def cek_prosa" in SKRIP.read_text(encoding="utf-8"):
        p6 = tmp / "proj6"
        for d in ("handoff/reports", "handoff/logs", "handoff/tasks", "src"):
            (p6 / d).mkdir(parents=True)
        (p6 / "handoff/logs/TASK-6-imu.log").write_text(
            "[BOOT] 8c. ConfigBackup OK\n[BOOT] 8d. Init DisplayManager...\n"
            "MPU6050 6-DOF IMU : ONLINE (0x68) | Roll: 1.2 deg, Pitch: -3.4 deg\nGravitasi: 1.01 G\n"
            "{\"roll\":-31.6,\"pitch\":-14.8,\"accelG\":3.46}\n", encoding="utf-8")
        (p6 / "src/imu.py").write_text("def baca():\n    return 0\n", encoding="utf-8")
        benar = ("# REPORT-6\n## Ringkasan Fakta\n"
                 "- Saat boot tercetak `[BOOT] 8c. ConfigBackup OK` (`handoff/logs/TASK-6-imu.log:1`).\n"
                 "- IMU `MPU6050 6-DOF IMU : ONLINE (0x68) | Roll: 1.2 deg` dan `Gravitasi: 1.01 G` (`handoff/logs/TASK-6-imu.log:3..4`).\n"
                 "- Stream `\"roll\":-31.6` (`TASK-6-imu.log:5`), potongan `MPU6050 ... Pitch: -3.4 deg` (`handoff/logs/TASK-6-imu.log:3`).\n"
                 "- Perintah `python handoff/tools/x.py 9` (`handoff/logs/TASK-6-imu.log:1`); fungsi `bacaImu` (`src/imu.py:1`).\n"
                 "- Daemon (`handoff/logs/TASK-6-imu.log:1` `ConfigBackup OK`).\n"
                 "- Dua baris `[BOOT] 8c. ConfigBackup OK` dan `Gravitasi: 1.01 G` (`handoff/logs/TASK-6-imu.log:1`, `:4`).\n## Periksa Diri\n- ok\n")
        rc, out = jalan(p6, benar, "REPORT-6.md")
        cek(rc == 0 and "0 ERROR" in out and "kutipan `" not in out,
            "kutipan di prosa yang benar (rentang ..,  berantai, lanjutan, potongan ..., di dalam kurung) lolos; perintah dan rujukan kode dilewati", out)
        karang = ("# REPORT-6\n## Anomali / Pertanyaan\n"
                  "1. Kondisi C: `MPU6050 6-DOF IMU : ONLINE (0x68) | Roll: 12.2 deg, Pitch: -43.2 deg` dan `Gravitasi: 2.83 G`"
                  " (`handoff/logs/TASK-6-imu.log:1..2`). Lalu `\"roll\":-31.6` (`handoff/logs/TASK-6-imu.log:4`).\n"
                  "2. Tercetak `Init Display` (`handoff/logs/TASK-6-imu.log:1`).\n## Periksa Diri\n- ok\n")
        rc, out = jalan(p6, karang, "REPORT-6.md")
        cek(rc == 1 and len(re.findall(r"ERROR +baris 3: kutipan `", out)) == 3 and "Roll: 12.2" in out and "Gravitasi: 2.83 G" in out
            and "teks itu ada di handoff/logs/TASK-6-imu.log:5" in out,
            "kutipan karangan di Anomali (v3.15): 3 masalah, rujukan baris salah diberi baris yang benar", out)
        cek("WARNING    baris 4" in out and "Init Display" in out and "TASK-6-imu.log:2" in out,
            "kutipan tanpa angka yang tidak cocok: peringatan, dengan petunjuk barisnya", out)

        (p6 / "handoff/logs/ff.log").write_bytes(b"\x0c[BOOT] a\n[BOOT] b\n")
        rc, out = jalan(p6, "# R\n```bukti\nhandoff/logs/ff.log:2 | [BOOT] b\nhandoff/logs/ff.log:1 | [BOOT] a\n```\n## Periksa Diri\n", "REPORT-F.md")
        cek(rc == 0 and "0 ERROR" in out, "log diawali form feed: nomor baris sama dengan grep -n (form feed tidak memulai baris baru)", out)

        p7 = tmp / "proj7"
        (p7 / "handoff/reports").mkdir(parents=True)
        CATAT = SKRIP.parent / "record.py"

        def catat(log, teks, *opsi):
            subprocess.run([sys.executable, str(CATAT), *opsi, f"handoff/logs/{log}",
                            f'"{sys.executable}" -c "print(\'{teks}\')"'], cwd=p7, capture_output=True)
        catat("TASK-7-diff.log", "[UJI] semua 3 file")
        catat("TASK-7-diff.log", "[UJI] hanya src")
        catat("TASK-7-sama.log", "[UJI] x=1")
        catat("TASK-7-sama.log", "[UJI] x=1")
        catat("TASK-7-tambah.log", "[UJI] a=1")
        catat("TASK-7-tambah.log", "[UJI] b=2", "--append")
        rep7 = ("# REPORT-7\n```bukti\nhandoff/logs/TASK-7-diff.log:1 | [UJI] hanya src\nhandoff/logs/TASK-7-sama.log:1 | [UJI] x=1\n"
                "handoff/logs/TASK-7-tambah.log:2 | [UJI] b=2\n```\n## Periksa Diri\n- ok\n")
        rc, out = jalan(p7, rep7, "REPORT-7.md")
        cek(rc == 0 and out.count("ditimpa dengan perintah lain") == 1 and "TASK-7-diff.log ditimpa" in out and "semua 3 file" in out,
            "log ditimpa dengan perintah lain -> peringatan; perintah sama diulang dan --append tidak", out)

        (p6 / "handoff/tasks/TASK-T-templat.md").write_text(
            "# TASK-T\n## Kriteria terima\n| Kriteria | Harapan | Teramati | Bukti | Status |\n|---|---|---|---|---|\n"
            "| K1 build | `elf=` berbeda dari sebelum flash | | `<log>:<baris>` | |\n| K2 A1 | n ≥ 10 | | `<log>:<baris>` ×2 | |\n"
            "| K3 | user: perangkat dimiringkan | | `user: \"...\"` | |\n| S1 crash | 0 `Guru Meditation` | | `hitung(<log>, \"...\")` | |\n"
            "## Konteks\n| Kriteria | Harapan | Teramati | Bukti | Status |\n|---|---|---|---|---|\n| K1 lama | x | y | - | TIDAK DIUJI |\n",
            encoding="utf-8")
        data = "## Data yang Diminta\n| Kriteria | Harapan | Teramati | Bukti | Status |\n|---|---|---|---|---|\n"
        salin = ("# REPORT-T\n" + data + "| K1 build | elf= berbeda dari sebelum flash | - | - | TIDAK DIUJI |\n"
                 "| K2 A1 boot | n ≥ 10 | - | - | TIDAK DIUJI |\n| K2 A1 offset | n ≥ 10 | - | - | TIDAK DIUJI |\n"
                 "| K3 | user: perangkat dimiringkan | - | - | TIDAK DIUJI |\n| S1 crash | 0 `Guru Meditation` | - | - | TIDAK DIUJI |\n"
                 "\n## Periksa Diri\n- ok\n")
        rc, out = jalan(p6, salin, "REPORT-T.md")
        cek(rc == 0 and "templat" not in out, "templat tabel Data disalin (backtick boleh hilang, baris boleh dipecah berawalan sama): lolos; tabel berisi Teramati bukan templat", out)
        ubah = (salin.replace("| K1 build | elf= berbeda dari sebelum flash |", "| K1 build | elf=048bd707 |")
                .replace("| K3 | user: perangkat dimiringkan | - | - | TIDAK DIUJI |\n", "")
                .replace("| S1 crash | 0 `Guru Meditation` | - | - | TIDAK DIUJI |\n", "")
                .replace("| K2 A1 offset |", "| K2 A10 |"))
        rc, out = jalan(p6, ubah, "REPORT-T.md")
        cek(rc == 1 and "berbeda dari templat" in out and "elf=048bd707" in out and "baris templat \"S1 crash\"" in out
            and "kriteria K3" in out and "baris templat \"K3\"" not in out,
            "Harapan diubah dan baris templat hilang -> masalah (K3 hilang dilaporkan sekali oleh cek nomor K)", out)
    else:
        print("SKIP  uji v3.15: check_evidence.py versi lama")
    if "def cek_kode_keluar" in SKRIP.read_text(encoding="utf-8"):  # sejak v3.18
        p8 = tmp / "proj8"
        (p8 / "handoff/reports").mkdir(parents=True)
        (p8 / "scratchpad").mkdir()
        CATAT8 = SKRIP.parent / "record.py"
        # alat.py <nama> <n>: n run pertama untuk nama itu keluar 1, sesudahnya keluar 0; output selalu sama.
        (p8 / "alat.py").write_text(
            "import pathlib, sys\nnama, gagal = sys.argv[1], int(sys.argv[2])\np = pathlib.Path(nama + '.n')\n"
            "n = int(p.read_text()) if p.exists() else 0\np.write_text(str(n + 1))\n"
            "print('lulus=20/20')\nsys.exit(1 if n < gagal else 0)\n", encoding="utf-8")
        (p8 / "scratchpad/bungkus.py").write_text("print('hasil=7')\n", encoding="utf-8")

        def catat8(log, perintah, *opsi):
            subprocess.run([sys.executable, str(CATAT8), *opsi, f"handoff/logs/{log}", f'"{sys.executable}" {perintah}'],
                           cwd=p8, capture_output=True)

        catat8("satu.log", "alat.py a 1")
        catat8("ulang.log", "alat.py b 2")
        catat8("ulang.log", "alat.py b 2")
        catat8("ulang.log", "alat.py b 2")
        catat8("beda.log", "alat.py c 9")
        catat8("beda.log", "alat.py d 0")
        catat8("tambah.log", "alat.py e 1")
        catat8("tambah.log", "alat.py e 1", "--append")
        catat8("bersih.log", "alat.py f 0")
        catat8("bungkus.log", f'"{p8 / "scratchpad/bungkus.py"}"')
        (p8 / "handoff/logs/tap.log").write_text("# tests 328\n# pass: 328\n# fail 0\n", encoding="utf-8")
        data = "# REPORT-8\n## Data yang Diminta\n" + TABEL
        tutup = "\n## Periksa Diri\n- ok\n"

        rc, out = jalan(p8, data + "| K1 persiapan | lulus=20/20 | lulus=20/20 | `handoff/logs/satu.log:1` | OK |\n" + tutup)
        cek(rc == 0 and "WARNING    baris 5: status OK merujuk handoff/logs/satu.log" in out and "keluar dengan kode 1" in out,
            "baris OK merujuk log berkode keluar 1 -> peringatan (pola alat uji mencetak lulus tetapi keluar gagal)", out)
        rc, out = jalan(p8, data + "| K1 tanpa cek ulang (exit 1) | lulus=20/20 | lulus=20/20 | `handoff/logs/satu.log:1` | OK |\n"
                        "| K2 uji merah sebelum perbaikan | lulus=20/20 | lulus=20/20 | `handoff/logs/satu.log:1` | OK |\n"
                        "| K3 kode_keluar=1 diharapkan | lulus=20/20 | lulus=20/20 | `handoff/logs/satu.log:1` | OK |\n" + tutup)
        cek(rc == 0 and "keluar dengan kode" not in out, "baris yang mengakui kode keluar atau uji merah: tanpa peringatan", out)
        rc, out = jalan(p8, data + "| K1 lulus (exit 0) | lulus=20/20 | lulus=20/20 | `handoff/logs/satu.log:1` | OK |\n" + tutup)
        cek("keluar dengan kode 1" in out, "baris menyebut kode keluar yang salah (exit 0, nyatanya 1): tetap peringatan", out)
        rc, out = jalan(p8, data + "| K1 persiapan | lulus=20/20 | lulus=19/20 | `handoff/logs/satu.log:1` | GAGAL |\n" + tutup)
        cek("keluar dengan kode" not in out, "baris GAGAL yang merujuk log gagal: tanpa peringatan kode keluar", out)
        rc, out = jalan(p8, data + "| K1 bersih | lulus=20/20 | lulus=20/20 | `handoff/logs/bersih.log:1` | OK |\n" + tutup)
        cek(rc == 0 and "kode" not in out and "gagal" not in out.replace("GAGAL", ""), "log kode keluar 0 sekali jalan: tanpa peringatan baru", out)

        rc, out = jalan(p8, data + "| K1 ulang | lulus=20/20 | lulus=20/20 | `handoff/logs/ulang.log:1` | OK |\n" + tutup)
        cek(rc == 0 and "dijalankan 3 kali, 2 run lebih dulu gagal" in out and "keluar dengan kode" not in out,
            "perintah sama diulang sampai hijau: peringatan menyebut jumlah run dan run gagal", out)
        rc, out = jalan(p8, data + "| K1 ulang | lulus=20/20 | lulus=20/20 | `handoff/logs/ulang.log:1` | OK |\n"
                        "\n## Anomali / Pertanyaan\n- ulang.log dijalankan ulang karena gagal.\n" + tutup)
        cek("2 run lebih dulu gagal" in out, "disebut di Anomali tetap peringatan: head mencocokkan jumlah run dengan provenance", out)
        rc, out = jalan(p8, data + "| K1 beda | lulus=20/20 | lulus=20/20 | `handoff/logs/beda.log:1` | OK |\n" + tutup)
        cek("ditimpa dengan perintah lain" in out and "lebih dulu gagal" not in out, "perintah berbeda: peringatan lama saja, bukan ulang sampai hijau", out)
        rc, out = jalan(p8, data + "| K1 tambah | lulus=20/20 | lulus=20/20 | `handoff/logs/tambah.log:1` | OK |\n" + tutup)
        cek("lebih dulu gagal" not in out and "keluar dengan kode 1" in out,
            "--append: isi run gagal masih ada di log, jadi bukan tertimpa; baris OK tetap diperingatkan", out)
        asal8 = p8 / "handoff/logs/provenance.jsonl"
        catatan = asal8.read_text(encoding="utf-8").splitlines()
        akhir = next(l for l in reversed(catatan) if "ulang.log" in l)
        asal8.write_text("\n".join(catatan + [akhir.replace('"jenis": "log"', '"jenis": "redact"')]) + "\n", encoding="utf-8")
        rc, out = jalan(p8, data + "| K1 ulang | lulus=20/20 | lulus=20/20 | `handoff/logs/ulang.log:1` | OK |\n" + tutup)
        cek("dijalankan 3 kali, 2 run lebih dulu gagal" in out, "catatan redact bukan run: jumlah run tidak bertambah", out)

        rc, out = jalan(p8, data + "| K1 bungkus | hasil=7 | hasil=7 | `handoff/logs/bungkus.log:1` | OK |\n" + tutup)
        cek(rc == 0 and "memakai path sementara" in out and "bungkus.py" in out, "log dari skrip di scratchpad: peringatan path sementara", out)
        rc, out = jalan(p8, data + "| K1 bersih | lulus=20/20 | lulus=20/20 | `handoff/logs/bersih.log:1` | OK |\n" + tutup)
        cek("path sementara" not in out, "perintah di repo: tanpa peringatan path sementara", out)

        rc, out = jalan(p8, data + "| K1 tests | tests=328 dan pass=328 dan fail=0 | tests=328 dan pass=328 dan fail=0 | `handoff/logs/tap.log:1, 2, 3` | OK |\n" + tutup)
        cek(rc == 0 and "tidak terlihat" not in out, "Teramati kunci=nilai cocok dengan `tests 328` dan `pass: 328` di log (tanda palsu sebelum v3.18)", out)
        rc, out = jalan(p8, data + "| K1 tests | tests=329 | tests=329 | `handoff/logs/tap.log:1` | OK |\n" + tutup)
        cek(rc == 1 and "tidak terlihat" in out, "nilai yang berbeda tetap tidak terlihat", out)
    else:
        print("SKIP  uji v3.18: check_evidence.py versi lama")
    if "def cek_klaim_hitung" in SKRIP.read_text(encoding="utf-8"):  # sejak v3.18.1
        p9 = tmp / "proj9"
        for d in ("handoff/reports", "handoff/logs/raw", "handoff/logs/lain", "docs"):
            (p9 / d).mkdir(parents=True)
        subprocess.run(["git", "init", "-q"], cwd=p9, capture_output=True)
        (p9 / ".gitignore").write_text("handoff/logs/raw/\n", encoding="utf-8")
        (p9 / "handoff/logs/base.log").write_text("[10:00:00] [NET] err=0\n", encoding="utf-8")
        (p9 / "handoff/logs/audit.log").write_text("butir a ok\nbutir b GALAT elemen kosong\n", encoding="utf-8")
        (p9 / "handoff/logs/tabel.log").write_text(
            "# Nilai SMOKE\n| Aksi | Waktu | Konfirmasi |\n|---|---|---|\n| #1 off 1 | 20:25:12 | - |\n"
            "| #2 on 1 | 20:25:38 | +3.750 s |\n", encoding="utf-8")
        (p9 / "handoff/logs/pantau.log").write_text("[PC 07:29:26] rst:0x1 (POWERON_RESET)\n", encoding="utf-8")
        (p9 / "handoff/logs/raw/pantau.log").write_text("[PC 07:29:20] port dibuka\n", encoding="utf-8")
        (p9 / "handoff/logs/dup.log").write_text("x\n", encoding="utf-8")
        (p9 / "handoff/logs/lain/dup.log").write_text("x\n", encoding="utf-8")
        (p9 / "docs/dok.md").write_text("## lokasi\ntabel lokasi\ntabel sensor\n", encoding="utf-8")
        awal = "# REPORT-9\n## Data yang Diminta\n" + TABEL + "| K1 dasar | err=0 | err=0 | `handoff/logs/base.log:1` | OK |\n\n"
        tutup = "\n## Periksa Diri\n- ok\n"

        lampiran = ("### Lampiran K1\n| Item | Bukti dokumen | Kategori |\n|---|---|---|\n"
                    "| `lokasi` | hitung(docs/dok.md, \"lokasi\")=0 | kode-saja |\n"
                    "| `sensor` | hitung(docs/dok.md, \"sensor\")=1 | sama |\n")
        rc, out = jalan(p9, awal + lampiran + tutup)
        cek(rc == 1 and "klaim hitung(docs/dok.md, \"lokasi\")=0, padahal 2 baris" in out and "\"sensor\")=1" not in out,
            "klaim hitung()=N di tabel lampiran FAKTA dihitung ulang: 0 padahal 2 -> masalah; klaim yang benar lolos", out)
        prosa = ("## Ringkasan Fakta\n- Audit: `hitung(handoff/logs/audit.log, \"GALAT\")` = 0.\n"
                 "- Singkat: `hitung(..., \"GALAT\")` = 0, isi log dibaca.\n"
                 "- Benar: hitung(handoff/logs/audit.log, \"ok\") → 1.\n")
        rc, out = jalan(p9, awal + prosa + tutup)
        cek(rc == 1 and out.count("klaim hitung") == 1 and "\"GALAT\")=0, padahal 1 baris" in out,
            "klaim hitung()=N di prosa dihitung ulang; lingkup yang disingkat `...` dilewati", out)
        harapan = ("| Kriteria | Harapan | Catatan |\n|---|---|---|\n| K2 | `hitung(docs/dok.md, \"lokasi\")` = 5 | dicek head |\n\n"
                   + TABEL + "| K3 kontrak | `hitung(docs/dok.md, \"sensor\")` = 1 | 1 baris | hitung(docs/dok.md, \"sensor\") | OK |\n")
        rc, out = jalan(p9, awal + harapan + tutup)
        cek(rc == 0 and "klaim hitung" not in out, "syarat hitung() di kolom Harapan bukan klaim hasil: tidak dihitung ulang", out)

        rc, out = jalan(p9, awal + "## Anomali\n- Aksi #2 gagal tetapi diberi `Konfirmasi +3.750 s` (`handoff/logs/tabel.log:5`).\n"
                        "- Waktu aksi #2: `Waktu 20:25:38` (`tabel.log:5`).\n" + tutup)
        cek(rc == 0 and "tidak ada di baris" not in out,
            "kutipan `<nama kolom> <isi sel>` dari baris tabel di log cocok (tanda palsu `Konfirmasi +3.750 s`)", out)
        rc, out = jalan(p9, awal + "## Anomali\n- `Konfirmasi 20:25:38` (`handoff/logs/tabel.log:5`).\n" + tutup)
        cek(rc == 1 and "tidak ada di baris yang dirujuk" in out, "nilai dari kolom lain tetap tidak cocok", out)

        rc, out = jalan(p9, awal + "## Anomali\n- Reset lewat `--reset-com8` (`base.log:1`).\n"
                        "- Boot: `rst:0x1 (POWERON_RESET)` (`pantau.log:1`).\n" + tutup)
        cek(rc == 0 and "tidak ada di baris" not in out and "tidak dicek" not in out,
            "nama opsi bukan kutipan; nama log yang salinan mentahnya diabaikan git merujuk salinan yang ter-track", out)
        rc, out = jalan(p9, awal + "## Anomali\n- Boot: `rst:0x9` (`pantau.log:1`).\n" + tutup)
        cek(rc == 1 and "tidak ada di baris yang dirujuk" in out,
            "kutipan salah di log bernama ganda (salinan mentah diabaikan git) kini dicek -> masalah", out)
        rc, out = jalan(p9, awal + "## Anomali\n- `ERR 42` (`hilang.log:3`).\n- `x` (`dup.log:1`).\n" + tutup)
        cek(rc == 0 and out.count("tidak dicek") == 2 and "hilang.log tidak ada" in out and "ambigu" in out,
            "kutipan prosa yang file lognya tidak ada atau namanya ambigu: peringatan, bukan dilewati diam-diam", out)
        if "def log_bersama" in SKRIP.read_text(encoding="utf-8"):  # sejak v3.20.1
            # Pencarian cadangan baris log melewati log yang diabaikan git (log mentah bisa berukuran GB).
            (p9 / "handoff/logs/raw/sesi.log").write_text("[07:29:20] [PORT] dibuka\n", encoding="utf-8")
            (p9 / "handoff/logs/lain/boot.log").write_text("[07:29:26] [BOOT] rst:0x1\n", encoding="utf-8")
            rc, out = jalan(p9, awal + "## Bukti Mentah\n```\n[07:29:20] [PORT] dibuka\n```\n" + tutup)
            cek(rc == 1 and "tidak ada di file log mana pun (2 log yang diabaikan git tidak dicari)" in out
                and "raw/sesi.log" not in out,
                "baris log yang hanya ada di log yang diabaikan git: log itu tidak dicari sebagai file lain", out)
            rc, out = jalan(p9, awal + "## Bukti Mentah\n```\n[07:29:26] [BOOT] rst:0x1\n```\n" + tutup)
            cek(rc == 1 and "baris yang sama ada di handoff/logs/lain/boot.log" in out,
                "baris log di log lain yang tidak diabaikan git tetap menyebut file-nya", out)
            rc, out = jalan(p9, "# REPORT-9\n## Data yang Diminta\n" + TABEL
                            + "| K1 port | dibuka | dibuka | `handoff/logs/raw/sesi.log:1` | OK |\n\n"
                            + "## Bukti Mentah\n```\n[07:29:20] [PORT] dibuka\n```\n" + tutup)
            cek(rc == 0 and "tidak ada di file" not in out, "log yang diabaikan git tetap dicari bila report merujuknya", out)
        else:
            print("SKIP  uji v3.20.1: check_evidence.py versi lama")
    else:
        print("SKIP  uji v3.18.1: check_evidence.py versi lama")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

# ---- v3.24.1: A log gagal yang tidak disebut report, B hitung(<folder>) membaca semua file teks, C ekstensi rujukan ----
import hashlib
import json

tmp2 = Path(tempfile.mkdtemp(prefix="cekbukti2_"))
KASUS = []
GIT = ["git", "-c", "user.name=uji", "-c", "user.email=uji@example.com", "-c", "core.autocrlf=false"]
MARKA = "tidak disebut di report"  # penanda peringatan A
OK_LOG = "[10:00:00] lulus=3/3\n"
GAGAL_LOG = "[10:00:01] FAIL WidgetAlpha\n"
PERIKSA_T = "\n## Periksa Diri\n- ok\n"
PAT = "WidgetAlpha"
TABEL_FAKTA = "| No | Pertanyaan | Jawaban | Bukti | Status |\n|---|---|---|---|---|\n"
L15 = "".join(f"L{i}\n" for i in range(1, 16))


def kasus(id_):
    def pasang(fn):
        KASUS.append((id_, fn))
        return fn
    return pasang


def proyek(nama, git=False):
    p = tmp2 / nama
    for d in ("handoff/reports", "handoff/logs"):
        (p / d).mkdir(parents=True)
    if git:
        subprocess.run(["git", "init", "-q"], cwd=p, capture_output=True)
    return p


def tulis(p, rel, isi):
    f = p / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(isi if isinstance(isi, bytes) else isi.encode("utf-8"))


def git(p, *args):
    subprocess.run(GIT + list(args), cwd=p, capture_output=True)


def rec(nama, isi, perintah, kode, **kw):
    r = {"file": f"handoff/logs/{nama}", "jenis": "log", "perintah": perintah, "kode_keluar": kode,
         "mulai": "2026-11-13T10:00:00", "selesai": "2026-11-13T10:00:01", "tambah": False,
         "sha256": hashlib.sha256(isi.encode("utf-8")).hexdigest()}
    r.update(kw)
    return r


def prov(p, recs, mode="w"):
    with open(p / "handoff/logs/provenance.jsonl", mode, encoding="utf-8", newline="\n") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")


def a_proyek(nama, *baru, ok="TASK-001-ok.log", git_=False, tanpa_prov=False):
    """Proyek dengan log hijau `ok` dan log lain; tiap `baru` = (nama log, isi, perintah, kode[, tambahan catatan])."""
    p = proyek(nama, git_)
    tulis(p, f"handoff/logs/{ok}", OK_LOG)
    recs = [rec(ok, OK_LOG, "node --test a.js", 0)]
    for n, isi, perintah, kode, *ex in baru:
        tulis(p, f"handoff/logs/{n}", isi)
        recs.append(rec(n, isi, perintah, kode, **(ex[0] if ex else {})))
    if not tanpa_prov:
        prov(p, recs)
    return p


def laporan(nomor="001", ok="TASK-001-ok.log", ekstra="", blocked=False):
    return (f"# REPORT-{nomor}\n## Data yang Diminta\n" + TABEL
            + f"| K1 | lulus=3/3 | lulus=3/3 | handoff/logs/{ok}:1 | OK |\n\n" + ekstra
            + ("\nStatus akhir: BLOCKED\n" if blocked else "") + PERIKSA_T)


def lari(p, nama, isi, *args):
    f = p / "handoff" / "reports" / nama
    f.write_bytes(isi.encode("utf-8"))
    r = subprocess.run([sys.executable, "-B", str(SKRIP), *args, str(f.relative_to(p))], cwd=p,
                       capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


def pa(out):
    return [l for l in out.splitlines() if MARKA in l]


def n_cocok(out, lingkup="src"):
    m = re.search(rf"padahal (\d+) baris di {lingkup} cocok", out)
    return int(m.group(1)) if m else 0


def r_none(bukti='hitung(src, "WidgetAlpha")'):
    return ("# REPORT-001\n## Data yang Diminta\n" + TABEL_FAKTA
            + f"| 1 | Ada pemakai WidgetAlpha di src? | tidak ada | {bukti} | NONE |\n" + PERIKSA_T)


def b_proyek(nama, git_=False):
    p = proyek(nama, git_)
    tulis(p, "src/main.js", "export const a = 1;\n")
    for f in ("App.jsx", "Panel.tsx", "audit.mjs", "Detail.css", "Makefile"):
        tulis(p, f"src/{f}", f"// {PAT}\n")
    return p


# ---- A ----
@kasus("A1")
def test_a1_failed_log_not_mentioned():
    p = a_proyek("a1", ("TASK-001-fail.log", GAGAL_LOG, "node --test b.js", 1))
    rc, out = lari(p, "REPORT-001.md", laporan())
    w = pa(out)
    cek(rc == 0 and "0 ERROR" in out and len(w) == 1 and "handoff/logs/TASK-001-fail.log" in w[0]
        and "kode 1" in w[0] and "node --test b.js" in w[0],
        "A1 log gagal yang tidak disebut report: 1 peringatan dengan path, kode, perintah; 0 ERROR; exit 0", out)


@kasus("A2")
def test_a2_only_in_porcelain_line():
    p = a_proyek("a2", ("TASK-001-fail.log", GAGAL_LOG, "node --test b.js", 1))
    rc, out = lari(p, "REPORT-001.md", laporan(ekstra="```\n?? handoff/logs/TASK-001-fail.log\n```\n"))
    cek(len(pa(out)) == 1, "A2 nama log hanya di baris git status: tetap 1 peringatan", out)


@kasus("A3")
def test_a3_mentioned_in_prose():
    p = a_proyek("a3", ("TASK-001-fail.log", GAGAL_LOG, "node --test b.js", 1))
    rc, out = lari(p, "REPORT-001.md", laporan(ekstra="## Anomali\nRun TASK-001-fail.log keluar 1 karena WidgetAlpha.\n"))
    cek(rc == 0 and not pa(out), "A3 log disebut di prosa Anomali: 0 peringatan", out)


@kasus("A4")
def test_a4_referenced_by_ok_row():
    p = a_proyek("a4", ("TASK-001-fail.log", OK_LOG, "node --test b.js", 1))
    isi = laporan().replace("\n\n", "\n| K2 | lulus=3/3 | lulus=3/3 | handoff/logs/TASK-001-fail.log:1 | OK |\n\n", 1)
    rc, out = lari(p, "REPORT-001.md", isi)
    cek(out.count("status OK merujuk") == 1 and not pa(out), "A4 log gagal dirujuk baris OK: peringatan lama 1, peringatan A 0", out)


@kasus("A5")
def test_a5_overwritten_green():
    p = a_proyek("a5", ("TASK-001-x.log", GAGAL_LOG, "c1", 1), ("TASK-001-x.log", OK_LOG, "c2", 0))
    rc, out = lari(p, "REPORT-001.md", laporan())
    cek(not pa(out), "A5 run gagal tertimpa run hijau: 0 peringatan", out)


@kasus("A6")
def test_a6_append_after_green():
    p = a_proyek("a6", ("TASK-001-x.log", OK_LOG, "c1", 0), ("TASK-001-x.log", GAGAL_LOG, "c2", 1, {"tambah": True}))
    rc, out = lari(p, "REPORT-001.md", laporan())
    cek(len(pa(out)) == 1, "A6 run hijau lalu --append gagal: 1 peringatan", out)


@kasus("A7")
def test_a7_other_task_numbers():
    p = a_proyek("a7", ("TASK-002-fail.log", GAGAL_LOG, "c", 1), ("TASK-0011-fail.log", GAGAL_LOG, "c", 1),
                 ("TASK-001a-fail.log", GAGAL_LOG, "c", 1))
    rc, out = lari(p, "REPORT-001.md", laporan())
    cek(not pa(out), "A7 log task lain (002, 0011, 001a) untuk REPORT-001: 0 peringatan", out)


@kasus("A7b")
def test_a7b_letter_suffix():
    p = a_proyek("a7b", ("TASK-001a-fail.log", GAGAL_LOG, "c", 1), ("TASK-001-fail.log", GAGAL_LOG, "c", 1),
                 ok="TASK-001a-ok.log")
    rc, out = lari(p, "REPORT-001a.md", laporan("001a", "TASK-001a-ok.log"))
    w = pa(out)
    cek(len(w) == 1 and "TASK-001a-fail.log" in w[0], "A7b REPORT-001a: tepat 1 peringatan, untuk TASK-001a-fail.log", out)


@kasus("A8")
def test_a8_log_without_task_prefix():
    p = a_proyek("a8", ("build.log", GAGAL_LOG, "make", 1))
    rc, out = lari(p, "REPORT-001.md", laporan())
    cek(not pa(out), "A8 log gagal tanpa awalan task: 0 peringatan", out)


@kasus("A9")
def test_a9_result_file_record():
    p = a_proyek("a9", ("TASK-001-out.csv", "a,b\n", "node run.js --result out.csv", 1, {"jenis": "hasil"}))
    rc, out = lari(p, "REPORT-001.md", laporan())
    cek(not pa(out), "A9 catatan jenis hasil berkode 1: 0 peringatan", out)


@kasus("A10")
def test_a10_blocked_report():
    p = a_proyek("a10", ("TASK-001-fail.log", GAGAL_LOG, "c", 1))
    rc, out = lari(p, "REPORT-001.md", laporan(blocked=True))
    cek(not pa(out), "A10 report BLOCKED: 0 peringatan", out)


@kasus("A11")
def test_a11_log_file_deleted():
    p = a_proyek("a11", ("TASK-001-fail.log", GAGAL_LOG, "c", 1))
    (p / "handoff/logs/TASK-001-fail.log").unlink()
    rc, out = lari(p, "REPORT-001.md", laporan())
    cek(len(pa(out)) == 1, "A11 file log sudah dihapus, catatan masih ada: 1 peringatan", out)


@kasus("A12")
def test_a12_no_provenance():
    p = a_proyek("a12", ("TASK-001-fail.log", GAGAL_LOG, "c", 1), tanpa_prov=True)
    rc, out = lari(p, "REPORT-001.md", laporan())
    cek(rc == 0 and not pa(out) and "Traceback" not in out, "A12 tanpa file provenance: 0 peringatan, tanpa galat", out)


@kasus("A13")
def test_a13_exit_code_null():
    p = a_proyek("a13", ("TASK-001-fail.log", GAGAL_LOG, "c", None))
    rc, out = lari(p, "REPORT-001.md", laporan())
    cek(not pa(out), "A13 kode_keluar null: 0 peringatan", out)


@kasus("A14")
def test_a14_redact_after_failed_run():
    p = a_proyek("a14", ("TASK-001-fail.log", GAGAL_LOG, "c", 1), ("TASK-001-fail.log", GAGAL_LOG, "redact", 0, {"jenis": "redact"}))
    rc, out = lari(p, "REPORT-001.md", laporan())
    w = pa(out)
    cek(len(w) == 1 and "kode 1" in w[0], "A14 run gagal diikuti catatan redact: 1 peringatan, kode 1", out)


@kasus("A15")
def test_a15_case_insensitive_mention():
    p = a_proyek("a15", ("TASK-001-FAIL.log", GAGAL_LOG, "c", 1))
    rc, out = lari(p, "REPORT-001.md", laporan(ekstra="## Anomali\nRun task-001-fail.log keluar 1 karena WidgetAlpha.\n"))
    cek(not pa(out), "A15 nama log berbeda huruf besar-kecil di report: dianggap disebut", out)


@kasus("A16")
def test_a16_at_report_sees_overwritten_failure():
    p = a_proyek("a16", ("TASK-001-fail.log", GAGAL_LOG, "node --test b.js", 1), git_=True)
    tulis(p, "handoff/reports/REPORT-001.md", laporan())
    git(p, "add", "-A")
    git(p, "commit", "-q", "-m", "satu")
    tulis(p, "handoff/logs/TASK-001-fail.log", OK_LOG)
    prov(p, [rec("TASK-001-fail.log", OK_LOG, "node --test b.js", 0)], "a")
    git(p, "add", "-A")
    git(p, "commit", "-q", "-m", "dua")
    rc1, out1 = lari(p, "REPORT-001.md", laporan(), "--at-report")
    rc2, out2 = lari(p, "REPORT-001.md", laporan())
    cek(len(pa(out1)) == 1 and not pa(out2), "A16 --at-report: 1 peringatan (run gagal pada commit report); working tree: 0", out1 + out2)


@kasus("A17")
def test_a17_failed_then_append_green():
    p = a_proyek("a17", ("TASK-001-x.log", GAGAL_LOG, "c", 1), ("TASK-001-x.log", OK_LOG, "c2", 0, {"tambah": True}))
    rc, out = lari(p, "REPORT-001.md", laporan())
    w = pa(out)
    cek(len(w) == 1 and "kode 1" in w[0], "A17 run gagal diikuti --append hijau: 1 peringatan, kode 1", out)


@kasus("A18")
def test_a18_multiple_logs_ordered():
    p = a_proyek("a18", ("TASK-001-a.log", GAGAL_LOG, "ca", 1), ("TASK-001-a.log", GAGAL_LOG, "ca2", 2, {"tambah": True}),
                 ("TASK-001-b.log", GAGAL_LOG, "cb", 1), ("TASK-002-x.log", GAGAL_LOG, "cx", 1))
    rc, out = lari(p, "REPORT-001.md", laporan())
    w = pa(out)
    cek(len(w) == 2 and "TASK-001-a.log" in w[0] and "kode 2" in w[0] and "TASK-001-b.log" in w[1],
        "A18 dua log milik task: 2 peringatan, urut a lalu b, kode 2 untuk a; task lain tidak", out)


@kasus("A19")
def test_a19_name_without_suffix_and_lowercase():
    p = a_proyek("a19", ("TASK-001.log", GAGAL_LOG, "c", 1), ("task-001-fail.log", GAGAL_LOG, "c", 1))
    rc, out = lari(p, "REPORT-001.md", laporan())
    w = pa(out)
    cek(len(w) == 2 and any("TASK-001.log" in l for l in w) and any("task-001-fail.log" in l for l in w),
        "A19 TASK-001.log dan task-001-fail.log: masing-masing 1 peringatan", out)


@kasus("A20")
def test_a20_task_number_compared_as_text():
    p = a_proyek("a20", ("TASK-1-fail.log", GAGAL_LOG, "c", 1))
    rc, out = lari(p, "REPORT-001.md", laporan())
    cek(not pa(out), "A20 TASK-1-fail.log bukan milik REPORT-001: 0 peringatan", out)


@kasus("A21")
def test_a21_run_after_report_commit():
    p = a_proyek("a21", git_=True)
    tulis(p, "handoff/reports/REPORT-001.md", laporan())
    git(p, "add", "-A")
    git(p, "commit", "-q", "-m", "satu")
    tulis(p, "handoff/logs/TASK-001-probe.log", GAGAL_LOG)
    prov(p, [rec("TASK-001-probe.log", GAGAL_LOG, "node probe.js", 1)], "a")
    rc1, out1 = lari(p, "REPORT-001.md", laporan())
    rc2, out2 = lari(p, "REPORT-001.md", laporan(), "--at-report")
    cek(len(pa(out1)) == 1 and not pa(out2), "A21 run gagal sesudah commit report: working tree 1 peringatan; --at-report 0", out1 + out2)


KET = "tidak ada kecocokan"


def a_grep(nama, perintah_list, kode=1):
    return a_proyek(nama, *[(f"TASK-001-g{i}.log", GAGAL_LOG, c, kode) for i, c in enumerate(perintah_list)])


@kasus("A22")
def test_a22_rg_code1_explained():
    p = a_grep("a22", ['rg -n "WidgetAlpha" src'])
    rc, out = lari(p, "REPORT-001.md", laporan())
    w = pa(out)
    cek(rc == 0 and len(w) == 1 and "kode 1" in w[0] and 'rg -n "WidgetAlpha" src' in w[0] and KET in w[0],
        "A22 rg kode 1 tidak disebut: 1 peringatan dengan kode, perintah, keterangan; exit 0", out)


@kasus("A23")
def test_a23_rg_code2_plain():
    p = a_grep("a23", ['rg -n "WidgetAlpha" src'], kode=2)
    rc, out = lari(p, "REPORT-001.md", laporan())
    w = pa(out)
    cek(len(w) == 1 and "kode 2" in w[0] and KET not in w[0], "A23 rg kode 2: 1 peringatan tanpa keterangan", out)


@kasus("A24")
def test_a24_grep_family_code1():
    p = a_grep("a24", ["grep -rn WidgetAlpha src", "git grep -n WidgetAlpha", "C:/tools/rg.exe -n WidgetAlpha src"])
    rc, out = lari(p, "REPORT-001.md", laporan())
    w = pa(out)
    cek(len(w) == 3 and all(KET in l for l in w), "A24 grep, git grep, rg.exe kode 1: 3 peringatan, semuanya dengan keterangan", out)


@kasus("A25")
def test_a25_not_grep_code1():
    p = a_grep("a25", ["python -m pytest -k grep", "python tools/rg_check.py", "npm run grep"])
    rc, out = lari(p, "REPORT-001.md", laporan())
    w = pa(out)
    cek(len(w) == 3 and not any(KET in l for l in w), "A25 perintah bukan grep/rg kode 1: 3 peringatan tanpa keterangan", out)


@kasus("A26")
def test_a26_last_failure_decides():
    p = a_proyek("a26", ("TASK-001-x.log", GAGAL_LOG, 'rg -n "WidgetAlpha" src', 1),
                 ("TASK-001-x.log", GAGAL_LOG, "python -m pytest", 1, {"tambah": True}))
    rc, out = lari(p, "REPORT-001.md", laporan())
    w = pa(out)
    cek(len(w) == 1 and "python -m pytest" in w[0] and KET not in w[0],
        "A26 catatan gagal terakhir bukan grep: 1 peringatan tanpa keterangan", out)


@kasus("A27")
def test_a27_long_command_truncated_keeps_note():
    pola = "W" * 150
    p = a_grep("a27", [f'rg -n "{pola}" src'])
    rc, out = lari(p, "REPORT-001.md", laporan())
    w = pa(out)
    cek(len(w) == 1 and "W" * 113 in w[0] and "W" * 114 not in w[0] and KET in w[0],
        "A27 perintah rg 150 karakter: terpotong 120, keterangan tetap ada", out)


# ---- B ----
@kasus("B1")
def test_b1_none_with_jsx_users():
    p = b_proyek("b1")
    rc, out = lari(p, "REPORT-001.md", r_none())
    cek(rc == 1 and "status NONE, padahal 5 baris di src cocok" in out, "B1 NONE dengan pemakai di .jsx/.tsx/.mjs/.css/Makefile: ERROR 5 baris", out)


@kasus("B2")
def test_b2_binary_files_skipped():
    p = b_proyek("b2")
    tulis(p, "src/logo.png", PAT.encode() + b"\n")
    tulis(p, "src/blob.dat", PAT.encode() + b"\n\x00\x01")
    rc, out = lari(p, "REPORT-001.md", r_none())
    cek(n_cocok(out) == 5, "B2 logo.png dan blob.dat (byte NUL) tidak dihitung: tetap 5", out)


@kasus("B3")
def test_b3_old_extension_read_as_before():
    p = b_proyek("b3")
    tulis(p, "src/data.log", PAT.encode() + b"\n\x00\n")
    rc, out = lari(p, "REPORT-001.md", r_none())
    cek(n_cocok(out) == 6, "B3 data.log ber-NUL tetap dibaca (ekstensi lama): 6", out)


@kasus("B4")
def test_b4_ignored_folder():
    p = b_proyek("b4")
    tulis(p, "src/node_modules/x.jsx", f"// {PAT}\n")
    rc, out = lari(p, "REPORT-001.md", r_none())
    cek(n_cocok(out) == 5, "B4 src/node_modules/x.jsx diabaikan: tetap 5", out)


@kasus("B5")
def test_b5_prose_claim():
    p = b_proyek("b5")
    rc1, out1 = lari(p, "REPORT-001.md", '# REPORT-001\n## Ringkasan Fakta\n- Pemakai: hitung(src, "WidgetAlpha")=5\n' + PERIKSA_T)
    rc2, out2 = lari(p, "REPORT-001.md", '# REPORT-001\n## Ringkasan Fakta\n- Pemakai: hitung(src, "WidgetAlpha")=4\n' + PERIKSA_T)
    cek(rc1 == 0 and "0 ERROR" in out1 and rc2 == 1 and "padahal 5 baris di src cocok" in out2,
        "B5 klaim prosa =5 benar, =4 ERROR hitung ulang", out1 + out2)


@kasus("B6")
def test_b6_only_binary():
    p = proyek("b6")
    tulis(p, "src/logo.png", b"\x89PNG\x00\x01")
    rc, out = lari(p, "REPORT-001.md", r_none())
    cek(rc == 1 and "tidak berisi file teks" in out, "B6 folder hanya berisi logo.png: tidak berisi file teks", out)


@kasus("B7")
def test_b7_at_rev():
    p = b_proyek("b7", git_=True)
    git(p, "add", "-A")
    git(p, "commit", "-q", "-m", "satu")
    rc, out = lari(p, "REPORT-001.md", r_none(), "--at", "HEAD")
    cek(rc == 1 and "status NONE, padahal 5 baris di src cocok" in out, "B7 B1 pada mode --at <rev>: sama, 5 baris", out)


@kasus("B8")
def test_b8_new_extension_with_nul():
    p = b_proyek("b8")
    tulis(p, "src/blob.css", PAT.encode() + b"\n\x00\x01")
    rc, out = lari(p, "REPORT-001.md", r_none())
    cek(n_cocok(out) == 5, "B8 blob.css ber-NUL tidak dihitung: tetap 5", out)


@kasus("B9")
def test_b9_nul_at_boundary():
    awal = PAT.encode() + b"\n"
    pa_ = proyek("b9a")
    tulis(pa_, "src/a.dat", awal + b"x" * (8191 - len(awal)) + b"\x00")
    rc1, out1 = lari(pa_, "REPORT-001.md", r_none())
    pb = proyek("b9b")
    tulis(pb, "src/b.dat", awal + b"x" * (8192 - len(awal)) + b"\x00")
    rc2, out2 = lari(pb, "REPORT-001.md", r_none())
    cek("tidak berisi file teks" in out1 and n_cocok(out2) == 1,
        "B9 NUL di offset 8191 dilewati; NUL di offset 8192 tidak mencegah dihitung", out1 + out2)


@kasus("B10")
def test_b10_no_extension_dotfile_case():
    p = proyek("b10")
    for f in ("README", ".eslintrc", "App.JSX", "PIC.PNG"):
        tulis(p, f"src/{f}", f"// {PAT}\n")
    rc, out = lari(p, "REPORT-001.md", r_none())
    cek(n_cocok(out) == 3, "B10 README, .eslintrc, App.JSX dihitung; PIC.PNG tidak: 3", out)


@kasus("B11")
def test_b11_latin1_without_nul():
    p = proyek("b11")
    tulis(p, "src/latin.dat", b"\xff\xfe\n" + PAT.encode() + b"\n")
    rc, out = lari(p, "REPORT-001.md", r_none())
    cek(n_cocok(out) == 1 and "Traceback" not in out, "B11 file 0xFF tanpa NUL dihitung, tanpa galat", out)


@kasus("B12")
def test_b12_at_rev_follows_commit():
    p = proyek("b12", git=True)
    tulis(p, "src/main.js", "export const a = 1;\n")
    tulis(p, "src/App.jsx", f"// {PAT}\n")
    tulis(p, "src/more.jsx", f"// {PAT}\n")
    tulis(p, "src/blob.dat", PAT.encode() + b"\n\x00")
    git(p, "add", "-A")
    git(p, "commit", "-q", "-m", "satu")
    tulis(p, "src/App.jsx", PAT.encode() + b"\n\x00")
    tulis(p, "src/more.jsx", PAT.encode() + b"\n\x00")
    tulis(p, "src/blob.dat", f"// {PAT}\n")
    rc1, out1 = lari(p, "REPORT-001.md", r_none(), "--at", "HEAD")
    rc2, out2 = lari(p, "REPORT-001.md", r_none())
    cek(n_cocok(out1) == 2 and n_cocok(out2) == 1, "B12 --at HEAD mengikuti commit (2); working tree kebalikannya (1)", out1 + out2)


# ---- C ----
def c_proyek(nama):
    p = proyek(nama)
    tulis(p, "src/App.jsx", "// lulus=3/3\n")
    tulis(p, "src/app.js", "// lulus=3/3\n")
    return p


def r_bukti(bukti, teramati="lulus=3/3", harapan="lulus=3/3", ekstra=""):
    return ("# REPORT-001\n## Data yang Diminta\n" + TABEL + f"| K1 | {harapan} | {teramati} | {bukti} | OK |\n\n" + ekstra + PERIKSA_T)


@kasus("C1")
def test_c1_jsx_reference_in_table():
    p = c_proyek("c1")
    rc, out = lari(p, "REPORT-001.md", r_bukti("src/App.jsx:1"))
    rc1, o1 = lari(p, "REPORT-001.md", r_bukti("src/App.jsx:1", "lulus=9/9", "-"))
    rc2, o2 = lari(p, "REPORT-001.md", r_bukti("src/app.js:1", "lulus=9/9", "-"))
    m1 = [l for l in o1.splitlines() if "tidak terlihat" in l]
    m2 = [l for l in o2.splitlines() if "tidak terlihat" in l]
    cek(rc == 0 and "tanpa rujukan" not in out and len(m1) == 1 and m1 == m2,
        "C1 Bukti src/App.jsx:1 dicek; Teramati yang tidak terlihat memberi ERROR yang sama dengan .js", out + o1 + o2)


@kasus("C2")
def test_c2_jsx_reference_in_evidence_block():
    p = c_proyek("c2")
    rc1, o1 = lari(p, "REPORT-001.md", "# REPORT-001\n```bukti\nsrc/App.jsx:1 | // lulus=3/3\n```\n" + PERIKSA_T)
    rc2, o2 = lari(p, "REPORT-001.md", "# REPORT-001\n```bukti\nsrc/App.jsx:1 | isi salah\n```\n" + PERIKSA_T)
    cek(rc1 == 0 and "1 bukti dicek" in o1 and rc2 == 1 and "tidak sama dengan isi baris" in o2 and "tidak berformat" not in o2,
        "C2 blok bukti dengan .jsx: dicek; isi salah memberi ERROR kutipan, bukan ERROR format", o1 + o2)


@kasus("C3")
def test_c3_six_extensions():
    p = proyek("c3")
    ref = [("a/util.go", 1), ("lib/x.rs", 2), ("a/B.java", 3), ("x.vue", 1), ("s.css", 4), ("t.tsx", 9)]
    for n, _ in ref:
        tulis(p, n, L15)
    blok = "".join(f"{n}:{i} | L{i}\n" for n, i in ref)
    rc, out = lari(p, "REPORT-001.md", "# REPORT-001\n```bukti\n" + blok + "```\n" + PERIKSA_T)
    cek(rc == 0 and "6 bukti dicek" in out, "C3 .go .rs .java .vue .css .tsx dikenali: 6 bukti dicek", out)


@kasus("C4")
def test_c4_host_port_and_version_text():
    p = c_proyek("c4")
    isi = r_bukti("src/app.js:1")
    isi = isi.replace("\n\n", "\n| K2 | - | - | example.com:8080 localhost:3000 127.0.0.1:8080 v3.24:1 | UNTESTED |\n\n", 1)
    isi += "\nLayanan lokal: example.com:8080, localhost:3000, 127.0.0.1:8080, v3.24:1.\n"
    rc, out = lari(p, "REPORT-001.md", isi)
    cek(rc == 0 and "0 ERROR, 0 WARNING" in out, "C4 host:port dan versi:baris bukan rujukan file", out)


@kasus("C5")
def test_c5_compiler_output_block():
    p = c_proyek("c5")
    a = r_bukti("src/app.js:1", ekstra="```\nsrc/App.tsx:26:10 - error TS2322\n```\n")
    b = r_bukti("src/app.js:1", ekstra="```\nsrc/app.ts:26:10 - error TS2322\n```\n")
    rc1, o1 = lari(p, "REPORT-001.md", a)
    rc2, o2 = lari(p, "REPORT-001.md", b)
    cek(rc1 == rc2 and o1 == o2, "C5 keluaran kompiler .tsx:26:10 di blok kode diperlakukan sama dengan .ts", o1 + o2)


@kasus("C6")
def test_c6_fourteen_extensions_full_names():
    p = proyek("c6")
    ref = [("a.c", 1), ("a.cc", 2), ("a.cs", 3), ("a.css", 4), ("a.h", 5), ("a.hh", 6), ("a.hxx", 7), ("a.ts", 8),
           ("a.tsx", 9), ("a.mts", 10), ("a.js", 12), ("a.jsx", 13), ("a.mjs", 14), ("a.cjs", 15)]
    for n, _ in ref:
        tulis(p, n, L15)
    blok = "".join(f"{n}:{i} | L{i}\n" for n, i in ref)
    rc, out = lari(p, "REPORT-001.md", "# REPORT-001\n```bukti\n" + blok + "```\n" + PERIKSA_T)
    cek(rc == 0 and "14 bukti dicek" in out, "C6 empat belas ekstensi yang berawalan sama dikenali dengan nama utuh: 14 bukti dicek", out)


@kasus("C7")
def test_c7_missing_jsx_file():
    p = c_proyek("c7")
    rc1, o1 = lari(p, "REPORT-001.md", r_bukti("src/Missing.jsx:1"))
    rc2, o2 = lari(p, "REPORT-001.md", r_bukti("src/Missing.js:1"))
    cek("file src/Missing.jsx tidak ada" in o1 and "tanpa rujukan" not in o1 and "file src/Missing.js tidak ada" in o2,
        "C7 rujukan .jsx ke file yang tidak ada: pesan `file ... tidak ada`, sama dengan .js", o1 + o2)


@kasus("C8")
def test_c8_tsx_line_and_column_in_cell():
    p = c_proyek("c8")
    rc1, o1 = lari(p, "REPORT-001.md", r_bukti("src/App.tsx:26:10"))
    rc2, o2 = lari(p, "REPORT-001.md", r_bukti("src/app.ts:26:10"))
    cek(rc1 == rc2 and o1 == o2, "C8 sel Bukti src/App.tsx:26:10 berperilaku sama dengan src/app.ts:26:10", o1 + o2)


@kasus("C9-jsx")
def test_c9_uppercase_jsx_recognized():
    p = proyek("c9a")
    tulis(p, "src/App.JSX", "// lulus=3/3\n")
    rc, out = lari(p, "REPORT-001.md", r_bukti("src/App.JSX:1"))
    cek(rc == 0 and "tanpa rujukan" not in out and "1 bukti dicek" in out, "C9-jsx src/App.JSX:1 dikenali", out)


@kasus("C9-makefile")
def test_c9_makefile_not_recognized():
    p = proyek("c9b")
    tulis(p, "Makefile", "a\nb\nlulus=3/3\n")
    rc, out = lari(p, "REPORT-001.md", r_bukti("Makefile:3"))
    cek(rc == 1 and "status OK tanpa rujukan file:baris" in out, "C9-makefile Makefile:3 tidak dikenali (di luar lingkup)", out)


@kasus("C10")
def test_c10_ccTLD_in_prose():
    p = c_proyek("c10")
    isi = r_bukti("src/app.js:1", ekstra="Layanan: db.example.cc:5432, cache.example.rs:6379, x.example.tf:443.\n")
    rc, out = lari(p, "REPORT-001.md", isi)
    cek(rc == 0 and "0 ERROR, 0 WARNING" in out, "C10 host:port berakhiran mirip ekstensi di prosa: tanpa temuan", out)


try:
    for id_, fn in KASUS:
        try:
            fn()
        except Exception as e:  # satu kasus yang rusak tidak menghentikan kasus lain
            cek(False, f"{id_} uji berhenti: {type(e).__name__}: {e}")
finally:
    shutil.rmtree(tmp2, ignore_errors=True)
print("\nRESULT:", "ALL OK" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
