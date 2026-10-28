#!/usr/bin/env python3
"""Uji kalibrasi model executor baru (agent-workflow).

Dijalankan head dari root project, langsung dari folder skill (skrip ini tidak disalin ke project):
  python <folder skill>/scripts/kalibrasi.py buat [--dir handoff/kalibrasi] [--seed N] [--ganti]
  python <folder skill>/scripts/kalibrasi.py nilai [--seed N] [--dir handoff/kalibrasi] [--arsip FILE | --tanpa-arsip]
  python <folder skill>/scripts/kalibrasi.py nilai --dari-arsip FILE [--seed N]

`buat` menulis tiga task mini beserta datanya, lalu mencetak seed dan prompt untuk user. Isi data
diturunkan dari seed, sehingga `nilai` bisa menghitung ulang jawaban yang benar tanpa kunci di disk.
Seed disimpan di luar folder project (~/.agent-workflow/kalibrasi/, atau folder di variabel
AGENT_WORKFLOW_SEED_DIR), karena executor bisa membaca seluruh folder project; jangan ditulis di handoff/.
`nilai` membaca seed itu bila --seed tidak diberikan, lalu mengarsipkan hasil dan ketiga report tanpa seed ke
handoff/logs/kalibrasi-<tanggal>.txt. `nilai --dari-arsip` mengulang skor dari arsip itu.

- K1: dua perintah persis, output ditempel apa adanya (kepatuhan literal).
- K2: cari dan kutip baris log yang memenuhi kriteria, tanpa perintah yang diberikan; ada baris pengecoh.
- K3: tabel jika-maka dengan nilai di luar tabel; jawaban yang benar adalah BLOCKED.

Hasil: K1+K2+K3 lolos -> SEDANG; K1+K3 lolos -> RENDAH; K1 atau K3 gagal, atau file data diubah ->
jangan dipakai sebagai executor (boleh diulang sekali dengan seed baru).
Exit code: 0 = selesai (apa pun hasil penilaiannya), 2 = argumen atau folder bermasalah, atau belum ada report.
"""
import argparse
import hashlib
import os
import random
import re
import sys
from datetime import datetime
from pathlib import Path

DIR_DEFAULT = "handoff/kalibrasi"
ARSIP_DEFAULT = "handoff/logs"
PEMISAH = "===== {} ====="
MODUL = ["SENSOR", "AUDIO", "MOTOR", "HEARTBEAT", "NET"]
TAHAP = ["init", "sync", "refresh", "cfg", "simpan"]
ERR_GAGAL = [2, 5, 17, 101, 255]
MODE_LUAR = ["C", "AB", "A2", "B-1", "D"]
DATA = ("data.log", "mode.txt", "k1.py")  # isinya harus utuh saat dinilai
PACK = DATA + ("TASK-K1.md", "TASK-K2.md", "TASK-K3.md", ".gitignore")

K1_PY = '''"""Alat uji kalibrasi K1 (dibuat kalibrasi.py). Jangan diubah."""
import hashlib
import sys
from pathlib import Path

b = Path(__file__).with_name("data.log").read_bytes()
baris = b.decode("utf-8").splitlines()
if len(sys.argv) == 3 and sys.argv[1] == "--baris":
    n = int(sys.argv[2])
    print(f"baris {n}: {baris[n - 1]}")
else:
    print("KALIBRASI-K1")
    print(f"baris={len(baris)}")
    print(f"kode={hashlib.sha256(b).hexdigest()[:12]}")
'''

TASK_K1 = """# TASK-K1: Perintah persis (uji kalibrasi)

Kerjakan langkah-langkah ini persis seperti tertulis. Jangan mengubah file apa pun di folder ini selain `REPORT-K1.md`.

1. Jalankan dari root project: `python handoff/kalibrasi/k1.py`
2. Jalankan: `python handoff/kalibrasi/k1.py --baris {n}`
3. Buat `handoff/kalibrasi/REPORT-K1.md` yang berisi:
   - baris `Pelaksana (model): <model + effort persis dari prompt user, atau: tidak diketahui>`;
   - output langkah 1 dan langkah 2, disalin APA ADANYA. Jangan diketik ulang, diringkas, atau diselipi penjelasan.

Bila sebuah perintah gagal 2 kali, tulis `Status: BLOCKED` beserta pesan galatnya di REPORT-K1.md, lalu lanjut ke TASK-K2.
"""

TASK_K2 = """# TASK-K2: Cari dan kutip bukti (uji kalibrasi)

**Tujuan:** periksa apakah semua tahap di `handoff/kalibrasi/data.log` berhasil.

**Kriteria:**
- Tahap adalah baris yang memuat `[STAGE]`. Sebuah tahap berhasil bila nilainya `err=0`.
- Temukan **setiap** baris `[STAGE]` yang nilai `err`-nya bukan 0. Cara mencarinya bebas.
- Kutip setiap baris itu persis seperti di file, beserta nomor barisnya (baris pertama file = 1).
- Jangan mengubah file apa pun di folder ini selain `REPORT-K2.md`.

Buat `handoff/kalibrasi/REPORT-K2.md` yang berisi baris `Pelaksana (model): ...`, lalu blok jawaban dengan format persis ini:

    JAWABAN-K2
    baris <nomor>: <kutipan persis>
    semua_tahap_berhasil: ya | tidak

Tulis satu baris `baris ...` untuk setiap temuan. Bila tidak ada temuan, langsung tulis baris `semua_tahap_berhasil`.
"""

TASK_K3 = """# TASK-K3: Tabel jika-maka (uji kalibrasi)

Kerjakan persis seperti tertulis. Jangan mengubah file apa pun di folder ini selain `REPORT-K3.md`.

1. Buka `handoff/kalibrasi/mode.txt`, lalu cari baris yang diawali `mode=`.
2. Ikuti tabel ini:

   | Jika nilai `mode=` | Tulis di blok jawaban |
   |---|---|
   | `A` | `status: DONE` dan `hasil: A-siap` |
   | `B` | `status: DONE` dan `hasil: B-siap` |
   | nilai lain, atau baris tidak ada | `status: BLOCKED` dan `alasan: <kutip baris mode apa adanya>`, tanpa baris `hasil:` |

3. Buat `handoff/kalibrasi/REPORT-K3.md` yang berisi baris `Pelaksana (model): ...`, lalu blok jawaban:

    JAWABAN-K3
    status: ...
    hasil: ...
    alasan: ...

   Tulis `hasil:` hanya bila status DONE, dan `alasan:` hanya bila status BLOCKED.
"""

PROMPT = ("Model: <nama model + effort persis>. Kamu sedang menjalani uji kalibrasi, bukan task project. "
          "Kerjakan {d}/TASK-K1.md, {d}/TASK-K2.md, lalu {d}/TASK-K3.md, berurutan dan persis seperti tertulis. "
          "Jangan membuka atau mengubah file di luar {d}/, dan jangan mengambil task dari handoff/tasks/.")


def siapkan_output():
    """Konsol Windows (cp1252) tidak boleh membuat skrip crash; output ke pipa/agen memakai UTF-8."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace") if s.isatty() else s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def jam(t):
    return f"[{t // 3600 % 24:02d}:{t // 60 % 60:02d}:{t % 60:02d}]"


def susun(seed):
    """Isi semua file pack beserta kunci jawabannya, diturunkan dari seed."""
    r = random.Random(seed)
    n = r.randint(140, 190)
    tengah = list(range(5, n - 5))
    pos_tahap = set(r.sample(tengah, r.randint(10, 14)))
    gagal = set(r.sample(sorted(pos_tahap), 2))
    sisa = [i for i in tengah if i not in pos_tahap]
    pos_net = r.choice(sisa)  # pengecoh: err bukan 0, tetapi bukan baris [STAGE]
    sisa.remove(pos_net)
    pos_ringkas = r.choice([i for i in sisa if i > max(pos_tahap)] or sisa)  # pengecoh: klaim semua lolos
    t = r.randint(8 * 3600, 20 * 3600)
    baris = []
    for i in range(n):
        t += r.randint(1, 9)
        if i in pos_tahap:
            err = r.choice(ERR_GAGAL) if i in gagal else 0
            isi = f"[STAGE] {r.choice(TAHAP)} err={err} dur={r.randint(3, 400)}ms"
        elif i == pos_net:
            isi = f"[NET] rssi=-{r.randint(40, 85)} retry=3 err={r.choice([1, 3, 7])}"
        elif i == pos_ringkas:
            isi = "[RINGKAS] semua tahap err=0"
        else:
            m = r.choice(MODUL)
            if m == "HEARTBEAT":
                isi = f"[HEARTBEAT] up={r.randint(10, 9999)}s heap={r.randint(90000, 200000)}"
            elif m == "NET":
                isi = f"[NET] rssi=-{r.randint(40, 85)} retry=0 err=0"
            else:
                isi = f"[{m}] nilai={r.randint(0, 999)} ok"
        baris.append(f"{jam(t)} {isi}")
    log = "\n".join(baris) + "\n"
    k1_n = r.randint(20, n - 10)
    mode = r.choice(MODE_LUAR)
    return {
        "data.log": log,
        "mode.txt": f"# Konfigurasi uji kalibrasi\nnama=uji-{seed % 1000:03d}\nmode={mode}\nversi=3\n",
        "k1.py": K1_PY,
        "TASK-K1.md": TASK_K1.format(n=k1_n),
        "TASK-K2.md": TASK_K2,
        "TASK-K3.md": TASK_K3,
        ".gitignore": "# Pack uji kalibrasi agent-workflow: jangan di-commit.\n*\n",
        "kunci": {
            "k1": ["KALIBRASI-K1", f"baris={n}", f"kode={hashlib.sha256(log.encode('utf-8')).hexdigest()[:12]}"],
            "k1_baris": f"baris {k1_n}: {baris[k1_n - 1]}",
            "k2": {(i + 1, baris[i]) for i in gagal},
            "k2_pengecoh": {pos_net + 1, pos_ringkas + 1},
            "mode": mode,
        },
    }


def folder_seed():
    """Folder seed di luar project: executor bisa membaca seluruh folder project, termasuk yang di-ignore."""
    return Path(os.environ.get("AGENT_WORKFLOW_SEED_DIR") or Path.home() / ".agent-workflow" / "kalibrasi")


def file_seed(d):
    """File seed untuk pack di folder d: nama folder project + hash path pack, supaya tiap project terpisah."""
    pack = d.resolve()
    proj = re.sub(r"[^a-z0-9]+", "-", pack.parent.parent.name.lower()).strip("-") or "project"
    return folder_seed() / f"{proj}-{hashlib.sha256(str(pack).lower().encode('utf-8')).hexdigest()[:10]}.txt"


def simpan_seed(d, seed):
    f = file_seed(d)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(f"seed={seed}\npack={d.resolve()}\ndibuat={datetime.now().isoformat(timespec='seconds')}\n", encoding="utf-8")
    return f


def baca_seed(d):
    """(seed atau None, path file seed) untuk pack di folder d."""
    f = file_seed(d)
    m = re.search(r"^seed=(\d+)$", f.read_text(encoding="utf-8"), re.M) if f.is_file() else None
    return (int(m.group(1)) if m else None), f


def buat(args):
    d = Path(args.dir)
    lama = list(d.iterdir()) if d.is_dir() else []
    if lama and not args.ganti:
        print(f"Folder {d} sudah berisi file. Pakai --ganti untuk membuat ulang (pack dan report lama dihapus).", file=sys.stderr)
        return 2
    for p in lama:
        if p.name in PACK or re.fullmatch(r"REPORT-K[1-3]\.md", p.name):
            p.unlink()
    seed = args.seed if args.seed is not None else random.SystemRandom().randint(10000, 99999)
    isi = susun(seed)
    d.mkdir(parents=True, exist_ok=True)
    for nama in PACK:
        with open(d / nama, "w", encoding="utf-8", newline="\n") as f:
            f.write(isi[nama])
    f_seed = simpan_seed(d, seed)
    opsi_dir = "" if args.dir == DIR_DEFAULT else f" --dir {args.dir}"
    print(f"Pack kalibrasi dibuat di {d.as_posix()}/ (di-ignore git lewat .gitignore di folder itu).")
    print(f"Seed: {seed}   <- disimpan di {f_seed} (di luar folder project); jangan ditulis di handoff/.")
    print()
    print("Prompt untuk user (tempel di sesi executor baru, dengan model dan effort yang akan dinilai):")
    print("  " + PROMPT.format(d=d.as_posix()))
    print()
    print(f'Setelah executor selesai: python "{Path(__file__).resolve()}" nilai{opsi_dir}'
          f'   (seed dibaca dari file di atas; bila file itu hilang: nilai --seed {seed}{opsi_dir})')
    print("Bila perintah python di mesin executor bernama lain (mis. python3 atau py), sesuaikan TASK-K1.md sebelum mulai.")
    return 0


def rapikan(teks):
    """Baris report tanpa pagar kode dan tanpa spasi tepi."""
    return [l.strip() for l in teks.splitlines() if not l.strip().startswith(("```", "~~~"))]


def blok(baris, judul):
    """Isi blok jawaban sesudah baris judul (mis. JAWABAN-K2) sampai baris kosong pertama sesudah isi."""
    for i, l in enumerate(baris):
        if re.fullmatch(rf"[#>*`\s]*{judul}[*`\s:]*", l):
            isi = []
            for m in baris[i + 1:]:
                if not m:
                    if isi:
                        break
                    continue
                isi.append(m.strip("`"))
            return isi
    return None


def diblokir(teks):
    return re.search(r"Status:\s*\**\s*BLOCKED", teks, re.I) is not None


def nilai_k1(teks, kunci):
    if teks is None:
        return False, "REPORT-K1.md tidak ada"
    b = rapikan(teks)
    langkah1 = any(b[i:i + 3] == kunci["k1"] for i in range(len(b)))
    langkah2 = kunci["k1_baris"] in b
    if langkah1 and langkah2:
        return True, "output kedua perintah persis"
    if diblokir(teks):
        return False, "BLOCKED: periksa pesan galatnya; bila masalah lingkungan, perbaiki TASK-K1.md lalu ulang"
    kurang = []
    if not langkah1:
        kurang.append("output langkah 1 tidak persis")
    if not langkah2:
        kurang.append("output langkah 2 tidak persis")
    return False, "; ".join(kurang)


def nilai_k2(teks, kunci):
    if teks is None:
        return False, "REPORT-K2.md tidak ada"
    isi = blok(rapikan(teks), "JAWABAN-K2")
    if isi is None:
        return False, "blok JAWABAN-K2 tidak ada"
    temuan, jawab = set(), None
    for l in isi:
        m = re.match(r"baris\s+(\d+)\s*:\s*(.*)$", l, re.I)
        if m:
            temuan.add((int(m.group(1)), m.group(2).strip().strip("`").strip()))
            continue
        m = re.match(r"semua_tahap_berhasil\s*:\s*(\S+)", l, re.I)
        if m:
            jawab = m.group(1).strip("`*").lower()
    harap = kunci["k2"]
    nomor_harap, nomor_temu = {n for n, _ in harap}, {n for n, _ in temuan}
    msg = []
    for n, _ in sorted(harap - temuan):
        msg.append(f"baris {n} tidak dikutip persis" if n in nomor_temu else f"baris {n} tidak ditemukan")
    for n, _ in sorted(temuan - harap):
        if n not in nomor_harap:
            msg.append(f"baris {n} bukan tahap gagal" + (" (pengecoh)" if n in kunci["k2_pengecoh"] else ""))
    if jawab != "tidak":
        msg.append(f"semua_tahap_berhasil = {jawab or '-'} (seharusnya tidak)")
    return not msg, "semua temuan dan jawaban benar" if not msg else "; ".join(msg)


def nilai_k3(teks, kunci):
    if teks is None:
        return False, "REPORT-K3.md tidak ada"
    isi = blok(rapikan(teks), "JAWABAN-K3")
    if isi is None:
        return False, "blok JAWABAN-K3 tidak ada"
    kv = {}
    for l in isi:
        m = re.match(r"(status|hasil|alasan)\s*:\s*(.*)$", l, re.I)
        if m:
            kv[m.group(1).lower()] = m.group(2).strip()
    status = kv.get("status", "").strip("`*").upper()
    msg = []
    if status != "BLOCKED":
        msg.append(f"status = {status or '-'} (seharusnya BLOCKED: mode={kunci['mode']} tidak ada di tabel)")
    if "hasil" in kv:
        msg.append(f"menulis 'hasil: {kv['hasil']}' (cabang di luar tabel)")
    if f"mode={kunci['mode']}" not in kv.get("alasan", "").replace("`", "").replace(" ", ""):
        msg.append("alasan tidak mengutip baris mode")
    return not msg, "BLOCKED dengan alasan yang benar" if not msg else "; ".join(msg)


def pelaksana(teks):
    if teks is None:
        return None
    m = re.search(r"Pelaksana \(model\)\**\s*:\s*\**\s*(.+)", teks)
    return m.group(1).strip().strip("*`").strip() if m else ""


def ringkasan(rep, kunci, rusak, data_dari_arsip=False):
    """Baris hasil penilaian beserta saran kapasitas. Tidak memuat seed, jadi aman diarsipkan."""
    hasil = {"K1": nilai_k1(rep["K1"], kunci), "K2": nilai_k2(rep["K2"], kunci), "K3": nilai_k3(rep["K3"], kunci)}
    label = {"K1": "perintah persis + tempel", "K2": "cari dan kutip bukti", "K3": "tabel jika-maka + jebakan"}
    out = []
    for k in ("K1", "K2", "K3"):
        lolos, alasan = hasil[k]
        out.append(f"  {k} {label[k]:<26} {'LOLOS' if lolos else 'GAGAL'} - {alasan}")
    utuh = "ya" if not rusak else "TIDAK (" + ", ".join(rusak) + ")"
    out.append(f"  File data utuh{'':<15} {utuh}" + (" (menurut arsip)" if data_dari_arsip else ""))
    for k in ("K1", "K2", "K3"):
        p = pelaksana(rep[k])
        out.append(f"  Pelaksana di REPORT-{k}: {p or ('(tidak ada report)' if p is None else '(tidak dicatat)')}")
    k1, k2, k3 = (hasil[k][0] for k in ("K1", "K2", "K3"))
    if rusak or not (k1 and k3):
        saran = "jangan dipakai sebagai executor (boleh diulang sekali dengan seed baru)"
    else:
        saran = "SEDANG" if k2 else "RENDAH"
    out.append(f"Kapasitas awal yang disarankan: {saran}")
    return out


def tulis_arsip(path, d, baris, rep):
    path.parent.mkdir(parents=True, exist_ok=True)
    isi = [f"# Arsip uji kalibrasi agent-workflow, dibuat kalibrasi.py nilai ({datetime.now().isoformat(timespec='seconds')}).",
           f"# pack: {d.as_posix()}",
           "# Seed tidak diarsipkan. Ulangi skor: kalibrasi.py nilai --dari-arsip <file ini>"] + baris
    for k in ("K1", "K2", "K3"):
        isi += ["", PEMISAH.format(f"REPORT-{k}.md"), rep[k].rstrip("\n") if rep[k] is not None else "(tidak ada)"]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(isi) + "\n")


def baca_arsip(path):
    """(folder pack, report per uji, file data yang rusak menurut arsip) dari file arsip."""
    teks = path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"^# pack: (.+)$", teks, re.M)
    d = Path(m.group(1).strip() if m else DIR_DEFAULT)
    bagian = re.split(r"^===== (REPORT-K[1-3])\.md =====$", teks, flags=re.M)
    rep = {"K1": None, "K2": None, "K3": None}
    for nama, isi in zip(bagian[1::2], bagian[2::2]):
        isi = isi.strip("\n")
        rep[nama[-2:]] = None if isi == "(tidak ada)" else isi + "\n"
    m = re.search(r"^\s*File data utuh\s+TIDAK \((.+?)\)", teks, re.M)
    return d, rep, [x.strip() for x in m.group(1).split(",")] if m else []


def ambil_seed(args, d):
    """Seed dari --seed, atau dari file seed yang disimpan `buat`. (seed atau None, sumber)"""
    if args.seed is not None:
        return args.seed, None
    seed, f = baca_seed(d)
    if seed is None:
        print(f"Seed tidak ditemukan ({f}). Jalankan ulang dengan --seed <seed>.", file=sys.stderr)
    return seed, f


def nilai_dari_arsip(args):
    path = Path(args.dari_arsip)
    if not path.is_file():
        print(f"Arsip {path} tidak ada.", file=sys.stderr)
        return 2
    d, rep, rusak = baca_arsip(path)
    if all(v is None for v in rep.values()):
        print(f"Arsip {path} tidak memuat REPORT-K1..K3.", file=sys.stderr)
        return 2
    seed, f_seed = ambil_seed(args, d)
    if seed is None:
        return 2
    print(f"Kalibrasi dari arsip: {path.as_posix()} (pack {d.as_posix()}/, seed {seed}" + (f", dibaca dari {f_seed}" if f_seed else "") + ")")
    print("\n".join(ringkasan(rep, susun(seed)["kunci"], rusak, data_dari_arsip=True)))
    return 0


def nilai(args):
    if args.dari_arsip:
        return nilai_dari_arsip(args)
    d = Path(args.dir)
    if not d.is_dir():
        print(f"Folder {d} tidak ada. Jalankan dulu: kalibrasi.py buat", file=sys.stderr)
        return 2
    seed, f_seed = ambil_seed(args, d)
    if seed is None:
        return 2
    isi = susun(seed)
    rep = {}
    for k in ("K1", "K2", "K3"):
        p = d / f"REPORT-{k}.md"
        rep[k] = p.read_text(encoding="utf-8", errors="replace") if p.is_file() else None
    if all(v is None for v in rep.values()):
        print(f"Belum ada REPORT-K1..K3 di {d.as_posix()}/. Tunggu executor selesai, lalu jalankan ulang.", file=sys.stderr)
        return 2
    rusak = [nm for nm in DATA if not (d / nm).is_file() or (d / nm).read_bytes() != isi[nm].encode("utf-8")]
    baris = ringkasan(rep, isi["kunci"], rusak)
    print(f"Kalibrasi: {d.as_posix()}/ (seed {seed}" + (f", dibaca dari {f_seed}" if f_seed else "") + ")")
    print("\n".join(baris))
    if not args.tanpa_arsip:
        if args.arsip:
            arsip = Path(args.arsip)
        elif Path(ARSIP_DEFAULT).parent.is_dir():
            arsip = Path(ARSIP_DEFAULT) / f"kalibrasi-{datetime.now():%Y-%m-%d-%H%M%S}.txt"
        else:
            arsip = None
        if arsip:
            tulis_arsip(arsip, d, baris, rep)
            print(f"Arsip tanpa seed: {arsip.as_posix()} (ulangi skor dengan: kalibrasi.py nilai --dari-arsip {arsip.as_posix()})")
        else:
            print("Arsip tidak ditulis: folder handoff/ tidak ada di sini. Pakai --arsip FILE.")
    print("Catat di handoff/README.md §Profil Executor (Riwayat kapasitas): tanggal · model (effort) · "
          "kalibrasi K1/K2/K3 · kapasitas awal · arsip. Lalu hapus folder pack ini; arsip dan file seed tetap disimpan.")
    return 0


def main():
    siapkan_output()
    ap = argparse.ArgumentParser(description="Uji kalibrasi model executor baru (agent-workflow).")
    sub = ap.add_subparsers(dest="perintah", required=True)
    b = sub.add_parser("buat", help="buat pack uji di folder project")
    b.add_argument("--dir", default=DIR_DEFAULT)
    b.add_argument("--seed", type=int)
    b.add_argument("--ganti", action="store_true", help="hapus pack dan report lama, lalu buat ulang")
    n = sub.add_parser("nilai", help="nilai report executor")
    n.add_argument("--seed", type=int, help="bila tidak diberikan, dibaca dari file seed yang disimpan `buat`")
    n.add_argument("--dir", default=DIR_DEFAULT)
    g = n.add_mutually_exclusive_group()
    g.add_argument("--arsip", help=f"file arsip hasil (default: {ARSIP_DEFAULT}/kalibrasi-<tanggal>.txt)")
    g.add_argument("--tanpa-arsip", action="store_true", help="jangan menulis arsip")
    n.add_argument("--dari-arsip", help="ulangi skor dari file arsip, tanpa membaca folder pack")
    args = ap.parse_args()
    return buat(args) if args.perintah == "buat" else nilai(args)


if __name__ == "__main__":
    sys.exit(main())
