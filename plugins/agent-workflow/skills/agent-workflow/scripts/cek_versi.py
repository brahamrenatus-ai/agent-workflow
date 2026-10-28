#!/usr/bin/env python3
"""Cek versi protokol agent-workflow di sebuah project.

Dijalankan dari root project, langsung dari folder skill (skrip ini tidak disalin ke project):
  python <folder skill>/scripts/cek_versi.py

Skrip ini:
- membaca penanda versi `agent-workflow vX` di handoff/README.md (atau skill <prefix>-dev untuk LITE);
- memeriksa setiap penanda di blok `penanda` pada references/changelog.md;
- memeriksa apakah instruksi head dan executor ada di folder skill setiap tool yang tercatat di README
  (penanda `tampak~`; hanya Claude Code dan Antigravity yang dikenali);
- mencetak penanda yang hilang, yang menjadi kandidat patch untuk jalur upgrade AUDIT.

Penanda teks dianggap ada bila teksnya ditemukan, atau bila file sasarannya memuat tag `<!-- aw: ID -->` dengan ID
penanda itu. Tag ikut tersalin dari template, jadi aturan tetap dikenali walau protokol ditulis dalam bahasa lain.

Penanda yang file sasarannya tidak ada (mis. instruksi executor di project LITE) dicatat "n/a", bukan "hilang".
Penanda bersyarat juga "n/a" bila syaratnya tidak terpenuhi: `@bila_secret` (project punya file secret lokal) dan
`@bila_ui` (project punya antarmuka pengguna: web, mobile, atau desktop).
Exit code: 0 = semua penanda yang berlaku ada, 1 = ada yang hilang.
"""
import fnmatch
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parent.parent / "references" / "changelog.md"
PERAN = {
    "head": ["*/skills/*head*/SKILL.md", "*/workflows/*head*.md"],
    "executor": ["*/skills/*executor*/SKILL.md", "*/workflows/*executor*.md", ".clinerules", "CONVENTIONS.md", "AGENTS.md", "GEMINI.md"],
    "dev": ["*/skills/*-dev/SKILL.md"],
    "readme": ["handoff/README.md"],
    "roadmap": ["handoff/ROADMAP.md"],
    "notes": ["handoff/NOTES.md"],
}
NAMA_SECRET = ["secrets.h", "secrets.hpp", "secret*.h", ".env", ".env.*", "*.env", "secrets.json", "secrets.yaml",
               "secrets.yml", "secrets.toml", "credentials.json"]
LEWATI = {".git", ".pio", "node_modules", ".venv", "venv", "__pycache__", "build", "dist", ".next", "graphify-out"}
# Tanda project ber-UI (syarat @bila_ui): dependensi framework antarmuka di package.json, atau file khas UI.
UI_NPM = {"react", "react-dom", "vue", "svelte", "@sveltejs/kit", "@angular/core", "next", "nuxt", "solid-js", "preact",
          "electron", "astro", "lit", "@ionic/core", "react-native", "expo", "vite"}
UI_FILE = ["*.html", "*.vue", "*.svelte", "*.jsx", "*.tsx", "*.xaml", "*.storyboard", "*.qml", "*.ui",
           "AndroidManifest.xml"]
TAG = re.compile(r"<!--\s*aw:([^>]*?)-->", re.I)
# Folder yang dipindai tiap tool untuk menemukan instruksi peran (SKILL.md §3, Lokasi instruksi per tool).
TOOL_PERAN = {
    "Claude Code": [".claude/skills/*{peran}*/SKILL.md"],
    "Antigravity": [".agents/skills/*{peran}*/SKILL.md", ".agent/skills/*{peran}*/SKILL.md", ".agent/workflows/*{peran}*.md"],
}
# Baris README yang mencatat tool tiap peran: baris Head di kepala; baris Executor dan Tool di Profil Executor.
BARIS_TOOL = {
    "head": r"^\s*-\s*\*\*Head\b",
    "executor": r"^\s*-\s*(\*\*Executor\b|Tool\b[^:]{0,12}:)",
}


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


def file_peran(root, peran):
    hasil = []
    for pola in PERAN[peran]:
        if "*/" in pola:
            hasil += [Path(p) for p in glob.glob(str(root / ".*" / pola.split("*/", 1)[1]))]
            hasil += [Path(p) for p in glob.glob(str(root / pola))]
        elif (root / pola).is_file():
            hasil.append(root / pola)
    return sorted({p for p in hasil if p.is_file()})


def baca(p):
    return p.read_text(encoding="utf-8", errors="replace").lower()


def jelajah(root, lewati=()):
    """(folder, nama file) di project, tanpa folder hasil build/dependensi (dan folder di `lewati`)."""
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in LEWATI and d not in lewati]
        for f in fns:
            yield dp, f


def ada_file_secret(root):
    for _, f in jelajah(root):
        if re.search(r"(example|sample|template|contoh)", f, re.I):
            continue
        if any(fnmatch.fnmatch(f, pola) for pola in NAMA_SECRET):
            return True
    return False


def ada_ui(root):
    """True bila project punya antarmuka pengguna: framework UI di package.json, Flutter, atau file khas UI.
    Folder handoff/ dilewati, karena log dan report di sana bukan bagian dari produk."""
    for dp, f in jelajah(root, {"handoff"}):
        if f == "package.json":
            try:
                pkg = json.loads(Path(dp, f).read_text(encoding="utf-8", errors="replace"))
            except ValueError:
                continue
            deps = {k for bagian in ("dependencies", "devDependencies") for k in (pkg.get(bagian) or {})}
            if deps & UI_NPM:
                return True
        elif f == "pubspec.yaml" and re.search(r"^\s*flutter\s*:", Path(dp, f).read_text(encoding="utf-8", errors="replace"), re.M):
            return True
        elif any(fnmatch.fnmatch(f, pola) for pola in UI_FILE):
            return True
    return False


def cocok(teks, isi):
    teks = teks.strip()
    if teks.startswith("re:"):
        return re.search(teks[3:], isi, re.I) is not None
    return teks.lower() in isi


def punya_tag(isi, pid):
    """True bila isi memuat tag `<!-- aw: ... -->` yang menyebut ID penanda ini."""
    return any(pid.lower() in re.split(r"[\s,]+", m.group(1).strip().lower()) for m in TAG.finditer(isi))


def tampak(root, peran):
    """('ada' / 'hilang' / 'n/a', catatan): instruksi peran ada di folder skill setiap tool yang tercatat di README."""
    readme = root / "handoff" / "README.md"
    if not readme.is_file():
        return "n/a", "handoff/README.md tidak ada"
    baris = [l for l in readme.read_text(encoding="utf-8", errors="replace").splitlines() if re.match(BARIS_TOOL[peran], l, re.I)]
    teks = " ".join(baris).lower()
    tools = [t for t in TOOL_PERAN if t.lower() in teks]
    if not tools:
        return "hilang", "tool belum tercatat di README"
    kurang = [t for t in tools if not any(glob.glob(str(root / pola.format(peran=peran))) for pola in TOOL_PERAN[t])]
    if kurang:
        return "hilang", "tidak ditemukan di " + ", ".join(f"{t} ({TOOL_PERAN[t][0].format(peran=peran)})" for t in kurang)
    return "ada", "ditemukan di " + ", ".join(tools)


def nilai_spec(root, spec, pid=""):
    """'ada' / 'hilang' / 'n/a' untuk satu penanda; teks juga dianggap ada bila file sasaran memuat tag ID-nya."""
    spec = spec.strip()
    if spec.startswith("tampak~"):
        return tampak(root, spec[7:].strip())[0]
    if spec.startswith("ada~"):
        return "ada" if (root / spec[4:].strip()).exists() else "hilang"
    if spec.startswith("file:"):
        path, teks = spec[5:].split("~", 1)
        p = root / path.strip()
        if not p.is_file():
            return "n/a"
        isi = baca(p)
        return "ada" if cocok(teks, isi) or (pid and punya_tag(isi, pid)) else "hilang"
    peran, teks = spec.split("~", 1)
    files = file_peran(root, peran.strip())
    if not files:
        return "n/a"
    return "ada" if any(cocok(teks, isi) or (pid and punya_tag(isi, pid)) for isi in map(baca, files)) else "hilang"


def muat_changelog():
    teks = CHANGELOG.read_text(encoding="utf-8")
    blok = re.search(r"```penanda\n(.*?)\n```", teks, re.S).group(1)
    label = dict(re.findall(r"^\|\s*([A-Z]\d*-?\d+)\s*\|\s*([^|]+?)\s*\|", teks, re.M))
    baris = []
    for l in blok.splitlines():
        if not l.strip() or l.lstrip().startswith("#"):
            continue
        versi, pid, sisa = l.split(None, 2)
        syarat = set(re.findall(r"@(bila_\w+)", sisa))
        specs = [s for s in re.sub(r"@bila_\w+", "", sisa).split("||") if s.strip()]
        baris.append((versi, pid, specs, syarat, label.get(pid, "")))
    return baris


def kunci_versi(v):
    return tuple(int(x) for x in v.split("."))


def main():
    siapkan_output()
    root = root_repo()
    penanda = muat_changelog()
    kondisi = {"bila_secret": ada_file_secret(root), "bila_ui": ada_ui(root)}
    tertulis = None
    for f in file_peran(root, "readme") + file_peran(root, "dev"):
        m = re.search(r"agent-workflow v(\d+(?:\.\d+)*)", f.read_text(encoding="utf-8", errors="replace"))
        if m:
            tertulis = m.group(1)
            break
    print(f"Root: {root}")
    print(f"Penanda versi tertulis: {'v' + tertulis if tertulis else 'tidak ada'} | file secret lokal: "
          f"{'ada' if kondisi['bila_secret'] else 'tidak ada'} | UI: {'ada' if kondisi['bila_ui'] else 'tidak ada'}")
    per_versi, hilang = {}, []
    for versi, pid, specs, syarat, lab in penanda:
        if not all(kondisi.get(s, True) for s in syarat):
            status = "n/a"
        else:
            hasil = [nilai_spec(root, s, pid) for s in specs]
            status = "ada" if "ada" in hasil else ("hilang" if "hilang" in hasil else "n/a")
        per_versi.setdefault(versi, []).append((pid, status, lab))
        if status == "hilang":
            catatan = [tampak(root, s.strip()[7:].strip())[1] for s in specs if s.strip().startswith("tampak~")]
            hilang.append((versi, pid, lab + (f" [{'; '.join(catatan)}]" if catatan else "")))
    urut = sorted(per_versi, key=kunci_versi)
    for versi in urut:
        rows = per_versi[versi]
        ok = sum(s == "ada" for _, s, _ in rows)
        berlaku = sum(s != "n/a" for _, s, _ in rows)
        kurang = [p for p, s, _ in rows if s == "hilang"]
        print(f"  v{versi:<5} {ok}/{berlaku} penanda" + (f" | hilang: {', '.join(kurang)}" if kurang else ""))
    efektif = None
    for versi in urut:
        if any(s == "hilang" for _, s, _ in per_versi[versi]):
            break
        efektif = versi
    if efektif:
        print(f"Versi efektif: v{efektif} (semua penanda sampai versi ini ada)")
    else:
        dasar = [p for p, s, _ in per_versi.get(urut[0], []) if s == "hilang"] if urut else []
        saran = "patch per baris masih tepat" if len(dasar) <= 2 else "audit penuh (SKILL.md §4) lebih tepat daripada upgrade per baris"
        print(f"Versi efektif: di bawah v{urut[0] if urut else '2.1'} (penanda dasar hilang: {', '.join(dasar) or '-'}); {saran}.")
    print("Instruksi peran per tool (README): " + "; ".join(f"{p} {tampak(root, p)[1]}" for p in ("head", "executor")))
    if hilang:
        print("Kandidat patch (cara patch di references/changelog.md):")
        for versi, pid, lab in hilang:
            print(f"  - {pid} (v{versi}): {lab}")
    return 1 if hilang else 0


if __name__ == "__main__":
    sys.exit(main())
