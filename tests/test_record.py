"""Uji fungsional scripts/record.py (v3.9): output tersimpan apa adanya, asal tercatat di handoff/logs/provenance.jsonl,
kode keluar diteruskan, --append, --result, --pwsh, dan hash yang tahan konversi CRLF. Sejak v3.12 juga nama opsi
dan file asal sebelum v3.12.
Pemakaian: python -X utf8 tests/test_record.py <folder skill>"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".claude/skills/agent-workflow").resolve()
CATAT = SKILL / "scripts" / "record.py"
ok = True


def cek(cond, msg, out=""):
    global ok
    print(("OK    " if cond else "GAGAL ") + msg)
    if not cond and out:
        print("      " + out.replace("\n", "\n      "))
    ok = ok and cond


def catat(proj, *args):
    return subprocess.run([sys.executable, str(CATAT)] + list(args), cwd=proj, capture_output=True)


def asal(proj):
    p = proj / "handoff/logs/provenance.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()] if p.is_file() else []


def hash_lf(b):
    return hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


py = f'"{sys.executable}"'
tmp = Path(tempfile.mkdtemp(prefix="catat_"))
try:
    proj = tmp / "proj"
    (proj / "handoff").mkdir(parents=True)
    r = catat(proj, "handoff/logs/a.log", f'{py} -c "print(\'baris satu\'); print(\'err=0\')"')
    log = proj / "handoff/logs/a.log"
    isi = log.read_bytes() if log.is_file() else b""
    cek(r.returncode == 0 and b"baris satu" in isi and b"err=0" in isi, "output perintah tersimpan di log", r.stderr.decode(errors="replace"))
    cek(b"baris satu" in r.stdout, "output juga ditampilkan di layar")
    rec = asal(proj)
    cek(len(rec) == 1 and rec[0]["file"] == "handoff/logs/a.log" and rec[0]["kode_keluar"] == 0 and rec[0]["jenis"] == "log",
        "provenance.jsonl memuat file, kode keluar, dan jenis")
    cek(bool(rec) and rec[0]["sha256"] == hash_lf(isi) and "print" in rec[0]["perintah"], "hash isi dan perintah tercatat")

    r = catat(proj, "handoff/logs/gagal.log", f'{py} -c "import sys; print(\'x\'); sys.exit(3)"')
    rec = asal(proj)
    cek(r.returncode == 3 and rec[-1]["kode_keluar"] == 3, "kode keluar perintah diteruskan (3)")

    r = catat(proj, "--append", "handoff/logs/a.log", f'{py} -c "print(\'baris tiga\')"')
    isi = log.read_bytes()
    rec = [x for x in asal(proj) if x["file"] == "handoff/logs/a.log"]
    cek(b"baris satu" in isi and b"baris tiga" in isi and rec[-1]["tambah"] is True and rec[-1]["sha256"] == hash_lf(isi),
        "--append: log ditambah, catatan terakhir mencakup seluruh isi")

    r = catat(proj, "--result", "handoff/logs/hasil.csv", "handoff/logs/b.log",
              f'{py} -c "open(\'handoff/logs/hasil.csv\',\'w\').write(\'a,b\\n1,2\\n\'); print(\'tulis csv\')"')
    rec = asal(proj)
    cek(r.returncode == 0 and any(x["file"] == "handoff/logs/hasil.csv" and x["jenis"] == "hasil" for x in rec),
        "--result: file yang ditulis perintah ikut tercatat", r.stderr.decode(errors="replace"))
    r = catat(proj, "--result", "handoff/logs/tidak-ada.csv", "handoff/logs/c.log", f'{py} -c "print(1)"')
    cek(b"tidak ada setelah perintah selesai" in r.stderr and not any(x["file"].endswith("tidak-ada.csv") for x in asal(proj)),
        "--result untuk file yang tidak dibuat: diberi tahu, tidak dicatat")

    # Konversi CRLF oleh git tidak dihitung sebagai perubahan
    lf = (proj / "handoff/logs/a.log").read_bytes().replace(b"\r\n", b"\n")
    (proj / "handoff/logs/a.log").write_bytes(lf.replace(b"\n", b"\r\n"))
    rec = [x for x in asal(proj) if x["file"] == "handoff/logs/a.log"]
    cek(hash_lf((proj / "handoff/logs/a.log").read_bytes()) == rec[-1]["sha256"], "hash sama setelah LF diubah menjadi CRLF")

    r = catat(proj, "handoff/logs/kosong.log", "   ")
    cek(r.returncode == 2, "perintah kosong: exit 2")

    # ---- v3.10: --result pola glob + hanya file yang ditulis selama perintah, penjaga log task DONE/BLOCKED ----
    if "def daftar_hasil" in CATAT.read_text(encoding="utf-8"):
        import os
        import time
        logs = proj / "handoff/logs"
        lama = logs / "TASK-001-uji_lama.log"
        lama.write_text("run kemarin\n", encoding="utf-8")
        os.utime(lama, (time.time() - 3600, time.time() - 3600))
        tulis = "; ".join(f"open(r'handoff/logs/TASK-001-uji_{n}.log','w').write('{n}\\n')" for n in ("a", "b"))
        (logs / "sub").mkdir()
        tulis += "; open(r'handoff/logs/sub/TASK-001-uji_c.log','w').write('c\\n')"
        r = catat(proj, "--result", "handoff/logs/TASK-001-uji_*.log", "--result", "handoff/logs/**/TASK-001-uji_c.log",
                  "handoff/logs/TASK-001-regresi.log", f'{py} -c "{tulis}; print(\'pelari selesai\')"')
        dicatat = {x["file"] for x in asal(proj) if x["jenis"] == "hasil"}
        cek(r.returncode == 0 and {"handoff/logs/TASK-001-uji_a.log", "handoff/logs/TASK-001-uji_b.log", "handoff/logs/sub/TASK-001-uji_c.log"} <= dicatat,
            "--result pola glob (juga **): semua file yang ditulis pelari tercatat", r.stderr.decode(errors="replace"))
        cek("handoff/logs/TASK-001-uji_lama.log" not in dicatat and b"TASK-001-uji_lama.log tidak ditulis selama perintah" in r.stderr,
            "--result pola glob: file lama yang cocok dilewati dan disebut", r.stderr.decode(errors="replace"))
        r = catat(proj, "--result", "handoff/logs/TASK-001-uji_lama.log", "handoff/logs/d.log", f'{py} -c "print(1)"')
        cek(not any(x["file"].endswith("uji_lama.log") for x in asal(proj)) and b"file lama" in r.stderr,
            "--result file tunggal yang tidak ditulis perintah: tidak dicatat (dulu ikut disahkan)")

        (proj / "handoff/tasks").mkdir()
        task = proj / "handoff/tasks/TASK-002-smoke.md"
        task.write_text("# TASK-002: SMOKE\n- Jenis: SMOKE · Status: IN_PROGRESS · Butuh executor: SEDANG\n", encoding="utf-8")
        r = catat(proj, "handoff/logs/TASK-002-smoke.log", f'{py} -c "print(\'run 1\')"')
        r = catat(proj, "handoff/logs/TASK-002-smoke.log", f'{py} -c "print(\'run 2\')"')
        smoke = logs / "TASK-002-smoke.log"
        cek(r.returncode == 0 and b"run 2" in smoke.read_bytes(), "task IN_PROGRESS: executor boleh menjalankan ulang (Periksa diri)")
        task.write_text(task.read_text(encoding="utf-8").replace("IN_PROGRESS", "DONE"), encoding="utf-8")
        n_asal = len(asal(proj))
        r = catat(proj, "handoff/logs/TASK-002-smoke.log", f'{py} -c "print(\'run sesi lain\')"')
        cek(r.returncode == 2 and b"DITOLAK" in r.stderr and b"run 2" in smoke.read_bytes() and len(asal(proj)) == n_asal,
            "task DONE: log yang ada tidak ditimpa, asal tidak berubah", r.stderr.decode(errors="replace"))
        r = catat(proj, "--append", "handoff/logs/TASK-002-smoke.log", f'{py} -c "print(\'tambahan\')"')
        cek(r.returncode == 2 and b"tambahan" not in smoke.read_bytes(), "task DONE: --append ke log yang ada juga ditolak")
        r = catat(proj, "handoff/logs/TASK-002-head-audit.log", f'{py} -c "print(\'audit head\')"')
        cek(r.returncode == 0 and (logs / "TASK-002-head-audit.log").is_file(), "task DONE: log baru bernama lain tetap boleh (pemeriksaan head)")
        r = catat(proj, "--overwrite", "handoff/logs/TASK-002-smoke.log", f'{py} -c "print(\'run 3\')"')
        cek(r.returncode == 0 and b"run 3" in smoke.read_bytes(), "task DONE + --overwrite: penimpaan yang disengaja diizinkan")
        task.write_text(task.read_text(encoding="utf-8").replace("DONE", "BLOCKED"), encoding="utf-8")
        r = catat(proj, "handoff/logs/TASK-002-smoke.log", f'{py} -c "print(1)"')
        cek(r.returncode == 2, "task BLOCKED: log yang ada juga dijaga")
        r = catat(proj, "handoff/logs/TASK-0020-lain.log", f'{py} -c "print(1)"')
        cek(r.returncode == 0, "nomor task dicocokkan utuh (TASK-0020 bukan TASK-002)")
    else:
        print("LEWAT uji v3.10: record.py versi lama")

    # v3.12: nama lama tetap diterima (opsi --tambah/--hasil/--timpa, catatan asal handoff/logs/asal.jsonl)
    if "ASAL_LAMA" in CATAT.read_text(encoding="utf-8"):
        lama = tmp / "lama"
        (lama / "handoff/logs").mkdir(parents=True)
        (lama / "handoff/logs/asal.jsonl").write_text("", encoding="utf-8")
        r1 = catat(lama, "handoff/logs/b.log", f'{py} -c "print(1)"')
        r2 = catat(lama, "--tambah", "--hasil", "handoff/logs/h.txt", "handoff/logs/b.log",
                   f'{py} -c "open(\'handoff/logs/h.txt\', \'w\').write(\'x\'); print(2)"')
        r3 = catat(lama, "--timpa", "handoff/logs/c.log", f'{py} -c "print(3)"')
        isi_lama = (lama / "handoff/logs/asal.jsonl").read_text(encoding="utf-8")
        cek(all(r.returncode == 0 for r in (r1, r2, r3)) and not (lama / "handoff/logs/provenance.jsonl").exists()
            and isi_lama.count('"file"') == 4 and "h.txt" in isi_lama,
            "project bernama lama: --tambah, --hasil, --timpa diterima; catatan tetap ditulis ke asal.jsonl",
            r2.stderr.decode(errors="replace") + isi_lama)
        bantuan = catat(lama, "--help").stdout.decode(errors="replace")
        cek("--append" in bantuan and "command" in bantuan and not any(o in bantuan for o in ("--tambah", "--hasil", "--timpa")),
            "--help hanya menampilkan nama opsi baru", bantuan)
    else:
        print("LEWAT uji v3.12: record.py versi lama")

    if shutil.which("pwsh") or shutil.which("powershell"):
        r = catat(proj, "--pwsh", "handoff/logs/ps.log", "Write-Output 'halo dari PowerShell'")
        isi = (proj / "handoff/logs/ps.log").read_bytes() if (proj / "handoff/logs/ps.log").is_file() else b""
        cek(r.returncode == 0 and b"halo dari PowerShell" in isi, "--pwsh: perintah PowerShell dijalankan", r.stderr.decode(errors="replace"))
    else:
        print("LEWAT --pwsh: PowerShell tidak ada di mesin ini")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("\nHASIL:", "SEMUA OK" if ok else "ADA YANG GAGAL")
sys.exit(0 if ok else 1)
