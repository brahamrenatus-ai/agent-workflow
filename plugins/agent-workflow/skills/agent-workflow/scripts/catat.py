#!/usr/bin/env python3
"""Pembungkus perintah untuk log bukti agent-workflow: jalankan perintah, simpan output-nya ke file log apa adanya,
lalu catat asal log itu (perintah, kode keluar, waktu, hash isi) di handoff/logs/asal.jsonl.

Dijalankan dari root project (skrip ini disalin ke handoff/tools/ oleh BOOTSTRAP/AUDIT):
  python handoff/tools/catat.py handoff/logs/TASK-NNN-<nama>.log "<perintah>"
  python handoff/tools/catat.py --pwsh handoff/logs/TASK-NNN-<nama>.log "<perintah PowerShell>"
  python handoff/tools/catat.py --tambah handoff/logs/TASK-NNN-<nama>.log "<perintah berikutnya>"
  python handoff/tools/catat.py --hasil handoff/logs/hasil.csv handoff/logs/TASK-NNN-<nama>.log "<perintah yang menulis hasil.csv>"
  python handoff/tools/catat.py --hasil "handoff/logs/TASK-NNN-uji_*.log" handoff/logs/TASK-NNN-regresi.log "<pelari uji>"

- Output (stdout + stderr) disimpan byte demi byte, tanpa diubah encoding-nya, dan ditampilkan juga di layar.
- `--tambah` menambahkan ke log yang sudah ada; catatan terakhir untuk sebuah file mencakup seluruh isinya.
- `--hasil FILE` (boleh berulang) mencatat file yang ditulis perintah itu sendiri, mis. CSV atau log per-test
  yang ditulis skrip pelari. FILE boleh pola glob (`*`, `?`, `[...]`, `**`); kutip polanya supaya shell tidak
  mengembangkannya sebelum perintah berjalan. Hanya file yang ditulis selama perintah berjalan yang dicatat; file
  lama yang cocok dilewati dan disebut di layar, supaya output run sebelumnya tidak ikut disahkan.
- Perintah dijalankan lewat shell bawaan (cmd di Windows, sh di Linux/macOS); `--pwsh` memakai PowerShell.
- Penjaga task selesai: log `TASK-NNN-*` yang sudah ada tidak ditimpa atau ditambah bila task TASK-NNN berstatus
  DONE atau BLOCKED, karena log itu bukti report yang sudah ditulis (mis. sesi lain menjalankan ulang task yang
  sudah selesai). Bila memang disengaja, tambahkan `--timpa`. Log baru dengan nama lain tetap boleh dibuat.

cek_bukti.py memakai catatan ini. Log yang dikutip report tetapi tidak tercatat diberi peringatan, dan log yang
isinya berubah setelah dicatat adalah masalah. Karena itu log bukti jangan diedit tangan; jalankan ulang
perintahnya. Hash dihitung setelah CRLF disamakan menjadi LF, supaya konversi akhir baris oleh git tidak dihitung
sebagai perubahan. Kode keluar skrip ini sama dengan kode keluar perintahnya (2 bila argumen salah atau penjaga
task selesai menolak).
"""
import argparse
import glob
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ASAL = Path("handoff") / "logs" / "asal.jsonl"
TASKS = Path("handoff") / "tasks"
# Selisih jam file sistem (mis. FAT 2 detik), supaya file yang ditulis tepat saat perintah mulai tetap dihitung baru.
TOLERANSI_MTIME = 2.0


def hash_isi(path):
    """SHA-256 isi file dengan CRLF disamakan menjadi LF (sama persis dengan cek_bukti.py)."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def waktu():
    return datetime.now().isoformat(timespec="seconds")


def catat(path, perintah, mulai, selesai, kode, jenis, tambah):
    rec = {"file": path.as_posix(), "jenis": jenis, "perintah": perintah, "kode_keluar": kode, "mulai": mulai,
           "selesai": selesai, "tambah": tambah, "sha256": hash_isi(path)}
    ASAL.parent.mkdir(parents=True, exist_ok=True)
    with open(ASAL, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def relatif(p):
    """Path relatif terhadap folder kerja (root project), dengan garis miring maju."""
    p = Path(p)
    try:
        return p.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        return p


def status_task(log):
    """(nomor, status) task pemilik log `TASK-NNN-*`, mis. ("049", "DONE"); None bila bukan log task atau task tidak ada."""
    m = re.match(r"TASK-(\d+[A-Za-z]?)(?=[-_.]|$)", log.name, re.I)
    if not m or not TASKS.is_dir():
        return None
    nomor = m.group(1)
    calon = sorted(TASKS.glob(f"TASK-{nomor}-*.md")) + sorted(TASKS.glob(f"TASK-{nomor}.md"))
    if not calon:
        return None
    teks = calon[0].read_text(encoding="utf-8", errors="replace")
    ms = re.search(r"Status\s*:\s*\**\s*(OPEN|IN_PROGRESS|DONE|BLOCKED)\b", teks, re.I)
    return (nomor, ms.group(1).upper()) if ms else None


def daftar_hasil(pola, sejak):
    """([file yang ditulis selama perintah], [file lama yang dilewati]) untuk satu --hasil (path atau pola glob)."""
    if any(ch in pola for ch in "*?["):
        cocok = [Path(p) for p in sorted(glob.glob(pola, recursive=True)) if Path(p).is_file()]
    else:
        cocok = [Path(pola)] if Path(pola).is_file() else []
    baru = [p for p in cocok if p.stat().st_mtime >= sejak - TOLERANSI_MTIME]
    return baru, [p for p in cocok if p not in baru]


def main():
    ap = argparse.ArgumentParser(description="Jalankan perintah, simpan output-nya ke log bukti, dan catat asalnya.")
    ap.add_argument("log", help="file log tujuan, mis. handoff/logs/TASK-012-test.log")
    ap.add_argument("perintah", help="perintah yang dijalankan, dalam satu string")
    ap.add_argument("--tambah", action="store_true", help="tambahkan ke log yang sudah ada")
    ap.add_argument("--pwsh", action="store_true", help="jalankan lewat PowerShell")
    ap.add_argument("--hasil", action="append", default=[],
                    help="file atau pola glob (dikutip) yang ditulis perintah itu sendiri; boleh berulang")
    ap.add_argument("--timpa", action="store_true", help="izinkan menimpa log task yang sudah DONE/BLOCKED")
    a = ap.parse_args()
    if not a.perintah.strip():
        print("[catat] perintah kosong", file=sys.stderr)
        return 2
    log = relatif(a.log)
    st = status_task(log)
    if st and st[1] in ("DONE", "BLOCKED") and log.is_file() and not a.timpa:
        print(f"[catat] DITOLAK: {log.as_posix()} adalah bukti TASK-{st[0]}, yang sudah {st[1]}. Menjalankan ulang "
              "perintahnya akan menimpa bukti report task itu. Pemeriksaan baru memakai nama log lain; bila task ini "
              "memang dibuka ulang dan penimpaan disengaja, tambahkan --timpa.", file=sys.stderr)
        return 2
    log.parent.mkdir(parents=True, exist_ok=True)
    if a.pwsh:
        exe = shutil.which("pwsh") or shutil.which("powershell")
        if not exe:
            print("[catat] PowerShell tidak ditemukan di PATH", file=sys.stderr)
            return 2
        args, shell = [exe, "-NoProfile", "-Command", a.perintah], False
    else:
        args, shell = a.perintah, True
    mulai, sejak = waktu(), time.time()
    with open(log, "ab" if a.tambah else "wb") as f:
        p = subprocess.Popen(args, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        while True:
            potong = p.stdout.read1(65536) if hasattr(p.stdout, "read1") else p.stdout.read(65536)
            if not potong:
                break
            f.write(potong)
            try:
                sys.stdout.buffer.write(potong)
                sys.stdout.buffer.flush()
            except (AttributeError, OSError):
                pass
        kode = p.wait()
    selesai = waktu()
    catat(log, a.perintah, mulai, selesai, kode, "log", a.tambah)
    sudah = {log.resolve()}
    for h in a.hasil:
        baru, lama = daftar_hasil(h, sejak)
        for ph in map(relatif, baru):
            if ph.resolve() not in sudah:
                sudah.add(ph.resolve())
                catat(ph, a.perintah, mulai, selesai, kode, "hasil", False)
        for ph in map(relatif, lama):
            print(f"[catat] --hasil {ph.as_posix()} tidak ditulis selama perintah berjalan (file lama); tidak dicatat",
                  file=sys.stderr)
        if not baru and not lama:
            jenis = "tidak cocok dengan file apa pun" if any(ch in h for ch in "*?[") else "tidak ada"
            print(f"[catat] --hasil {h} {jenis} setelah perintah selesai; tidak dicatat", file=sys.stderr)
    print(f"[catat] {log.as_posix()}: kode keluar {kode}; asal dicatat di {ASAL.as_posix()}", file=sys.stderr)
    return kode


if __name__ == "__main__":
    sys.exit(main())
