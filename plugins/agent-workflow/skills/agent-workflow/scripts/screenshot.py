#!/usr/bin/env python3
"""Foto tampilan halaman web di beberapa ukuran layar, beserta ukuran yang bisa dinilai skrip.

Dijalankan dari root project (skill agent-workflow menyalinnya ke handoff/tools/ untuk project ber-UI):
  python handoff/tools/screenshot.py <url atau file .html> handoff/logs/TASK-NNN-<layar>
  python handoff/tools/screenshot.py http://localhost:4173 handoff/logs/TASK-NNN-beranda --sizes 375x812 1366x768 --offline

Untuk setiap ukuran, halaman dibuka di Chrome, Chromium, atau Edge headless dengan emulasi perangkat lewat
DevTools Protocol. Lebar di bawah 768 px diemulasikan sebagai HP, sehingga `<meta name="viewport">` dihormati.
Lalu skrip:
- menyimpan tangkapan layar `<prefix>-<lebar>x<tinggi>.png` (layar pertama, seperti yang dilihat user);
- mencetak lebar layar, lebar halaman (`scrollWidth`), dan elemen yang keluar dari lebar layar (maks. 10).
  Elemen di dalam wadah bergulir atau terpotong sengaja (`overflow-x: auto/scroll/hidden`) tidak dihitung.
  Halaman yang lebih lebar dari layar HP ditata Chrome selebar isinya lalu diperkecil, seperti di HP sungguhan
  (teks menjadi kecil); kasus ini juga dilaporkan.

Mengapa tidak cukup `chrome --headless --window-size=375,812 --screenshot`: Chrome desktop menata halaman minimal
±500 px walau jendela diminta lebih sempit, lalu hanya memotong fotonya. Hasilnya tombol tampak terpotong padahal di
HP muat, atau sebaliknya.

Opsi:
  --sizes WxH ...   ukuran layar sasaran (bawaan: 375x812 1366x768)
  --offline         blokir semua host selain localhost dan 127.0.0.1 (aman untuk halaman yang memanggil layanan live)
  --wait MS         jeda sesudah halaman termuat, untuk render JavaScript (bawaan 1500)
Nama opsi sebelum v3.12 (--ukuran, --luring, --tunggu) tetap diterima.
Browser dicari di variabel CHROME, lalu lokasi umum Chrome, Chromium, dan Edge.
Exit code: 0 = semua ukuran tanpa elemen keluar layar, 1 = ada halaman lebih lebar dari layar atau elemen keluar
layar, 2 = gagal (argumen salah, browser tidak ditemukan, halaman tidak termuat).
"""
import argparse
import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

LOKASI_BROWSER = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]
NAMA_BROWSER = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge", "microsoft-edge"]
BATAS_HP = 768
# Diukur di halaman terhadap lebar layar W yang diemulasikan (bukan innerWidth: di emulasi HP, halaman yang lebih lebar
# dari layar ditata selebar isinya lalu diperkecil, sehingga innerWidth ikut membesar): lebar tata letak, lebar halaman,
# dan elemen terluar yang keluar dari W.
UKUR_JS = r"""((W) => {
  const doc = document.documentElement;
  const halaman = Math.max(doc.scrollWidth, document.body ? document.body.scrollWidth : 0);
  const dipotong = (el) => {
    for (let p = el.parentElement; p && p !== document.body && p !== doc; p = p.parentElement) {
      const o = getComputedStyle(p).overflowX;
      if (o === 'auto' || o === 'scroll' || o === 'hidden' || o === 'clip') return true;
    }
    return false;
  };
  const keluar = [];
  for (const el of document.querySelectorAll('body *')) {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || s.position === 'fixed' && r.left >= W) continue;
    if ((r.right > W + 1 || r.left < -1) && !dipotong(el)) keluar.push(el);
  }
  const terluar = keluar.filter((el) => !keluar.includes(el.parentElement));
  const nama = (el) => el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') +
    [...el.classList].slice(0, 2).map((c) => '.' + c).join('');
  return JSON.stringify({
    layar: W, tata: window.innerWidth, halaman: halaman, jumlah: terluar.length,
    keluar: terluar.slice(0, 10).map((el) => {
      const r = el.getBoundingClientRect();
      return {elemen: nama(el), kiri: Math.round(r.left), kanan: Math.round(r.right),
              teks: (el.innerText || el.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 40)};
    }),
  });
})"""


def siapkan_output():
    """Konsol Windows (cp1252) tidak boleh membuat skrip crash; output ke pipa/agen memakai UTF-8."""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(errors="replace") if s.isatty() else s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def cari_browser():
    calon = [os.environ.get("CHROME")] + [shutil.which(n) for n in NAMA_BROWSER] + LOKASI_BROWSER
    return next((c for c in calon if c and Path(c).is_file()), None)


class WebSocket:
    """Klien WebSocket minimal (RFC 6455) untuk DevTools Protocol: pesan teks, tanpa ekstensi."""

    def __init__(self, url, batas=30):
        alamat, _, path = url[len("ws://"):].partition("/")
        host, _, port = alamat.partition(":")
        self.s = socket.create_connection((host, int(port)), timeout=batas)
        kunci = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET /{path} HTTP/1.1\r\nHost: {alamat}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                        f"Sec-WebSocket-Key: {kunci}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        jawab = b""
        while b"\r\n\r\n" not in jawab:
            potong = self.s.recv(4096)
            if not potong:
                raise ConnectionError("koneksi DevTools tertutup saat handshake")
            jawab += potong
        if b" 101 " not in jawab.split(b"\r\n", 1)[0]:
            raise ConnectionError("handshake WebSocket ditolak: " + jawab.split(b"\r\n", 1)[0].decode(errors="replace"))
        self.sisa = jawab.split(b"\r\n\r\n", 1)[1]

    def baca(self, n):
        while len(self.sisa) < n:
            potong = self.s.recv(max(65536, n - len(self.sisa)))
            if not potong:
                raise ConnectionError("koneksi DevTools tertutup")
            self.sisa += potong
        data, self.sisa = self.sisa[:n], self.sisa[n:]
        return data

    def kirim(self, teks, opcode=0x1):
        data = teks.encode() if isinstance(teks, str) else teks
        kepala = bytes([0x80 | opcode])
        n = len(data)
        if n < 126:
            kepala += bytes([0x80 | n])
        elif n < 65536:
            kepala += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            kepala += bytes([0x80 | 127]) + struct.pack(">Q", n)
        topeng = os.urandom(4)
        self.s.sendall(kepala + topeng + bytes(b ^ topeng[i % 4] for i, b in enumerate(data)))

    def terima(self):
        pesan = b""
        while True:
            b0, b1 = self.baca(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self.baca(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self.baca(8))[0]
            topeng = self.baca(4) if b1 & 0x80 else None
            data = self.baca(n)
            if topeng:
                data = bytes(b ^ topeng[i % 4] for i, b in enumerate(data))
            opcode = b0 & 0x0F
            if opcode == 0x8:
                raise ConnectionError("DevTools menutup koneksi")
            if opcode == 0x9:
                self.kirim(data, opcode=0xA)
                continue
            if opcode in (0x0, 0x1, 0x2):
                pesan += data
                if b0 & 0x80:
                    return pesan.decode("utf-8", errors="replace")

    def tutup(self):
        try:
            self.s.close()
        except OSError:
            pass


class DevTools:
    """Pemanggil DevTools Protocol di atas satu tab: perintah menunggu jawabannya, event disimpan."""

    def __init__(self, ws):
        self.ws, self.nomor, self.event = ws, 0, []

    def __call__(self, metode, **param):
        self.nomor += 1
        self.ws.kirim(json.dumps({"id": self.nomor, "method": metode, "params": param}))
        while True:
            m = json.loads(self.ws.terima())
            if m.get("id") == self.nomor:
                if "error" in m:
                    raise RuntimeError(f"{metode}: {m['error'].get('message')}")
                return m.get("result", {})
            if "method" in m:
                self.event.append(m)

    def tunggu(self, nama, batas):
        akhir = time.time() + batas
        while time.time() < akhir:
            if any(e["method"] == nama for e in self.event):
                return True
            self.ws.s.settimeout(max(0.1, akhir - time.time()))
            try:
                m = json.loads(self.ws.terima())
            except socket.timeout:
                break
            if "method" in m:
                self.event.append(m)
        return any(e["method"] == nama for e in self.event)


def baca_port(berkas):
    """Port DevTools dari file DevToolsActivePort; None selama file belum lengkap (baris port + path) atau masih
    dikunci Chrome saat menulisnya (di Windows membacanya bisa gagal dengan PermissionError)."""
    try:
        baris = berkas.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    return baris[0].strip() if len(baris) >= 2 and baris[0].strip().isdigit() else None


def buka_browser(exe, profil, luring):
    args = [exe, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", "--hide-scrollbars",
            "--disable-extensions", f"--user-data-dir={profil}", "--remote-debugging-port=0", "about:blank"]
    if luring:
        args.insert(1, "--host-resolver-rules=MAP * ~NOTFOUND , EXCLUDE localhost , EXCLUDE 127.0.0.1")
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        args.insert(1, "--no-sandbox")  # Chrome menolak berjalan sebagai root (mis. di container) tanpa ini
    proses = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    berkas = Path(profil) / "DevToolsActivePort"
    for _ in range(150):
        port = baca_port(berkas)
        if port:
            buka = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            for _ in range(50):
                try:
                    tab = [t for t in json.loads(buka.open(f"http://127.0.0.1:{port}/json/list", timeout=5).read())
                           if t.get("type") == "page"]
                    if tab:
                        return proses, tab[0]["webSocketDebuggerUrl"]
                except OSError:
                    pass
                time.sleep(0.1)
        if proses.poll() is not None:
            break
        time.sleep(0.1)
    proses.kill()
    raise RuntimeError("browser tidak membuka DevTools dalam 15 detik")


def buka_halaman(cdp, url, batas=30):
    """Muat url dari awal. Lewat about:blank dulu: navigasi ke URL yang sama dengan fragmen (`#/rute`, router
    hash SPA) hanya berpindah di dalam dokumen, tanpa event load, sehingga ukuran kedua dan seterusnya macet."""
    for tujuan in ("about:blank", url):
        cdp.event.clear()
        hasil = cdp("Page.navigate", url=tujuan)
        if hasil.get("errorText"):
            raise RuntimeError(f"{tujuan} tidak termuat: {hasil['errorText']}")
        if not cdp.tunggu("Page.loadEventFired", batas):
            raise RuntimeError(f"{tujuan} tidak selesai dimuat dalam {batas} detik")


def foto(cdp, url, lebar, tinggi, tunggu_ms, keluar_png):
    hp = lebar < BATAS_HP
    cdp("Emulation.setDeviceMetricsOverride", width=lebar, height=tinggi, deviceScaleFactor=1, mobile=hp,
        screenWidth=lebar, screenHeight=tinggi)
    if hp:
        cdp("Emulation.setTouchEmulationEnabled", enabled=True, maxTouchPoints=5)
    else:
        cdp("Emulation.setTouchEmulationEnabled", enabled=False)
    buka_halaman(cdp, url)
    time.sleep(tunggu_ms / 1000)
    ukur = json.loads(cdp("Runtime.evaluate", expression=f"{UKUR_JS}({lebar})", returnByValue=True)["result"]["value"])
    png = base64.b64decode(cdp("Page.captureScreenshot", format="png")["data"])
    keluar_png.parent.mkdir(parents=True, exist_ok=True)
    keluar_png.write_bytes(png)
    return ukur


def main():
    siapkan_output()
    ap = argparse.ArgumentParser(description="Foto tampilan halaman di beberapa ukuran layar dan ukur elemen yang keluar layar.")
    ap.add_argument("halaman", metavar="page", help="URL (http://, https://, file://) atau path file .html")
    ap.add_argument("prefix", help="awalan file tangkapan layar, mis. handoff/logs/TASK-012-beranda")
    ap.add_argument("--sizes", dest="ukuran", nargs="+", default=["375x812", "1366x768"],
                    help="ukuran layar WxH (bawaan: 375x812 1366x768)")
    ap.add_argument("--offline", dest="luring", action="store_true", help="blokir semua host selain localhost dan 127.0.0.1")
    ap.add_argument("--wait", dest="tunggu", type=int, default=1500, help="jeda sesudah halaman termuat, dalam ms (bawaan 1500)")
    # Nama opsi sebelum v3.12, tetap diterima tanpa tampil di --help.
    ap.add_argument("--ukuran", dest="ukuran", nargs="+", help=argparse.SUPPRESS)
    ap.add_argument("--luring", dest="luring", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--tunggu", dest="tunggu", type=int, help=argparse.SUPPRESS)
    a = ap.parse_args()
    try:
        ukuran = [tuple(int(x) for x in u.lower().split("x")) for u in a.ukuran]
    except ValueError:
        print(f"[screenshot] ukuran harus berbentuk WxH, mis. 375x812: {a.ukuran}", file=sys.stderr)
        return 2
    if "://" in a.halaman:
        url = a.halaman
    elif Path(a.halaman).is_file():
        url = Path(a.halaman).resolve().as_uri()
    else:
        print(f"[screenshot] {a.halaman} bukan URL dan bukan file yang ada", file=sys.stderr)
        return 2
    exe = cari_browser()
    if not exe:
        print("[screenshot] Chrome, Chromium, atau Edge tidak ditemukan; isi variabel CHROME dengan path browser", file=sys.stderr)
        return 2
    profil = tempfile.mkdtemp(prefix="screenshot_")
    proses, ws = None, None
    ada_masalah = False
    try:
        proses, alamat = buka_browser(exe, profil, a.luring)
        ws = WebSocket(alamat)
        cdp = DevTools(ws)
        cdp("Page.enable")
        for lebar, tinggi in ukuran:
            png = Path(f"{a.prefix}-{lebar}x{tinggi}.png")
            u = foto(cdp, url, lebar, tinggi, a.tunggu, png)
            lebih = u["halaman"] > lebar + 1
            ada_masalah = ada_masalah or lebih or u["jumlah"] > 0
            jenis = "HP" if lebar < BATAS_HP else "desktop"
            catatan = ""
            if lebih:
                catatan = (" (lebih lebar dari layar; HP menata halaman selebar isinya lalu memperkecilnya)"
                           if u["tata"] > lebar + 1 else " (lebih lebar dari layar; perlu gulir mendatar)")
            print(f"[screenshot] {lebar}x{tinggi} ({jenis}): {png.as_posix()} | layar {lebar} px, halaman {u['halaman']} px"
                  f"{catatan} | elemen keluar layar: {u['jumlah']}")
            for e in u["keluar"]:
                print(f"  - {e['elemen']} kiri={e['kiri']} kanan={e['kanan']}" + (f" \"{e['teks']}\"" if e["teks"] else ""))
    except (RuntimeError, ConnectionError, OSError, ValueError, KeyError) as e:
        print(f"[screenshot] gagal: {e}", file=sys.stderr)
        return 2
    finally:
        if ws:
            ws.tutup()
        if proses:
            proses.terminate()
            try:
                proses.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proses.kill()
        for _ in range(20):
            shutil.rmtree(profil, ignore_errors=True)
            if not os.path.exists(profil):
                break
            time.sleep(0.25)
    return 1 if ada_masalah else 0


if __name__ == "__main__":
    sys.exit(main())
