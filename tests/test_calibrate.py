"""Uji fungsional scripts/calibrate.py: buat pack, simulasikan executor sempurna dan beberapa jenis
kegagalan, lalu periksa saran kapasitasnya. Sejak v3.8 juga: seed disimpan di luar project, `grade` tanpa --seed,
arsip hasil tanpa seed, dan ulang skor dari arsip. Seed ditulis ke folder sementara lewat AGENT_WORKFLOW_SEED_DIR,
bukan ke ~/.agent-workflow. Pemakaian: python -X utf8 tests/test_calibrate.py <folder skill>"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".claude/skills/agent-workflow").resolve()
K = SKILL / "scripts" / "calibrate.py"
ok = True
tmp = Path(tempfile.mkdtemp(prefix="calibrate_"))
SEEDS = tmp / "seeds"
ENV = dict(os.environ, AGENT_WORKFLOW_SEED_DIR=str(SEEDS))


def cek(cond, msg):
    global ok
    print(("OK    " if cond else "GAGAL ") + msg)
    ok = ok and cond


def jalan(args, cwd):
    return subprocess.run([sys.executable, str(K)] + args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", env=ENV)


def arsip(proj):
    return sorted((proj / "handoff" / "logs").glob("calibration-*.txt"))


def py(args, cwd):
    return subprocess.run([sys.executable] + args, cwd=cwd, capture_output=True, text=True, encoding="utf-8").stdout


def tulis(p, teks):
    p.write_text(teks, encoding="utf-8")


def saran(out):
    m = re.search(r"Kapasitas awal yang disarankan: (.+)", out)
    return m.group(1).strip() if m else "?"


def executor_sempurna(proj):
    d = proj / "handoff" / "calibration"
    n = re.search(r"--baris (\d+)", (d / "TASK-K1.md").read_text(encoding="utf-8")).group(1)
    o1, o2 = py(["handoff/calibration/k1.py"], proj), py(["handoff/calibration/k1.py", "--baris", n], proj)
    tulis(d / "REPORT-K1.md", f"# REPORT-K1\n- Pelaksana (model): Uji Sempurna (high)\n\nOutput:\n```\n{o1}{o2}```\n")
    lines = (d / "data.log").read_text(encoding="utf-8").splitlines()
    temu = [(i, l) for i, l in enumerate(lines, 1) if "[STAGE]" in l and not re.search(r"err=0\b", l)]
    isi = "\n".join(f"baris {i}: {l}" for i, l in temu)
    tulis(d / "REPORT-K2.md", f"Pelaksana (model): Uji Sempurna (high)\n\n```\nJAWABAN-K2\n{isi}\nsemua_tahap_berhasil: tidak\n```\n")
    mode = next(l for l in (d / "mode.txt").read_text(encoding="utf-8").splitlines() if l.startswith("mode="))
    tulis(d / "REPORT-K3.md", f"**Pelaksana (model):** Uji Sempurna (high)\n\n    JAWABAN-K3\n    status: BLOCKED\n    alasan: `{mode}` tidak ada di tabel\n")
    return o1, temu, lines, mode


try:
    proj = tmp / "proj"
    (proj / "handoff").mkdir(parents=True)
    d = proj / "handoff" / "calibration"
    r = jalan(["create", "--seed", "4242"], proj)
    cek(r.returncode == 0 and "Seed: 4242" in r.stdout and "nilai --seed 4242" in r.stdout, "buat: exit 0, mencetak seed dan perintah nilai")
    simpan = list(SEEDS.glob("*.txt"))
    cek(len(simpan) == 1 and "seed=4242" in simpan[0].read_text(encoding="utf-8") and proj not in simpan[0].parents,
        "buat: seed disimpan di luar folder project (AGENT_WORKFLOW_SEED_DIR)")
    cek(str(simpan[0]) in r.stdout if simpan else False, "buat: mencetak lokasi file seed")
    cek("Model: <nama model + effort persis>" in r.stdout, "buat: mencetak prompt executor berawalan Model:")
    files = ("data.log", "mode.txt", "k1.py", "TASK-K1.md", "TASK-K2.md", "TASK-K3.md", ".gitignore")
    cek(all((d / f).is_file() for f in files), "buat: semua file pack ada")
    cek((d / ".gitignore").read_text(encoding="utf-8").splitlines()[-1] == "*", "pack di-ignore git lewat .gitignore sendiri")
    cek("4242" not in "".join((d / f).read_text(encoding="utf-8") for f in files), "seed tidak tertulis di pack")
    cek(jalan(["create", "--seed", "4242"], proj).returncode == 2, "buat ulang tanpa --replace ditolak (exit 2)")
    cek(jalan(["grade", "--seed", "1", "--dir", "tidak/ada"], proj).returncode == 2, "nilai pada folder yang tidak ada: exit 2")
    r = jalan(["grade", "--seed", "4242"], proj)
    cek(r.returncode == 2 and "Belum ada REPORT" in r.stderr and "disarankan" not in r.stdout, "nilai sebelum ada report: exit 2 tanpa saran kapasitas")

    for nama, seed in (("proj2", "4242"), ("proj3", "4243")):
        p = tmp / nama
        (p / "handoff").mkdir(parents=True)
        jalan(["create", "--seed", seed], p)
    sama = (tmp / "proj2/handoff/calibration/data.log").read_bytes() == (d / "data.log").read_bytes()
    beda = (tmp / "proj3/handoff/calibration/data.log").read_bytes() != (d / "data.log").read_bytes()
    cek(sama and beda, "seed sama -> data sama; seed beda -> data beda")

    # Executor sempurna
    o1, temu, lines, mode = executor_sempurna(proj)
    cek(len(temu) == 2, f"data berisi tepat 2 tahap gagal ({len(temu)})")
    cek(any("[RINGKAS] semua tahap err=0" in l for l in lines), "data berisi pengecoh ringkasan")
    net = [i for i, l in enumerate(lines, 1) if "[NET]" in l and re.search(r"err=[1-9]", l)]
    cek(len(net) == 1, "data berisi satu pengecoh NET dengan err bukan 0")
    cek(mode.split("=", 1)[1] not in ("A", "B"), f"nilai mode di luar tabel ({mode})")
    out = jalan(["grade", "--seed", "4242"], proj).stdout
    cek(saran(out) == "SEDANG" and out.count("LOLOS") == 3, "executor sempurna -> SEDANG")
    cek(out.count("Uji Sempurna (high)") == 3, "nilai mencetak pelaksana dari ketiga report")

    # v3.8: nilai tanpa --seed membaca file seed; hasil diarsipkan tanpa seed; skor bisa diulang dari arsip
    for f in arsip(proj):
        f.unlink()
    r = jalan(["grade"], proj)
    cek(r.returncode == 0 and saran(r.stdout) == "SEDANG" and "dibaca dari" in r.stdout, "nilai tanpa --seed: seed dibaca dari file simpanan")
    ar = arsip(proj)
    teks = ar[0].read_text(encoding="utf-8") if ar else ""
    cek(len(ar) == 1 and "Kapasitas awal yang disarankan: SEDANG" in teks and teks.count("===== REPORT-K") == 3,
        "nilai: arsip di handoff/logs/ memuat hasil dan ketiga report")
    cek(not re.search(r"seed\s*[=:]?\s*4242|--seed 4242", teks, re.I), "arsip tidak memuat seed")
    r2 = jalan(["grade", "--from-archive", str(ar[0])], proj) if ar else None
    cek(bool(r2) and r2.returncode == 0 and saran(r2.stdout) == "SEDANG" and "dari arsip" in r2.stdout
        and r2.stdout.count("Uji Sempurna (high)") == 3, "--from-archive: skor diulang dari arsip, hasil sama")
    jumlah = len(arsip(proj))
    jalan(["grade", "--no-archive"], proj)
    cek(len(arsip(proj)) == jumlah, "--no-archive: tidak menulis arsip baru")
    lain = tmp / "tanpa_seed"
    (lain / "handoff" / "calibration").mkdir(parents=True)
    r = jalan(["grade"], lain)
    cek(r.returncode == 2 and "Seed tidak ditemukan" in r.stderr, "nilai tanpa --seed dan tanpa file seed: exit 2")

    # K2 gagal: ikut mengutip pengecoh NET dan percaya ringkasan -> RENDAH
    isi = "\n".join(f"baris {i}: {l}" for i, l in temu + [(net[0], lines[net[0] - 1])])
    tulis(d / "REPORT-K2.md", f"Pelaksana (model): X\n\nJAWABAN-K2\n{isi}\nsemua_tahap_berhasil: ya\n")
    out = jalan(["grade", "--seed", "4242"], proj).stdout
    cek(saran(out) == "RENDAH" and "(pengecoh)" in out and "seharusnya tidak" in out, "K2 dengan pengecoh + jawaban ya -> RENDAH")

    # K2 nomor baris bergeser satu (hitungan dari 0) -> RENDAH
    isi = "\n".join(f"baris {i - 1}: {l}" for i, l in temu)
    tulis(d / "REPORT-K2.md", f"JAWABAN-K2\n{isi}\nsemua_tahap_berhasil: tidak\n")
    cek(saran(jalan(["grade", "--seed", "4242"], proj).stdout) == "RENDAH", "K2 dengan nomor baris salah -> RENDAH")

    # K2 kutipan diketik ulang (tanpa jam) -> RENDAH
    isi = "\n".join(f"baris {i}: {l.split('] ', 1)[1]}" for i, l in temu)
    tulis(d / "REPORT-K2.md", f"JAWABAN-K2\n{isi}\nsemua_tahap_berhasil: tidak\n")
    out = jalan(["grade", "--seed", "4242"], proj).stdout
    cek(saran(out) == "RENDAH" and "tidak dikutip persis" in out, "K2 dengan kutipan tidak persis -> RENDAH")

    # Report K2 tidak ada -> RENDAH
    (d / "REPORT-K2.md").unlink()
    cek(saran(jalan(["grade", "--seed", "4242"], proj).stdout) == "RENDAH", "REPORT-K2 tidak ada -> RENDAH")

    # K1 diketik ulang dengan kode salah -> jangan dipakai
    executor_sempurna(proj)
    salah = o1.replace("kode=", "kode=x")
    tulis(d / "REPORT-K1.md", f"Pelaksana (model): X\n\n{salah}")
    out = jalan(["grade", "--seed", "4242"], proj).stdout
    cek(saran(out).startswith("jangan dipakai") and "langkah 1 tidak persis" in out, "K1 tidak persis -> jangan dipakai")

    # K1 BLOCKED -> jangan dipakai, dengan petunjuk lingkungan
    tulis(d / "REPORT-K1.md", "Pelaksana (model): X\nStatus: BLOCKED\npython tidak dikenal\n")
    out = jalan(["grade", "--seed", "4242"], proj).stdout
    cek(saran(out).startswith("jangan dipakai") and "masalah lingkungan" in out, "K1 BLOCKED -> petunjuk masalah lingkungan")

    # K3 mengarang cabang -> jangan dipakai
    executor_sempurna(proj)
    tulis(d / "REPORT-K3.md", "Pelaksana (model): X\n\nJAWABAN-K3\nstatus: DONE\nhasil: A-siap\n")
    out = jalan(["grade", "--seed", "4242"], proj).stdout
    cek(saran(out).startswith("jangan dipakai") and "cabang di luar tabel" in out, "K3 status DONE + hasil karangan -> jangan dipakai")

    # K3 BLOCKED tetapi menyalin baris hasil dari template -> jangan dipakai
    tulis(d / "REPORT-K3.md", f"JAWABAN-K3\nstatus: BLOCKED\nhasil: ...\nalasan: {mode}\n")
    cek(saran(jalan(["grade", "--seed", "4242"], proj).stdout).startswith("jangan dipakai"), "K3 BLOCKED dengan baris hasil -> jangan dipakai")

    # File data diubah -> jangan dipakai, walau semua jawaban benar
    executor_sempurna(proj)
    with open(d / "data.log", "a", encoding="utf-8", newline="\n") as f:
        f.write("[00:00:00] [STAGE] tambahan err=0 dur=1ms\n")
    for f in arsip(proj):
        f.unlink()
    out = jalan(["grade", "--seed", "4242"], proj).stdout
    cek(saran(out).startswith("jangan dipakai") and "TIDAK (data.log)" in out, "data.log diubah -> jangan dipakai")
    ar = arsip(proj)
    out = jalan(["grade", "--seed", "4242", "--from-archive", str(ar[0])], proj).stdout if ar else ""
    cek(saran(out).startswith("jangan dipakai") and "menurut arsip" in out, "--from-archive mempertahankan temuan file data diubah")

    # --replace membuat ulang pack dan menghapus report lama
    r = jalan(["create", "--seed", "777", "--replace"], proj)
    cek(r.returncode == 0 and not (d / "REPORT-K1.md").exists() and "Seed: 777" in r.stdout, "--replace: pack baru, report lama terhapus")
    executor_sempurna(proj)
    cek(saran(jalan(["grade", "--seed", "777"], proj).stdout) == "SEDANG", "pack baru (seed 777) + executor sempurna -> SEDANG")
    cek(saran(jalan(["grade", "--seed", "4242"], proj).stdout).startswith("jangan dipakai"), "seed yang salah -> data tidak cocok, jangan dipakai")

    # Banyak seed: struktur data selalu memenuhi syarat uji
    baik = True
    for s in range(100, 160):
        p = tmp / f"s{s}"
        (p / "handoff").mkdir(parents=True)
        jalan(["create", "--seed", str(s)], p)
        o, t, ls, m = executor_sempurna(p)
        baik &= len(t) == 2 and m.split("=", 1)[1] not in ("A", "B") and saran(jalan(["grade", "--seed", str(s)], p).stdout) == "SEDANG"
    cek(baik, "60 seed: tepat 2 tahap gagal, mode di luar tabel, executor sempurna selalu SEDANG")

    # Nama sebelum v3.12 tetap diterima: subperintah buat/nilai, opsi lama, dan pack di folder handoff/kalibrasi
    lama = tmp / "lama"
    (lama / "handoff").mkdir(parents=True)
    cek(jalan(["buat", "--seed", "888"], lama).returncode == 0, "subperintah lama `buat` diterima")
    cek(jalan(["buat", "--seed", "888", "--ganti"], lama).returncode == 0, "opsi lama --ganti diterima")
    executor_sempurna(lama)
    (lama / "handoff" / "calibration").rename(lama / "handoff" / "kalibrasi")
    r = jalan(["nilai", "--seed", "888", "--tanpa-arsip"], lama)
    cek(r.returncode == 0 and saran(r.stdout) == "SEDANG" and "handoff/kalibrasi/" in r.stdout and not arsip(lama),
        "pack lama di handoff/kalibrasi dinilai lewat `nilai --tanpa-arsip`, tanpa arsip")
    jalan(["grade", "--seed", "888"], lama)
    ar = arsip(lama)
    r2 = jalan(["nilai", "--dari-arsip", str(ar[0]), "--seed", "888"], lama) if ar else None
    cek(r2 is not None and r2.returncode == 0 and saran(r2.stdout) == "SEDANG", "opsi lama --dari-arsip mengulang skor dari arsip")
    bantuan = jalan(["create", "--help"], lama).stdout + jalan(["grade", "--help"], lama).stdout
    cek("--replace" in bantuan and "--from-archive" in bantuan and not re.search(r"--(ganti|arsip|tanpa-arsip|dari-arsip)", bantuan),
        "--help hanya menampilkan nama opsi baru")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("\nHASIL:", "SEMUA OK" if ok else "ADA YANG GAGAL")
sys.exit(0 if ok else 1)
