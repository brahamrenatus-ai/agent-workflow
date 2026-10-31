#!/usr/bin/env python3
"""Tunggu kabar worker Orca tanpa membangunkan sesi head untuk heartbeat (agent-workflow, sejak v3.16).

Dijalankan head di latar belakang dari root project (skrip ini disalin ke handoff/tools/ bila head memakai Orca):
  python handoff/tools/orca_wait.py
  python handoff/tools/orca_wait.py --ack <delivery_id>
  python handoff/tools/orca_wait.py --minutes 60 --run <run_id>

Skrip mengulang `orca orchestration check --wait --timeout-ms <ms> --json` sampai ada pesan yang perlu diproses,
galat, atau batas waktu (bawaan 36 menit) habis:
- Batch yang isinya hanya heartbeat di-ack pada panggilan berikutnya (`--ack`), lalu skrip menunggu lagi.
- Batch yang memuat pesan lain (worker_done, question, escalation, status, ...) dicetak, lalu skrip selesai. Batch itu
  belum di-ack: ack sesudah diproses, dengan `orca orchestration check --ack <delivery_id> --json` atau dengan
  menjalankan skrip ini lagi memakai `--ack <delivery_id>`.
- Bingkai keepalive yang ditulis Orca tiap 15 detik selama menunggu (`{"_keepalive":true,...}`) dibuang.

Skrip menunggu tanpa `--types`. Orca 1.4.244 mengetik pemberitahuan "You have N orchestration message" ke terminal
koordinator untuk pesan yang jenisnya tidak ada di filter waiter yang sedang aktif, dan tidak mengetik apa pun selama
ada waiter tanpa filter. Dengan loop `--types "worker_done,escalation,question"`, setiap heartbeat worker (bawaan
setiap 5 menit) membangunkan sesi head, yang lalu membaca ulang seluruh konteksnya.

Output diawali PESAN, TIMEOUT (tidak ada pesan selain heartbeat sampai batas waktu; heartbeat terakhir tiap dispatch
ikut dicetak), atau GALAT. Kode keluar 0 untuk PESAN dan TIMEOUT, 2 untuk GALAT atau argumen salah. Perintah Orca
diambil dari --orca, variabel ORCA_CLI_COMMAND, atau `orca`; file .py dijalankan dengan Python ini (untuk uji).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime

PUTARAN_MS = 540000  # satu panggilan check paling lama 9 menit
DISERAP = {"heartbeat"}  # jenis pesan yang di-ack di sini tanpa membangunkan head

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass


def perintah_orca(nama):
    nama = nama or os.environ.get("ORCA_CLI_COMMAND") or "orca"
    jalur = shutil.which(nama) or nama
    return [sys.executable, jalur] if jalur.lower().endswith(".py") else [jalur]


def tanpa_keepalive(teks):
    """Buang baris bingkai keepalive Orca; baris lain dipertahankan."""
    sisa = []
    for b in teks.split("\n"):
        s = b.strip()
        if s.startswith("{") and '"_keepalive"' in s:
            try:
                if json.loads(s).get("_keepalive") is True:
                    continue
            except (ValueError, AttributeError):
                pass
        sisa.append(b.rstrip("\r"))
    return "\n".join(sisa).strip()


def ringkas(teks, n=600):
    teks = " ".join(teks.split())
    return teks if len(teks) <= n else teks[:n] + " ..."


def periksa(orca, run, ack, ms):
    """Satu panggilan check. Hasil: (result Orca, None) atau (None, pesan galat)."""
    cmd = orca + ["orchestration", "check"] + (["--ack", ack] if ack else []) + ["--wait", "--timeout-ms", str(ms), "--json"]
    if run:
        cmd += ["--run", run]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=ms / 1000 + 120)
    except FileNotFoundError:
        return None, f"perintah Orca tidak ditemukan: {orca[-1]}"
    except subprocess.TimeoutExpired:
        return None, f"orca orchestration check tidak selesai dalam {ms // 1000 + 120} detik"
    keluar, galat = tanpa_keepalive(r.stdout or ""), tanpa_keepalive(r.stderr or "")
    try:
        doc = json.loads(keluar)
    except ValueError:
        return None, f"output orca bukan JSON (exit {r.returncode}): {ringkas(keluar or galat) or '(kosong)'}"
    if not isinstance(doc, dict) or doc.get("ok") is not True:
        e = doc.get("error") if isinstance(doc, dict) else None
        if isinstance(e, dict):
            return None, f"{e.get('code', 'galat')}: {e.get('message', '')}".strip()
        return None, f"orca menolak (exit {r.returncode}): {ringkas(keluar)}"
    hasil = doc.get("result")
    if not isinstance(hasil, dict):
        return None, f"output orca tanpa result: {ringkas(keluar)}"
    if hasil.get("cancelled") or hasil.get("connectionLost"):
        return None, "penantian dibatalkan atau koneksi ke Orca putus"
    return hasil, None


def isi_payload(m):
    try:
        p = json.loads(m.get("payload") or "{}")
    except ValueError:
        return {}
    return p if isinstance(p, dict) else {}


def cetak_pesan(hasil, n_hb):
    pesan = hasil.get("messages") or []
    lain = [m for m in pesan if m.get("type") not in DISERAP]
    ikut = len(pesan) - len(lain)
    d = hasil.get("deliveryId")
    keterangan = [f"{len(lain)} pesan"]
    if ikut:
        keterangan.append(f"+{ikut} heartbeat dalam batch ini")
    if n_hb:
        keterangan.append(f"heartbeat yang sudah di-ack: {n_hb}")
    print(f"PESAN {d or '(tanpa deliveryId)'}: " + "; ".join(keterangan))
    for m in lain:
        print(f"- [{m.get('type')}] {m.get('id')} dari {m.get('from_handle')}: {m.get('subject')}")
        body = (m.get("body") or "").strip()
        if body:
            print("  " + body.replace("\n", "\n  "))
        if m.get("payload"):
            print(f"  payload: {m['payload']}")
    if d:
        print(f"Ack sesudah diproses: orca orchestration check --ack {d} --json")


def cetak_timeout(menit, hb, n_hb):
    print(f"TIMEOUT: tidak ada pesan selain heartbeat dalam {menit:g} menit. Heartbeat di-ack: {n_hb}.")
    sekarang = datetime.now()
    for dispatch, (waktu, fase, task) in sorted(hb.items()):
        lalu = int((sekarang - waktu).total_seconds() // 60)
        print(f"- dispatch {dispatch} (task {task}): heartbeat terakhir {waktu:%H:%M:%S} ({lalu} menit lalu), phase {fase}")
    if not hb:
        print("- tidak ada heartbeat selama menunggu")


def main():
    p = argparse.ArgumentParser(description="Tunggu kabar worker Orca; heartbeat di-ack tanpa membangunkan sesi head.")
    p.add_argument("--minutes", type=float, default=36, help="batas waktu menunggu, dalam menit (bawaan 36)")
    p.add_argument("--ack", metavar="DELIVERY_ID", help="ack batch yang sudah diproses sebelum mulai menunggu")
    p.add_argument("--run", metavar="RUN_ID", help="Run yang ditunggu (bawaan: Run yang terikat ke terminal ini)")
    p.add_argument("--orca", metavar="CLI", help="perintah Orca (bawaan: ORCA_CLI_COMMAND, atau orca)")
    args = p.parse_args()
    if args.minutes <= 0:
        p.error("--minutes harus lebih dari 0")
    orca = perintah_orca(args.orca)
    akhir = time.monotonic() + args.minutes * 60
    ack, hb, n_hb = args.ack, {}, 0
    while True:
        ms = max(1000, min(PUTARAN_MS, int((akhir - time.monotonic()) * 1000)))
        mulai = time.monotonic()
        hasil, galat = periksa(orca, args.run, ack, ms)
        if galat:
            print(f"GALAT: {galat}")
            return 2
        ack = None
        pesan = hasil.get("messages") or []
        if pesan and all(m.get("type") in DISERAP for m in pesan):
            ack = hasil.get("deliveryId")
            if not ack:
                print("GALAT: batch heartbeat tanpa deliveryId, jadi tidak bisa di-ack. Pastikan terminal ini koordinator "
                      "sebuah Run (orca orchestration run-current --json), atau beri --run.")
                return 2
            for m in pesan:
                pl = isi_payload(m)
                hb[pl.get("dispatchId") or m.get("from_handle") or "?"] = (datetime.now(), pl.get("phase") or "-", pl.get("taskId") or "-")
            n_hb += len(pesan)
            continue
        if pesan:
            cetak_pesan(hasil, n_hb)
            return 0
        if time.monotonic() >= akhir:
            cetak_timeout(args.minutes, hb, n_hb)
            return 0
        if time.monotonic() - mulai < 1:  # Orca kembali seketika tanpa pesan: jangan berputar cepat
            time.sleep(1)


if __name__ == "__main__":
    sys.exit(main())
