"""Jalankan semua uji skill agent-workflow dan cetak PASS/FAIL per uji.

Pemakaian (dari root repo): python tests/run_tests.py [folder skill]
Bawaan folder skill: plugins/agent-workflow/skills/agent-workflow. Butuh Python 3.9+ dan git di PATH.
Uji yang gagal dicetak dengan semua baris keluarannya selain baris lulus (OK/PASS), termasuk traceback utuh.
Di GitHub Actions (GITHUB_ACTIONS=true) setiap uji yang gagal juga dicetak sebagai anotasi ::error, yang
terbaca lewat API anotasi publik tanpa login (log job butuh login).
"""
import os
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
    ("test_identifiers", [S]),
    ("test_check_evidence", [S / "scripts" / "check_evidence.py"]),
    ("test_record", [S]),
    ("test_check_secrets", [S / "scripts" / "check_secrets.py"]),
    ("test_check_process_notes", [S]),
    ("test_redact_provenance", [S]),
    ("test_calibrate", [S]),
    ("test_orca_wait", [S]),
    ("test_context_size", [S]),
    ("test_head_restart", [S]),
    ("test_screenshot", [S]),  # dilewati bila Chrome, Chromium, atau Edge tidak ada
    ("test_orca_cli", [S]),  # dilewati bila Orca tidak terpasang
]
DI_ACTIONS = os.environ.get("GITHUB_ACTIONS") == "true"


def perintah_actions(teks, properti=False):
    """Escape teks untuk perintah alur kerja GitHub Actions; nilai properti (title) juga meng-escape ':' dan ','."""
    teks = teks.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return teks.replace(":", "%3A").replace(",", "%2C") if properti else teks


gagal = []
for nama, args in UJI:
    r = subprocess.run([sys.executable, "-X", "utf8", str(T / f"{nama}.py"), *map(str, args)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    baris = (r.stdout + r.stderr).splitlines()
    salah = [l for l in baris if l.startswith("FAIL") or "SOME FAILED" in l or "Traceback" in l]
    if r.returncode == 0 and not salah:
        ringkas = next((l for l in reversed(baris) if l.startswith("RESULT")), "")
        print(f"PASS   {nama}: {ringkas}")
        continue
    gagal.append(nama)
    # Semua baris selain baris lulus, supaya traceback tercetak utuh, bukan hanya baris pertamanya.
    rinci = [l for l in baris if l.strip() and not l.startswith(("OK", "PASS"))][-60:] or baris[-25:]
    print(f"FAIL   {nama} (exit {r.returncode})")
    print("\n".join("       " + l for l in rinci))
    if DI_ACTIONS:
        pesan = chr(10).join(rinci[-40:]) or "(no output)"
        print(f"::error title={perintah_actions(f'{nama} (exit {r.returncode})', True)}::{perintah_actions(pesan)}")
print(f"\n{'ALL TESTS PASSED' if not gagal else 'FAILED: ' + ', '.join(gagal)} ({len(UJI) - len(gagal)}/{len(UJI)})")
sys.exit(1 if gagal else 0)
