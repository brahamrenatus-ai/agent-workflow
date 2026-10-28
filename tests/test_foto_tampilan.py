"""Uji scripts/foto_tampilan.py (v3.10.1): lebar layar benar-benar emulasi (bukan jendela Chrome minimal ±500 px yang
dipotong), tangkapan layar berukuran sesuai, dan ukuran halaman/elemen yang keluar layar bisa dinilai skrip.
Dilewati bila Chrome/Chromium/Edge tidak ada di mesin ini.
Pemakaian: python -X utf8 tests/test_foto_tampilan.py <folder skill>"""
import importlib.util
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(sys.argv[1]).resolve()
SKRIP = SKILL / "scripts" / "foto_tampilan.py"
ok = True


def cek(cond, msg, out=""):
    global ok
    print(("OK    " if cond else "GAGAL ") + msg)
    if not cond and out:
        print("      " + out.replace("\n", "\n      "))
    ok = ok and cond


if not SKRIP.is_file():
    print("LEWAT uji foto_tampilan: skrip belum ada di versi ini")
    print("\nHASIL: SEMUA OK")
    sys.exit(0)
sys.dont_write_bytecode = True  # jangan meninggalkan __pycache__ di folder skill
spec = importlib.util.spec_from_file_location("foto_tampilan", SKRIP)
modul = importlib.util.module_from_spec(spec)
spec.loader.exec_module(modul)
if hasattr(modul, "baca_port"):  # v3.10.2: file DevToolsActivePort dibaca hanya bila lengkap dan tidak dikunci
    d_port = Path(tempfile.mkdtemp(prefix="uji_port_"))
    try:
        f = d_port / "DevToolsActivePort"
        cek(modul.baca_port(f) is None, "baca_port: file belum ada -> tunggu (None)")
        f.write_text("59123", encoding="utf-8")
        cek(modul.baca_port(f) is None, "baca_port: baris path belum tertulis -> tunggu (None)")
        f.write_text("59123\n/devtools/browser/abc\n", encoding="utf-8")
        cek(modul.baca_port(f) == "59123", "baca_port: file lengkap -> port")
        if sys.platform == "win32":
            import msvcrt
            fh = open(f, "r+")
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 10)
            try:
                cek(modul.baca_port(f) is None, "baca_port: file dikunci Chrome (Windows, PermissionError) -> tunggu, bukan gagal")
            finally:
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 10)
                fh.close()
    finally:
        shutil.rmtree(d_port, ignore_errors=True)
if not modul.cari_browser():
    print("LEWAT uji foto_tampilan selebihnya: Chrome, Chromium, atau Edge tidak ada di mesin ini")
    print("\nHASIL:", "SEMUA OK" if ok else "ADA YANG GAGAL")
    sys.exit(0 if ok else 1)

KEPALA = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>'
HALAMAN = {
    # Dua tombol 200 px yang membungkus ke baris baru di bawah 400 px. Di jendela 500 px yang dipotong ke 375 px
    # (cara lama), tombol kedua tampak terpotong; di emulasi 375 px yang benar, keduanya muat.
    "jebakan.html": KEPALA + '<body style="margin:0"><div style="display:flex;flex-wrap:wrap">'
                    '<button style="width:200px">Satu</button><button id="dua" style="width:200px">Dua</button></div>'
                    '<p id="lebar"></p><script>document.getElementById("lebar").textContent="w="+innerWidth</script></body></html>',
    "lebar.html": KEPALA + '<body style="margin:0"><div id="kotak" style="width:600px;height:40px;background:#c33">lebar</div></body></html>',
    "gulir.html": KEPALA + '<body style="margin:0"><nav style="overflow-x:auto;white-space:nowrap">'
                  '<span style="display:inline-block;width:900px">tab tab tab</span></nav><p>isi</p></body></html>',
    "potong.html": KEPALA + '<body style="margin:0;overflow-x:hidden"><div id="lebar-terpotong" style="width:600px">teks panjang</div></body></html>',
}


def jalan(*args):
    r = subprocess.run([sys.executable, "-X", "utf8", str(SKRIP), *map(str, args)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=180)
    return r.returncode, r.stdout + r.stderr


def ukuran_png(p):
    b = p.read_bytes()
    return struct.unpack(">II", b[16:24]) if b[:8] == b"\x89PNG\r\n\x1a\n" else None


tmp = Path(tempfile.mkdtemp(prefix="uji_foto_"))
try:
    for nama, isi in HALAMAN.items():
        (tmp / nama).write_text(isi, encoding="utf-8")
    rc, out = jalan(tmp / "jebakan.html", tmp / "out/jebakan", "--ukuran", "375x812", "1366x768", "--tunggu", "300")
    cek(rc == 0 and "layar 375 px, halaman 375 px" in out and "elemen keluar layar: 0" in out,
        "lebar 375 px diemulasikan sungguhan: tombol yang membungkus tidak dilaporkan keluar layar", out)
    cek(ukuran_png(tmp / "out/jebakan-375x812.png") == (375, 812) and ukuran_png(tmp / "out/jebakan-1366x768.png") == (1366, 768),
        "tangkapan layar berukuran persis 375x812 dan 1366x768", out)
    rc, out = jalan(tmp / "lebar.html", tmp / "out/lebar", "--ukuran", "375x812", "--tunggu", "300")
    cek(rc == 1 and "layar 375 px, halaman 600 px (lebih lebar dari layar" in out and "div#kotak" in out,
        "elemen 600 px di layar 375 px: halaman lebih lebar dari layar dan elemennya disebut, exit 1", out)
    rc, out = jalan(tmp / "gulir.html", tmp / "out/gulir", "--ukuran", "375x812", "--tunggu", "300")
    cek(rc == 0 and "halaman 375 px" in out and "elemen keluar layar: 0" in out,
        "isi di dalam wadah bergulir (overflow-x: auto) tidak dihitung keluar layar", out)
    rc, out = jalan(tmp / "potong.html", tmp / "out/potong", "--ukuran", "375x812", "--tunggu", "300")
    cek(rc == 1 and "div#lebar-terpotong" in out,
        "halaman yang menyembunyikan gulir (body overflow-x: hidden) tetap ketahuan memotong elemen", out)
    if "def buka_halaman" in SKRIP.read_text(encoding="utf-8"):  # v3.10.2
        url_hash = (tmp / "jebakan.html").resolve().as_uri() + "#/hari-ini"
        rc, out = jalan(url_hash, tmp / "out/hash", "--ukuran", "375x812", "1366x768", "--tunggu", "300")
        cek(rc == 0 and out.count("elemen keluar layar: 0") == 2 and (tmp / "out/hash-1366x768.png").is_file(),
            "URL dengan rute hash (#/...) di dua ukuran: ukuran kedua juga termuat (lewat about:blank)", out)
    else:
        print("LEWAT uji rute hash: foto_tampilan.py versi lama")
    rc, out = jalan(tmp / "jebakan.html", tmp / "out/luring", "--ukuran", "375x812", "--luring", "--tunggu", "300")
    cek(rc == 0 and "layar 375 px" in out, "--luring: halaman lokal tetap termuat", out)
    rc, out = jalan(tmp / "tidak-ada.html", tmp / "out/x")
    cek(rc == 2 and "bukan URL dan bukan file" in out, "file yang tidak ada: exit 2", out)
    rc, out = jalan(tmp / "jebakan.html", tmp / "out/x", "--ukuran", "375kali812")
    cek(rc == 2 and "WxH" in out, "ukuran salah format: exit 2", out)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("\nHASIL:", "SEMUA OK" if ok else "ADA YANG GAGAL")
sys.exit(0 if ok else 1)
