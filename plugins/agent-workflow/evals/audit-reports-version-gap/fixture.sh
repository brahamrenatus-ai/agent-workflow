#!/usr/bin/env bash
# Fixture: project kecil yang README-nya mengaku agent-workflow v3.17, tetapi file protokolnya hampir kosong.
# check_version.py memberi versi efektif "di bawah v2.1" dan menyarankan audit penuh.
set -euo pipefail
git init -q
mkdir -p handoff/tasks handoff/reports src .claude/skills/demo-head .claude/skills/demo-executor
cat > handoff/README.md <<'EOF'
# Handoff Demo: Protokol Head <-> Executor
> Dibuat dengan skill **agent-workflow v3.17** (bootstrap v3.10 2026-10-28).

- **Head:** `.claude/skills/demo-head/SKILL.md` (Claude Code: `/demo-head`).
- **Executor:** `.claude/skills/demo-executor/SKILL.md` (Claude Code).

## Alur
1. Head menulis task di `handoff/tasks/`.
2. Executor menulis report di `handoff/reports/`.
EOF
cat > handoff/ROADMAP.md <<'EOF'
# ROADMAP
## 1. Tertunda untuk Sesi Head Berikutnya
- (kosong)
## 3. Backlog
| ID | Jenis | Judul | Status |
|---|---|---|---|
| R1 | FIX | Validasi input kosong | BELUM |
EOF
cat > handoff/NOTES.md <<'EOF'
# NOTES
## 3. Register Keputusan
| Tanggal | Keputusan | Oleh |
|---|---|---|
EOF
cat > .claude/skills/demo-head/SKILL.md <<'EOF'
---
name: demo-head
description: Head project demo
---
# Head
Baca handoff/README.md, tulis task, triase report.
EOF
cat > .claude/skills/demo-executor/SKILL.md <<'EOF'
---
name: demo-executor
description: Executor project demo
---
# Executor
Kerjakan task, tulis report.
EOF
cat > src/hitung.py <<'EOF'
def tambah(a, b):
    return a + b
EOF
git add -A
git -c user.email=eval@example.com -c user.name=eval commit -qm "fixture: protokol demo"
