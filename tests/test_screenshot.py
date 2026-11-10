"""Uji scripts/screenshot.py (v3.10.1): lebar layar benar-benar emulasi (bukan jendela Chrome minimal ±500 px yang
dipotong), tangkapan layar berukuran sesuai, dan ukuran halaman/elemen yang keluar layar bisa dinilai skrip.
Dilewati bila Chrome/Chromium/Edge tidak ada di mesin ini.
Pemakaian: python -X utf8 tests/test_screenshot.py <folder skill>"""
import http.server
import importlib.util
import inspect
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

SKILL = Path(sys.argv[1]).resolve()
SKRIP = SKILL / "scripts" / "screenshot.py"
ok = True


def cek(cond, msg, out=""):
    global ok
    print(("OK    " if cond else "FAIL  ") + msg)
    if not cond and out:
        print("      " + out.replace("\n", "\n      "))
    ok = ok and cond


if not SKRIP.is_file():
    print("SKIP  uji screenshot: skrip belum ada di versi ini")
    print("\nRESULT: ALL OK")
    sys.exit(0)
sys.dont_write_bytecode = True  # jangan meninggalkan __pycache__ di folder skill
spec = importlib.util.spec_from_file_location("screenshot", SKRIP)
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
if "--sizes" in SKRIP.read_text(encoding="utf-8"):  # v3.12: nama opsi berbahasa Inggris, nama lama tetap diterima
    # Tanpa browser: halaman yang tidak ada ditolak sesudah argumen dibaca, jadi opsi yang tidak dikenal terlihat dari pesannya.
    r = subprocess.run([sys.executable, "-X", "utf8", str(SKRIP), "tidak-ada.html", "x", "--ukuran", "375x812", "--luring",
                        "--tunggu", "10"], capture_output=True, text=True, encoding="utf-8")
    cek(r.returncode == 2 and "bukan URL dan bukan file" in r.stderr, "opsi lama --ukuran, --luring, --tunggu diterima", r.stderr)
    bantuan = subprocess.run([sys.executable, "-X", "utf8", str(SKRIP), "--help"], capture_output=True, text=True,
                             encoding="utf-8").stdout
    cek("--sizes" in bantuan and "page" in bantuan and not any(o in bantuan for o in ("--ukuran", "--luring", "--tunggu", "UKURAN", "TUNGGU")),
        "--help hanya menampilkan nama opsi baru", bantuan)
# v3.19.1: --offline tetap mengizinkan host halaman itu sendiri, dan --allow-host menambah host lain.
IZIN = "--allow-host" in SKRIP.read_text(encoding="utf-8")
if IZIN:
    aturan = getattr(modul, "aturan_luring", None)
    cek(aturan is not None and aturan() == "MAP * ~NOTFOUND , EXCLUDE localhost , EXCLUDE 127.0.0.1",
        "aturan_luring(): semua host diblokir kecuali localhost dan 127.0.0.1")
    cek(aturan is not None and aturan(("192.168.4.1", "*.lan")).endswith(
        "EXCLUDE 127.0.0.1 , EXCLUDE 192.168.4.1 , EXCLUDE *.lan"), "aturan_luring(kecuali): host tambahan ikut dikecualikan")
    param = inspect.signature(modul.buka_browser).parameters.get("kecuali")
    cek(param is not None and param.default == (), "buka_browser(..., kecuali=()) untuk alat project yang memanggilnya")
    d_izin = Path(tempfile.mkdtemp(prefix="uji_izin_"))
    try:
        (d_izin / "a.html").write_text("<p>a</p>", encoding="utf-8")
        for argumen, pesan, nama in (
                (["--allow-host", "10.0.0.2"], "hanya berlaku bersama --offline", "--allow-host tanpa --offline: exit 2"),
                (["--offline", "--allow-host", "10.0.0.2:80"], "tanpa port", "--allow-host dengan port: exit 2")):
            r = subprocess.run([sys.executable, "-X", "utf8", str(SKRIP), str(d_izin / "a.html"), str(d_izin / "x"), *argumen],
                               capture_output=True, text=True, encoding="utf-8")
            cek(r.returncode == 2 and pesan in r.stderr, nama, r.stdout + r.stderr)
    finally:
        shutil.rmtree(d_izin, ignore_errors=True)
    bantuan = subprocess.run([sys.executable, "-X", "utf8", str(SKRIP), "--help"], capture_output=True, text=True,
                             encoding="utf-8").stdout
    cek("--allow-host" in bantuan, "--help menampilkan --allow-host", bantuan)
if not modul.cari_browser():
    print("SKIP  uji screenshot selebihnya: Chrome, Chromium, atau Edge tidak ada di mesin ini")
    print("\nRESULT:", "ALL OK" if ok else "SOME FAILED")
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
    if not p.is_file():  # tangkapan gagal dibuat: cek ini FAIL, cek berikutnya tetap berjalan
        return None
    b = p.read_bytes()
    return struct.unpack(">II", b[16:24]) if b[:8] == b"\x89PNG\r\n\x1a\n" else None


PNG_1PX = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010806000000"
                        "1f15c4890000000d49444154789c6360000002000154a24f5f0000000049454e44ae426082")


class ServerUji(http.server.ThreadingHTTPServer):
    """Koneksi yang diputus browser saat ditutup (ConnectionResetError di Windows) bukan kegagalan uji."""
    daemon_threads = True

    def handle_error(self, request, client_address):
        if not isinstance(sys.exc_info()[1], ConnectionError):
            super().handle_error(request, client_address)


def penyaji(catatan, nama, isi, jenis):
    class Penyaji(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            catatan[nama].append(self.path)
            badan = isi()
            self.send_response(200)
            self.send_header("Content-Type", jenis)
            self.send_header("Content-Length", str(len(badan)))
            self.end_headers()
            self.wfile.write(badan)

        def log_message(self, *a):
            pass
    return Penyaji


def uji_host_perangkat(tmp):
    """v3.19.1: 127.0.0.2 meniru Web UI perangkat, 127.0.0.3 meniru layanan lain di jaringan lokal yang dipanggil halaman.
    Sebelumnya --offline memblokir halaman perangkat itu sendiri (net::ERR_NAME_NOT_RESOLVED, exit 2)."""
    catatan = {"perangkat": [], "api": []}
    try:
        api = ServerUji(("127.0.0.3", 0), penyaji(catatan, "api", lambda: PNG_1PX, "image/png"))
    except OSError as e:
        print(f"SKIP  uji host perangkat: 127.0.0.3 tidak bisa dipakai di mesin ini ({e})")
        return
    html = (KEPALA + f'<body><p>perangkat</p><img src="http://127.0.0.3:{api.server_address[1]}/titik.png"></body></html>').encode()
    try:
        perangkat = ServerUji(("127.0.0.2", 0), penyaji(catatan, "perangkat", lambda: html,
                                                                             "text/html; charset=utf-8"))
    except OSError as e:
        api.server_close()
        print(f"SKIP  uji host perangkat: 127.0.0.2 tidak bisa dipakai di mesin ini ({e})")
        return
    for s in (api, perangkat):
        threading.Thread(target=s.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.2:{perangkat.server_address[1]}/"
        rc, out = jalan(url, tmp / "out/perangkat", "--sizes", "375x812", "--offline", "--wait", "300")
        cek(rc == 0 and "/" in catatan["perangkat"] and not catatan["api"] and "127.0.0.2" in out,
            "--offline: halaman di alamat perangkat termuat, host lain yang dipanggilnya tetap diblokir",
            f"{out}\nperangkat={catatan['perangkat']} api={catatan['api']}")
        catatan["api"].clear()
        rc, out = jalan(url, tmp / "out/izin", "--sizes", "375x812", "--offline", "--allow-host", "127.0.0.3", "--wait", "300")
        cek(rc == 0 and "/titik.png" in catatan["api"], "--offline --allow-host: host tambahan itu bisa dihubungi",
            f"{out}\napi={catatan['api']}")
    finally:
        for s in (api, perangkat):
            s.shutdown()
            s.server_close()


tmp = Path(tempfile.mkdtemp(prefix="uji_foto_"))
try:
    for nama, isi in HALAMAN.items():
        (tmp / nama).write_text(isi, encoding="utf-8")
    rc, out = jalan(tmp / "jebakan.html", tmp / "out/jebakan", "--sizes", "375x812", "1366x768", "--wait", "300")
    cek(rc == 0 and "layar 375 px, halaman 375 px" in out and "elemen keluar layar: 0" in out,
        "lebar 375 px diemulasikan sungguhan: tombol yang membungkus tidak dilaporkan keluar layar", out)
    cek(ukuran_png(tmp / "out/jebakan-375x812.png") == (375, 812) and ukuran_png(tmp / "out/jebakan-1366x768.png") == (1366, 768),
        "tangkapan layar berukuran persis 375x812 dan 1366x768", out)
    rc, out = jalan(tmp / "lebar.html", tmp / "out/lebar", "--sizes", "375x812", "--wait", "300")
    cek(rc == 1 and "layar 375 px, halaman 600 px (lebih lebar dari layar" in out and "div#kotak" in out,
        "elemen 600 px di layar 375 px: halaman lebih lebar dari layar dan elemennya disebut, exit 1", out)
    rc, out = jalan(tmp / "gulir.html", tmp / "out/gulir", "--sizes", "375x812", "--wait", "300")
    cek(rc == 0 and "halaman 375 px" in out and "elemen keluar layar: 0" in out,
        "isi di dalam wadah bergulir (overflow-x: auto) tidak dihitung keluar layar", out)
    rc, out = jalan(tmp / "potong.html", tmp / "out/potong", "--sizes", "375x812", "--wait", "300")
    cek(rc == 1 and "div#lebar-terpotong" in out,
        "halaman yang menyembunyikan gulir (body overflow-x: hidden) tetap ketahuan memotong elemen", out)
    if "def buka_halaman" in SKRIP.read_text(encoding="utf-8"):  # v3.10.2
        url_hash = (tmp / "jebakan.html").resolve().as_uri() + "#/hari-ini"
        rc, out = jalan(url_hash, tmp / "out/hash", "--sizes", "375x812", "1366x768", "--wait", "300")
        cek(rc == 0 and out.count("elemen keluar layar: 0") == 2 and (tmp / "out/hash-1366x768.png").is_file(),
            "URL dengan rute hash (#/...) di dua ukuran: ukuran kedua juga termuat (lewat about:blank)", out)
    else:
        print("SKIP  uji rute hash: screenshot.py versi lama")
    rc, out = jalan(tmp / "jebakan.html", tmp / "out/luring", "--sizes", "375x812", "--offline", "--wait", "300")
    cek(rc == 0 and "layar 375 px" in out, "--offline: halaman lokal tetap termuat", out)
    if IZIN:
        uji_host_perangkat(tmp)
    else:
        print("SKIP  uji host perangkat: screenshot.py versi lama")
    # v3.23: browser yang tidak siap dicoba sekali lagi (browser palsu = interpreter Python, yang langsung keluar)
    r = subprocess.run([sys.executable, "-X", "utf8", str(SKRIP), str(tmp / "jebakan.html"), str(tmp / "out/palsu"),
                        "--startup-timeout", "2"], capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=120, env=dict(os.environ, CHROME=sys.executable))
    cek(r.returncode != 0 and "mencoba sekali lagi" in r.stderr and "2 percobaan" in r.stderr,
        "browser yang tidak siap dicoba sekali lagi; pesan gagal menyebut jumlah percobaan", r.stdout + r.stderr)
    rc, out = jalan("--help")
    cek(rc == 0 and "--startup-timeout" in out, "--help memuat --startup-timeout", out[-400:])
    rc, out = jalan(tmp / "tidak-ada.html", tmp / "out/x")
    cek(rc == 2 and "bukan URL dan bukan file" in out, "file yang tidak ada: exit 2", out)
    rc, out = jalan(tmp / "jebakan.html", tmp / "out/x", "--sizes", "375kali812")
    cek(rc == 2 and "WxH" in out, "ukuran salah format: exit 2", out)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("\nRESULT:", "ALL OK" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
