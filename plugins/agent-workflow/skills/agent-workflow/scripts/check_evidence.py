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
     Teramati `kunci=nilai` juga cocok dengan `kunci nilai` dan `kunci: nilai` di baris itu, mis. `tests 328` dari test runner;
   - Harapan berbentuk `kunci=nilai`, `kunci<N`, `kunci>=N`, `=N`, `<N` (digabung dengan "dan" atau ";")
     dinilai otomatis; status OK yang bertentangan dengan hasilnya adalah masalah;
   - tabel task FACT (kolom Pertanyaan, Jawaban, Bukti, Status): FOUND butuh `file:baris` atau `hitung`,
     NONE butuh `hitung(lingkup, "pola")` yang hasilnya 0, UNSURE tidak dicek. Lingkup `hitung` boleh
     satu file, sebuah folder (semua file teks di dalamnya), atau pola glob seperti `src/**/*.cpp`.
   - status ditulis OK, FAIL, atau UNTESTED (task FACT: FOUND, NONE, UNSURE). Bentuk lain juga diterima: PASS,
     NOT TESTED, NOT FOUND, dan nama sebelum v3.20 (padanannya di references/changelog.md skill, bagian v3.20).
3. Di blok kode lain: baris berformat log (diawali `[HH:MM:SS]` atau `[TAG]`), output `grep -n` atau
   Select-String (`file:baris:isi`), dan tabel `LineNumber Line` dari Select-String harus cocok dengan file.
   Baris log harus ada di file yang dirujuk report; bila hanya ada di file lain, skrip menyebut file itu. Log yang
   diabaikan git (mis. log mentah di handoff/logs/raw/) tidak ikut dicari sebagai file lain (v3.20.1).
4. Asal log, bila handoff/logs/provenance.jsonl ada (ditulis record.py): log di handoff/logs/ yang dirujuk report harus
   tercatat dengan hash yang sama. Log yang berubah setelah dicatat adalah masalah. Log tanpa catatan diberi
   peringatan, atau masalah bila --require-provenance dipakai. Log yang hanya muncul di baris output
   `git status --porcelain` (mis. di bagian Periksa Diri) bukan bukti, jadi asalnya tidak dicek. Log yang
   disamarkan `check_secrets.py --redact` tetap cocok, karena skrip itu menambahkan catatan asal baru.
5. Kriteria task: bila kriteria terima di handoff/tasks/TASK-NNN-*.md bernomor K1, K2, ..., setiap nomor harus
   muncul di awal kolom Kriteria tabel Data report.
6. Templat tabel Data di task: tabel task berkolom Kriteria, Harapan, dan Teramati yang kolom Teramati dan Status-nya
   kosong adalah templat. Setiap barisnya harus ada di tabel Data report dengan Harapan yang sama persis (backtick
   diabaikan). Satu baris templat boleh dipecah menjadi beberapa baris report yang kolom Kriterianya berawalan sama,
   mis. `S6 sensors` -> `S6 sensors (IMU)` dan `S6 sensors (ToF)`.
7. Kutipan di prosa (di luar tabel dan blok kode): teks berbacktick yang langsung diikuti rujukan dalam kurung,
   mis. `ka_err=0` (`handoff/logs/a.log:12`), harus ada di baris yang dirujuk bila rujukannya file log. Beberapa
   kutipan boleh berantai (`a` dan `b` (`a.log:3..4`)); rentang `:3..4`, `:3-4`, dan daftar `:3, 9` dicek sebagai
   satu kesatuan; `...` di tengah kutipan menandai potongan. Kutipan berangka yang tidak cocok adalah masalah, yang
   tanpa angka peringatan. Kutipan perintah (`git ...`, `python ...`) dan nama opsi (`--reset`) dilewati. Bila baris
   yang dirujuk baris tabel Markdown, kutipan `<nama kolom> <isi sel>` juga cocok (mis. `Konfirmasi +3.750 s`).
   Kutipan yang tidak bisa dicek karena file lognya tidak ada atau namanya ambigu diberi peringatan (v3.18.1).
8. Klaim `hitung(lingkup, "pola")=N` di luar kolom Bukti tabel kriteria, mis. di prosa atau di tabel lampiran task
   FACT: N harus sama dengan jumlah baris yang cocok (v3.18.1). Kolom Harapan dan lingkup yang disingkat
   (`hitung(..., "pola")`) tidak dicek; nilai yang tidak sama adalah masalah.
Peringatan (tidak menggagalkan): klaim berhasil/lulus di luar tabel tanpa rujukan `file:baris`, status FAIL
yang sebenarnya memenuhi Harapan, report (selain BLOCKED) tanpa bagian Periksa Diri, kriteria task yang belum
bernomor K, angka bersatuan (mis. `3-6 detik`, `7,20:1`, `45%`) di Ringkasan Fakta, Keputusan Implementasi,
atau Anomali tanpa rujukan `file:baris` di baris yang sama dan tanpa tanda perkiraan/HYPOTHESIS, dan log yang
dirujuk report tetapi ditimpa dengan perintah lain (menurut provenance.jsonl; `--append` tidak dihitung).
Tiga peringatan lain juga dari provenance.jsonl (v3.18):
- baris OK yang merujuk log dengan kode keluar bukan 0, kecuali baris itu menyebut kode keluarnya (`exit 1`,
  `kode_keluar=1`) atau menandainya uji merah;
- log yang perintahnya sama dengan run sebelumnya yang gagal lalu tertimpa (ulang sampai hijau), walau disebut di
  Anomali: jumlah run dan run yang gagal hanya terlihat di provenance.jsonl, jadi head yang mencocokkannya;
- log dari perintah yang memakai path sementara (scratchpad, Temp, /tmp), karena skrip di sana tidak bisa diperiksa ulang.

Rujukan `file:baris` boleh berupa path dari root repo, atau nama file saja bila tepat satu file bernama itu
ada di handoff/logs/. Salinan yang diabaikan git (mis. log mentah di handoff/logs/raw/) tidak membuat nama itu
ambigu bila hanya satu salinan yang tidak diabaikan (v3.18.1). Beberapa baris dari satu file: `file:12, 40, 41`, atau `file:12`, `:40` di sel yang sama.
Nomor baris dihitung seperti grep dan editor: baris dipisah CR LF, LF, atau CR. Form feed dan pemisah Unicode lain
(yang juga dipisah str.splitlines()) tidak memulai baris baru.

Report lama (AUDIT, pemeriksaan ulang): file kode dan dokumen bisa berubah sesudah report ditriase, sehingga kutipan yang dulu
benar terbaca salah. `--at <commit>` membaca semua file yang dirujuk (termasuk log, task, dan provenance.jsonl) pada
commit itu lewat git, tanpa mengubah working tree. `--at-report` memakai commit terakhir yang mengubah tiap report;
report yang belum di-commit dicek terhadap working tree. Commit itu bisa juga memuat suntingan head saat triase,
jadi bandingkan kedua mode: ERROR yang muncul di keduanya adalah temuan, sedangkan yang hanya muncul di salah satu
biasanya artefak perubahan file sesudah report ditulis.

Report berbahasa Inggris juga dikenali: judul `Self-check`, `Fact Summary`, `Implementation Decisions`, `Anomalies`
(report) dan `Acceptance criteria` (task); kolom `Criteria`, `Expected`, `Observed`, `Evidence`, `Status`; status
`PASS`, `FAIL`, `NOT TESTED`, `FOUND`, `NOT FOUND`, `UNSURE`; bukti `count(file, "pola")`; blok ```evidence; dan
`Final status: BLOCKED`. Kata kunci lain ditulis seperti di template.
Temuan berlabel ERROR atau WARNING (sebelum v3.20.1: MASALAH, PERINGATAN).
Exit code: 0 = tanpa ERROR, 1 = ada ERROR, 2 = report atau commit tidak ditemukan.
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
# Hasil yang diklaim tepat sesudah `hitung(...)`: `=0`, `= 3`, `→ 3` (v3.18.1).
KLAIM_HITUNG = re.compile(r"\s*`?\s*(?:==|=|→|->)\s*`?\s*(\d+)(?!\d|[.,]\d)")
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
# Nilai baku sejak v3.20: OK, FAIL, NONE (jawaban task FACT tanpa temuan), UNTESTED. Nama lain dan nama lama tetap diterima.
STATUS = {"OK": "OK", "PASS": "OK", "PASSED": "OK", "FOUND": "OK", "LOLOS": "OK", "TERPENUHI": "OK", "DITEMUKAN": "OK",
          "FAIL": "FAIL", "FAILED": "FAIL", "GAGAL": "FAIL", "TIDAK TERPENUHI": "FAIL",
          "NONE": "NONE", "NOT FOUND": "NONE", "TIDAK ADA": "NONE",
          "UNTESTED": "UNTESTED", "NOT TESTED": "UNTESTED", "UNSURE": "UNTESTED", "NOT SURE": "UNTESTED", "N/A": "UNTESTED",
          "-": "UNTESTED", "TIDAK DIUJI": "UNTESTED", "TIDAK YAKIN": "UNTESTED"}
# Judul dan baris yang dicari skrip, dalam bahasa Indonesia atau Inggris.
JUDUL_PERIKSA = re.compile(r"^#+\s*(?:Periksa Diri|Self[- ]?check)", re.I | re.M)
JUDUL_KRITERIA = r"(?:Kriteria terima|Acceptance criteria)"
BLOCKED = re.compile(r"(?:Status(?: akhir)?|Final status)\s*:\s*\**\s*BLOCKED", re.I)
BLOK_BUKTI = ("bukti", "evidence")
# Kutipan di prosa (v3.15): `teks` (`file:baris`), juga `a` dan `b` (`file:3..4`). Rujukan prosa boleh berupa rentang.
REF_PROSA = re.compile(rf"(?<![\w/.\\-])(?:({FILE}))?:(\d+)(?:(?:\.\.|–|-)(\d+))?((?:\s*,\s*\d+)*)(?![\d:])", re.I)
KUTIP_RUJUK = re.compile(r"`([^`\n]+)`\s*\(([^()\n]*)\)")
KUTIP_RANTAI = re.compile(r"`([^`\n]+)`\s*(?:,|;|/|\bdan\b|\band\b|\batau\b|\bor\b)\s*$", re.I)
SPAN = re.compile(r"`([^`\n]+)`")
PERINTAH = re.compile(r"^(?:&\s*)?(?:git|python3?|py|node|npm|npx|pnpm|yarn|pio|pip|cd|bash|sh|pwsh|powershell|cmd|curl|docker|"
                      r"make|cargo|go|dotnet|flutter|adb|orca|claude|agy|select-string|get-\w+)(?:\s|$)", re.I)
ELISI = re.compile(r"\s*(?:\.\.\.|…)\s*")
# Nama opsi baris perintah (`--reset-com8`, `--mode=x`) bukan kutipan isi log (v3.18.1).
OPSI = re.compile(r"--[A-Za-z][\w-]*(?:=\S+)?")
PEMISAH_TABEL = re.compile(r"^\s*\|?\s*:?-{3,}")
# Provenance (v3.18): path sementara di perintah, dan baris tabel yang mengakui kode keluar bukan 0.
SEMENTARA = re.compile(r"[\\/](?:scratchpad|temp|tmp)[\\/]", re.I)
AKUI_KELUAR = re.compile(r"(?:\bexit(?:[ _]?code)?|\bkode[ _]keluar)\D{0,3}(\d+)", re.I)
AKUI_MERAH = re.compile(r"\b(?:merah|red)\b", re.I)


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


def pisah_baris(teks):
    """Baris seperti grep -n dan editor: dipisah CR LF, LF, atau CR saja. str.splitlines() juga memisah form feed,
    \\x1c-\\x1e, \\x85, dan U+2028/2029, sehingga nomor baris log yang memuatnya bergeser dari nomor di grep."""
    b = re.split(r"\r\n|\r|\n", teks)
    return b[:-1] if b and b[-1] == "" else b


def tanpa_spasi_sama(s):
    return re.sub(r"\s*=\s*", "=", rapi(s))


def hash_isi(isi):
    """SHA-256 isi file (bytes) dengan CRLF disamakan menjadi LF (sama persis dengan record.py)."""
    return hashlib.sha256(isi.replace(b"\r\n", b"\n")).hexdigest()


def asal_dipakai(berkas):
    """Path relatif catatan asal: provenance.jsonl, atau asal.jsonl (nama sebelum v3.12) bila hanya itu yang ada."""
    return ASAL_LAMA if not berkas.ada(berkas.root / ASAL) and berkas.ada(berkas.root / ASAL_LAMA) else ASAL


def muat_asal(berkas):
    """Semua catatan per file dari handoff/logs/provenance.jsonl, urut waktu ({path relatif huruf kecil: [catatan]});
    None bila tidak ada."""
    p = berkas.root / asal_dipakai(berkas)
    if not berkas.ada(p):
        return None
    asal = {}
    for l in pisah_baris(berkas.teks(p)):
        try:
            rec = json.loads(l)
        except ValueError:
            continue
        if isinstance(rec, dict) and rec.get("file") and rec.get("sha256"):
            asal.setdefault(rec["file"].replace("\\", "/").lower(), []).append(rec)
    return asal


def kode_gagal(rec):
    return rec.get("kode_keluar") not in (0, None)


def pisah_run(riwayat):
    """(catatan yang tertimpa, catatan yang isinya ada di log sekarang) dari riwayat satu log.
    Isi log sekarang berasal dari run terakhir tanpa --append, ditambah --append sesudahnya; redact bukan run."""
    runs = [r for r in riwayat if r.get("jenis") != "redact"]
    awal = max((i for i, r in enumerate(runs) if not r.get("tambah")), default=0)
    return runs[:awal], runs[awal:]


def cek_kode_keluar(no, baris, refs, berkas, asal, hasil):
    """Baris OK yang merujuk log gagal (v3.18). Contoh: alat uji mencetak lulus=20/20 tetapi keluar 1 karena
    syarat keluarnya masih 19, dan Harapan tidak menuntut kode keluar. Uji merah yang diharapkan diakui di barisnya."""
    if asal is None:
        return
    dilihat = set()
    for nama, _ in refs:
        p, _ = berkas.cari(nama)
        rel = berkas.rel(p) if p else None
        if not rel or rel in dilihat or not rel.lower().startswith("handoff/logs/"):
            continue
        dilihat.add(rel)
        kode = [r.get("kode_keluar") for r in pisah_run(asal.get(rel.lower(), []))[1] if kode_gagal(r)]
        if not kode or AKUI_MERAH.search(baris) or str(kode[-1]) in AKUI_KELUAR.findall(baris):
            continue
        hasil.peringatan(no, f"status OK merujuk {rel}, padahal perintahnya keluar dengan kode {kode[-1]} (provenance); bila "
                             "kegagalan itu memang diharapkan, sebut kode keluarnya di baris ini; bila tidak, ubah statusnya")


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
        riwayat = asal.get(rel.lower(), [])
        rec = riwayat[-1] if riwayat else None
        if rec is None:
            pesan = f"log {rel} tidak tercatat di {sumber} (tidak dibuat lewat record.py)"
            (hasil.masalah if wajib else hasil.peringatan)(0, pesan)
        elif hash_isi(berkas.mentah(p)) != rec["sha256"]:
            hasil.masalah(0, f"log {rel} berubah setelah dicatat record.py (perintah: {rec.get('perintah', '?')}); "
                             "jalankan ulang perintahnya, jangan mengedit log")
        else:
            hasil.dicek += 1
        # Log yang ditimpa dengan perintah lain (pola mempersempit perintah bukti, v3.15); --append dan redact bukan penimpaan.
        timpa = [(a, b) for a, b in zip(riwayat, riwayat[1:])
                 if b.get("jenis") != "redact" and not b.get("tambah") and a.get("perintah") != b.get("perintah")]
        if timpa:
            a, b = timpa[-1]
            hasil.peringatan(0, f"log {rel} ditimpa dengan perintah lain: `{a.get('perintah', '?')}` ({a.get('mulai', '?')}) -> "
                                f"`{b.get('perintah', '?')}` ({b.get('mulai', '?')}); sebut alasannya di Anomali, "
                                "atau simpan output tiap perintah di log bernama sendiri")
        # Ulang sampai hijau (v3.18): run yang gagal tertimpa, jadi hanya provenance yang menyimpannya.
        lama, kini = pisah_run(riwayat)
        if kini and not any(kode_gagal(r) for r in kini):
            sama = [r for r in lama if r.get("perintah") == kini[0].get("perintah")]
            gagal = sum(kode_gagal(r) for r in sama)
            if gagal:
                hasil.peringatan(0, f"log {rel}: perintah yang sama dijalankan {len(sama) + 1} kali, {gagal} run lebih dulu gagal "
                                    "lalu tertimpa (provenance); sebut jumlah run dan penyebabnya di Anomali")
        sementara = next((r for r in kini if SEMENTARA.search(r.get("perintah", ""))), None)
        if sementara:
            hasil.peringatan(0, f"log {rel} dibuat perintah yang memakai path sementara: `{sementara.get('perintah')}`; "
                                "skrip di sana tidak bisa diperiksa ulang. Simpan alatnya di repo, atau jalankan perintah di task")


def cek_kriteria(path_report, data, berkas, hasil):
    """Kriteria task di tabel Data report: nomor K1..Kn (cek_nomor_k) dan templat tabel Data (cek_templat).
    `data` berisi (sel Kriteria, sel Harapan atau None, nomor baris) dari tabel Data report."""
    m = re.match(r"REPORT-([\w-]+?)\.md$", path_report.name, re.I)
    if not m:
        return
    calon = berkas.glob(f"handoff/tasks/TASK-{m.group(1)}-*.md") + berkas.glob(f"handoff/tasks/TASK-{m.group(1)}.md")
    if not calon:
        return
    teks = berkas.teks(calon[0])
    hilang = cek_nomor_k(calon[0].name, teks, [k for k, _, _ in data], hasil)
    cek_templat(calon[0].name, teks, data, hilang, hasil)


def cek_nomor_k(nama_task, teks, kolom_kriteria, hasil):
    """Setiap kriteria K1..Kn di task harus punya baris di tabel Data (kolom Kriteria diawali nomornya).
    Mengembalikan nomor K yang tidak punya baris."""
    mk = re.search(rf"^#+\s*{JUDUL_KRITERIA}[^\n]*\n(.*?)(?=^#+\s|\Z)", teks, re.M | re.S | re.I)
    if not mk or not mk.group(1).strip():
        return set()
    # Hanya nomor di awal kriteria (sel pertama tabel, atau awal butir), bukan sebutan K9 di tengah teks.
    awal = re.compile(r"^\s*(?:\|\s*)?(?:[-*]\s+|\d+[.)]\s+)?[*`]*\s*K(\d+)\b")
    nomor = sorted({int(m.group(1)) for m in (awal.match(l) for l in pisah_baris(mk.group(1))) if m})
    if not nomor:
        hasil.peringatan(0, f"kriteria terima di {nama_task} belum bernomor K1, K2, ...; kelengkapan tabel Data tidak dicek otomatis")
        return set()
    hilang = set()
    for n in nomor:
        if not any(re.match(rf"^\W*K{n}\b", c) for c in kolom_kriteria):
            hasil.masalah(0, f"kriteria K{n} di {nama_task} tidak punya baris di tabel Data (kolom Kriteria diawali K{n})")
            hilang.add(n)
        else:
            hasil.dicek += 1
    return hilang


def tabel_md(teks):
    """Tabel Markdown di luar blok kode: [(sel header huruf kecil, [sel per baris])]."""
    hasil, baris, i, pagar = [], pisah_baris(teks), 0, None
    while i < len(baris):
        t = baris[i]
        m = re.match(r"^\s*(```|~~~)", t)
        if m:
            pagar = None if pagar and t.strip().startswith(pagar) else (pagar or m.group(1))
            i += 1
            continue
        if pagar is None and t.strip().startswith("|"):
            j = i
            while j < len(baris) and baris[j].strip().startswith("|"):
                j += 1
            if j - i >= 3 and re.match(r"^\s*\|?\s*:?-{3,}", baris[i + 1]):
                hasil.append(([c.lower() for c in sel(baris[i])], [sel(b) for b in baris[i + 2:j]]))
            i = j
            continue
        i += 1
    return hasil


def kunci_sel(s):
    """Isi sel untuk dibandingkan: tanpa backtick dan tanda tebal, spasi dirapatkan, huruf kecil."""
    return rapi(s.replace("`", "").replace("*", "")).lower()


def cek_templat(nama_task, teks, data, hilang_k, hasil):
    """Templat tabel Data di task (kolom Kriteria, Harapan, Teramati; Teramati dan Status kosong): setiap baris templat
    ada di tabel Data report dengan Harapan yang sama. Satu baris templat boleh dipecah menjadi beberapa baris report
    yang kolom Kriterianya berawalan sama (mis. `K2 A1` -> `K2 A1 boot`, `K2 A1 offset`)."""
    def kosong(s):
        return not rapi(s) or re.fullmatch(r"<[^<>]*>", rapi(s)) is not None

    templat = []
    for h, rows in tabel_md(teks):
        ik = 0 if h and ("kriteria" in h[0] or "criteri" in h[0]) else None
        ih = next((i for i, c in enumerate(h) if "harapan" in c or "expected" in c), None)
        it = next((i for i, c in enumerate(h) if "teramati" in c or "observed" in c), None)
        ist = next((i for i, c in enumerate(h) if "status" in c), None)
        if ik is None or ih is None or it is None:
            continue
        rows = [c for c in rows if len(c) == len(h) and kunci_sel(c[ik])]
        if rows and all(kosong(c[it]) and (ist is None or kosong(c[ist])) for c in rows):
            templat += [(kunci_sel(c[ik]), rapi(c[ik]), kunci_sel(c[ih]), rapi(c[ih])) for c in rows]
    if not templat:
        return
    dipakai = set()
    for k, harapan, no in data:
        kk = kunci_sel(k)
        cocok = [t for t in templat if kk == t[0] or (kk.startswith(t[0]) and not kk[len(t[0])].isalnum())]
        if not cocok:
            continue
        t = max(cocok, key=lambda t: len(t[0]))
        dipakai.add(t[0])
        if harapan is None or kunci_sel(harapan) != t[2]:
            hasil.masalah(no, f"Harapan \"{rapi(harapan or '')}\" berbeda dari templat tabel Data di {nama_task} (\"{t[3]}\"); "
                              "salin Harapan persis dari task, dan tulis FAIL bila Teramati tidak memenuhinya")
        else:
            hasil.dicek += 1
    for t in templat:
        mk = re.match(r"k(\d+)\b", t[0])
        if t[0] not in dipakai and not (mk and int(mk.group(1)) in hilang_k):
            hasil.masalah(0, f"baris templat \"{t[1]}\" dari {nama_task} tidak ada di tabel Data report (kolom Kriteria diawali \"{t[1]}\")")


def cek_angka(no, baris, hasil):
    """Angka bersatuan tanpa rujukan file:baris di baris yang sama, kecuali ditandai perkiraan/HYPOTHESIS."""
    teks = re.sub(r"`[^`]*`", " ", baris)
    if REF.search(baris) or PERKIRAAN.search(teks):
        return
    m = ANGKA_SATUAN.search(teks)
    if m:
        hasil.peringatan(no, f"angka \"{m.group(0).strip()}\" tanpa rujukan file:baris di baris ini; "
                             "rujuk sumbernya, atau tandai sebagai perkiraan/HYPOTHESIS")


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
        self._indeks = self._pohon = self._bersama = None

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
        """Semua file di bawah folder p (rekursif), terurut supaya pesan yang menyebut file lain sama di setiap run;
        [] bila p bukan folder."""
        if self.rev is None:
            return sorted(q for q in p.rglob("*") if q.is_file()) if p.is_dir() else []
        r = self.rel(p)
        if r is None:
            return []
        awal = r.rstrip("/") + "/"
        return sorted(self.root / n for n in self.pohon() if n.startswith(awal))

    def diabaikan(self, p):
        """True bila file di working tree diabaikan git (.gitignore). Pada commit (`rev`) semua file ter-track."""
        if self.rev is not None:
            return False
        r = self.rel(p)
        return r is not None and self.git("check-ignore", "-q", "--", r).returncode == 0

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
            if len(cocok) > 1:
                # Salinan yang diabaikan git (log mentah di handoff/logs/raw/) bukan bukti bersama; bila hanya satu
                # salinan yang tidak diabaikan, itulah yang dirujuk, sama dengan yang dibaca --at-report (v3.18.1).
                cocok = [q for q in cocok if not self.diabaikan(q)] or cocok
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
            asli = pisah_baris(self.teks(path))
            self._isi[path] = (asli, [rapi(b) for b in asli])
        return self._isi[path]

    def semua_log(self):
        return [p for daftar in self.indeks().values() for p in daftar]

    def log_bersama(self):
        """(log yang tidak diabaikan git, jumlah log yang diabaikan), untuk pencarian cadangan cari_baris_log (v3.20.1).
        Log mentah yang diabaikan git bukan bukti bersama dan bisa berukuran GB: membaca semuanya membuat satu cek berjalan
        belasan menit dengan memori GB. Pada commit (`rev`) semua file ter-track; di luar repo git semua log dicari."""
        if self._bersama is None:
            semua, abaikan = self.semua_log(), set()
            if self.rev is None and semua:
                rel = {self.rel(p): p for p in semua}
                masuk = b"\0".join(r.encode("utf-8") for r in rel if r)
                out = subprocess.run(["git", "-C", str(self.root), "check-ignore", "--stdin", "-z"], input=masuk,
                                     capture_output=True).stdout
                abaikan = {rel[n] for n in (x.decode("utf-8", "replace") for x in out.split(b"\0")) if n in rel}
            self._bersama = ([p for p in semua if p not in abaikan], len(abaikan))
        return self._bersama

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
        self.temuan.append((no, "ERROR", pesan))

    def peringatan(self, no, pesan):
        self.temuan.append((no, "WARNING", pesan))

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


def cek_klaim_hitung(no, teks, berkas, hasil):
    """Klaim `hitung(lingkup, "pola")=N` di luar kolom Bukti tabel kriteria: N harus sama dengan jumlah baris yang cocok
    (v3.18.1). Contoh: lampiran task FACT berisi klaim `=0` yang ternyata tidak 0, tetapi lolos karena
    dulu hanya sel Bukti tabel kriteria yang dihitung ulang. Lingkup yang disingkat (`hitung(..., "ERROR")`) dilewati."""
    for m in HITUNG.finditer(teks):
        klaim = KLAIM_HITUNG.match(teks, m.end())
        if not klaim or ELISI.search(m.group(1)):
            continue
        for nama, pola, jumlah in hitung_cocok(no, m.group(0), berkas, hasil):
            if jumlah != int(klaim.group(1)):
                hasil.masalah(no, f"klaim hitung({nama}, \"{pola}\")={klaim.group(1)}, padahal {jumlah} baris di {nama} cocok")


def cek_lampiran(tabel, berkas, hasil):
    """Tabel tanpa kolom Bukti dan Status, mis. lampiran task FACT: klaim `hitung(...)=N` di selnya dicek, kecuali di
    kolom Harapan, yang berisi syarat, bukan hasil (v3.18.1)."""
    h = [c.lower() for c in sel(tabel[0][1])]
    harapan = {i for i, c in enumerate(h) if "harapan" in c or "expected" in c}
    for no, baris in tabel[2:]:
        for i, c in enumerate(sel(baris)):
            if i not in harapan:
                cek_klaim_hitung(no, c, berkas, hasil)


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
    bersama, diabaikan = berkas.log_bersama()
    for p in bersama:
        if p not in dirujuk and any(q in b for b in berkas.baris(p)[1]):
            hasil.masalah(no, f"baris log tidak ada di file yang dirujuk report; baris yang sama ada di "
                              f"{p.relative_to(berkas.root).as_posix()}. Rujuk file itu bila memang berasal dari sana")
            return
    lewat = f" ({diabaikan} log yang diabaikan git tidak dicari)" if diabaikan else ""
    hasil.masalah(no, f"baris log tidak ada di file log mana pun{lewat}: \"{q[:120]}\"")


def norm_status(teks):
    s = re.sub(r"[^A-Z/ -]", "", rapi(teks).upper()).strip()
    return STATUS.get(re.sub(r"\s+", " ", s), "")


def terlihat(teramati, baris_bukti):
    gabung = [tanpa_spasi_sama(b) for b in baris_bukti]
    token = TOKEN.findall(teramati)
    if token:
        # Kunci dan nilai boleh dipisah `=`, `:`, atau spasi: test runner mencetak `tests 328`, bukan `tests=328`.
        return all(any(re.search(rf"(?<![\w.]){re.escape(k)}(?:=|:\s*|\s+){re.escape(v)}(?![\w.])", g) for g in gabung) for k, v in token)
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


def cek_tabel(tabel, berkas, hasil, data=None, asal=None):
    (_, header), rows = tabel[0], tabel[2:]
    h = [c.lower() for c in sel(header)]

    def kolom(*nama):
        return next((i for i, c in enumerate(h) if any(n in c for n in nama)), None)

    if data is not None and h and ("kriteria" in h[0] or "criteri" in h[0]):
        ih = kolom("harapan", "expected")
        for no, b in rows:
            c = sel(b)
            if c:
                data.append((c[0], c[ih] if ih is not None and ih < len(c) else None, no))

    fakta = kolom("pertanyaan", "question") is not None  # tabel task FACT: Jawaban berperan sebagai Teramati
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
        if status == "NONE":
            if not HITUNG.search(ambil("bukti")):
                hasil.masalah(no, "status NONE butuh bukti `hitung(lingkup, \"pola\")` yang hasilnya 0")
            for nama, pola, jumlah in hitung_cocok(no, ambil("bukti"), berkas, hasil):
                if jumlah:
                    hasil.masalah(no, f"status NONE, padahal {jumlah} baris di {nama} cocok dengan \"{pola}\"")
            continue
        if status not in ("OK", "FAIL"):
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
                                      "(tulis UNTESTED sampai user menjawab)")
                else:
                    hasil.peringatan(no, "bukti berupa pengamatan user; head yang memverifikasinya")
            else:
                hasil.masalah(no, "status OK tanpa rujukan file:baris di kolom Bukti")
            continue
        bukti = [b for b in (ambil_baris(no, nama, n, berkas, hasil) for nama, n in refs) if b is not None]
        if status == "OK":
            cek_kode_keluar(no, baris, refs, berkas, asal, hasil)
        teramati = ambil("teramati")
        if bukti and not ada_hitung and not fakta and rapi(teramati) not in ("", "-") and not terlihat(teramati, bukti):
            hasil.masalah(no, f"Teramati \"{rapi(teramati)}\" tidak terlihat di baris yang dirujuk")
        nilai = nilai_harapan(ambil("harapan"), teramati)
        if nilai is False and status == "OK":
            hasil.masalah(no, f"status OK, padahal Teramati \"{rapi(teramati)}\" tidak memenuhi Harapan \"{rapi(ambil('harapan'))}\"")
        elif nilai is True and status == "FAIL":
            hasil.peringatan(no, f"status FAIL, padahal Teramati memenuhi Harapan \"{rapi(ambil('harapan'))}\"")
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


def rujukan_prosa(teks):
    """[(nama file, awal, akhir)] dari teks: `f.log:3`, `f.log:3..4`, `f.log:3-4`, `f.log:3, 9`, dan `:9` lanjutan."""
    hasil, terakhir = [], None
    for m in REF_PROSA.finditer(teks):
        if m.group(1):
            terakhir = m.group(1)
        elif not terakhir:
            continue
        a = int(m.group(2))
        hasil.append((terakhir, a, max(a, int(m.group(3) or a))))
        hasil += [(terakhir, int(n), int(n)) for n in re.findall(r"\d+", m.group(4) or "")]
    return hasil


def bukan_kutipan(s):
    """Span berbacktick yang bukan kutipan isi file: rujukan, nama file, hitung(), user:, perintah, atau nama opsi."""
    s = s.strip()
    return (not s or REF_PROSA.fullmatch(s) is not None or (REF_PROSA.search(s) is not None and re.search(FILE, s, re.I) is not None)
            or re.fullmatch(FILE, s, re.I) is not None or re.search(r"(?:hitung|count)\(|\buser\s*:", s, re.I) is not None
            or PERINTAH.match(s) is not None or OPSI.fullmatch(s) is not None)


def kutipan_kolom(q, asli, n):
    """True bila kutipan q berbentuk `<nama kolom> <isi sel>` untuk baris ke-n (mulai 1) di asli yang berupa baris tabel
    Markdown; nama kolom diambil dari kepala tabel itu (v3.18.1, tanda palsu `Konfirmasi +3.750 s` dari tabel di log)."""
    i = n - 1
    if not 0 <= i < len(asli) or not asli[i].lstrip().startswith("|"):
        return False
    j = i
    while j > 0 and asli[j - 1].lstrip().startswith("|"):
        j -= 1
    if j + 1 >= i or not PEMISAH_TABEL.match(asli[j + 1]):
        return False
    kepala, isi = sel(asli[j]), sel(asli[i])
    if len(kepala) != len(isi):
        return False
    q = rapi(q)
    for nama, nilai in zip(kepala, isi):
        nama = rapi(nama).strip("`*")
        if nama and q.lower().startswith(nama.lower()):
            sisa = q[len(nama):].lstrip(" :=")
            if sisa and sisa in rapi(nilai):
                return True
    return False


def cek_prosa(no, t, berkas, hasil):
    """Kutipan di prosa: `teks` (`file:baris`) harus ada di baris yang dirujuk bila rujukannya file log (v3.15).
    Contoh: kutipan karangan di bagian Anomali dulu lolos, karena hanya blok bukti, tabel, dan blok kode yang dicek."""
    for m in KUTIP_RUJUK.finditer(t):
        refs = rujukan_prosa(m.group(2))
        if not any(n.lower().endswith(LOG_EXT) for n, _, _ in refs):
            continue
        # Kutipan di dalam kurung sesudah rujukannya, mis. (`a.log:1` `START ip=...`), adalah yang dikutip dari baris itu.
        kutipan = [s for s in SPAN.findall(m.group(2)) if not bukan_kutipan(s)]
        if not kutipan:
            kutipan, sebelum = [m.group(1)], t[:m.start()]
            mr = KUTIP_RANTAI.search(sebelum)
            while mr:
                kutipan.insert(0, mr.group(1))
                sebelum = sebelum[:mr.start()]
                mr = KUTIP_RANTAI.search(sebelum)
            kutipan = [q for q in kutipan if not bukan_kutipan(q)]
        calon, files, catatan, tak_dicek, rentang = [], [], [], [], []
        for nama, a, b in refs:
            p, galat = berkas.cari(nama)
            if p is None:
                if nama.lower().endswith(LOG_EXT) and galat not in tak_dicek:
                    tak_dicek.append(galat)
                continue
            isi = berkas.baris(p)[1]
            if a < 1 or a > len(isi):
                catatan.append(f"{nama} hanya {len(isi)} baris")
            potong = isi[a - 1:min(len(isi), b)] if a >= 1 else []
            calon += potong + ([" ".join(potong)] if b > a else [])
            files.append(p)
            rentang.append((p, a, b))
        if not files:
            # Dulu dilewati diam-diam; nama ambigu atau file yang tidak ada berarti kutipan itu tidak pernah dicek (v3.18.1).
            if kutipan and tak_dicek:
                daftar = ", ".join(f"`{rapi(q)[:60]}`" for q in kutipan)
                hasil.peringatan(no, f"kutipan {daftar} tidak dicek: {'; '.join(tak_dicek)}")
            continue
        for q in kutipan:
            bagian = [rapi(x) for x in ELISI.split(q) if rapi(x)]
            if not bagian:
                continue
            if any(all(x in c for x in bagian) for c in calon) or (
                    len(bagian) == 1 and any(kutipan_kolom(q, berkas.baris(p)[0], n) for p, a, b in rentang for n in range(a, b + 1))):
                hasil.dicek += 1
                continue
            ada = [f"{p.relative_to(berkas.root).as_posix()}:{i}" for p in files
                   for i, c in enumerate(berkas.baris(p)[1], 1) if all(x in c for x in bagian)][:3]
            ruj = ", ".join(f"{n}:{a}" + (f"..{b}" if b > a else "") for n, a, b in refs)
            petunjuk = (f"; teks itu ada di {', '.join(ada)}" if ada else "; teks itu tidak ada di file yang dirujuk") + \
                       (f" ({'; '.join(catatan)})" if catatan else "")
            pesan = f"kutipan `{rapi(q)[:100]}` tidak ada di baris yang dirujuk ({ruj}){petunjuk}"
            (hasil.masalah if re.search(r"\d", q) else hasil.peringatan)(no, pesan)


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
    baris = pisah_baris(teks)
    hasil = Hasil(path_report.name)
    dirujuk = file_dirujuk(teks, berkas, path_report)
    i, ada_tabel, data, bagian = 0, False, [], ""
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
            if len(tabel) >= 3 and PEMISAH_TABEL.match(tabel[1][1]):
                if cek_tabel(tabel, berkas, hasil, data, asal):
                    ada_tabel = True
                else:
                    cek_lampiran(tabel, berkas, hasil)
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
        if not s.startswith(("#", ">")):
            cek_prosa(i + 1, t, berkas, hasil)
            cek_klaim_hitung(i + 1, t, berkas, hasil)
        i += 1
    blocked = BLOCKED.search(teks)
    # Log yang hanya tercantum di output git status (Periksa Diri) bukan bukti, jadi asalnya tidak dicek (v3.9.2).
    bukti_log = file_dirujuk("\n".join(b for b in baris if not STATUS_GIT.match(b)), berkas, path_report)
    cek_asal(bukti_log, berkas, asal, wajib_asal, hasil)
    if not blocked:
        cek_kriteria(path_report, data, berkas, hasil)
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
        print(f"  Ringkas: {h.dicek} bukti dicek, {h.jumlah('ERROR')} ERROR, {h.jumlah('WARNING')} WARNING.")
        total += h.jumlah("ERROR")
    if total:
        print("Perbaiki ERROR di atas: kutip baris yang benar dari file, atau ubah status kriterianya menjadi FAIL / UNTESTED (task FACT: UNSURE).")
    return 2 if kurang and not total else (1 if total else 0)


if __name__ == "__main__":
    sys.exit(main())
