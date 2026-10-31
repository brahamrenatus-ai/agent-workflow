"""Uji fungsional scripts/context_size.py (v3.17) dengan folder konfigurasi Claude Code palsu: transkrip sesi dicari
lewat CLAUDE_CODE_SESSION_ID, ukuran prompt pesan asisten terakhir, AMAN/BESAR/TIDAK DIKETAHUI, transkrip besar, --limit.
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
    print(("OK    " if cond else "GAGAL ") + msg)
    if not cond and out:
        print("      " + out.replace("\n", "\n      "))
    ok = ok and cond


def asisten(ts, inp, baca, tulis):
    return {"type": "assistant", "timestamp": ts, "message": {"id": f"msg_{ts}", "role": "assistant", "content": [],
            "usage": {"input_tokens": inp, "cache_read_input_tokens": baca, "cache_creation_input_tokens": tulis, "output_tokens": 9}}}


def jalankan(konfig, sesi, *args):
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_CONFIG_DIR", "CLAUDE_CODE_SESSION_ID")}
    if konfig is not None:
        env["CLAUDE_CONFIG_DIR"] = str(konfig)
    if sesi is not None:
        env["CLAUDE_CODE_SESSION_ID"] = sesi
    r = subprocess.run([sys.executable, str(SKRIP), *args], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, timeout=60)
    return r.returncode, r.stdout + r.stderr


if not SKRIP.is_file():
    cek(False, f"scripts/context_size.py ada ({SKRIP})")
    print("\nHASIL: ADA YANG GAGAL")
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
    cek(rc == 0 and out.startswith("BESAR: konteks sesi ini 231.208 token (pesan terakhir 2026-10-31T01:01:05), batas 200.000.")
        and "/clear" in out, "pesan asisten terakhir 8 + 230.000 + 1.200 = 231.208 token > 200.000: BESAR, sarankan /clear", out)
    rc, out = jalankan(konfig, sesi, "--limit", "300000")
    cek(rc == 0 and out.startswith("AMAN: konteks sesi ini 231.208 token") and "batas 300.000" in out, "--limit 300000: AMAN", out)
    rc, out = jalankan(konfig, None)
    cek(rc == 0 and out.startswith("TIDAK DIKETAHUI: variabel CLAUDE_CODE_SESSION_ID tidak ada"), "tanpa CLAUDE_CODE_SESSION_ID: TIDAK DIKETAHUI, exit 0", out)
    rc, out = jalankan(konfig, "00000000-dead-beef-0000-000000000000")
    cek(rc == 0 and out.startswith("TIDAK DIKETAHUI: transkrip sesi 00000000-dead-beef-0000-000000000000 tidak ditemukan"),
        "transkrip sesi tidak ada: TIDAK DIKETAHUI", out)

    kosong = "22222222-2222-2222-2222-222222222222"
    (folder / f"{kosong}.jsonl").write_text(json.dumps(baris[0]) + "\n", encoding="utf-8")
    rc, out = jalankan(konfig, kosong)
    cek(rc == 0 and out.startswith("TIDAK DIKETAHUI: belum ada pesan asisten bertoken"), "transkrip tanpa pesan asisten: TIDAK DIKETAHUI", out)

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
    cek(rc == 0 and out.startswith("AMAN: konteks sesi ini 50.001 token"), "pesan bertoken hanya di awal transkrip besar: dibaca dengan memindai ulang seluruh file", out)

    rc, out = jalankan(konfig, sesi, "--limit", "0")
    cek(rc == 2 and "--limit" in out, "--limit 0 ditolak (exit 2)", out)
    rc, out = jalankan(konfig, sesi, "--help")
    cek(rc == 0 and "--limit" in out, "--help menyebut --limit", out)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print("\nHASIL:", "SEMUA OK" if ok else "ADA YANG GAGAL")
sys.exit(0 if ok else 1)
