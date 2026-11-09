"""Uji fungsional scripts/context_size.py (v3.17) dengan folder konfigurasi Claude Code palsu: transkrip sesi dicari
lewat CLAUDE_CODE_SESSION_ID, ukuran prompt pesan asisten terakhir, OK/LARGE/UNKNOWN, transkrip besar, --limit.
Pemakaian: python -X utf8 tests/test_context_size.py <folder skill>"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".claude/skills/agent-workflow").resolve()
SKRIP = SKILL / "scripts" / "context_size.py"
ok = True


def cek(cond, msg, out=""):
    global ok
    print(("OK    " if cond else "FAIL  ") + msg)
    if not cond and out:
        print("      " + out.replace("\n", "\n      "))
    ok = ok and cond


def asisten(ts, inp, baca, tulis):
    return {"type": "assistant", "timestamp": ts, "message": {"id": f"msg_{ts}", "role": "assistant", "content": [],
            "usage": {"input_tokens": inp, "cache_read_input_tokens": baca, "cache_creation_input_tokens": tulis, "output_tokens": 9}}}


def jalankan(konfig, sesi, *args, cwd=None):
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_CONFIG_DIR", "CLAUDE_CODE_SESSION_ID")}
    if konfig is not None:
        env["CLAUDE_CONFIG_DIR"] = str(konfig)
    if sesi is not None:
        env["CLAUDE_CODE_SESSION_ID"] = sesi
    r = subprocess.run([sys.executable, str(SKRIP), *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, timeout=60, cwd=cwd)
    return r.returncode, r.stdout + r.stderr


if not SKRIP.is_file():
    cek(False, f"scripts/context_size.py ada ({SKRIP})")
    print("\nRESULT: SOME FAILED")
    sys.exit(1)

tmp = Path(tempfile.mkdtemp(prefix="context_size_"))
try:
    konfig = tmp / "akun"
    folder = konfig / "projects" / "G--Project-demo"
    folder.mkdir(parents=True)
    sesi = "11111111-2222-3333-4444-555555555555"
    baris = [{"type": "user", "timestamp": "2026-10-31T01:00:00Z", "message": {"role": "user", "content": "halo"}},
             asisten("2026-10-31T01:00:05Z", 5, 1000, 500),
             {"type": "user", "timestamp": "2026-10-31T01:01:00Z", "message": {"role": "user", "content": [{"type": "tool_result", "content": "x"}]}},
             asisten("2026-10-31T01:01:05Z", 8, 230000, 1200),
             {"type": "system", "subtype": "turn_duration", "timestamp": "2026-10-31T01:01:06Z"}]
    (folder / f"{sesi}.jsonl").write_text("\n".join(json.dumps(b) for b in baris) + "\n", encoding="utf-8")
    # sesi lain di folder yang sama tidak boleh terbaca
    (folder / "99999999-0000-0000-0000-000000000000.jsonl").write_text(json.dumps(asisten("2026-10-31T02:00:00Z", 1, 1, 1)) + "\n", encoding="utf-8")

    rc, out = jalankan(konfig, sesi)
    cek(rc == 0 and out.startswith("LARGE: konteks sesi ini 231.208 token (pesan terakhir 2026-10-31T01:01:05), batas 200.000.")
        and "/clear" in out, "pesan asisten terakhir 8 + 230.000 + 1.200 = 231.208 token > 200.000: LARGE, sarankan /clear", out)
    rc, out = jalankan(konfig, sesi, "--limit", "300000")
    cek(rc == 0 and out.startswith("OK: konteks sesi ini 231.208 token") and "batas 300.000" in out, "--limit 300000: OK", out)
    rc, out = jalankan(konfig, None)
    cek(rc == 0 and out.startswith("UNKNOWN: variabel CLAUDE_CODE_SESSION_ID tidak ada"), "tanpa CLAUDE_CODE_SESSION_ID: UNKNOWN, exit 0", out)
    rc, out = jalankan(konfig, "00000000-dead-beef-0000-000000000000")
    cek(rc == 0 and out.startswith("UNKNOWN: transkrip sesi 00000000-dead-beef-0000-000000000000 tidak ditemukan"),
        "transkrip sesi tidak ada: UNKNOWN", out)

    kosong = "22222222-2222-2222-2222-222222222222"
    (folder / f"{kosong}.jsonl").write_text(json.dumps(baris[0]) + "\n", encoding="utf-8")
    rc, out = jalankan(konfig, kosong)
    cek(rc == 0 and out.startswith("UNKNOWN: belum ada pesan asisten bertoken"), "transkrip tanpa pesan asisten: UNKNOWN", out)

    # transkrip > 4 MB: pesan terakhir di ekor; dan pesan bertoken yang hanya ada di awal tetap ditemukan
    besar = "33333333-3333-3333-3333-333333333333"
    isi = [json.dumps(asisten("2026-10-31T03:00:00Z", 1, 50000, 0))]
    isi += [json.dumps({"type": "user", "timestamp": "2026-10-31T03:00:01Z", "message": {"role": "user", "content": "y" * 1000}})] * 5000
    isi.append(json.dumps(asisten("2026-10-31T03:30:00Z", 2, 410000, 300)))
    (folder / f"{besar}.jsonl").write_text("\n".join(isi) + "\n", encoding="utf-8")
    rc, out = jalankan(konfig, besar)
    cek(rc == 0 and "410.302 token (pesan terakhir 2026-10-31T03:30:00)" in out, "transkrip besar: pesan asisten terakhir dibaca dari ekor file", out)
    awal = "44444444-4444-4444-4444-444444444444"
    (folder / f"{awal}.jsonl").write_text("\n".join(isi[:-1]) + "\n", encoding="utf-8")
    rc, out = jalankan(konfig, awal)
    cek(rc == 0 and out.startswith("OK: konteks sesi ini 50.001 token"), "pesan bertoken hanya di awal transkrip besar: dibaca dengan memindai ulang seluruh file", out)

    rc, out = jalankan(konfig, sesi, "--limit", "0")
    cek(rc == 2 and "--limit" in out, "--limit 0 ditolak (exit 2)", out)
    rc, out = jalankan(konfig, sesi, "--help")
    cek(rc == 0 and "--limit" in out, "--help menyebut --limit", out)

    if "--handoff-limit" in SKRIP.read_text(encoding="utf-8"):  # sejak v3.18
        proj = tmp / "proj"
        (proj / "handoff").mkdir(parents=True)
        rc, out = jalankan(konfig, sesi, cwd=proj)
        cek(rc == 0 and "TIDY" not in out, "tanpa ROADMAP: tanpa baris TIDY", out)
        roadmap = proj / "handoff/ROADMAP.md"
        roadmap.write_text("# ROADMAP\n## 1. Tertunda\n" + "x" * 9000 + "\n## 3. Backlog\n" + "y" * 90000 + "\n", encoding="utf-8")
        rc, out = jalankan(konfig, sesi, "--limit", "300000", cwd=proj)
        cek(rc == 0 and out.startswith("OK:") and "\nTIDY: ROADMAP §1 9 KB, batas 8 KB" in out,
            "§1 9.001 byte > 8 KB: baris kedua TIDY, baris pertama tetap OK (bagian lain tidak dihitung)", out)
        rc, out = jalankan(konfig, None, cwd=proj)
        cek(out.startswith("UNKNOWN") and "TIDY" in out, "di luar sesi Claude Code TIDY tetap dicetak", out)
        rc, out = jalankan(konfig, sesi, "--handoff-limit", "20", cwd=proj)
        cek(rc == 0 and "TIDY" not in out, "--handoff-limit 20: tanpa TIDY", out)
        roadmap.write_text("# ROADMAP\n## 1. Tertunda\nsingkat\n## 3. Backlog\n" + "y" * 90000 + "\n", encoding="utf-8")
        rc, out = jalankan(konfig, sesi, cwd=proj)
        cek(rc == 0 and "TIDY" not in out, "§1 pendek, ROADMAP panjang: tanpa TIDY", out)
        rc, out = jalankan(konfig, sesi, "--handoff-limit", "0", cwd=proj)
        cek(rc == 2 and "--handoff-limit" in out, "--handoff-limit 0 ditolak (exit 2)", out)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\nRESULT:", "ALL OK" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
