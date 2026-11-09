#!/usr/bin/env python3
"""Mulai sesi head baru di terminal Orca ini sesudah giliran head selesai (agent-workflow, sejak v3.18).

Dijalankan head dari root project, sebagai perintah terakhir gilirannya, bila user sudah menyetujuinya di README:
  python handoff/tools/head_restart.py --skill <prefix>-head
  python handoff/tools/head_restart.py --skill <prefix>-head --grace 60

Model tidak bisa menjalankan `/clear`, dan `/clear` menghentikan tugas latar belakang sesi. Karena itu skrip ini
melepas salinan dirinya sebagai proses terpisah, lalu langsung selesai. Proses itu:
1. menunggu terminal menganggur (`orca terminal wait --for tui-idle`), yaitu saat giliran head selesai;
2. menunggu jeda (bawaan 30 detik), supaya user sempat membaca pesan terakhir head;
3. batal bila selama jeda ada pesan baru di transkrip sesi, terminal tidak lagi menganggur, atau baris input terminal
   tidak kosong. Bila ragu ia batal, karena akibatnya hanya user mengetik `/clear` sendiri;
4. mengetik `/clear`, menunggu sesi baru siap, lalu mengetik `/<skill>`.

Nama skill ditulis tanpa garis miring depan, karena Git Bash mengubah argumen berawalan `/` menjadi path Windows.
Hanya berjalan di terminal Orca: terminalnya diambil dari variabel ORCA_TERMINAL_HANDLE, jadi skrip ini hanya mengetik
ke terminal yang menjalankannya. Catatan proses terpisah ditulis ke file di folder sementara, yang disebut di output.

Output diawali SCHEDULED atau ERROR. Kode keluar 0 untuk SCHEDULED, 2 untuk ERROR atau argumen salah. Perintah Orca diambil
dari --orca, variabel ORCA_CLI_COMMAND, atau `orca`; file .py dijalankan dengan Python ini (untuk uji). Baris log proses
terpisah diawali CANCELLED, FAILED, atau DONE. Kata sebelum v3.20.1: JADWAL, GALAT, BATAL, GAGAL, SELESAI.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

SKILL = re.compile(r"[\w][\w:.-]*\Z")
BARIS_INPUT = re.compile(r"^\s*[❯>]\s*(.*?)\s*$")  # baris input Claude Code; bentuk lain dianggap ragu, jadi batal
MULAI_DETIK = 3  # supaya perintah ini selesai dulu dan terminal masih tercatat sibuk saat penantian dimulai
SIAP_DETIK = 2  # jeda sesudah /clear sebelum sesi baru diperiksa


def perintah_orca(nama):
    nama = nama or os.environ.get("ORCA_CLI_COMMAND") or "orca"
    jalur = shutil.which(nama) or nama
    return [sys.executable, jalur] if jalur.lower().endswith(".py") else [jalur]


def panggil(orca, *args, detik=60):
    """Satu perintah Orca berkeluaran JSON. Hasil: (result, None) atau (None, pesan galat)."""
    try:
        r = subprocess.run(orca + list(args) + ["--json"], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=detik)
    except FileNotFoundError:
        return None, f"perintah Orca tidak ditemukan: {orca[-1]}"
    except subprocess.TimeoutExpired:
        return None, f"perintah Orca tidak selesai dalam {detik} detik: {' '.join(args[:2])}"
    teks = "\n".join(b for b in (r.stdout or "").split("\n") if '"_keepalive"' not in b)
    try:
        doc = json.loads(teks)
    except ValueError:
        return None, f"output Orca bukan JSON (exit {r.returncode}): {' '.join((teks or r.stderr or '').split())[:300]}"
    if not isinstance(doc, dict) or doc.get("ok") is not True:
        e = doc.get("error") if isinstance(doc, dict) else None
        return None, f"{e.get('code', 'galat')}: {e.get('message', '')}".strip() if isinstance(e, dict) else f"Orca menolak: {teks[:300]}"
    hasil = doc.get("result")
    return (hasil, None) if isinstance(hasil, dict) else (None, f"output Orca tanpa result: {teks[:300]}")


def tunggu_idle(orca, h, detik):
    """None bila terminal menganggur; selain itu pesan alasannya."""
    hasil, galat = panggil(orca, "terminal", "wait", "--terminal", h, "--for", "tui-idle", "--timeout-ms", str(int(detik * 1000)),
                           detik=detik + 30)
    if galat:
        return galat
    return None if (hasil.get("wait") or {}).get("satisfied") is True else f"terminal tidak menganggur dalam {detik} detik"


def input_kosong(orca, h):
    """(True, None) bila baris input Claude Code ditemukan dan kosong; selain itu (False, alasan)."""
    hasil, galat = panggil(orca, "terminal", "read", "--terminal", h)
    if galat:
        return False, galat
    t = hasil.get("terminal") or {}
    if (t.get("draft") or "").strip():  # Orca memisahkan ketikan user ke `draft`, jadi baris input di `tail` tetap kosong
        return False, "ada ketikan user di baris input"
    ekor = t.get("tail") or t.get("text") or ""
    baris = ekor.split("\n") if isinstance(ekor, str) else [str(b) for b in ekor]
    for b in reversed(baris[-8:]):
        m = BARIS_INPUT.match(b)
        if m:
            return (True, None) if not m.group(1) else (False, "baris input tidak kosong")
    return False, "baris input tidak ditemukan"


def transkrip():
    sesi = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not sesi:
        return None
    dir_env = os.environ.get("CLAUDE_CONFIG_DIR")
    projects = (Path(dir_env) if dir_env else Path.home() / ".claude") / "projects"
    return next((p for p in projects.glob(f"*/{sesi}.jsonl") if p.is_file()), None) if projects.is_dir() else None


def jumlah_pesan(p):
    """Jumlah pesan masuk di transkrip (prompt user dan hasil alat); bertambah berarti sesi dipakai lagi."""
    return p.read_bytes().count(b'"type":"user"') if p else 0


def ketik(orca, h, teks):
    """None bila teks diterima terminal; selain itu pesan alasannya."""
    hasil, galat = panggil(orca, "terminal", "send", "--terminal", h, "--text", teks, "--enter", "--wait-submit", "5", detik=30)
    if galat:
        return galat
    return None if (hasil.get("send") or {}).get("accepted") is True else f"terminal tidak menerima {teks}"


def kerja(a, catat):
    """Bagian proses terpisah. Kode keluar hanya untuk uji; catatannya ada di file log."""
    orca, h, tr = perintah_orca(a.orca), a.terminal, transkrip()
    time.sleep(0 if a.no_start_delay else MULAI_DETIK)
    alasan = tunggu_idle(orca, h, a.wait_minutes * 60)
    if alasan:
        catat(f"CANCELLED: {alasan}")
        return 1
    awal = jumlah_pesan(tr)
    catat(f"terminal menganggur; jeda {a.grace} detik")
    time.sleep(a.grace)
    if jumlah_pesan(tr) != awal:
        catat("CANCELLED: ada pesan baru di transkrip selama jeda")
        return 1
    alasan = tunggu_idle(orca, h, 5)
    kosong, alasan_input = input_kosong(orca, h) if not alasan else (False, alasan)
    if not kosong:
        catat(f"CANCELLED: {alasan_input}")
        return 1
    alasan = ketik(orca, h, "/clear")
    if alasan:
        catat(f"CANCELLED: /clear gagal: {alasan}")
        return 1
    catat("/clear terkirim")
    time.sleep(0 if a.no_start_delay else SIAP_DETIK)
    alasan = tunggu_idle(orca, h, 60) or ketik(orca, h, f"/{a.skill}")
    if alasan:
        catat(f"FAILED: sesudah /clear, sesi baru belum memuat skill: {alasan}")
        return 1
    catat(f"DONE: /{a.skill} terkirim")
    return 0


def lepas(a, log):
    """Jalankan bagian kerja sebagai proses yang tidak ikut berhenti bersama sesi."""
    cmd = [sys.executable, os.path.abspath(__file__), "--worker", "--skill", a.skill, "--grace", str(a.grace),
           "--wait-minutes", str(a.wait_minutes), "--terminal", a.terminal, "--log", str(log)]
    if a.orca:
        cmd += ["--orca", a.orca]
    if os.name == "nt":
        cara = {"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP}
    else:
        cara = {"start_new_session": True}
    subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True, **cara)


def main():
    p = argparse.ArgumentParser(description="Mulai sesi head baru di terminal Orca ini sesudah giliran head selesai.")
    p.add_argument("--skill", required=True, help="nama skill head tanpa garis miring depan, mis. proyek-head")
    p.add_argument("--grace", type=int, default=30, help="jeda sesudah giliran selesai, dalam detik (bawaan 30)")
    p.add_argument("--wait-minutes", type=float, default=15, help="batas menunggu giliran selesai, dalam menit (bawaan 15)")
    p.add_argument("--orca", metavar="CLI", help="perintah Orca (bawaan: ORCA_CLI_COMMAND, atau orca)")
    p.add_argument("--terminal", default=os.environ.get("ORCA_TERMINAL_HANDLE"), help=argparse.SUPPRESS)
    p.add_argument("--log", help=argparse.SUPPRESS)
    p.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--no-start-delay", action="store_true", help=argparse.SUPPRESS)  # untuk uji: tanpa jeda tetap
    a = p.parse_args()
    a.skill = a.skill.lstrip("/")
    if not SKILL.match(a.skill):
        print(f"ERROR: nama skill '{a.skill}' tidak valid. Tulis tanpa garis miring depan, mis. --skill proyek-head "
              "(Git Bash mengubah argumen berawalan / menjadi path).")
        return 2
    if a.grace < 0 or a.wait_minutes <= 0:
        p.error("--grace tidak boleh negatif dan --wait-minutes harus lebih dari 0")
    if not a.terminal:
        print("ERROR: variabel ORCA_TERMINAL_HANDLE tidak ada, jadi ini bukan terminal Orca. Sarankan user menjalankan "
              f"/clear lalu /{a.skill}.")
        return 2
    log = Path(a.log) if a.log else Path(tempfile.gettempdir()) / f"agent-workflow-head-restart-{a.terminal}.log"

    def catat(pesan):
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {pesan}\n")

    if a.worker:
        return kerja(a, catat)
    lepas(a, log)
    print(f"SCHEDULED: sesudah giliran ini selesai dan jeda {a.grace} detik, /clear lalu /{a.skill} diketik ke terminal ini. "
          f"Batal bila user mengirim prompt atau mengetik selama jeda. Catatan: {log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
