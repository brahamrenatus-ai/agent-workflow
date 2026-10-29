"""Uji penanda tampak~ di scripts/check_version.py (v3.8, K1/K2): instruksi head dan executor harus ada di folder skill
setiap tool yang tercatat di handoff/README.md. Kasus diambil dari project lapangan: robot meja (tool head tidak tercatat), aplikasi budidaya
(executor Antigravity + cadangan Claude Code), dan IoT SCADA (head di dua tool).
Pemakaian: python -X utf8 tests/test_check_version_visible.py <folder skill>"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".claude/skills/agent-workflow").resolve()
CV = SKILL / "scripts" / "check_version.py"
ok = True


def cek(cond, msg):
    global ok
    print(("OK    " if cond else "GAGAL ") + msg)
    ok = ok and cond


def proyek(root, readme, files):
    (root / "handoff").mkdir(parents=True)
    (root / "handoff" / "README.md").write_text(readme, encoding="utf-8")
    for f in files:
        p = root / f
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("---\nname: x\n---\n", encoding="utf-8")


def jalan(root):
    out = subprocess.run([sys.executable, str(CV)], cwd=root, capture_output=True, text=True, encoding="utf-8").stdout
    status = {}
    for pid in ("K1", "K2"):
        status[pid] = "hilang" if re.search(rf"^  - {pid} \(v3\.8\)", out, re.M) else "bukan-hilang"
    baris = next((l for l in out.splitlines() if l.startswith("Instruksi peran per tool")), "")
    return out, status, baris


tmp = Path(tempfile.mkdtemp(prefix="tampak_"))
try:
    # 1. Robot meja sebelum v3.8: tool head tidak tercatat, instruksi hanya di .agents/skills
    p = tmp / "robot"
    proyek(p, "# Handoff\n- **Head agent** (perencana): Instruksi: `.agents/skills/robot-head/SKILL.md`.\n"
              "- **Executor** (pelaksana): Instruksi: `.agents/skills/robot-executor/SKILL.md`.\n\n## Profil Executor\n"
              "- Tool: Antigravity · Model: berganti per task\n",
           [".agents/skills/robot-head/SKILL.md", ".agents/skills/robot-executor/SKILL.md"])
    out, st, baris = jalan(p)
    cek(st["K1"] == "hilang" and "tool belum tercatat di README" in out, "Robot meja lama: K1 hilang karena tool head tidak tercatat")
    cek(st["K2"] == "bukan-hilang" and "executor ditemukan di Antigravity" in baris, "Robot meja lama: K2 ada (executor di Antigravity)")

    # 2. Robot meja setelah README mencatat Claude Code, tetapi penunjuk .claude/skills belum ada
    (p / "handoff" / "README.md").write_text(
        "# Handoff\n- **Head:** `.agents/skills/robot-head/SKILL.md` · tool: Claude Code\n"
        "- **Executor:** `.agents/skills/robot-executor/SKILL.md`\n\n## Profil Executor\n- Tool: Antigravity\n", encoding="utf-8")
    out, st, baris = jalan(p)
    cek(st["K1"] == "hilang" and "tidak ditemukan di Claude Code (.claude/skills/*head*/SKILL.md)" in out,
        "Robot meja + tool tercatat, tanpa penunjuk: K1 hilang dengan lokasi yang dicari")

    # 3. Penunjuk ditambahkan
    proyek_pointer = p / ".claude/skills/robot-head/SKILL.md"
    proyek_pointer.parent.mkdir(parents=True)
    proyek_pointer.write_text("---\nname: robot-head\n---\n", encoding="utf-8")
    out, st, baris = jalan(p)
    cek(st["K1"] == "bukan-hilang" and "head ditemukan di Claude Code" in baris, "Robot meja + penunjuk: K1 ada")

    # 4. Budidaya: executor Antigravity + cadangan Claude Code; penunjuk Claude Code belum ada -> K2 hilang
    p = tmp / "budidaya"
    proyek(p, "# Handoff\n- **Head:** `.claude/skills/budidaya-head/SKILL.md` (Claude Code: `/budidaya-head`).\n"
              "- **Executor:** `.agents/skills/budidaya-executor/SKILL.md`.\n\n## Profil Executor\n"
              "- Tool utama: Antigravity. Cadangan: Claude Code.\n",
           [".claude/skills/budidaya-head/SKILL.md", ".agents/skills/budidaya-executor/SKILL.md"])
    out, st, baris = jalan(p)
    cek(st["K1"] == "bukan-hilang", "Budidaya: K1 ada (head kanonis di .claude/skills)")
    cek(st["K2"] == "hilang" and "executor tidak ditemukan di Claude Code" in baris, "Budidaya tanpa penunjuk executor: K2 hilang (Claude Code)")
    (p / ".claude/skills/budidaya-executor").mkdir(parents=True)
    (p / ".claude/skills/budidaya-executor/SKILL.md").write_text("---\nname: budidaya-executor\n---\n", encoding="utf-8")
    out, st, baris = jalan(p)
    cek(st["K2"] == "bukan-hilang" and "executor ditemukan di Claude Code, Antigravity" in baris, "Budidaya + penunjuk executor: K2 ada untuk kedua tool")

    # 5. SCADA: head disebut di Claude Code dan Antigravity
    p = tmp / "scada"
    proyek(p, "# Handoff\n- **Head:** `.agents/skills/scada-head/SKILL.md` (`/scada-head` di Claude Code dan Antigravity).\n"
              "- **Executor:** `.agents/skills/scada-executor/SKILL.md` (Antigravity: `/scada-executor`).\n\n"
              "## Profil Executor\n- Tool: Antigravity.\n",
           [".agents/skills/scada-head/SKILL.md", ".claude/skills/scada-head/SKILL.md", ".agents/skills/scada-executor/SKILL.md"])
    out, st, baris = jalan(p)
    cek(st["K1"] == "bukan-hilang" and "head ditemukan di Claude Code, Antigravity" in baris, "SCADA: K1 ada untuk kedua tool")

    # 6. Tanpa handoff/README.md: n/a, bukan hilang
    p = tmp / "lite"
    p.mkdir()
    out, st, baris = jalan(p)
    cek(st["K1"] == "bukan-hilang" and st["K2"] == "bukan-hilang" and "handoff/README.md tidak ada" in baris, "Tanpa README: K1/K2 n/a")

    # 7. Tool yang tidak dikenali (mis. Cline) tidak diperiksa: tetap dianggap belum tercatat untuk head
    p = tmp / "cline"
    proyek(p, "# Handoff\n- **Head:** `.clinerules` (Cline)\n\n## Profil Executor\n- Tool: Cline\n", [])
    out, st, baris = jalan(p)
    cek(st["K1"] == "hilang" and "tool belum tercatat" in out, "Tool tak dikenali: dilaporkan sebagai belum tercatat (cek manual)")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("\nHASIL:", "SEMUA OK" if ok else "ADA YANG GAGAL")
sys.exit(0 if ok else 1)
