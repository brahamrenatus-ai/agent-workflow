#!/usr/bin/env python3
"""Bacaan awal sesi: ROADMAP + NOTES dengan bagian besar dipendekkan, ditambah task per status
(agent-workflow, sejak v3.23).

Pakai (dari root project):
  python handoff/tools/brief.py                    handoff/ROADMAP.md + handoff/NOTES.md (LITE: di root project)
  python handoff/tools/brief.py --full register    bagian yang judulnya memuat teks itu dicetak utuh (bisa berulang)
  python handoff/tools/brief.py --all              semua bagian utuh
  python handoff/tools/brief.py <file.md> ...      file lain, dengan aturan yang sama

File tidak diubah. NOTES dan ROADMAP tumbuh bersama umur project, dan sesi baru yang membaca keduanya utuh bisa
menghabiskan sebagian besar konteksnya sebelum mulai bekerja. Yang dicetak:
- bagian (`## `) sampai --limit KB (bawaan 6) apa adanya, begitu juga §1 dan §2 ROADMAP dan judul di FULL;
- bagian yang lebih besar: baris tertutup disembunyikan (sel Status berawalan DONE, usulan yang sudah diputuskan,
  isi sub-bagian "Selesai"), dan baris lain dipotong --cut karakter (bawaan 200) dengan awalan `[L<nomor baris>]`;
- task per status, dan task DONE yang belum bertanda triase head.

Baris yang dipotong dibuka utuh di filenya pada nomor baris itu. Sebelum memutuskan sesuatu, cari dulu topiknya di
file aslinya (mis. `rg -n "<kata kunci>" handoff/NOTES.md handoff/ROADMAP.md`), karena keputusan lama bisa berada
di baris yang dipotong atau disembunyikan.

Output diawali BRIEF (ukuran sebelum dan sesudah) lalu TASKS; ERROR bila file keadaan tidak ditemukan.
Kode keluar: 0, atau 2 untuk ERROR.
"""
import argparse
import re
import sys
from pathlib import Path

# Penyesuaian per project (dibawa dari salinan lama saat upgrade).
FULL = []  # potongan judul bagian yang selalu dicetak utuh, mis. ["Anomali Terbuka"]
CLOSED = ("DONE", "selesai")  # awal sel Status yang berarti baris tertutup; huruf besar-kecil tidak dibedakan
DECIDED = ("terima", "diterima", "tolak", "ditolak", "parkir", "diparkir", "accepted", "rejected", "parked")
CLOSED_HEADING = ("selesai", "done", "closed")  # sub-bagian (###) yang seluruh isinya tertutup
TRIAGE = r"(?:Triase head|Head triage)\s*:\s*[^\s(]"  # tanda triase di file task

RE_STATUS = re.compile(r"Status\s*:\s*\**\s*(OPEN|IN_PROGRESS|DONE|BLOCKED)\b", re.I)
RE_PEMISAH = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
RE_PAGAR = re.compile(r"^\s*(```|~~~)")


def bersih(sel):
    """Sel tanpa markup pembuka (tebal, coret, backtick, centang)."""
    return re.sub(r"^[^0-9A-Za-z(]+", "", sel).strip()


def sel_tabel(baris):
    """Sel satu baris tabel Markdown; `\\|` tidak memisah sel."""
    isi = baris.strip()
    if isi.startswith("|"):
        isi = isi[1:]
    if isi.endswith("|") and not isi.endswith("\\|"):
        isi = isi[:-1]
    return [s.strip() for s in re.split(r"(?<!\\)\|", isi)]


def berawalan(teks, kata):
    return any(re.match(re.escape(k) + r"\b", teks, re.I) for k in kata)


def tertutup(sel, kolom_status, kolom_putus):
    if kolom_status is not None and kolom_status < len(sel) and berawalan(bersih(sel[kolom_status]), CLOSED):
        return True
    if kolom_putus is not None and kolom_putus < len(sel) and berawalan(bersih(sel[kolom_putus]), DECIDED):
        return True
    return False


def bagian(baris):
    """[(judul, awal, akhir)] per judul `## ` di luar blok kode; indeks 0-based, akhir eksklusif.
    Bagian pertama berjudul kosong bila file punya isi sebelum judul pertama."""
    batas, dalam = [], False
    for i, b in enumerate(baris):
        if RE_PAGAR.match(b):
            dalam = not dalam
        elif not dalam and b.startswith("## "):
            batas.append(i)
    hasil = []
    if not batas or batas[0] > 0:
        hasil.append(("", 0, batas[0] if batas else len(baris)))
    for n, i in enumerate(batas):
        hasil.append((baris[i], i, batas[n + 1] if n + 1 < len(batas) else len(baris)))
    return hasil


def dicetak_utuh(judul, ukuran, nama, a):
    if a.all or ukuran <= a.limit * 1024:
        return True
    j = judul.lower()
    if any(t.lower() in j for t in list(FULL) + a.full):
        return True
    return nama.upper().startswith("ROADMAP") and bool(re.match(r"##\s*[12][.\s]", judul))


def potong(b, i, a, hitung):
    if len(b) <= a.cut + 24:
        return b
    hitung["dipotong"] += 1
    return f"[L{i + 1}] {b[:a.cut].rstrip()} …(+{len(b) - a.cut})"


def pendekkan_bagian(baris, awal, akhir, a, hitung):
    out = [baris[awal]]
    kolom_status = kolom_putus = None
    sub_tertutup = kosong = False
    for i in range(awal + 1, akhir):
        b = baris[i]
        if not b.strip():
            kolom_status = kolom_putus = None
            if not kosong:
                out.append("")
            kosong = True
            continue
        kosong = False
        if re.match(r"#{3,6}\s", b):
            sub_tertutup = any(k in b.lower() for k in CLOSED_HEADING)
            kolom_status = kolom_putus = None
            out.append(b)
        elif b.lstrip().startswith("|"):
            if RE_PEMISAH.match(b):
                if not sub_tertutup:
                    out.append(b)
            elif i + 1 < akhir and RE_PEMISAH.match(baris[i + 1]):
                sel = [bersih(s).lower() for s in sel_tabel(b)]
                kolom_status = next((n for n, s in enumerate(sel) if s.startswith("status")), None)
                usul = any(s.startswith(("usul", "proposal")) for s in sel)
                kolom_putus = next((n for n, s in enumerate(sel) if s.startswith(("keputusan", "decision"))), None) if usul else None
                if not sub_tertutup:
                    out.append(potong(b, i, a, hitung))
            elif sub_tertutup or tertutup(sel_tabel(b), kolom_status, kolom_putus):
                hitung["tertutup"] += 1
            else:
                out.append(potong(b, i, a, hitung))
        elif sub_tertutup:
            hitung["tertutup"] += 1
        else:
            out.append(potong(b, i, a, hitung))
    return out


def pendekkan(path, tampil, a):
    """(baris keluaran, ukuran asli, dipotong, tertutup) untuk satu file."""
    mentah = path.read_bytes()
    baris = mentah.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out = [f"===== {tampil} ====="]
    total = {"dipotong": 0, "tertutup": 0}
    for judul, awal, akhir in bagian(baris):
        ukuran = len("\n".join(baris[awal:akhir]).encode("utf-8"))
        if dicetak_utuh(judul, ukuran, path.name, a):
            out.extend(baris[awal:akhir])
            continue
        hitung = {"dipotong": 0, "tertutup": 0}
        isi = pendekkan_bagian(baris, awal, akhir, a, hitung)
        while isi and not isi[-1]:
            isi.pop()
        out.extend(isi)
        out.append(f"[brief] bagian ini dipendekkan: {hitung['dipotong']} baris dipotong, {hitung['tertutup']} baris "
                   f"tertutup disembunyikan; utuh di {tampil} baris {awal + 1}-{akhir}.")
        out.append("")
        for k in total:
            total[k] += hitung[k]
    return out, len(mentah), total["dipotong"], total["tertutup"]


def daftar(nama, maks=12):
    if not nama:
        return "-"
    lebih = f", +{len(nama) - maks} lagi" if len(nama) > maks else ""
    return ", ".join(nama[:maks]) + lebih


def ringkas_task(root):
    folder = root / "handoff" / "tasks"
    if not folder.is_dir():
        return None
    task = []  # (nomor, huruf, nama, status, bertanda triase)
    for p in folder.glob("TASK-*.md"):
        m = re.match(r"TASK-(\d+)([A-Za-z]?)", p.name)
        if not m:
            continue
        try:
            teks = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        ms = RE_STATUS.search(teks)
        task.append((int(m.group(1)), m.group(2).upper(), m.group(0), ms.group(1).upper() if ms else "?",
                     bool(re.search(TRIAGE, teks, re.I))))
    if not task:
        return "TASKS: belum ada file task."
    task.sort()
    per = {}
    for t in task:
        per.setdefault(t[3], []).append(t[2])
    # Task lama dari sebelum tanda triase dipakai tidak dihitung: yang dilaporkan hanya task DONE tanpa tanda
    # sesudah task bertanda yang terakhir.
    batas = max((i for i, t in enumerate(task) if t[4]), default=-1)
    belum = [t[2] for i, t in enumerate(task) if i > batas and t[3] == "DONE" and not t[4]]
    bagian_ = [f"TASKS: {len(task)} file, terakhir {task[-1][2]}"]
    for s in ("OPEN", "IN_PROGRESS", "BLOCKED"):
        bagian_.append(f"{s}: {daftar(per.get(s, []))}")
    if per.get("?"):
        bagian_.append(f"status tidak terbaca: {daftar(per['?'], 5)}")
    bagian_.append(f"DONE belum ditriase: {daftar(belum, 8)}")
    return " | ".join(bagian_)


def temukan(root):
    for dasar in (root / "handoff", root):
        ada = [p for p in (dasar / "ROADMAP.md", dasar / "NOTES.md") if p.is_file()]
        if ada:
            return ada
    return []


def kb(n):
    return f"{n / 1024:.1f} KB"


def main():
    for aliran in (sys.stdout, sys.stderr):
        if hasattr(aliran, "reconfigure"):
            aliran.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Bacaan awal sesi: ROADMAP + NOTES dengan bagian besar dipendekkan.")
    ap.add_argument("file", nargs="*", help="file Markdown; bawaan handoff/ROADMAP.md dan handoff/NOTES.md")
    ap.add_argument("--full", action="append", default=[], metavar="TEKS", help="bagian yang judulnya memuat TEKS dicetak utuh")
    ap.add_argument("--all", action="store_true", help="semua bagian utuh")
    ap.add_argument("--limit", type=float, default=6, metavar="KB", help="bagian sampai ukuran ini dicetak utuh (bawaan 6)")
    ap.add_argument("--cut", type=int, default=200, metavar="N", help="panjang potongan baris di bagian besar (bawaan 200)")
    a = ap.parse_args()
    if a.limit < 0 or a.cut < 40:
        print("ERROR: --limit tidak boleh negatif dan --cut minimal 40.")
        return 2
    root = Path.cwd()
    if a.file:
        berkas = [Path(f) for f in a.file]
        hilang = [str(p) for p in berkas if not p.is_file()]
        if hilang:
            print("ERROR: file tidak ditemukan: " + ", ".join(hilang))
            return 2
    else:
        berkas = temukan(root)
        if not berkas:
            di_skrip = Path(__file__).resolve().parents[2] if len(Path(__file__).resolve().parents) > 2 else root
            berkas = temukan(di_skrip)
            if berkas:
                root = di_skrip
        if not berkas:
            print("ERROR: handoff/ROADMAP.md dan handoff/NOTES.md tidak ditemukan (LITE: ROADMAP.md dan NOTES.md di root). "
                  "Jalankan dari root project, atau sebut filenya.")
            return 2
    isi, ukuran, dipotong, ditutup = [], [], 0, 0
    for p in berkas:
        try:
            tampil = p.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            tampil = p.as_posix()
        out, asli, n_potong, n_tutup = pendekkan(p, tampil, a)
        sesudah = len("\n".join(out).encode("utf-8"))
        ukuran.append(f"{p.name} {kb(asli)}" + (f" -> {kb(sesudah)}" if n_potong or n_tutup else ""))
        isi.extend(out)
        dipotong += n_potong
        ditutup += n_tutup
    if dipotong or ditutup:
        print(f"BRIEF: {', '.join(ukuran)}; {dipotong} baris dipotong, {ditutup} baris tertutup disembunyikan. "
              "Baris [L<n>] utuh: buka filenya pada nomor baris itu; bagian utuh: --full \"<judul>\". "
              "Sebelum memutuskan, cari topiknya di file aslinya.")
    else:
        print(f"BRIEF: {', '.join(ukuran)}; semua bagian utuh.")
    task = ringkas_task(root)
    if task:
        print(task)
    print("\n".join(isi))
    return 0


if __name__ == "__main__":
    sys.exit(main())
