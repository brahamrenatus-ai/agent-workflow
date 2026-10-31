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
    ("test_check_version_tags", [S]),
    ("test_check_version_visible", [S]),
    ("test_check_evidence", [S / "scripts" / "check_evidence.py"]),
    ("test_record", [S]),
    ("test_check_secrets", [S / "scripts" / "check_secrets.py"]),
    ("test_redact_provenance", [S]),
    ("test_calibrate", [S]),
    ("test_orca_wait", [S]),
    ("test_screenshot", [S]),  # dilewati bila Chrome, Chromium, atau Edge tidak ada
    ("test_orca_cli", [S]),  # dilewati bila Orca tidak terpasang
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
