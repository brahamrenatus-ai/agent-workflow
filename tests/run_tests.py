"""Jalankan semua uji skill agent-workflow dan cetak LULUS/GAGAL per uji.

Pemakaian (dari root repo): python tests/run_tests.py [folder skill]
Bawaan folder skill: plugins/agent-workflow/skills/agent-workflow. Butuh Python 3.9+ dan git di PATH.
"""
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

T = Path(__file__).resolve().parent
S = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else T.parent / "plugins/agent-workflow/skills/agent-workflow"
UJI = [
    ("check_skill", [S]),
    ("test_cek_versi_tag", [S]),
    ("test_cek_versi_tampak", [S]),
    ("test_cek_bukti", [S / "scripts" / "cek_bukti.py"]),
    ("test_catat", [S]),
    ("test_cek_secret", [S / "scripts" / "cek_secret.py"]),
    ("test_redact_asal", [S]),
    ("test_kalibrasi", [S]),
    ("test_foto_tampilan", [S]),  # dilewati bila Chrome, Chromium, atau Edge tidak ada
]
gagal = []
for nama, args in UJI:
    r = subprocess.run([sys.executable, "-X", "utf8", str(T / f"{nama}.py"), *map(str, args)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = r.stdout + r.stderr
    salah = [l for l in out.splitlines() if l.startswith("GAGAL") or "ADA YANG GAGAL" in l or "Traceback" in l]
    if r.returncode == 0 and not salah:
        ringkas = next((l for l in reversed(out.splitlines()) if l.startswith("HASIL")), "")
        print(f"LULUS  {nama}: {ringkas}")
    else:
        gagal.append(nama)
        print(f"GAGAL  {nama} (exit {r.returncode})")
        print("\n".join("       " + l for l in (salah or out.splitlines())[-25:]))
print(f"\n{'SEMUA UJI LULUS' if not gagal else 'ADA YANG GAGAL: ' + ', '.join(gagal)} ({len(UJI) - len(gagal)}/{len(UJI)})")
sys.exit(1 if gagal else 0)
