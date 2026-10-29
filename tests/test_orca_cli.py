"""Uji perintah Orca di teks skill terhadap Orca yang terpasang (sejak v3.11).

Setiap perintah `orca ...` di dalam backtick pada SKILL.md dan references/*.md dicocokkan dengan bantuan Orca:
subperintahnya harus dikenal (`orca <subperintah> --help` keluar 0 dan baris Usage-nya cocok), dan setiap opsi
`--...` yang ditulis harus muncul di bantuan subperintah itu. Ini menjaga aturan "perintah dicek jalan" untuk teks
skill sendiri saat Orca berganti versi.

Dilewati bila Orca tidak terpasang (mis. di CI). Di Linux, `orca` di luar terminal Orca biasanya pembaca layar GNOME,
jadi yang dipakai hanya ORCA_CLI_COMMAND atau `orca-ide`.
Pemakaian: python -X utf8 tests/test_orca_cli.py <folder skill>
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
SKILL = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "plugins/agent-workflow/skills/agent-workflow"
ok = True


def cek(cond, msg, out=""):
    global ok
    print(("OK    " if cond else "GAGAL ") + msg)
    if not cond and out:
        print("      " + out.strip().replace("\n", "\n      ")[:1500])
    ok = ok and cond


def lewat(alasan):
    print(f"LEWAT {alasan}")
    print("\nHASIL: SEMUA OK")
    sys.exit(0)


def cari_orca():
    if os.environ.get("ORCA_CLI_COMMAND"):
        return os.environ["ORCA_CLI_COMMAND"]
    if sys.platform.startswith("linux"):
        return shutil.which("orca-ide")
    return shutil.which("orca")


def jalan(orca, args):
    try:
        r = subprocess.run([orca, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return 99, str(e)
    return r.returncode, r.stdout + r.stderr


teks = "\n".join(p.read_text(encoding="utf-8") for p in [SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md"))])
perintah = sorted(set(re.findall(r"`(orca [^`]+)`", teks)))
if not perintah:
    lewat("tidak ada perintah Orca di teks skill (versi sebelum v3.11)")
orca = cari_orca()
if not orca:
    lewat("Orca tidak terpasang di mesin ini (di Linux hanya ORCA_CLI_COMMAND atau orca-ide yang dipakai)")
rc, versi = jalan(orca, ["--version"])
if rc != 0 or not re.fullmatch(r"\d+\.\d+\.\d+\S*", versi.strip()):
    lewat(f"'{orca} --version' bukan versi Orca: {versi.strip()[:80]!r}")
print(f"Orca {versi.strip()} ({orca}); {len(perintah)} perintah di teks skill")

bantuan = {}
for p in perintah:
    kata = []
    for t in p.split()[1:]:
        if not re.fullmatch(r"[a-z][a-z-]*", t):
            break
        kata.append(t)
    opsi = sorted(set(re.findall(r"(?<![\w-])(--[a-z][a-z-]*)", p)))
    kunci = " ".join(kata)
    if kunci not in bantuan:
        bantuan[kunci] = jalan(orca, [*kata, "--help"])
    rc, out = bantuan[kunci]
    usage = re.search(r"^Usage: orca ((?:[a-z][a-z-]* ?)+)", out, re.M)
    jalur = usage.group(1).split() if usage else []
    # Argumen posisi (mis. topik `orchestration` di `orca skills get orchestration`) boleh menyusul jalur Usage.
    cek(rc == 0 and jalur and kata[:len(jalur)] == jalur and len(kata) - len(jalur) <= 1,
        f"`orca {kunci}` dikenal Orca (Usage: orca {' '.join(jalur) or '-'})", out)
    kurang = [o for o in opsi if o not in out]
    cek(not kurang, f"opsi di `{p[:90]}` ada di bantuannya" + (f" (tidak ada: {', '.join(kurang)})" if kurang else ""))

# Kata kerja orchestration yang dirujuk tanpa awalan `orca` (mis. `worker-retain`) juga harus dikenal.
rc, out = jalan(orca, ["orchestration", "--help"])
verba = set(re.findall(r"^  ([a-z][a-z-]+) ", out, re.M))
dirujuk = set(re.findall(r"`(worker-[a-z]+|run-[a-z]+)\b", teks))
cek(rc == 0 and dirujuk <= verba, f"kata kerja orchestration yang dirujuk ({', '.join(sorted(dirujuk))}) dikenal Orca"
    + (f"; tidak dikenal: {sorted(dirujuk - verba)}" if dirujuk - verba else ""), out)
print("\nHASIL:", "SEMUA OK" if ok else "ADA YANG GAGAL")
sys.exit(0 if ok else 1)
