"""Uji fungsional scripts/check_evidence.py pada project palsu. Pemakaian: python -X utf8 tests/test_check_evidence.py <path check_evidence.py>"""
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
    print(("OK    " if cond else "GAGAL ") + msg)
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
    cek(rc == 0 and "0 masalah" in out, "report yang benar: exit 0, 0 masalah", out)
    cek("Ringkas: 12 bukti dicek" in out, "semua bukti terhitung (tabel, blok bukti, blok log, grep -n, Select-String)", out)

    # Pola REPORT-054: blok kode berisi baris log karangan
    rc, out = jalan(proj, "Pelaksana (model): X\nLog: `handoff/logs/a.log`\n\n```\n[OLED_STAT] init=1 render_fail=0 last_ok_ms_ago=26 ka_err=4 bus_resets=133\n[OLED_STAGE] refresh err=0\n[OLED_STAGE] on err=0\n```\n")
    cek(rc == 1 and out.count("tidak ada di file log mana pun") == 2, "baris log karangan (pola REPORT-054) -> 2 masalah, baris asli lolos", out)

    rc, out = jalan(proj, "## Data\n" + TABEL + "| on | err=0 | err=255 | `handoff/logs/a.log:3` | OK |\n")
    cek(rc == 1 and "tidak memenuhi Harapan" in out, "OK yang bertentangan dengan Harapan -> masalah", out)
    rc, out = jalan(proj, "## Data\n" + TABEL + "| on | err=0 | err=0 | `handoff/logs/a.log:3` | OK |\n")
    cek(rc == 1 and "tidak terlihat di baris yang dirujuk" in out, "Teramati karangan (err=0 padahal baris berisi err=255) -> masalah", out)
    rc, out = jalan(proj, "## Data\n" + TABEL + "| on | err=0 | err=0 | lihat log di atas | OK |\n")
    cek(rc == 1 and "OK tanpa rujukan" in out, "OK tanpa rujukan file:baris -> masalah", out)
    rc, out = jalan(proj, "## Data\n" + TABEL + "| fps | fps>=15 | fps=12.3 | `a.log:6` | OK |\n")
    cek(rc == 1 and "tidak memenuhi Harapan" in out, "perbandingan angka fps>=15 vs 12.3 -> masalah", out)
    rc, out = jalan(proj, "## Data\n" + TABEL + "| refresh | err=0 | err=0 | `handoff/logs/a.log:2` | GAGAL |\n")
    cek(rc == 0 and "PERINGATAN" in out and "padahal Teramati memenuhi" in out, "GAGAL yang memenuhi Harapan -> peringatan saja", out)

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
    cek(rc == 0 and "0 masalah" in out and "3 bukti dicek" in out, "rujukan lanjutan `:5` dan hitung() untuk kriteria '0 kemunculan' -> lolos", out)
    rc, out = jalan(proj, "## Data\n" + TABEL + "| crash | =0 | 0 | hitung(handoff/logs/a.log, \"Guru|rst:0x\") | OK |\n")
    cek(rc == 1 and "kolom, header" in out, "tanda | tanpa escape di sel -> masalah jumlah kolom, bukan baris terlewat", out)
    rc, out = jalan(proj, "## Data\n" + TABEL + "| stage | =2 | 2 | hitung(handoff/logs/a.log, \"OLED_STAGE\") | OK |\n"
                          "| rusak | =0 | 0 | hitung(handoff/logs/a.log, \"(\") | OK |\n")
    cek(rc == 1 and "3 baris di handoff/logs/a.log cocok" in out and "bukan regex yang valid" in out, "hitung() yang tidak cocok dan pola rusak -> masalah", out)
    (proj / "src").mkdir()
    (proj / "src/x.cpp").write_text("int a = 1;\nint b = 2;\nint c = 3;\n", encoding="utf-8")
    rc, out = jalan(proj, "```bukti\nhandoff/logs/a.log:2 | refresh err=0\n```\nSebelum perubahan:\n```\nsrc/x.cpp:3:int c = 999;\n```\n"
                          "```powershell\nSelect-String -Path src/x.cpp -Pattern int\n```\n```\nLineNumber Line\n---------- ----\n         1 int a = 0;\n```\n")
    cek(rc == 0 and "0 masalah" in out, "kutipan grep/Select-String atas file kode dilewati (bisa versi sebelum perubahan)", out)
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
    cek(rc == 0 and "0 masalah" in out and "4 bukti dicek" in out and "Periksa Diri" not in out,
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
                cek(rc == 0 and "0 masalah" in out, "kutipan report lama ke asal.jsonl dibaca dari provenance.jsonl (isi sama)", out)
                rc, out = jalan(p4, "```bukti\nhandoff/tools/catat.py:1 | import sys\n```\n", "REPORT-M.md")
                cek(rc == 1 and "sejak v3.12 bernama handoff/tools/record.py" in out,
                    "kutipan report lama ke catat.py: masalah, dengan nama barunya dan saran --at-report", out)
        else:
            print("LEWAT uji v3.12: check_evidence.py versi lama")

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
        print("LEWAT uji v3.9: check_evidence.py versi lama")

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
        cek(rc == 0 and "tidak tercatat" not in out and "0 masalah" in out,
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
        print("LEWAT uji v3.9.2: check_evidence.py versi lama")

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
        cek(rc == 0 and "0 masalah" in out and "Periksa Diri" not in out, "report berbahasa Inggris (Self-check, Criteria/Expected/Observed/Evidence, PASS, count, evidence): 0 masalah", out)
        cek(out.count("tanpa rujukan file:baris di baris ini") == 1 and "5 sec" in out, "Fact Summary: angka tanpa rujukan diberi peringatan; 'estimate' dianggap perkiraan", out)
        salah = en.replace("| K1 tests | failed=0 |", "| K1 tests | failed>0 |").replace("| K2 errors | =0 | 0 | count(handoff/logs/run.log, \"ERROR\") | PASS |\n", "")
        rc, out = jalan(p4, salah, "REPORT-7.md")
        cek(rc == 1 and "status OK, padahal" in out and "kriteria K2" in out, "bahasa Inggris: PASS yang melanggar Expected dan kriteria K2 yang hilang tertangkap", out)
        fakta = ("# REPORT-7\n## Answers\n| No | Question | Answer | Evidence | Status |\n|---|---|---|---|---|\n"
                 "| 1 | Any TEST line? | none | count(handoff/logs/run.log, \"TEST\") | NOT FOUND |\n| 2 | ? | ? | - | UNSURE |\n\n## Self-check\n")
        rc, out = jalan(p4, fakta, "REPORT-7.md")
        cek(rc == 1 and "status TIDAK ADA, padahal 1 baris" in out, "NOT FOUND yang hitungannya > 0 adalah masalah; UNSURE tidak dicek", out)
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
        cek(rc == 0 and "0 masalah" in out and f"pada commit {c1[:8]}" in out, "--at <commit>: kutipan dan hitung(src/**/*.py) dicocokkan dengan isi file pada commit itu", out)
        rc, out = jalan_arg(p5, "--at-report", "handoff/reports/REPORT-*.md")
        cek(rc == 0 and "0 masalah" in out and f"pada commit {c1[:8]}" in out, "--at-report (argumen glob): commit terakhir yang mengubah report dipakai", out)
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
        print("LEWAT uji v3.10: check_evidence.py versi lama")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("\nHASIL:", "SEMUA OK" if ok else "ADA YANG GAGAL")
sys.exit(0 if ok else 1)
