"""Uji penanda tampak~ di scripts/check_version.py (v3.8, K1/K2): instruksi head dan executor harus ada di folder skill
setiap tool yang tercatat di handoff/README.md. Kasus: tool head tidak tercatat, executor Antigravity + cadangan
Claude Code, dan head di dua tool.
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
    print(("OK    " if cond else "FAIL  ") + msg)
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
    # 1. Project lama sebelum v3.8: tool head tidak tercatat, instruksi hanya di .agents/skills
    p = tmp / "lama"
    proyek(p, "# Handoff\n- **Head agent** (perencana): Instruksi: `.agents/skills/lama-head/SKILL.md`.\n"
              "- **Executor** (pelaksana): Instruksi: `.agents/skills/lama-executor/SKILL.md`.\n\n## Profil Executor\n"
              "- Tool: Antigravity · Model: berganti per task\n",
           [".agents/skills/lama-head/SKILL.md", ".agents/skills/lama-executor/SKILL.md"])
    out, st, baris = jalan(p)
    cek(st["K1"] == "hilang" and "tool belum tercatat di README" in out, "Project lama lama: K1 hilang karena tool head tidak tercatat")
    cek(st["K2"] == "bukan-hilang" and "executor ditemukan di Antigravity" in baris, "Project lama lama: K2 ada (executor di Antigravity)")

    # 2. Project lama setelah README mencatat Claude Code, tetapi penunjuk .claude/skills belum ada
    (p / "handoff" / "README.md").write_text(
        "# Handoff\n- **Head:** `.agents/skills/lama-head/SKILL.md` · tool: Claude Code\n"
        "- **Executor:** `.agents/skills/lama-executor/SKILL.md`\n\n## Profil Executor\n- Tool: Antigravity\n", encoding="utf-8")
    out, st, baris = jalan(p)
    cek(st["K1"] == "hilang" and "tidak ditemukan di Claude Code (.claude/skills/*head*/SKILL.md)" in out,
        "Project lama + tool tercatat, tanpa penunjuk: K1 hilang dengan lokasi yang dicari")

    # 3. Penunjuk ditambahkan
    proyek_pointer = p / ".claude/skills/lama-head/SKILL.md"
    proyek_pointer.parent.mkdir(parents=True)
    proyek_pointer.write_text("---\nname: lama-head\n---\n", encoding="utf-8")
    out, st, baris = jalan(p)
    cek(st["K1"] == "bukan-hilang" and "head ditemukan di Claude Code" in baris, "Project lama + penunjuk: K1 ada")

    # 4. Cadangan: executor Antigravity + cadangan Claude Code; penunjuk Claude Code belum ada -> K2 hilang
    p = tmp / "cadangan"
    proyek(p, "# Handoff\n- **Head:** `.claude/skills/cadangan-head/SKILL.md` (Claude Code: `/cadangan-head`).\n"
              "- **Executor:** `.agents/skills/cadangan-executor/SKILL.md`.\n\n## Profil Executor\n"
              "- Tool utama: Antigravity. Cadangan: Claude Code.\n",
           [".claude/skills/cadangan-head/SKILL.md", ".agents/skills/cadangan-executor/SKILL.md"])
    out, st, baris = jalan(p)
    cek(st["K1"] == "bukan-hilang", "Cadangan: K1 ada (head kanonis di .claude/skills)")
    cek(st["K2"] == "hilang" and "executor tidak ditemukan di Claude Code" in baris, "Cadangan tanpa penunjuk executor: K2 hilang (Claude Code)")
    (p / ".claude/skills/cadangan-executor").mkdir(parents=True)
    (p / ".claude/skills/cadangan-executor/SKILL.md").write_text("---\nname: cadangan-executor\n---\n", encoding="utf-8")
    out, st, baris = jalan(p)
    cek(st["K2"] == "bukan-hilang" and "executor ditemukan di Claude Code, Antigravity" in baris, "Cadangan + penunjuk executor: K2 ada untuk kedua tool")

    # 5. Dua tool: head disebut di Claude Code dan Antigravity
    p = tmp / "duatool"
    proyek(p, "# Handoff\n- **Head:** `.agents/skills/duatool-head/SKILL.md` (`/duatool-head` di Claude Code dan Antigravity).\n"
              "- **Executor:** `.agents/skills/duatool-executor/SKILL.md` (Antigravity: `/duatool-executor`).\n\n"
              "## Profil Executor\n- Tool: Antigravity.\n",
           [".agents/skills/duatool-head/SKILL.md", ".claude/skills/duatool-head/SKILL.md", ".agents/skills/duatool-executor/SKILL.md"])
    out, st, baris = jalan(p)
    cek(st["K1"] == "bukan-hilang" and "head ditemukan di Claude Code, Antigravity" in baris, "Dua tool: K1 ada untuk kedua tool")

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
print("\nRESULT:", "ALL OK" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
