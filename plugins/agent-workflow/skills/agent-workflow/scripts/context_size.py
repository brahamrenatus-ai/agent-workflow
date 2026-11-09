#!/usr/bin/env python3
"""Ukur konteks sesi Claude Code yang menjalankan skrip ini (agent-workflow, sejak v3.17).

Dijalankan head (atau skill dev di LITE) dari root project, di titik aman sesudah triase dan commit:
  python handoff/tools/context_size.py
  python handoff/tools/context_size.py --limit 150000

Claude Code memberi perintah yang dijalankannya variabel CLAUDE_CODE_SESSION_ID. Skrip mencari transkrip sesi itu
(`<CLAUDE_CONFIG_DIR atau ~/.claude>/projects/*/<id>.jsonl`), lalu membaca ukuran prompt pesan asisten terakhir:
input + cache_read + cache_creation. Angka itulah yang dibaca ulang setiap kali sesi bangun.

Output diawali satu kata:
- OK: konteks di bawah batas;
- LARGE: konteks melewati batas (bawaan 200 ribu token). Sarankan user menjalankan `/clear` lalu skill head, karena
  model tidak bisa menjalankan `/clear` sendiri. Ringkas otomatis bukan pengganti: sesudah diringkas, Claude Code
  hanya membawa 5.000 token pertama setiap skill;
- UNKNOWN: bukan sesi Claude Code, atau transkripnya tidak ditemukan.
Bila handoff/ROADMAP.md §1 (serah terima, sejak v3.18) lebih besar dari --handoff-limit KB, baris kedua diawali TIDY.
Bagian itu dibaca ulang setiap sesi head baru, dan tumbuh tiap serah terima bila ditulis sebagai catatan harian.
Kode keluar 0 untuk semua hasil ini (2 untuk argumen salah). Kata pembuka sebelum v3.20.1: AMAN, BESAR,
TIDAK DIKETAHUI, dan RAPIKAN.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

EKOR = 4 * 1024 * 1024  # transkrip bisa puluhan MB; pesan terakhir hampir selalu ada di bagian akhir


def folder_konfigurasi():
    dir_env = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(dir_env) if dir_env else Path.home() / ".claude"


def cari_transkrip(sesi):
    projects = folder_konfigurasi() / "projects"
    if not projects.is_dir():
        return None
    return next((p for p in projects.glob(f"*/{sesi}.jsonl") if p.is_file()), None)


def konteks_terakhir(path):
    """(token prompt pesan asisten terakhir, waktu pesan itu) atau (None, None)."""
    ukuran = path.stat().st_size
    with open(path, "rb") as f:
        for mulai in ([max(0, ukuran - EKOR), 0] if ukuran > EKOR else [0]):
            f.seek(mulai)
            baris = f.read().split(b"\n")
            if mulai:
                baris = baris[1:]  # baris pertama bisa terpotong
            for b in reversed(baris):
                if b'"usage"' not in b:
                    continue
                try:
                    e = json.loads(b)
                except ValueError:
                    continue
                u = (e.get("message") or {}).get("usage") if e.get("type") == "assistant" else None
                if isinstance(u, dict):
                    return (u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                            + u.get("cache_creation_input_tokens", 0)), e.get("timestamp", "")
    return None, None


def ribuan(n):
    return f"{n:,}".replace(",", ".")


def ukuran_serah_terima(path=Path("handoff") / "ROADMAP.md"):
    """Ukuran §1 ROADMAP dalam byte; None bila file atau bagiannya tidak ada. Nomor bagian netral bahasa."""
    if not path.is_file():
        return None
    m = re.search(r"^##\s*1\b[^\n]*\n(.*?)(?=^##\s|\Z)", path.read_text(encoding="utf-8", errors="replace"), re.M | re.S)
    return len(m.group(1).encode("utf-8")) if m else None


def ukur_konteks(limit):
    """Baris hasil ukur konteks sesi: diawali OK, LARGE, atau UNKNOWN."""
    sesi = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not sesi:
        return "UNKNOWN: variabel CLAUDE_CODE_SESSION_ID tidak ada (bukan dijalankan dari sesi Claude Code)."
    path = cari_transkrip(sesi)
    if not path:
        return f"UNKNOWN: transkrip sesi {sesi} tidak ditemukan di {folder_konfigurasi() / 'projects'}."
    token, waktu = konteks_terakhir(path)
    if token is None:
        return f"UNKNOWN: belum ada pesan asisten bertoken di {path.name}."
    rinci = f"konteks sesi ini {ribuan(token)} token (pesan terakhir {waktu[:19] or '?'}), batas {ribuan(limit)}"
    if token > limit:
        return (f"LARGE: {rinci}. Sesudah triase dan commit, sarankan user menjalankan /clear lalu skill head; "
                "keadaan ada di handoff/.")
    return f"OK: {rinci}."


def main():
    p = argparse.ArgumentParser(description="Ukur konteks sesi Claude Code yang menjalankan skrip ini.")
    p.add_argument("--limit", type=int, default=200000, help="batas saran sesi baru, dalam token (bawaan 200000)")
    p.add_argument("--handoff-limit", type=int, default=8, help="batas ROADMAP §1, dalam KB (bawaan 8)")
    args = p.parse_args()
    if args.limit <= 0:
        p.error("--limit harus lebih dari 0")
    if args.handoff_limit <= 0:
        p.error("--handoff-limit harus lebih dari 0")
    print(ukur_konteks(args.limit))
    serah = ukuran_serah_terima()
    if serah is not None and serah > args.handoff_limit * 1024:
        print(f"TIDY: ROADMAP §1 {(serah + 1023) // 1024} KB, batas {args.handoff_limit} KB. Tulis ulang sebagai keadaan terkini: "
              "yang selesai dihapus, keputusan ke register NOTES, item ke Backlog; riwayatnya tetap ada di git.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
