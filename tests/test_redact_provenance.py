"""Uji gabungan v3.9.1: log dari record.py yang disamarkan check_secrets.py --redact tetap lolos check_evidence.py, karena
check_secrets menambahkan catatan asal berjenis redact. Log yang sudah diedit tangan, log tanpa catatan asal, dan
project tanpa provenance.jsonl tidak ikut disahkan. Semua token di sini palsu.
Pemakaian: python -X utf8 tests/test_redact_provenance.py <folder skill>"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".claude/skills/agent-workflow").resolve()
ok = True
TG = "AAH" + "palsuTokenBot_0123456789-abcdefghij"[:32]  # A + 34 karakter
GH = "ghp_" + "palsu0123456789abcdefghijklmnopqrstuv"[:36]
py = f'"{sys.executable}"'


def cek(cond, msg, out=""):
    global ok
    print(("OK    " if cond else "GAGAL ") + msg)
    if not cond and out:
        print("      " + str(out).replace("\n", "\n      "))
    ok = ok and cond


def proyek(dasar, nama):
    p = dasar / nama
    (p / "handoff" / "tools").mkdir(parents=True)
    (p / "handoff" / "reports").mkdir()
    subprocess.run(["git", "init", "-q"], cwd=p, check=True)
    for s in ("record.py", "check_secrets.py", "check_evidence.py"):
        shutil.copy(SKILL / "scripts" / s, p / "handoff" / "tools" / s)
    return p


def alat(p, skrip, *args):
    r = subprocess.run([sys.executable, f"handoff/tools/{skrip}", *args], cwd=p, capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


def cetak(*baris):
    """Perintah python yang mencetak baris-baris ini (untuk record.py)."""
    return f'{py} -c "' + "; ".join(f"print('{b}')" for b in baris) + '"'


def asal(p):
    f = p / "handoff" / "logs" / "provenance.jsonl"
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()] if f.is_file() else []


def hash_lf(f):
    return hashlib.sha256(f.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def report(p, nama, log, no, kutipan, teramati):
    isi = (f"# {nama}\nStatus: DONE\n\n## Data yang Diminta\n| Kriteria | Harapan | Teramati | Bukti | Status |\n|---|---|---|---|---|\n"
           f"| K1 polling | {teramati} | {teramati} | `{log}:{no}` | OK |\n\n## Bukti Mentah\n```bukti\n{log}:{no} | {kutipan}\n```\n\n"
           "## Periksa Diri\n- check_evidence 0 masalah\n")
    (p / "handoff" / "reports" / f"{nama}.md").write_text(isi, encoding="utf-8")
    return alat(p, "check_evidence.py", f"handoff/reports/{nama}.md")


tmp = Path(tempfile.mkdtemp(prefix="redact_asal_"))
try:
    p = proyek(tmp, "proj")
    URL = f"HTTP Request: POST https://api.telegram.org/bot7123456789:{TG}/getUpdates 200"
    LOG = "handoff/logs/TASK-001-bot.log"

    # 1. Log dari record.py berisi token; report merujuknya -> lolos sebelum disamarkan
    rc, out = alat(p, "record.py", LOG, cetak(URL, "[10:00:01] [BOT] polling ok"))
    cek(rc == 0 and len(asal(p)) == 1, "record.py: log tercatat di provenance.jsonl", out)
    rc, out = report(p, "REPORT-001", LOG, 2, "[10:00:01] [BOT] polling ok", "polling ok")
    cek(rc == 0 and "0 masalah" in out, "sebelum disamarkan: check_evidence 0 masalah", out)

    # 2. --redact: log disamarkan dan catatan asal redact ditambahkan; check_evidence tetap lolos
    lama = asal(p)[-1]
    rc, out = alat(p, "check_secrets.py", LOG, "--redact")
    isi = (p / LOG).read_text(encoding="utf-8")
    rec = asal(p)
    cek(rc == 0 and TG not in isi and "bot<REDACTED>/getUpdates" in isi, "check_secrets --redact menyamarkan token di URL bot<token>", out)
    cek(len(rec) == 2 and rec[-1].get("jenis") == "redact" and rec[-1].get("sha256") == hash_lf(p / LOG)
        and rec[-1].get("sha256_sebelum") == lama["sha256"] and rec[-1].get("perintah") == lama["perintah"]
        and rec[-1].get("kode_keluar") == lama["kode_keluar"] and rec[-1].get("file") == lama["file"],
        "catatan redact: hash baru, hash sebelumnya, perintah dan kode keluar asal tetap", rec)
    cek("catatan asal redact ditambahkan" in out and "provenance.jsonl" in out, "output menyebut catatan asal dan provenance.jsonl untuk di-git add", out)
    rc, out = report(p, "REPORT-001", LOG, 2, "[10:00:01] [BOT] polling ok", "polling ok")
    cek(rc == 0 and "0 masalah" in out and "berubah setelah dicatat" not in out, "sesudah disamarkan: check_evidence tetap 0 masalah", out)
    rc, out = report(p, "REPORT-001", LOG, 1, "HTTP Request: POST https://api.telegram.org/bot<REDACTED>/getUpdates 200", "200")
    cek(rc == 0 and "0 masalah" in out, "kutipan baris yang sudah disamarkan (berisi <REDACTED>) cocok", out)

    # 3. Redact kedua kali: tidak ada temuan -> tidak ada catatan baru
    rc, out = alat(p, "check_secrets.py", LOG, "--redact")
    cek(rc == 0 and "0 baris bertemuan" in out and len(asal(p)) == 2, "redact ulang tanpa temuan: provenance.jsonl tidak berubah", out)

    # 4. Log diedit tangan setelah dicatat, lalu disamarkan: tidak disahkan, check_evidence tetap menandainya
    LOG2 = "handoff/logs/TASK-002-edit.log"
    alat(p, "record.py", LOG2, cetak(f"token {GH}", "[10:05:00] [BOT] kirim ok"))
    with open(p / LOG2, "a", encoding="utf-8", newline="\n") as f:
        f.write("[10:05:09] [BOT] baris karangan\n")
    n = len(asal(p))
    rc, out = alat(p, "check_secrets.py", LOG2, "--redact")
    cek(GH not in (p / LOG2).read_text(encoding="utf-8") and len(asal(p)) == n and "sudah berubah setelah dicatat" in out,
        "log yang diedit tangan tetap disamarkan, tetapi catatan asalnya tidak diperbarui (peringatan)", out)
    rc, out = report(p, "REPORT-002", LOG2, 3, "[10:05:09] [BOT] baris karangan", "baris karangan")
    cek(rc == 1 and "berubah setelah dicatat" in out, "check_evidence tetap menandai log yang diedit tangan", out)

    # 5. Log tanpa catatan asal: disamarkan, provenance.jsonl tidak berubah (tidak ada catatan yang dikarang)
    (p / "handoff/logs/manual.log").write_text(f"tok {GH}\n", encoding="utf-8")
    n = len(asal(p))
    rc, out = alat(p, "check_secrets.py", "handoff/logs/manual.log", "--redact")
    cek(rc == 0 and GH not in (p / "handoff/logs/manual.log").read_text(encoding="utf-8") and len(asal(p)) == n
        and not any(r["file"].endswith("manual.log") for r in asal(p)), "log tanpa catatan asal: disamarkan, tidak dicatat", out)

    # 6. --staged --redact: file yang di-stage juga mendapat catatan redact
    LOG3 = "handoff/logs/TASK-003-staged.log"
    alat(p, "record.py", LOG3, cetak(f"Authorization: Bearer {GH}"))
    subprocess.run(["git", "add", LOG3], cwd=p, check=True)
    rc, out = alat(p, "check_secrets.py", "--staged", "--redact")
    rec = [r for r in asal(p) if r["file"] == LOG3]
    cek(len(rec) == 2 and rec[-1]["jenis"] == "redact" and rec[-1]["sha256"] == hash_lf(p / LOG3), "--staged --redact: catatan redact ditambahkan", out)
    rc, out = report(p, "REPORT-003", LOG3, 1, "Authorization: Bearer <REDACTED>", "Bearer")
    cek(rc == 0 and "0 masalah" in out, "log yang disamarkan (pola yang sudah ada sejak v3.2) lolos check_evidence; v3.9: berubah setelah dicatat", out)

    # 7. Path dengan backslash (Windows): catatan tetap ditemukan
    if os.name == "nt":
        LOG4 = "handoff/logs/TASK-004-win.log"
        alat(p, "record.py", LOG4, cetak(f"token {GH}"))
        rc, out = alat(p, "check_secrets.py", LOG4.replace("/", "\\"), "--redact")
        rec = [r for r in asal(p) if r["file"] == LOG4]
        cek(len(rec) == 2 and rec[-1]["jenis"] == "redact", "path dengan backslash: catatan redact tetap ditambahkan", out)
    cek(all(isinstance(r, dict) for r in asal(p)), "semua baris provenance.jsonl tetap JSON yang valid")

    # 8. Project tanpa provenance.jsonl: --redact bekerja seperti dulu, provenance.jsonl tidak dibuat
    q = proyek(tmp, "tanpa_asal")
    (q / "handoff/logs").mkdir(parents=True)
    (q / "handoff/logs/a.log").write_text(f"tok {GH}\n", encoding="utf-8")
    rc, out = alat(q, "check_secrets.py", "handoff/logs/a.log", "--redact")
    cek(rc == 0 and GH not in (q / "handoff/logs/a.log").read_text(encoding="utf-8") and not (q / "handoff/logs/provenance.jsonl").exists(),
        "tanpa provenance.jsonl: disamarkan, provenance.jsonl tidak dibuat", out)

    # 9. Project bernama lama (sebelum v3.12): ketiga alat tetap memakai handoff/logs/asal.jsonl
    if "ASAL_LAMA" in (SKILL / "scripts" / "record.py").read_text(encoding="utf-8"):
        s = proyek(tmp, "nama_lama")
        (s / "handoff/logs").mkdir(parents=True)
        f_lama = s / "handoff/logs/asal.jsonl"
        f_lama.write_text("", encoding="utf-8")
        rc1, out1 = alat(s, "record.py", LOG, cetak(URL, "[10:00:01] [BOT] polling ok"))
        rc2, out2 = alat(s, "check_secrets.py", LOG, "--redact")
        rc3, out3 = report(s, "REPORT-001", LOG, 2, "[10:00:01] [BOT] polling ok", "polling ok")
        rec = [json.loads(l) for l in f_lama.read_text(encoding="utf-8").splitlines() if l.strip()]
        cek(rc1 == 0 and rc2 == 0 and len(rec) == 2 and rec[-1].get("jenis") == "redact" and "asal.jsonl" in out2
            and not (s / "handoff/logs/provenance.jsonl").exists() and rc3 == 0 and "0 masalah" in out3
            and "berubah setelah" not in out3,
            "project bernama lama: record, check_secrets --redact, dan check_evidence memakai asal.jsonl", out1 + out2 + out3)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("\nHASIL:", "SEMUA OK" if ok else "ADA YANG GAGAL")
sys.exit(0 if ok else 1)
