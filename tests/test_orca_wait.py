"""Uji fungsional scripts/orca_wait.py (v3.16) dengan `orca` palsu: batch heartbeat di-ack lalu menunggu lagi, pesan lain
dicetak tanpa di-ack, TIMEOUT dengan heartbeat terakhir per dispatch, keepalive dibuang, galat Orca, dan argumen.
Pemakaian: python -X utf8 tests/test_orca_wait.py <folder skill>"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".claude/skills/agent-workflow").resolve()
SKRIP = SKILL / "scripts" / "orca_wait.py"
ok = True


def cek(cond, msg, out=""):
    global ok
    print(("OK    " if cond else "GAGAL ") + msg)
    if not cond and out:
        print("      " + out.replace("\n", "\n      "))
    ok = ok and cond


# orca palsu: setiap panggilan mengambil langkah berikutnya dari skenario (langkah terakhir diulang),
# mencatat argumennya, menulis keepalive, lalu mencetak hasil seperti `--json` Orca.
PALSU = r'''
import json, os, sys, time
d = os.environ["ORCA_PALSU"]
langkah = json.load(open(os.path.join(d, "skenario.json"), encoding="utf-8"))
p = os.path.join(d, "nomor.txt")
i = int(open(p).read()) if os.path.exists(p) else 0
open(p, "w").write(str(i + 1))
with open(os.path.join(d, "panggilan.jsonl"), "a", encoding="utf-8") as f:
    f.write(json.dumps(sys.argv[1:]) + "\n")
s = langkah[min(i, len(langkah) - 1)]
time.sleep(s.get("tidur", 0))
ka = b'{"_keepalive":true,"_heartbeat":true,"elapsedMs":15000,"deadlineMs":540000}\n'
sys.stderr.buffer.write(ka * s.get("keepalive_err", 0))
keluar = s["keluar"]
teks = json.dumps(keluar, indent=2, ensure_ascii=False) if isinstance(keluar, dict) else keluar
sys.stdout.buffer.write(ka * s.get("keepalive_out", 0) + teks.encode("utf-8") + b"\n")
sys.exit(s.get("kode", 0))
'''


def hasil(pesan, delivery):
    return {"id": "x", "ok": True, "result": {"runId": "run_uji", "deliveryId": delivery, "messages": pesan, "count": len(pesan),
                                              "replayed": False, "acknowledged": None, "timedOut": not pesan,
                                              "cancelled": False, "connectionLost": False}, "_meta": {"runtimeId": "r"}}


def pesan(jenis, nomor, subjek, body="", payload=None):
    return {"id": f"msg_{nomor}", "run_id": "run_uji", "from_handle": "term_worker", "subject": subjek, "body": body,
            "type": jenis, "payload": json.dumps(payload) if payload else None, "created_at": "2026-10-31T00:00:00Z"}


def hb(nomor, dispatch, fase):
    return pesan("heartbeat", nomor, "alive", payload={"taskId": "task_uji", "dispatchId": dispatch, "phase": fase})


def jalankan(d, langkah, *args):
    for f in ("nomor.txt", "panggilan.jsonl"):
        (d / f).unlink(missing_ok=True)
    (d / "skenario.json").write_text(json.dumps(langkah, ensure_ascii=False), encoding="utf-8")
    env = dict(os.environ, ORCA_PALSU=str(d))
    r = subprocess.run([sys.executable, str(SKRIP), "--orca", str(d / "orca_palsu.py"), *args], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=env, timeout=120)
    p = d / "panggilan.jsonl"
    panggil = [json.loads(b) for b in p.read_text(encoding="utf-8").splitlines()] if p.is_file() else []
    return r, r.stdout + r.stderr, panggil


if not SKRIP.is_file():
    cek(False, f"scripts/orca_wait.py ada ({SKRIP})")
    print("\nHASIL: ADA YANG GAGAL")
    sys.exit(1)

tmp = Path(tempfile.mkdtemp(prefix="orca_wait_"))
try:
    (tmp / "orca_palsu.py").write_text(PALSU, encoding="utf-8")

    # 1. Batch heartbeat di-ack di panggilan berikutnya, lalu worker_done mengakhiri penantian.
    wd = pesan("worker_done", 2, "TASK-007 DONE", "Selesai — “kutip” ✓\nbaris dua",
               {"taskId": "task_uji", "dispatchId": "ctx_a", "outcome": "succeeded"})
    r, out, pg = jalankan(tmp, [{"keluar": hasil([hb(1, "ctx_a", "implementing")], "delivery_hb1"), "keepalive_err": 2, "keepalive_out": 1},
                                {"keluar": hasil([wd], "delivery_wd"), "keepalive_err": 1}])
    cek(r.returncode == 0 and r.stdout.startswith("PESAN delivery_wd: 1 pesan; heartbeat yang sudah di-ack: 1"),
        "heartbeat di-ack, worker_done dicetak dengan PESAN, exit 0", out)
    cek("- [worker_done] msg_2 dari term_worker: TASK-007 DONE" in out and "  Selesai — “kutip” ✓\n  baris dua" in out
        and '"outcome": "succeeded"' in out, "isi worker_done (subjek, body bertakuk, payload) tercetak utuh, termasuk karakter non-ASCII", out)
    cek("Ack sesudah diproses: orca orchestration check --ack delivery_wd --json" in out, "batch yang dicetak belum di-ack; perintah ack-nya dicetak", out)
    cek("_keepalive" not in out, "bingkai keepalive dari stdout dan stderr Orca dibuang", out)
    cek(len(pg) == 2 and pg[0][:2] == ["orchestration", "check"] and "--wait" in pg[0] and "--json" in pg[0]
        and "--types" not in pg[0] and "--ack" not in pg[0], "panggilan pertama: check --wait --json tanpa --types dan tanpa --ack", str(pg))
    cek(len(pg) == 2 and pg[1][pg[1].index("--ack") + 1] == "delivery_hb1" if len(pg) == 2 and "--ack" in pg[1] else False,
        "panggilan kedua meng-ack batch heartbeat sambil menunggu lagi", str(pg))
    cek(len(pg) >= 1 and pg[0][pg[0].index("--timeout-ms") + 1] == "540000", "satu panggilan menunggu paling lama 9 menit", str(pg))

    # 2. TIMEOUT: heartbeat terakhir per dispatch dicetak; batch heartbeat yang tertunda di-ack sebelum keluar.
    r, out, pg = jalankan(tmp, [{"keluar": hasil([hb(3, "ctx_b", "reviewing"), hb(4, "ctx_c", "testing")], "delivery_hb2")},
                                {"keluar": hasil([], None), "tidur": 0.3}], "--minutes", "0.02")
    cek(r.returncode == 0 and r.stdout.startswith("TIMEOUT: tidak ada pesan selain heartbeat dalam 0.02 menit. Heartbeat di-ack: 2."),
        "TIMEOUT sesudah batas waktu, exit 0", out)
    cek("- dispatch ctx_b (task task_uji): heartbeat terakhir" in out and "phase reviewing" in out and "dispatch ctx_c" in out
        and "phase testing" in out, "heartbeat terakhir tiap dispatch dicetak dengan phase-nya", out)
    cek(any("--ack" in a and a[a.index("--ack") + 1] == "delivery_hb2" for a in pg), "batch heartbeat terakhir di-ack sebelum TIMEOUT", str(pg))
    r, out, pg = jalankan(tmp, [{"keluar": hasil([], None), "tidur": 0.2}], "--minutes", "0.01")
    cek(r.returncode == 0 and "Heartbeat di-ack: 0." in out and "- tidak ada heartbeat selama menunggu" in out,
        "TIMEOUT tanpa heartbeat menyebut tidak ada heartbeat", out)

    # 3. Batch campuran: tidak di-ack, heartbeat di dalamnya hanya dihitung.
    q = pesan("question", 6, "Pakai opsi mana?", "opsi 1 atau 2")
    r, out, pg = jalankan(tmp, [{"keluar": hasil([hb(5, "ctx_a", "implementing"), q], "delivery_q")}])
    cek(r.returncode == 0 and r.stdout.startswith("PESAN delivery_q: 1 pesan; +1 heartbeat dalam batch ini")
        and "- [question] msg_6 dari term_worker: Pakai opsi mana?" in out and "[heartbeat]" not in out,
        "batch heartbeat + question: question dicetak, heartbeat hanya dihitung", out)
    cek(len(pg) == 1, "batch campuran tidak di-ack oleh skrip (satu panggilan saja)", str(pg))

    # 4. --ack, --run, dan galat.
    r, out, pg = jalankan(tmp, [{"keluar": hasil([wd], "delivery_x")}], "--ack", "delivery_lama", "--run", "run_uji")
    cek(len(pg) == 1 and pg[0][pg[0].index("--ack") + 1] == "delivery_lama" and pg[0][pg[0].index("--run") + 1] == "run_uji",
        "--ack dan --run diteruskan ke panggilan pertama", str(pg))
    r, out, _ = jalankan(tmp, [{"keluar": {"id": "x", "ok": False, "error": {"code": "runtime_unavailable", "message": "Orca is not running"}},
                                "kode": 1}])
    cek(r.returncode == 2 and r.stdout.startswith("GALAT: runtime_unavailable: Orca is not running"), "galat JSON Orca: GALAT dengan kodenya, exit 2", out)
    r, out, _ = jalankan(tmp, [{"keluar": "Error: unknown command", "kode": 1, "keepalive_err": 1}])
    cek(r.returncode == 2 and "GALAT: output orca bukan JSON (exit 1): Error: unknown command" in out and "_keepalive" not in out,
        "output bukan JSON: GALAT dengan potongan output, exit 2", out)
    r, out, _ = jalankan(tmp, [{"keluar": hasil([hb(7, "ctx_a", "implementing")], None)}])
    cek(r.returncode == 2 and "GALAT: batch heartbeat tanpa deliveryId" in out, "batch heartbeat tanpa deliveryId: GALAT, bukan berputar", out)
    r2 = subprocess.run([sys.executable, str(SKRIP), "--orca", "orca-tidak-ada-di-path-uji"], capture_output=True, text=True,
                        encoding="utf-8", errors="replace", timeout=60)
    cek(r2.returncode == 2 and "GALAT: perintah Orca tidak ditemukan" in r2.stdout, "Orca tidak ada di PATH: GALAT, exit 2", r2.stdout + r2.stderr)
    r2 = subprocess.run([sys.executable, str(SKRIP), "--minutes", "0"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    cek(r2.returncode == 2 and "--minutes" in r2.stderr, "--minutes 0 ditolak (exit 2)", r2.stdout + r2.stderr)
    r2 = subprocess.run([sys.executable, str(SKRIP), "--help"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    cek(r2.returncode == 0 and "--minutes" in r2.stdout and "--ack" in r2.stdout and "--run" in r2.stdout, "--help menyebut opsi", r2.stdout)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\nHASIL:", "SEMUA OK" if ok else "ADA YANG GAGAL")
sys.exit(0 if ok else 1)
