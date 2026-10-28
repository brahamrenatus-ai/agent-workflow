#!/usr/bin/env python3
"""Cek secret di file sebelum commit, tanpa mencetak nilainya.

Skill agent-workflow memasang skrip ini ke handoff/tools/cek_secret.py. Isi SECRET_FILES di bawah
dengan file secret lokal project (yang di-ignore git). Bila daftar itu kosong, skrip mencari sendiri
file secret yang lazim (secrets.h, .env, secrets.json, ...).

Yang dicari:
1. Nilai asli dari file secret lokal: #define dan konstanta string C/C++, KEY=VALUE (.env), serta
   nilai string JSON/YAML/TOML sederhana. Yang dilewati:
   - nilai < 8 karakter;
   - nama yang bukan rahasia (SSID, HOST, PORT, USER, ...), termasuk URL tanpa user:password@;
   - placeholder, yaitu nilai yang sama dengan file contoh di sebelahnya, berbentuk
     HURUF_BESAR_SAJA, atau berisi kata seperti "your", "example", "changeme".
2. Pola umum: refresh/access token, header Authorization, JWT, kunci API Google, AWS access key,
   token GitHub/Slack, token bot Telegram (juga di URL api.telegram.org/bot<token>), kunci live Stripe,
   kunci "sk-..." panjang, dan private key.

Scan pola saja tidak cukup: token tanpa awalan khas (mis. refresh token Spotify) akan lolos.

Pemakaian (folder, file, atau pola glob; glob diproses skrip ini, jadi aman di PowerShell):
  python handoff/tools/cek_secret.py handoff/logs
  python handoff/tools/cek_secret.py handoff/logs/x.log --redact   # ganti temuan dengan <REDACTED>
  python handoff/tools/cek_secret.py --staged                      # file yang di-stage untuk commit
  python handoff/tools/cek_secret.py --list-sources                # file secret yang terbaca, tanpa nilai

Log yang tercatat di handoff/logs/asal.jsonl (dibuat catat.py) dan disamarkan dengan --redact mendapat catatan
asal baru berjenis "redact", supaya cek_bukti.py tidak menandainya "berubah setelah dicatat". Catatan itu hanya
ditambahkan bila isi log sebelum disamarkan masih sama dengan catatan terakhirnya, jadi log yang diedit tangan
tidak ikut disahkan.

Exit code: 0 = bersih (atau semua temuan sudah disamarkan), 1 = ada temuan, 2 = salah pakai.
"""
import argparse
import fnmatch
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Diisi saat dipasang: path file secret lokal, relatif terhadap root repo, mis. ["include/secrets.h", ".env"].
SECRET_FILES = []

REDACTED = "<REDACTED>"
LEWATI_FOLDER = {".git", ".pio", "node_modules", ".venv", "venv", "__pycache__", "build", "dist", ".next"}
NAMA_CALON = ["secrets.h", "secrets.hpp", "secret*.h", ".env", ".env.*", "*.env",
              "secrets.json", "secrets.yaml", "secrets.yml", "secrets.toml", "credentials.json"]
NAMA_CONTOH = re.compile(r"(example|sample|template|contoh)", re.I)
BUKAN_RAHASIA = re.compile(r"(SSID|HOST|PORT|REGION|ENDPOINT|DOMAIN|(^|_)USER(NAME)?$|(^|_)NAME$|(^|_)MODE$|"
                           r"(^|_)ENV$|DEBUG|LEVEL|TIMEOUT)", re.I)
URL_TANPA_KREDENSIAL = re.compile(r"^(?!.*://[^/\s:@]+:[^/\s@]+@)")  # URL tanpa user:password@ bukan rahasia
PLACEHOLDER = re.compile(r"(your|xxx|changeme|example|placeholder|masukkan|ganti|isi_|dummy|todo|<|>|\.\.\.)", re.I)
MAKS_UKURAN = 100 * 1024 * 1024
ASAL = Path("handoff") / "logs" / "asal.jsonl"

_TB = r"(?<![A-Za-z0-9_\-])"  # batas token: jangan cocok di tengah kata (mis. "task-...")
POLA = [
    ("refresh/access token", re.compile(r"(?:refresh|access|id)_token[\"']?\s*[=:]\s*[\"']?(?P<s>[A-Za-z0-9_\-.]{20,})")),
    ("header Authorization", re.compile(r"Authorization:\s*(?:Bearer|Basic|Token)\s+(?P<s>[A-Za-z0-9+/=_\-.]{20,})", re.I)),
    ("JWT", re.compile(_TB + r"(?P<s>eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,})")),
    ("kunci API Google", re.compile(_TB + r"(?P<s>AIza[0-9A-Za-z_\-]{35})")),
    ("AWS access key", re.compile(_TB + r"(?P<s>(?:AKIA|ASIA)[0-9A-Z]{16})(?![0-9A-Z])")),
    ("token GitHub", re.compile(_TB + r"(?P<s>gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{40,})")),
    ("token Slack", re.compile(_TB + r"(?P<s>xox[abprs]-[A-Za-z0-9-]{10,})")),
    # Format gitleaks: <id bot>:A + 34 karakter. Awalan "bot" diizinkan karena httpx mencatat URL Bot API utuh.
    ("token bot Telegram", re.compile(r"(?:(?<=bot)|" + _TB + r")(?P<s>\d{5,16}:A[A-Za-z0-9_\-]{34})(?![A-Za-z0-9_\-])")),
    ("kunci live Stripe", re.compile(_TB + r"(?P<s>(?:sk|rk)_live_[0-9A-Za-z]{20,})")),
    ("kunci API sk-...", re.compile(_TB + r"(?P<s>sk-(?:ant-|proj-)?[A-Za-z0-9_\-]{32,})")),
    ("private key", re.compile(r"(?P<s>-----BEGIN [A-Z ]*PRIVATE KEY-----)")),
]

RX_DEFINE = re.compile(r'^\s*#\s*define\s+([A-Za-z_]\w*)\s+"([^"]*)"', re.M)
RX_ASSIGN = re.compile(r'\b([A-Za-z_]\w*)\s*(?:\[\s*\])?\s*=\s*"([^"]*)"')
RX_ENV = re.compile(r'^\s*(?:export\s+)?([A-Za-z_]\w*)\s*=\s*(.*?)\s*$', re.M)
RX_YAML = re.compile(r'^\s*([A-Za-z_][\w.\-]*)\s*:\s*["\']?([^"\'#\n]+?)["\']?\s*(?:#.*)?$', re.M)


def siapkan_output():
    """Konsol Windows (cp1252) tidak boleh membuat skrip crash; output ke pipa/agen memakai UTF-8."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace") if s.isatty() else s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def root_repo():
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except OSError:
        pass
    return Path.cwd()


def di_ignore(root, path):
    try:
        return subprocess.run(["git", "-C", str(root), "check-ignore", "-q", str(path)], capture_output=True).returncode == 0
    except OSError:
        return True


def pasangan(path):
    """(nama, nilai) dari satu file secret. Isi file tidak pernah dicetak."""
    teks = path.read_text(encoding="utf-8", errors="replace")
    nama = path.name.lower()
    if nama.endswith(".json"):
        hasil = []

        def jalan(o, kunci=""):
            if isinstance(o, dict):
                for k, v in o.items():
                    jalan(v, str(k))
            elif isinstance(o, list):
                for v in o:
                    jalan(v, kunci)
            elif isinstance(o, str):
                hasil.append((kunci, o))
        try:
            jalan(json.loads(teks))
        except ValueError:
            print(f"PERINGATAN: {path} tidak bisa dibaca sebagai JSON; nilainya tidak dicek.")
        return hasil
    if nama.endswith((".yaml", ".yml")):
        return RX_YAML.findall(teks)
    if nama.startswith(".env") or nama.endswith(".env"):
        hasil = []
        for k, v in RX_ENV.findall(teks):
            if k.startswith("#"):
                continue
            v = re.sub(r"\s+#.*$", "", v).strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            hasil.append((k, v))
        return hasil
    return RX_DEFINE.findall(teks) + RX_ASSIGN.findall(teks)


def file_contoh(path):
    """File contoh di sebelah file secret, mis. .env.example atau secrets.example.h."""
    dasar = path.name.split(".")[0] or path.name
    return [p for p in path.parent.iterdir()
            if p != path and p.is_file() and NAMA_CONTOH.search(p.name) and (dasar.lower() in p.name.lower() or p.name.startswith(".env"))]


def sumber_secret(root, tambahan):
    daftar = [root / f for f in SECRET_FILES] + [Path(f) for f in tambahan]
    otomatis = not daftar
    if otomatis:
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d not in LEWATI_FOLDER]
            daftar += [Path(dp) / f for f in fns
                       if not NAMA_CONTOH.search(f) and any(fnmatch.fnmatch(f, pola) for pola in NAMA_CALON)]
    sumber = []
    for p in daftar:
        if not p.is_file():
            print(f"PERINGATAN: file secret {p} tidak ada; dilewati.")
            continue
        if not di_ignore(root, p):
            print(f"PERINGATAN: {p} tampak seperti file secret tetapi TIDAK di-ignore git.")
        contoh = {v for c in file_contoh(p) for _, v in pasangan(c)}
        nilai = []
        for k, v in pasangan(p):
            if re.search(r"(URL|URI)$", k, re.I) and URL_TANPA_KREDENSIAL.match(v):
                continue
            if (len(v) < 8 or BUKAN_RAHASIA.search(k) or v in contoh or PLACEHOLDER.search(v)
                    or re.fullmatch(r"[A-Z][A-Z0-9]*_[A-Z0-9_]*", v)):
                continue
            nilai.append((k, v))
        sumber.append((p, nilai))
    return sumber, otomatis


def kumpulkan(root, paths, staged, lewati):
    calon = []
    if staged:
        out = subprocess.run(["git", "-C", str(root), "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                             capture_output=True, text=True, encoding="utf-8").stdout
        calon += [root / p for p in out.splitlines() if p]
    for a in paths:
        if any(c in a for c in "*?["):
            calon += [Path(p) for p in glob.glob(a, recursive=True)]
        elif os.path.isdir(a):
            for dp, dns, fns in os.walk(a):
                dns[:] = [d for d in dns if d not in LEWATI_FOLDER]
                calon += [Path(dp) / f for f in fns]
        else:
            calon.append(Path(a))
    unik, hasil = set(lewati), []
    for f in calon:
        r = f.resolve()
        if r in unik or not r.is_file():
            continue
        unik.add(r)
        hasil.append(f)
    return hasil


def hash_isi(path):
    """SHA-256 isi file dengan CRLF disamakan menjadi LF (sama persis dengan catat.py dan cek_bukti.py)."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def perbarui_asal(root, path, sebelum):
    """Log dari catat.py yang baru disamarkan mendapat catatan asal berjenis redact (perintah asal tetap dicatat).
    Hanya bila hash isi sebelum disamarkan sama dengan catatan terakhirnya: log yang diedit tangan tidak ikut disahkan."""
    asal = root / ASAL
    try:
        rel = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return
    if not asal.is_file():
        return
    terakhir = None
    for l in asal.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rec = json.loads(l)
        except ValueError:
            continue
        if isinstance(rec, dict) and str(rec.get("file", "")).replace("\\", "/").lower() == rel.lower():
            terakhir = rec
    if terakhir is None:
        return
    if terakhir.get("sha256") != sebelum:
        print(f"PERINGATAN: {rel} sudah berubah setelah dicatat catat.py, jadi catatan asalnya tidak diperbarui "
              "(cek_bukti.py tetap menandainya). Jalankan ulang perintahnya lewat catat.py.")
        return
    rec = dict(terakhir, jenis="redact", sha256=hash_isi(path), sha256_sebelum=sebelum,
               disamarkan=datetime.now().isoformat(timespec="seconds"))
    with open(asal, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"{rel}: catatan asal redact ditambahkan; git add ulang {ASAL.as_posix()} bersama log ini.")


def periksa(path, values, redact, root):
    """Cetak file:baris + jenis temuan, dengan nilai disamarkan. Kembalikan jumlah baris bertemuan."""
    if path.stat().st_size > MAKS_UKURAN:
        print(f"PERINGATAN: {path} lebih dari 100 MB; dilewati.")
        return 0
    data = path.read_bytes()
    if b"\0" in data[:8192]:
        return 0  # file biner
    teks = data.decode("utf-8", errors="surrogateescape")
    keluar, jumlah = [], 0
    for no, baris in enumerate(teks.splitlines(keepends=True), 1):
        jenis, baru = [], baris
        for nama, v in values:
            if v in baru:
                jenis.append(f"nilai {nama}")
                baru = baru.replace(v, REDACTED)
        for label, rx in POLA:
            def ganti(m, label=label):
                jenis.append(label)
                a, b = m.start("s") - m.start(), m.end("s") - m.start()
                return m.group(0)[:a] + REDACTED + m.group(0)[b:]
            baru = rx.sub(ganti, baru)
        if jenis:
            jumlah += 1
            cuplikan = baru.strip().encode("utf-8", errors="replace").decode("utf-8")[:120]
            print(f"{path}:{no}: {', '.join(sorted(set(jenis)))} | {cuplikan}")
        keluar.append(baru)
    if redact and jumlah:
        sebelum = hash_isi(path)
        path.write_bytes("".join(keluar).encode("utf-8", errors="surrogateescape"))
        perbarui_asal(root, path, sebelum)
    return jumlah


def main():
    ap = argparse.ArgumentParser(description="Cek secret di file tanpa mencetak nilainya.")
    ap.add_argument("paths", nargs="*", help="file, folder, atau pola glob")
    ap.add_argument("--staged", action="store_true", help="cek file yang di-stage untuk commit")
    ap.add_argument("--redact", action="store_true", help="ganti temuan dengan <REDACTED> di file")
    ap.add_argument("--secret-file", action="append", default=[], help="file secret tambahan (bisa berulang)")
    ap.add_argument("--list-sources", action="store_true", help="tampilkan file secret yang terbaca, tanpa nilai")
    a = ap.parse_args()
    siapkan_output()
    root = root_repo()
    sumber, otomatis = sumber_secret(root, a.secret_file)
    if a.list_sources:
        asal = "dicari otomatis" if otomatis else "dari SECRET_FILES/--secret-file"
        print(f"Root: {root} | file secret ({asal}): {len(sumber)}")
        for p, nilai in sumber:
            print(f"  {p}: {len(nilai)} nilai dicek ({', '.join(k for k, _ in nilai) or '-'})")
        return 0
    if not a.paths and not a.staged:
        ap.print_usage()
        return 2
    if not sumber:
        print("PERINGATAN: tidak ada file secret yang terbaca; hanya pola umum yang dicek.")
    values = [kv for _, nilai in sumber for kv in nilai]
    lewati = {p.resolve() for p, _ in sumber}
    files = kumpulkan(root, a.paths, a.staged, lewati)
    total = sum(periksa(f, values, a.redact, root) for f in files)
    akhir = " (sudah disamarkan; jangan lupa git add ulang)" if a.redact and total else ""
    print(f"{len(files)} file dicek, {total} baris bertemuan{akhir}.")
    return 1 if total and not a.redact else 0


if __name__ == "__main__":
    sys.exit(main())
