"""Uji fungsional scripts/head_restart.py (v3.18) dengan `orca` palsu: urutan perintah, pembatalan saat user mengetik atau
mengirim prompt, galat Orca, argumen, dan proses terpisah yang tetap jalan sesudah pemanggilnya selesai.
Pemakaian: python -X utf8 tests/test_head_restart.py <folder skill>"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SKILL = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".claude/skills/agent-workflow").resolve()
SKRIP = SKILL / "scripts" / "head_restart.py"
ok = True


def cek(cond, msg, out=""):
    global ok
    print(("OK    " if cond else "GAGAL ") + msg)
    if not cond and out:
        print("      " + str(out).replace("\n", "\n      "))
    ok = ok and cond


# orca palsu: tiap subperintah (wait, read, send) mengambil langkah berikutnya dari skenario; langkah terakhir diulang.
PALSU = r'''
import json, os, subprocess, sys
d = os.environ["ORCA_PALSU"]
langkah = json.load(open(os.path.join(d, "skenario.json"), encoding="utf-8"))
with open(os.path.join(d, "panggilan.jsonl"), "a", encoding="utf-8") as f:
    f.write(json.dumps(sys.argv[1:]) + "\n")
aksi = sys.argv[2]
p = os.path.join(d, "no_" + aksi)
i = int(open(p).read()) if os.path.exists(p) else 0
open(p, "w").write(str(i + 1))
s = langkah[aksi][min(i, len(langkah[aksi]) - 1)]
if s.get("tambah_transkrip"):
    # Tanpa mewarisi stdout: pemanggil menunggu pipa tertutup, jadi baris transkrip harus tertulis sesudah orca palsu selesai.
    subprocess.Popen([sys.executable, "-c", "import sys, time; time.sleep(1); open(sys.argv[1], 'ab').write(b'{\"type\":\"user\"}\\n')",
                      os.environ["TRANSKRIP"]], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print(json.dumps(s["keluar"]))
'''
SIAGA = {"ok": True, "result": {"wait": {"satisfied": True, "status": "running"}}}
BELUM = {"ok": True, "result": {"wait": {"satisfied": False, "status": "running"}}}
KIRIM = {"ok": True, "result": {"send": {"accepted": True}}}
LAYAR = {"ok": True, "result": {"terminal": {"tail": ["● selesai", "─" * 40, "❯", "─" * 40, "  ⏵⏵ auto mode on"]}}}
DITOLAK = {"ok": False, "error": {"code": "agent_prompt_blocked", "message": "dialog terbuka"}}


def skenario(wait=None, read=None, send=None):
    return {"wait": wait or [{"keluar": SIAGA}], "read": read or [{"keluar": LAYAR}], "send": send or [{"keluar": KIRIM}]}


def jalankan(d, langkah, *args, grace="0"):
    for f in ("panggilan.jsonl", "no_wait", "no_read", "no_send", "catat.log"):
        (d / f).unlink(missing_ok=True)
    (d / "skenario.json").write_text(json.dumps(langkah, ensure_ascii=False), encoding="utf-8")
    log = d / "catat.log"
    r = subprocess.run([sys.executable, str(SKRIP), "--worker", "--no-start-delay", "--skill", "demo-head", "--grace", grace,
                        "--terminal", "term_uji", "--log", str(log), "--orca", str(d / "orca_palsu.py"), *args],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=lingkungan(d), timeout=60)
    panggil = [json.loads(b) for b in (d / "panggilan.jsonl").read_text(encoding="utf-8").splitlines()]
    return r.returncode, log.read_text(encoding="utf-8") if log.is_file() else "", panggil


def lingkungan(d):
    env = {k: v for k, v in os.environ.items() if k not in ("ORCA_TERMINAL_HANDLE", "CLAUDE_CONFIG_DIR", "CLAUDE_CODE_SESSION_ID")}
    env.update(ORCA_PALSU=str(d), TRANSKRIP=str(d / "akun/projects/demo/sesi-uji.jsonl"), CLAUDE_CONFIG_DIR=str(d / "akun"),
               CLAUDE_CODE_SESSION_ID="sesi-uji")
    return env


def teks_kirim(panggil):
    return [p[p.index("--text") + 1] for p in panggil if p[1] == "send"]


if not SKRIP.is_file():
    cek(False, f"scripts/head_restart.py ada ({SKRIP})")
    print("\nHASIL: ADA YANG GAGAL")
    sys.exit(1)

tmp = Path(tempfile.mkdtemp(prefix="head_restart_"))
try:
    (tmp / "orca_palsu.py").write_text(PALSU, encoding="utf-8")
    trans = tmp / "akun/projects/demo/sesi-uji.jsonl"
    trans.parent.mkdir(parents=True)
    trans.write_bytes(b'{"type":"user"}\n{"type":"assistant"}\n')

    rc, log, pg = jalankan(tmp, skenario())
    urutan = [p[1] for p in pg]
    cek(rc == 0 and urutan == ["wait", "wait", "read", "send", "wait", "send"] and teks_kirim(pg) == ["/clear", "/demo-head"]
        and "SELESAI: /demo-head terkirim" in log, "alur normal: tunggu, cek input, /clear, tunggu, /<skill>", (urutan, log))
    cek(all("--terminal" in p and p[p.index("--terminal") + 1] == "term_uji" for p in pg), "setiap perintah menyebut terminal ini", pg)
    cek(all("--enter" in p for p in pg if p[1] == "send"), "teks dikirim dengan Enter", pg)

    rc, log, pg = jalankan(tmp, skenario(), "--skill", "/demo-head")
    cek(teks_kirim(pg) == ["/clear", "/demo-head"], "nama skill berawalan / diterima, tidak menjadi //", pg)

    draf = {"ok": True, "result": {"terminal": dict(LAYAR["result"]["terminal"], draft="ketikan user")}}
    rc, log, pg = jalankan(tmp, skenario(read=[{"keluar": draf}]))
    cek(rc == 1 and not teks_kirim(pg) and "ada ketikan user" in log,
        "ketikan user di `draft` (baris input di tail tetap kosong): batal, tanpa mengirim apa pun", (log, pg))
    isi = {"ok": True, "result": {"terminal": {"tail": ["● selesai", "❯ teks yang belum dikirim", "  ⏵⏵ auto mode on"]}}}
    rc, log, pg = jalankan(tmp, skenario(read=[{"keluar": isi}]))
    cek(rc == 1 and not teks_kirim(pg) and "tidak kosong" in log, "baris input berisi teks: batal", (log, pg))
    asing = {"ok": True, "result": {"terminal": {"tail": ["● selesai", "| kotak input bentuk lain |"]}}}
    rc, log, pg = jalankan(tmp, skenario(read=[{"keluar": asing}]))
    cek(rc == 1 and not teks_kirim(pg) and "tidak ditemukan" in log, "baris input tidak dikenali: batal (ragu berarti batal)", (log, pg))

    rc, log, pg = jalankan(tmp, skenario(wait=[{"keluar": BELUM}]))
    cek(rc == 1 and [p[1] for p in pg] == ["wait"] and "tidak menganggur" in log, "terminal tidak pernah menganggur: batal", (log, pg))
    rc, log, pg = jalankan(tmp, skenario(wait=[{"keluar": SIAGA}, {"keluar": BELUM}]))
    cek(rc == 1 and not teks_kirim(pg), "terminal sibuk lagi sesudah jeda: batal", (log, pg))
    rc, log, pg = jalankan(tmp, skenario(wait=[{"keluar": SIAGA, "tambah_transkrip": True}, {"keluar": SIAGA}]), grace="3")
    cek(rc == 1 and not teks_kirim(pg) and "pesan baru di transkrip" in log, "user mengirim prompt selama jeda: batal", (log, pg))

    rc, log, pg = jalankan(tmp, skenario(send=[{"keluar": DITOLAK}]))
    cek(rc == 1 and teks_kirim(pg) == ["/clear"] and "agent_prompt_blocked" in log, "/clear ditolak Orca: berhenti, skill tidak dikirim", (log, pg))
    rc, log, pg = jalankan(tmp, skenario(wait=[{"keluar": SIAGA}, {"keluar": SIAGA}, {"keluar": BELUM}]))
    cek(rc == 1 and teks_kirim(pg) == ["/clear"] and "GAGAL sesudah /clear" in log, "sesi baru tidak siap: skill tidak dikirim, tercatat di log", (log, pg))
    rc, log, pg = jalankan(tmp, skenario(wait=[{"keluar": DITOLAK}]))
    cek(rc == 1 and not teks_kirim(pg), "galat Orca saat menunggu: batal", (log, pg))

    env = lingkungan(tmp)
    r = subprocess.run([sys.executable, str(SKRIP), "--skill", "demo-head"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    cek(r.returncode == 2 and r.stdout.startswith("GALAT:") and "/clear lalu /demo-head" in r.stdout, "di luar terminal Orca: GALAT, exit 2", r.stdout)
    env_h = dict(env, ORCA_TERMINAL_HANDLE="term_uji")
    r = subprocess.run([sys.executable, str(SKRIP), "--skill", "C:/Program Files/Git/demo-head"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env_h)
    cek(r.returncode == 2 and "tidak valid" in r.stdout, "nama skill yang dirusak Git Bash menjadi path: GALAT, tidak dijadwalkan", r.stdout)
    r = subprocess.run([sys.executable, str(SKRIP), "--help"], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    cek(r.returncode == 0 and "--skill" in r.stdout and "--grace" in r.stdout, "--help menyebut --skill dan --grace", r.stdout)

    # Proses terpisah: pemanggil selesai lebih dulu, lalu log tetap ditulis sampai SELESAI.
    for f in ("panggilan.jsonl", "no_wait", "no_read", "no_send"):
        (tmp / f).unlink(missing_ok=True)
    (tmp / "skenario.json").write_text(json.dumps(skenario(), ensure_ascii=False), encoding="utf-8")
    log = tmp / "lepas.log"
    r = subprocess.run([sys.executable, str(SKRIP), "--skill", "demo-head", "--grace", "0", "--log", str(log), "--orca", str(tmp / "orca_palsu.py")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=env_h, timeout=60)
    belum = not log.is_file() or "SELESAI" not in log.read_text(encoding="utf-8")
    cek(r.returncode == 0 and r.stdout.startswith("JADWAL:") and "/clear lalu /demo-head" in r.stdout and str(log) in r.stdout and belum,
        "pemanggil selesai sebelum proses terpisah selesai, dan menyebut file catatan", r.stdout)
    akhir = time.monotonic() + 30
    isi_log = ""
    while time.monotonic() < akhir and "SELESAI" not in isi_log:
        time.sleep(0.5)
        isi_log = log.read_text(encoding="utf-8") if log.is_file() else ""
    cek("SELESAI: /demo-head terkirim" in isi_log, "proses terpisah menyelesaikan alur sesudah pemanggilnya selesai", isi_log)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\nHASIL:", "SEMUA OK" if ok else "ADA YANG GAGAL")
sys.exit(0 if ok else 1)
