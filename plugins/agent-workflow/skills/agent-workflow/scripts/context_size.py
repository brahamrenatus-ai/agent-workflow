#!/usr/bin/env python3
"""Ukur konteks sesi Claude Code yang menjalankan skrip ini (agent-workflow, sejak v3.17).

Dijalankan head (atau skill dev di LITE) dari root project, di titik aman sesudah triase dan commit:
  python handoff/tools/context_size.py
  python handoff/tools/context_size.py --limit 150000

Claude Code memberi perintah yang dijalankannya variabel CLAUDE_CODE_SESSION_ID. Skrip mencari transkrip sesi itu
(`<CLAUDE_CONFIG_DIR atau ~/.claude>/projects/*/<id>.jsonl`), lalu membaca ukuran prompt pesan asisten terakhir:
input + cache_read + cache_creation. Angka itulah yang dibaca ulang setiap kali sesi bangun.

Output diawali satu kata:
- AMAN: konteks di bawah batas;
- BESAR: konteks melewati batas (bawaan 200 ribu token). Sarankan user menjalankan `/clear` lalu skill head, karena
  model tidak bisa menjalankan `/clear` sendiri. Ringkas otomatis bukan pengganti: sesudah diringkas, Claude Code
  hanya membawa 5.000 token pertama setiap skill;
- TIDAK DIKETAHUI: bukan sesi Claude Code, atau transkripnya tidak ditemukan.
Kode keluar 0 untuk ketiganya (2 untuk argumen salah).
"""
import argparse
import json
import os
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


def main():
    p = argparse.ArgumentParser(description="Ukur konteks sesi Claude Code yang menjalankan skrip ini.")
    p.add_argument("--limit", type=int, default=200000, help="batas saran sesi baru, dalam token (bawaan 200000)")
    args = p.parse_args()
    if args.limit <= 0:
        p.error("--limit harus lebih dari 0")
    sesi = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not sesi:
        print("TIDAK DIKETAHUI: variabel CLAUDE_CODE_SESSION_ID tidak ada (bukan dijalankan dari sesi Claude Code).")
        return 0
    path = cari_transkrip(sesi)
    if not path:
        print(f"TIDAK DIKETAHUI: transkrip sesi {sesi} tidak ditemukan di {folder_konfigurasi() / 'projects'}.")
        return 0
    token, waktu = konteks_terakhir(path)
    if token is None:
        print(f"TIDAK DIKETAHUI: belum ada pesan asisten bertoken di {path.name}.")
        return 0
    rinci = f"konteks sesi ini {ribuan(token)} token (pesan terakhir {waktu[:19] or '?'}), batas {ribuan(args.limit)}"
    if token > args.limit:
        print(f"BESAR: {rinci}. Sesudah triase dan commit, sarankan user menjalankan /clear lalu skill head; "
              "keadaan ada di handoff/.")
    else:
        print(f"AMAN: {rinci}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
