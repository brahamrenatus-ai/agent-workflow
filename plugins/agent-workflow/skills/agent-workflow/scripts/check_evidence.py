#!/usr/bin/env python3
"""Pemeriksa bukti report agent-workflow: kutipan dan status OK dicocokkan dengan file log.

Dijalankan dari root project (skrip ini disalin ke handoff/tools/ oleh BOOTSTRAP/AUDIT):
  python handoff/tools/check_evidence.py [--require-provenance] handoff/reports/REPORT-NNN.md [report lain ...]
  python handoff/tools/check_evidence.py --at <commit> handoff/reports/REPORT-NNN.md
  python handoff/tools/check_evidence.py --at-report handoff/reports/REPORT-0*.md

Executor menjalankannya sebelum mengubah status task ke DONE; head menjalankannya lagi saat triase.

Yang dicek:
1. Blok ```bukti: tiap baris `file:baris | kutipan` -> kutipan harus ada di baris itu.
2. Tabel yang punya kolom Bukti dan Status (format REPORT_TEMPLATE juga punya Harapan dan Teramati):
   - status OK wajib punya bukti di kolom Bukti, dalam salah satu bentuk berikut:
     `file:baris` (baris itu harus ada); `hitung(file, "pola")`, yaitu jumlah baris yang cocok dengan pola
     regex, mis. untuk "0 kemunculan Guru Meditation" (Teramati harus sama dengan jumlah itu); atau
     `user: "<kutipan>"` untuk pengamatan user, yang dicatat sebagai peringatan karena head yang
     memverifikasinya. Kutipan user yang sama dengan teks Harapan (≥ 4 kata) adalah masalah, karena pengamatan
     user tidak boleh dikarang;
   - nilai Teramati harus terlihat di salah satu baris yang dirujuk (tulis nilainya persis seperti di baris itu);
   - Harapan berbentuk `kunci=nilai`, `kunci<N`, `kunci>=N`, `=N`, `<N` (digabung dengan "dan" atau ";")
     dinilai otomatis; status OK yang bertentangan dengan hasilnya adalah masalah;
   - tabel task FAKTA (kolom Pertanyaan, Jawaban, Bukti, Status): DITEMUKAN butuh `file:baris` atau `hitung`,
     TIDAK ADA butuh `hitung(lingkup, "pola")` yang hasilnya 0, TIDAK YAKIN tidak dicek. Lingkup `hitung` boleh
     satu file, sebuah folder (semua file teks di dalamnya), atau pola glob seperti `src/**/*.cpp`.
3. Di blok kode lain: baris berformat log (diawali `[HH:MM:SS]` atau `[TAG]`), output `grep -n` atau
   Select-String (`file:baris:isi`), dan tabel `LineNumber Line` dari Select-String harus cocok dengan file.
   Baris log harus ada di file yang dirujuk report; bila hanya ada di file lain, skrip menyebut file itu.
4. Asal log, bila handoff/logs/provenance.jsonl ada (ditulis record.py): log di handoff/logs/ yang dirujuk report harus
   tercatat dengan hash yang sama. Log yang berubah setelah dicatat adalah masalah. Log tanpa catatan diberi
   peringatan, atau masalah bila --require-provenance dipakai. Log yang hanya muncul di baris output
   `git status --porcelain` (mis. di bagian Periksa Diri) bukan bukti, jadi asalnya tidak dicek. Log yang
   disamarkan `check_secrets.py --redact` tetap cocok, karena skrip itu menambahkan catatan asal baru.
5. Kriteria task: bila kriteria terima di handoff/tasks/TASK-NNN-*.md bernomor K1, K2, ..., setiap nomor harus
   muncul di awal kolom Kriteria tabel Data report.
Peringatan (tidak menggagalkan): klaim berhasil/lulus di luar tabel tanpa rujukan `file:baris`, status GAGAL
yang sebenarnya memenuhi Harapan, report (selain BLOCKED) tanpa bagian Periksa Diri, kriteria task yang belum
bernomor K, dan angka bersatuan (mis. `3-6 detik`, `7,20:1`, `45%`) di Ringkasan Fakta, Keputusan Implementasi,
atau Anomali tanpa rujukan `file:baris` di baris yang sama dan tanpa tanda perkiraan/HIPOTESIS.

Rujukan `file:baris` boleh berupa path dari root repo, atau nama file saja bila tepat satu file bernama itu
ada di handoff/logs/. Beberapa baris dari satu file: `file:12, 40, 41`, atau `file:12`, `:40` di sel yang sama.

Report lama (AUDIT, survei): file kode dan dokumen bisa berubah sesudah report ditriase, sehingga kutipan yang dulu
benar terbaca salah. `--at <commit>` membaca semua file yang dirujuk (termasuk log, task, dan provenance.jsonl) pada
commit itu lewat git, tanpa mengubah working tree. `--at-report` memakai commit terakhir yang mengubah tiap report;
report yang belum di-commit dicek terhadap working tree. Commit itu bisa juga memuat suntingan head saat triase,
jadi bandingkan kedua mode: MASALAH yang muncul di keduanya adalah temuan, sedangkan yang hanya muncul di salah satu
biasanya artefak perubahan file sesudah report ditulis.

Report berbahasa Inggris juga dikenali: judul `Self-check`, `Fact Summary`, `Implementation Decisions`, `Anomalies`
(report) dan `Acceptance criteria` (task); kolom `Criteria`, `Expected`, `Observed`, `Evidence`, `Status`; status
`PASS`, `FAIL`, `NOT TESTED`, `FOUND`, `NOT FOUND`, `UNSURE`; bukti `count(file, "pola")`; blok ```evidence; dan
`Final status: BLOCKED`. Kata kunci lain ditulis seperti di template.
Exit code: 0 = tidak ada masalah, 1 = ada masalah, 2 = report atau commit tidak ditemukan.
"""
import fnmatch
import glob
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

EKSTENSI = "log|txt|md|csv|tsv|json|jsonl|yaml|yml|ini|toml|cfg|out|py|ps1|sh|c|h|cpp|hpp|ino|js|ts|html|sql"
FILE = rf"(?:[A-Za-z]:[/\\])?(?:[\w.-]+[/\\])*[\w.-]+\.(?:{EKSTENSI})"
REF = re.compile(rf"(?<![\w/.\\-])({FILE}):(\d+(?:\s*,\s*\d+)*)(?![\d:])", re.I)
REF_LANJUT = re.compile(rf"(?<![\w/.\\-])({FILE}):(\d+(?:\s*,\s*\d+)*)(?![\d:])|(?<![\w/.\\-]):(\d+)(?![\d:])", re.I)
HITUNG = re.compile(r"(?:hitung|count)\(\s*`?([^,`()]+?)`?\s*,\s*[\"'](.+?)[\"']\s*\)", re.I)
GREP_N = re.compile(rf"^\s*({FILE}):(\d+):(.*)$", re.I)
BARIS_LOG = re.compile(r"^\s*(\[\d{1,2}:\d{2}:\d{2}(?:\.\d+)?\]|\[[A-Z][A-Z0-9_]+\])")
SEBUT_LOG = re.compile(rf"(?<![\w/.\\-])((?:handoff[/\\]logs[/\\])?(?:[\w.-]+[/\\])*[\w.-]+\.(?:log|txt|csv|out|jsonl))(?![\w:])", re.I)
# Satu baris output `git status --porcelain`/`-s`: kode status lalu satu path (atau `lama -> baru`), boleh berbacktick.
STATUS_GIT = re.compile(r"^\s*(?:[-*]\s+)?`?\s*(?:\?\?|!!|[MTADRCU]{1,2})\s+[^\s`]+(?:\s+->\s+[^\s`]+)?`?\s*$")
KLAIM = re.compile(r"\b(lulus|lolos|berhasil|sukses|passed|succeeded|success(?:ful)?)\b", re.I)
TOKEN = re.compile(r"([A-Za-z_][\w.]*)\s*=\s*([^\s,;|`]+)")
SYARAT = re.compile(r"^([A-Za-z_][\w.]*)?\s*(==|=|!=|<=|>=|<|>|≤|≥)\s*(-?\d+(?:[.,]\d+)?|\S+)\s*([A-Za-z%]*)$")
ANGKA = re.compile(r"-?\d+(?:[.,]\d+)?")
LOG_EXT = (".log", ".txt", ".csv", ".tsv", ".out", ".json", ".jsonl")  # baris kode boleh berubah sesudah dikutip
EKSTENSI_SET = set(EKSTENSI.split("|"))
ABAIKAN = {".git", ".pio", "node_modules", ".venv", "venv", "__pycache__", "build", "dist"}
ASAL = Path("handoff") / "logs" / "provenance.jsonl"
ASAL_LAMA = Path("handoff") / "logs" / "asal.jsonl"  # nama sebelum v3.12
# Nama sebelum v3.12 -> (nama baru, isinya sama). Report lama yang mengutip file yang hanya berganti nama dibaca dari
# nama barunya, karena nomor barisnya tetap berlaku. Salinan alat isinya berubah, jadi hanya nama barunya yang disebut.
NAMA_V312 = {
    "handoff/logs/asal.jsonl": ("handoff/logs/provenance.jsonl", True),
    "handoff/struktur.md": ("handoff/STRUCTURE.md", True),
    "docs/struktur.md": ("docs/STRUCTURE.md", True),
    "handoff/tools/cek_bukti.py": ("handoff/tools/check_evidence.py", False),
    "handoff/tools/catat.py": ("handoff/tools/record.py", False),
    "handoff/tools/cek_secret.py": ("handoff/tools/check_secrets.py", False),
    "handoff/tools/foto_tampilan.py": ("handoff/tools/screenshot.py", False),
}
BAGIAN_ANGKA = re.compile(r"ringkasan fakta|keputusan implementasi|anomali|fact summary|implementation decision|anomal(?:y|ies)", re.I)
ANGKA_SATUAN = re.compile(r"(?<![\w.,/-])\d+(?:[.,]\d+)?(?:\s*[–-]\s*\d+(?:[.,]\d+)?)?\s*"
                          r"(?:ms|s|secs?|detik|menit|mins?|jam|hours?|%|MB|KB|GB|kg|°C|mA|V|Hz|dB|:1)(?![\w])", re.I)
PERKIRAAN = re.compile(r"HIPOTESIS|HYPOTHESIS|perkiraan|estimasi|kira-kira|sekitar|±|~|"
                       r"(?<![\\\w])(?:estimated?|approx(?:imately)?|roughly)\b", re.I)  # bukan `\approx` LaTeX
STATUS = {"OK": "OK", "LOLOS": "OK", "TERPENUHI": "OK", "PASS": "OK", "PASSED": "OK", "DITEMUKAN": "OK", "FOUND": "OK",
          "GAGAL": "GAGAL", "TIDAK TERPENUHI": "GAGAL", "FAIL": "GAGAL", "FAILED": "GAGAL",
          "TIDAK ADA": "TIDAK ADA", "NOT FOUND": "TIDAK ADA",
          "TIDAK DIUJI": "TIDAK DIUJI", "TIDAK YAKIN": "TIDAK DIUJI", "NOT TESTED": "TIDAK DIUJI", "UNTESTED": "TIDAK DIUJI",
          "UNSURE": "TIDAK DIUJI", "NOT SURE": "TIDAK DIUJI", "N/A": "TIDAK DIUJI", "-": "TIDAK DIUJI"}
# Judul dan baris yang dicari skrip, dalam bahasa Indonesia atau Inggris.
JUDUL_PERIKSA = re.compile(r"^#+\s*(?:Periksa Diri|Self[- ]?check)", re.I | re.M)
JUDUL_KRITERIA = r"(?:Kriteria terima|Acceptance criteria)"
BLOCKED = re.compile(r"(?:Status(?: akhir)?|Final status)\s*:\s*\**\s*BLOCKED", re.I)
BLOK_BUKTI = ("bukti", "evidence")


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


def rapi(s):
    """Spasi dirapatkan; backtick tepi dan elipsis akhir (potongan output PowerShell) dibuang."""
    s = s.strip().strip("`").strip()
    s = re.sub(r"(\.\.\.|…)$", "", s).rstrip()
    return re.sub(r"\s+", " ", s)


def tanpa_spasi_sama(s):
    return re.sub(r"\s*=\s*", "=", rapi(s))


def hash_isi(isi):
    """SHA-256 isi file (bytes) dengan CRLF disamakan menjadi LF (sama persis dengan record.py)."""
    return hashlib.sha256(isi.replace(b"\r\n", b"\n")).hexdigest()


def asal_dipakai(berkas):
    """Path relatif catatan asal: provenance.jsonl, atau asal.jsonl (nama sebelum v3.12) bila hanya itu yang ada."""
    return ASAL_LAMA if not berkas.ada(berkas.root / ASAL) and berkas.ada(berkas.root / ASAL_LAMA) else ASAL


def muat_asal(berkas):
    """Catatan terakhir per file dari handoff/logs/provenance.jsonl ({path relatif huruf kecil: catatan}); None bila tidak ada."""
    p = berkas.root / asal_dipakai(berkas)
    if not berkas.ada(p):
        return None
    asal = {}
    for l in berkas.teks(p).splitlines():
        try:
            rec = json.loads(l)
        except ValueError:
            continue
        if isinstance(rec, dict) and rec.get("file") and rec.get("sha256"):
            asal[rec["file"].replace("\\", "/").lower()] = rec
    return asal


def cek_asal(dirujuk, berkas, asal, wajib, hasil):
    """Log di handoff/logs/ yang dirujuk report harus tercatat record.py dengan hash yang sama."""
    if asal is None:
        return
    sumber = asal_dipakai(berkas).as_posix()
    for p in dirujuk:
        try:
            rel = p.resolve().relative_to(berkas.root.resolve()).as_posix()
        except ValueError:
            continue
        if not rel.lower().startswith("handoff/logs/") or rel.lower() in (ASAL.as_posix().lower(), ASAL_LAMA.as_posix().lower()):
            continue
        rec = asal.get(rel.lower())
        if rec is None:
            pesan = f"log {rel} tidak tercatat di {sumber} (tidak dibuat lewat record.py)"
            (hasil.masalah if wajib else hasil.peringatan)(0, pesan)
        elif hash_isi(berkas.mentah(p)) != rec["sha256"]:
            hasil.masalah(0, f"log {rel} berubah setelah dicatat record.py (perintah: {rec.get('perintah', '?')}); "
                             "jalankan ulang perintahnya, jangan mengedit log")
        else:
            hasil.dicek += 1


def cek_kriteria(path_report, kolom_kriteria, berkas, hasil):
    """Setiap kriteria K1..Kn di task harus punya baris di tabel Data (kolom Kriteria diawali nomornya)."""
    m = re.match(r"REPORT-([\w-]+?)\.md$", path_report.name, re.I)
    if not m:
        return
    calon = berkas.glob(f"handoff/tasks/TASK-{m.group(1)}-*.md") + berkas.glob(f"handoff/tasks/TASK-{m.group(1)}.md")
    if not calon:
        return
    teks = berkas.teks(calon[0])
    mk = re.search(rf"^#+\s*{JUDUL_KRITERIA}[^\n]*\n(.*?)(?=^#+\s|\Z)", teks, re.M | re.S | re.I)
    if not mk or not mk.group(1).strip():
        return
    # Hanya nomor di awal kriteria (sel pertama tabel, atau awal butir), bukan sebutan K9 di tengah teks.
    awal = re.compile(r"^\s*(?:\|\s*)?(?:[-*]\s+|\d+[.)]\s+)?[*`]*\s*K(\d+)\b")
    nomor = sorted({int(m.group(1)) for m in (awal.match(l) for l in mk.group(1).splitlines()) if m})
    if not nomor:
        hasil.peringatan(0, f"kriteria terima di {calon[0].name} belum bernomor K1, K2, ...; kelengkapan tabel Data tidak dicek otomatis")
        return
    for n in nomor:
        if not any(re.match(rf"^\W*K{n}\b", c) for c in kolom_kriteria):
            hasil.masalah(0, f"kriteria K{n} di {calon[0].name} tidak punya baris di tabel Data (kolom Kriteria diawali K{n})")
        else:
            hasil.dicek += 1


def cek_angka(no, baris, hasil):
    """Angka bersatuan tanpa rujukan file:baris di baris yang sama, kecuali ditandai perkiraan/HIPOTESIS."""
    teks = re.sub(r"`[^`]*`", " ", baris)
    if REF.search(baris) or PERKIRAAN.search(teks):
        return
    m = ANGKA_SATUAN.search(teks)
    if m:
        hasil.peringatan(no, f"angka \"{m.group(0).strip()}\" tanpa rujukan file:baris di baris ini; "
                             "rujuk sumbernya, atau tandai sebagai perkiraan/HIPOTESIS")


def glob_rx(pola):
    """Regex untuk pola glob relatif (`*` dan `?` tidak melewati `/`, `**/` = nol atau lebih folder)."""
    rx, i = "", 0
    while i < len(pola):
        if pola.startswith("**/", i):
            rx, i = rx + "(?:.*/)?", i + 3
        elif pola.startswith("**", i):
            rx, i = rx + ".*", i + 2
        elif pola[i] == "*":
            rx, i = rx + "[^/]*", i + 1
        elif pola[i] == "?":
            rx, i = rx + "[^/]", i + 1
        elif pola[i] == "[":
            j = pola.find("]", i + 1)
            if j < 0:
                rx, i = rx + re.escape("["), i + 1
            else:
                rx, i = rx + fnmatch.translate(pola[i:j + 1])[4:-3], j + 1
        else:
            rx, i = rx + re.escape(pola[i]), i + 1
    return re.compile(rx + r"\Z", re.I if sys.platform == "win32" else 0)


class Berkas:
    """Isi file yang dirujuk report (di-cache), dengan pencarian nama file di handoff/logs/.

    Tanpa `rev`, file dibaca dari working tree. Dengan `rev` (opsi --at), semua file dibaca pada commit itu
    lewat `git ls-tree`/`git show`, sehingga kutipan report lama dicocokkan dengan isi file saat report ditulis."""

    def __init__(self, root, rev=None):
        self.root, self.rev = root, rev
        self._isi, self._mentah = {}, {}
        self._indeks = self._pohon = None

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], capture_output=True)

    def pohon(self):
        """Path relatif (garis miring maju) semua file ter-track pada commit `rev`."""
        if self._pohon is None:
            out = self.git("ls-tree", "-r", "--name-only", "-z", self.rev).stdout
            self._pohon = {n.decode("utf-8", "replace") for n in out.split(b"\0") if n}
        return self._pohon

    def rel(self, p):
        try:
            return p.resolve().relative_to(self.root.resolve()).as_posix()
        except ValueError:
            return None

    def ada(self, p):
        if self.rev is None:
            return p.is_file()
        r = self.rel(p)
        return r is not None and r in self.pohon()

    def mentah(self, p):
        """Isi file (bytes)."""
        if p not in self._mentah:
            self._mentah[p] = p.read_bytes() if self.rev is None else self.git("show", f"{self.rev}:{self.rel(p)}").stdout
        return self._mentah[p]

    def teks(self, p):
        return self.mentah(p).decode("utf-8", errors="replace")

    def glob(self, pola):
        """File (bukan folder) yang cocok dengan pola glob relatif terhadap root, terurut."""
        if self.rev is None:
            try:
                return sorted(p for p in self.root.glob(pola) if p.is_file())
            except (NotImplementedError, ValueError):
                return []
        rx = glob_rx(pola[2:] if pola.startswith("./") else pola)
        return sorted(self.root / r for r in self.pohon() if rx.match(r))

    def isi_folder(self, p):
        """Semua file di bawah folder p (rekursif); [] bila p bukan folder."""
        if self.rev is None:
            return [q for q in p.rglob("*") if q.is_file()] if p.is_dir() else []
        r = self.rel(p)
        if r is None:
            return []
        awal = r.rstrip("/") + "/"
        return [self.root / n for n in self.pohon() if n.startswith(awal)]

    def indeks(self):
        if self._indeks is None:
            self._indeks = {}
            for p in self.isi_folder(self.root / "handoff" / "logs"):
                self._indeks.setdefault(p.name.lower(), []).append(p)
        return self._indeks

    def cari(self, nama):
        """(path, None) bila file ditemukan; (None, pesan) bila tidak."""
        nama = nama.replace("\\", "/")
        p = Path(nama) if Path(nama).is_absolute() else self.root / nama
        if self.ada(p):
            return p, None
        if "/" not in nama:
            cocok = self.indeks().get(nama.lower(), [])
            if len(cocok) == 1:
                return cocok[0], None
            if len(cocok) > 1:
                return None, f"nama file {nama} ambigu ({len(cocok)} file di handoff/logs/); tulis path lengkapnya"
        pindah = NAMA_V312.get(("handoff/logs/" + nama if "/" not in nama else self.rel(p) or "").lower())
        if pindah:
            baru, isi_sama = pindah
            if isi_sama and self.ada(self.root / baru):
                return self.root / baru, None
            return None, f"file {nama} tidak ada (sejak v3.12 bernama {baru}; report lama dicek dengan --at-report)"
        return None, f"file {nama} tidak ada" + (" (log mentah hanya ada di mesin lokal?)" if "raw" in nama else "")

    def baris(self, path):
        if path not in self._isi:
            asli = self.teks(path).splitlines()
            self._isi[path] = (asli, [rapi(b) for b in asli])
        return self._isi[path]

    def semua_log(self):
        return [p for daftar in self.indeks().values() for p in daftar]

    def daftar_file(self, nama):
        """File untuk hitung(): satu file, semua file teks di sebuah folder, atau pola glob. ([path], None) atau ([], pesan)."""
        nama = nama.strip().replace("\\", "/")

        def boleh(p):
            try:
                bagian = set(p.relative_to(self.root).parts)
            except ValueError:
                bagian = set(p.parts)
            return not (bagian & ABAIKAN)

        if any(ch in nama for ch in "*?["):
            if Path(nama).is_absolute():
                return [], f"pola file {nama} harus relatif terhadap root repo"
            cocok = [p for p in self.glob(nama) if boleh(p)]
            return (cocok, None) if cocok else ([], f"pola file {nama} tidak cocok dengan file apa pun")
        p = Path(nama) if Path(nama).is_absolute() else self.root / nama
        isi = self.isi_folder(p)
        if isi:
            cocok = sorted(q for q in isi if boleh(q) and q.suffix.lower().lstrip(".") in EKSTENSI_SET)
            return (cocok, None) if cocok else ([], f"folder {nama} tidak berisi file teks")
        path, galat = self.cari(nama)
        return ([path], None) if path else ([], galat)


class Hasil:
    def __init__(self, nama):
        self.nama, self.temuan, self.dicek = nama, [], 0

    def masalah(self, no, pesan):
        self.temuan.append((no, "MASALAH", pesan))

    def peringatan(self, no, pesan):
        self.temuan.append((no, "PERINGATAN", pesan))

    def jumlah(self, jenis):
        return sum(1 for _, j, _ in self.temuan if j == jenis)


def rujukan(teks):
    """Daftar (nama file, nomor baris) dari teks; `f.log:3, 9` dan `f.log:3`, `:9` sama-sama dua rujukan."""
    hasil, terakhir = [], None
    for m in REF_LANJUT.finditer(teks):
        if m.group(1):
            terakhir = m.group(1)
            hasil += [(terakhir, int(n)) for n in re.split(r"\s*,\s*", m.group(2))]
        elif terakhir:
            hasil.append((terakhir, int(m.group(3))))
    return hasil


def hitung_cocok(no, sel_bukti, berkas, hasil):
    """(lingkup, pola, jumlah baris cocok) untuk setiap `hitung(lingkup, "pola")` yang valid di sel."""
    hitungan = []
    for nama, pola in HITUNG.findall(sel_bukti):
        files, galat = berkas.daftar_file(nama)
        if galat:
            hasil.masalah(no, f"hitung({nama.strip()}): {galat}")
            continue
        try:
            rx = re.compile(pola)
        except re.error as e:
            hasil.masalah(no, f"pola hitung \"{pola}\" bukan regex yang valid ({e})")
            continue
        hasil.dicek += 1
        hitungan.append((nama.strip(), pola, sum(1 for p in files for b in berkas.baris(p)[0] if rx.search(b))))
    return hitungan


def cek_hitung(no, sel_bukti, teramati, berkas, hasil):
    """Bukti `hitung(...)`: Teramati harus sama dengan jumlah baris yang cocok. True bila sel memuat bentuk ini."""
    for nama, pola, jumlah in hitung_cocok(no, sel_bukti, berkas, hasil):
        obs = ANGKA.search(teramati or "")
        if not obs or angka(obs.group(0)) != jumlah:
            hasil.masalah(no, f"Teramati \"{rapi(teramati)}\" tidak sama dengan hitungan: {jumlah} baris di {nama} cocok dengan \"{pola}\"")
    return bool(HITUNG.search(sel_bukti))


def ambil_baris(no, nama, n, berkas, hasil):
    path, galat = berkas.cari(nama)
    if galat:
        hasil.masalah(no, f"rujukan {nama}:{n}: {galat}")
        return None
    asli, _ = berkas.baris(path)
    if n < 1 or n > len(asli):
        hasil.masalah(no, f"rujukan {nama}:{n}: file itu hanya {len(asli)} baris")
        return None
    hasil.dicek += 1
    return asli[n - 1]


def cek_kutipan(no, nama, n, kutipan, berkas, hasil):
    isi = ambil_baris(no, nama, n, berkas, hasil)
    if isi is not None and rapi(kutipan) not in rapi(isi):
        hasil.masalah(no, f"kutipan untuk {nama}:{n} tidak sama dengan isi baris itu: \"{rapi(isi)[:120]}\"")


def cari_baris_log(no, teks, berkas, dirujuk, hasil):
    q = rapi(teks)
    for p in dirujuk:
        if any(q in b for b in berkas.baris(p)[1]):
            hasil.dicek += 1
            return
    for p in berkas.semua_log():
        if p not in dirujuk and any(q in b for b in berkas.baris(p)[1]):
            hasil.masalah(no, f"baris log tidak ada di file yang dirujuk report; baris yang sama ada di "
                              f"{p.relative_to(berkas.root).as_posix()}. Rujuk file itu bila memang berasal dari sana")
            return
    hasil.masalah(no, f"baris log tidak ada di file log mana pun: \"{q[:120]}\"")


def norm_status(teks):
    s = re.sub(r"[^A-Z/ -]", "", rapi(teks).upper()).strip()
    return STATUS.get(re.sub(r"\s+", " ", s), "")


def terlihat(teramati, baris_bukti):
    gabung = [tanpa_spasi_sama(b) for b in baris_bukti]
    token = TOKEN.findall(teramati)
    if token:
        return all(any(re.search(rf"(?<![\w.]){re.escape(k)}={re.escape(v)}(?![\w.])", g) for g in gabung) for k, v in token)
    return any(rapi(teramati) in rapi(b) for b in baris_bukti)


def angka(s):
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def nilai_harapan(harapan, teramati):
    """True/False bila Harapan bisa dinilai otomatis terhadap Teramati; None bila tidak."""
    h = rapi(harapan)
    if not h or h == "-" or not rapi(teramati):
        return None
    hasil = []
    for bagian in [b.strip().strip("`").strip() for b in re.split(r"\s+(?:dan|and)\s+|;", h) if b.strip()]:
        m = SYARAT.match(bagian)
        if not m:
            return None
        kunci, op, nilai, _ = m.groups()
        op = {"≤": "<=", "≥": ">=", "==": "="}.get(op, op)
        mt = re.search(rf"(?<![\w.]){re.escape(kunci)}\s*=\s*([^\s,;|`]+)", teramati) if kunci else None
        if mt:
            obs = mt.group(1)
        else:
            ma = ANGKA.search(teramati)
            if not ma:
                return None
            obs = ma.group(0)
        a, b = angka(obs), angka(nilai)
        if a is not None and b is not None:
            hasil.append({"=": a == b, "!=": a != b, "<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op])
        elif op in ("=", "!="):
            hasil.append((obs == nilai) == (op == "="))
        else:
            return None
    return all(hasil)


def sel(baris):
    s = baris.strip()
    s = s[1:] if s.startswith("|") else s
    s = s[:-1] if s.endswith("|") and not s.endswith("\\|") else s
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", s)]


def cek_tabel(tabel, berkas, hasil, kolom_kriteria=None):
    (_, header), rows = tabel[0], tabel[2:]
    h = [c.lower() for c in sel(header)]
    if kolom_kriteria is not None and h and ("kriteria" in h[0] or "criteri" in h[0]):
        kolom_kriteria += [sel(b)[0] for _, b in rows if sel(b)]

    def kolom(*nama):
        return next((i for i, c in enumerate(h) if any(n in c for n in nama)), None)

    fakta = kolom("pertanyaan", "question") is not None  # tabel task FAKTA: Jawaban berperan sebagai Teramati
    k = {"harapan": kolom("harapan", "expected"), "teramati": kolom("teramati", "observed"),
         "bukti": kolom("bukti", "evidence", "rujukan"), "status": kolom("status")}
    if fakta and k["teramati"] is None:
        k["teramati"] = kolom("jawaban", "answer")
    if k["status"] is None or k["bukti"] is None:
        return False
    for no, baris in rows:
        c = sel(baris)
        if len(c) != len(h):
            hasil.masalah(no, f"baris tabel punya {len(c)} kolom, header {len(h)}; tanda | di dalam sel ditulis \\|")
            continue
        ambil = lambda nama: c[k[nama]] if k[nama] is not None and k[nama] < len(c) else ""  # noqa: E731
        status = norm_status(ambil("status"))
        if status == "TIDAK ADA":
            if not HITUNG.search(ambil("bukti")):
                hasil.masalah(no, "status TIDAK ADA butuh bukti `hitung(lingkup, \"pola\")` yang hasilnya 0")
            for nama, pola, jumlah in hitung_cocok(no, ambil("bukti"), berkas, hasil):
                if jumlah:
                    hasil.masalah(no, f"status TIDAK ADA, padahal {jumlah} baris di {nama} cocok dengan \"{pola}\"")
            continue
        if status not in ("OK", "GAGAL"):
            continue
        refs = rujukan(HITUNG.sub("", ambil("bukti")))
        ada_hitung = cek_hitung(no, ambil("bukti"), ambil("teramati"), berkas, hasil)
        if status == "OK" and not refs and not ada_hitung:
            if re.search(r"\buser\s*:", ambil("bukti"), re.I):
                # "Kutipan user" yang hanya menyalin teks Harapan bukan pengamatan user (Pelajaran 15)
                kutip = " \"'`“”"
                kutipan = rapi(re.sub(r"(?is)^.*?\buser\s*:", "", ambil("bukti")).strip(kutip)).strip(kutip)
                harapan = rapi(ambil("harapan")).strip(kutip)
                if len(kutipan.split()) >= 4 and kutipan.lower() == harapan.lower():
                    hasil.masalah(no, "kutipan user sama dengan teks Harapan; pengamatan user tidak boleh dikarang "
                                      "(tulis TIDAK DIUJI sampai user menjawab)")
                else:
                    hasil.peringatan(no, "bukti berupa pengamatan user; head yang memverifikasinya")
            else:
                hasil.masalah(no, "status OK tanpa rujukan file:baris di kolom Bukti")
            continue
        bukti = [b for b in (ambil_baris(no, nama, n, berkas, hasil) for nama, n in refs) if b is not None]
        teramati = ambil("teramati")
        if bukti and not ada_hitung and not fakta and rapi(teramati) not in ("", "-") and not terlihat(teramati, bukti):
            hasil.masalah(no, f"Teramati \"{rapi(teramati)}\" tidak terlihat di baris yang dirujuk")
        nilai = nilai_harapan(ambil("harapan"), teramati)
        if nilai is False and status == "OK":
            hasil.masalah(no, f"status OK, padahal Teramati \"{rapi(teramati)}\" tidak memenuhi Harapan \"{rapi(ambil('harapan'))}\"")
        elif nilai is True and status == "GAGAL":
            hasil.peringatan(no, f"status GAGAL, padahal Teramati memenuhi Harapan \"{rapi(ambil('harapan'))}\"")
    return True


def sumber_select_string(teks):
    """Path tunggal di `Select-String -Path <file>`; None bila tidak ada, berpola, atau lebih dari satu file."""
    m = re.search(r"Select-String\b.*?-Path\s+(['\"]?)([^\s'\",|]+)\1(\s*,)?", teks, re.I)
    if not m or m.group(3) or any(ch in m.group(2) for ch in "*?"):
        return None
    return m.group(2)


def cek_blok_kode(blok, sebelum, berkas, dirujuk, hasil):
    """Output grep/Select-String atas file log dicocokkan per baris; atas file kode dilewati (bisa berupa kutipan sebelum perubahan)."""
    sumber = sumber_select_string(" ".join(sebelum + [t for _, t in blok]))
    sumber_kode = bool(sumber) and not sumber.lower().endswith(LOG_EXT)
    mode_tabel = False
    for no, t in blok:
        if re.match(r"^\s*LineNumber\s+Line\s*$", t):
            mode_tabel = True
            continue
        if mode_tabel and re.match(r"^\s*-+\s+-+\s*$", t):
            continue
        m = GREP_N.match(t)
        if m:
            if m.group(1).lower().endswith(LOG_EXT):
                cek_kutipan(no, m.group(1), int(m.group(2)), m.group(3), berkas, hasil)
            continue
        if sumber_kode:
            continue
        m = re.match(r"^\s*(\d+)\s(.*)$", t) if mode_tabel else re.match(r"^\s*(\d+):\s?(\[.*)$", t)
        if m and sumber:
            cek_kutipan(no, sumber, int(m.group(1)), m.group(2), berkas, hasil)
            continue
        if m:
            t = m.group(2)
        if BARIS_LOG.match(t):
            cari_baris_log(no, t, berkas, dirujuk, hasil)


def file_dirujuk(teks, berkas, path_report):
    """File yang ada dan disebut teks, lewat rujukan `file:baris` atau nama log; report itu sendiri tidak dihitung."""
    hasil = []
    for nama in {m.group(1) for m in REF.finditer(teks)} | {m.group(1) for m in SEBUT_LOG.finditer(teks)}:
        p, _ = berkas.cari(nama)
        if p and p not in hasil and p.resolve() != path_report.resolve():
            hasil.append(p)
    return hasil


def periksa(path_report, berkas, asal=None, wajib_asal=False):
    teks = path_report.read_text(encoding="utf-8", errors="replace")
    baris = teks.splitlines()
    hasil = Hasil(path_report.name)
    dirujuk = file_dirujuk(teks, berkas, path_report)
    i, ada_tabel, kolom_kriteria, bagian = 0, False, [], ""
    while i < len(baris):
        t = baris[i]
        pagar = re.match(r"^\s*(```|~~~)\s*([\w-]*)", t)
        if pagar:
            tanda, info, j = pagar.group(1), pagar.group(2).lower(), i + 1
            while j < len(baris) and not baris[j].strip().startswith(tanda):
                j += 1
            blok = [(k + 1, baris[k]) for k in range(i + 1, min(j, len(baris)))]
            if info in BLOK_BUKTI:
                for no, b in blok:
                    if not b.strip():
                        continue
                    m = re.match(rf"^\s*({FILE}):(\d+)\s*\|\s?(.*)$", b, re.I)
                    if m:
                        cek_kutipan(no, m.group(1), int(m.group(2)), m.group(3), berkas, hasil)
                    else:
                        hasil.masalah(no, "baris blok bukti tidak berformat `file:baris | kutipan`")
            else:
                cek_blok_kode(blok, baris[max(0, i - 15):i], berkas, dirujuk, hasil)
            i = j + 1
            continue
        if t.strip().startswith("|"):
            j = i
            while j < len(baris) and baris[j].strip().startswith("|"):
                j += 1
            tabel = [(k + 1, baris[k]) for k in range(i, j)]
            if len(tabel) >= 3 and re.match(r"^\s*\|?\s*:?-{3,}", tabel[1][1]):
                ada_tabel = cek_tabel(tabel, berkas, hasil, kolom_kriteria) or ada_tabel
            i = j
            continue
        s = t.strip()
        if s.startswith("#"):
            bagian = s
        mk = KLAIM.search(s)
        if mk and not REF.search(s) and not re.search(r"hanya bila|only if", s, re.I) and not s.startswith(("#", "(", ">")):
            hasil.peringatan(i + 1, f"klaim \"{mk.group(0)}\" tanpa rujukan file:baris")
        if BAGIAN_ANGKA.search(bagian) and s and not s.startswith(("#", "(")):
            cek_angka(i + 1, s, hasil)
        i += 1
    blocked = BLOCKED.search(teks)
    # Log yang hanya tercantum di output git status (Periksa Diri) bukan bukti, jadi asalnya tidak dicek (v3.9.2).
    bukti_log = file_dirujuk("\n".join(b for b in baris if not STATUS_GIT.match(b)), berkas, path_report)
    cek_asal(bukti_log, berkas, asal, wajib_asal, hasil)
    if not blocked:
        cek_kriteria(path_report, kolom_kriteria, berkas, hasil)
    if hasil.dicek == 0 and not ada_tabel and not blocked:
        hasil.masalah(0, "tidak ada bukti yang bisa dicek (blok bukti, tabel Bukti/Status, atau baris log dari file)")
    if not blocked and not JUDUL_PERIKSA.search(teks):
        hasil.peringatan(0, "report tanpa bagian Periksa Diri (pemeriksaan sebelum DONE)")
    return hasil


def baca_argumen(argv):
    """(opsi, report) dari argumen; pola glob di argumen dikembangkan sendiri, supaya juga jalan di PowerShell."""
    opsi, reports, i = {"wajib_asal": False, "pada": None, "pada_report": False}, [], 0
    while i < len(argv):
        a = argv[i]
        # Nama opsi sebelum v3.12 (--wajib-asal, --pada-report, --pada) tetap diterima.
        if a in ("--require-provenance", "--wajib-asal"):
            opsi["wajib_asal"] = True
        elif a in ("--at-report", "--pada-report"):
            opsi["pada_report"] = True
        elif a in ("--at", "--pada") or a.startswith(("--at=", "--pada=")):
            if "=" not in a:
                i += 1
                if i >= len(argv):
                    return None, []
                opsi["pada"] = argv[i]
            else:
                opsi["pada"] = a.split("=", 1)[1]
        elif a in ("-h", "--help"):
            return None, []
        elif any(ch in a for ch in "*?["):
            reports += sorted(glob.glob(a)) or [a]
        else:
            reports.append(a)
        i += 1
    return opsi, reports


def commit_report(root, report):
    """Hash commit terakhir yang mengubah report; None bila report belum pernah di-commit."""
    out = subprocess.run(["git", "-C", str(root), "log", "-1", "--format=%H", "--", str(report.resolve())],
                         capture_output=True, text=True)
    return out.stdout.strip() or None


def main():
    siapkan_output()
    opsi, args = baca_argumen(sys.argv[1:])
    if not opsi or not args:
        print(__doc__)
        return 2
    root = root_repo()
    if opsi["pada"]:
        cek = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "--quiet", opsi["pada"] + "^{commit}"],
                             capture_output=True, text=True)
        if cek.returncode != 0:
            print(f"Commit {opsi['pada']} tidak ditemukan.", file=sys.stderr)
            return 2
        opsi["pada"] = cek.stdout.strip()
    cache = {}

    def berkas_untuk(rev):
        if rev not in cache:
            b = Berkas(root, rev)
            cache[rev] = (b, muat_asal(b))
        return cache[rev]

    total, kurang = 0, False
    for arg in args:
        p = Path(arg)
        if not p.is_file():
            print(f"Report {arg} tidak ditemukan.", file=sys.stderr)
            kurang = True
            continue
        rev = commit_report(root, p) if opsi["pada_report"] else opsi["pada"]
        berkas, asal = berkas_untuk(rev)
        h = periksa(p, berkas, asal, opsi["wajib_asal"])
        if rev:
            print(f"{h.nama} (file dibaca pada commit {rev[:8]})")
        elif opsi["pada_report"]:
            print(f"{h.nama} (belum di-commit; file dibaca dari working tree)")
        else:
            print(h.nama)
        for no, jenis, pesan in sorted(h.temuan):
            print(f"  {jenis:<10} baris {no}: {pesan}")
        print(f"  Ringkas: {h.dicek} bukti dicek, {h.jumlah('MASALAH')} masalah, {h.jumlah('PERINGATAN')} peringatan.")
        total += h.jumlah("MASALAH")
    if total:
        print("Perbaiki masalah di atas: kutip baris yang benar dari file, atau ubah status kriterianya menjadi GAGAL / TIDAK DIUJI (task FAKTA: TIDAK YAKIN).")
    return 2 if kurang and not total else (1 if total else 0)


if __name__ == "__main__":
    sys.exit(main())
