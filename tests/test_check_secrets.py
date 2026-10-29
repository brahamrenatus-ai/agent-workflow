"""Uji scripts/check_secrets.py generik pada project palsu (semua rahasia di sini palsu). Argumen: path skrip."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SKRIP = Path(sys.argv[1]).resolve()
hasil = []


def cek(nama, cond, info=""):
    hasil.append(bool(cond))
    print(("LOLOS " if cond else "GAGAL ") + nama + (f"  [{info}]" if info and not cond else ""))


def git(repo, *a):
    subprocess.run(["git", "-C", str(repo), *a], capture_output=True, check=True)


def jalankan(repo, *a, skrip=SKRIP):
    r = subprocess.run([sys.executable, str(skrip), *a], cwd=repo, capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


def repo_baru(dasar, nama, files, ignore):
    repo = dasar / nama
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / ".gitignore").write_text(ignore, encoding="utf-8")
    for rel, isi in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(isi if isinstance(isi, bytes) else isi.encode("utf-8"))
    return repo


tmp = Path(tempfile.mkdtemp(prefix="uji_cek_secret_"))
try:
    # ---------- T1: header C, deteksi otomatis ----------
    PASS, CSEC = "palsu-pass-123", "0123456789abcdef0123456789abcdef"
    r1 = repo_baru(tmp, "c", {
        "include/secrets.h": f'#define ROBOT_WIFI_SSID "RumahKu-5G-Lantai2"\n#define ROBOT_WIFI_PASSWORD "{PASS}"\n'
                             f'#define SPOTIFY_CLIENT_SECRET "{CSEC}"\n#define GEMINI_API_KEY "MASUKKAN_KUNCI_DI_SINI"\n#define SHORT "abc"\n'
                             'static const char* AP_PASS = "ap-rahasia-99";\n',
        "include/secrets.example.h": '#define GEMINI_API_KEY "MASUKKAN_KUNCI_DI_SINI"\n#define SPOTIFY_CLIENT_SECRET "CLIENT_SECRET_ANDA"\n',
        "logs/a.log": ("boot ok\nWiFi SSID RumahKu-5G-Lantai2 tersambung\n"
                       f"pass={PASS} (debug)\nsecret {CSEC} di tengah\nkunci MASUKKAN_KUNCI_DI_SINI placeholder\n"
                       "lihat handoff/tasks/task-053-fix-oled-blackout-prolonged-operation.md\n"
                       "Payload: grant_type=refresh_token&refresh_token=AQBcdefghijklmnopqrstuvwxyz0123456789_-XYZ\n"
                       "Authorization: Basic 4a2e... [len=88]\nAuthorization: Bearer BQDabcdefghijklmnopqrstuvwxyz12345\n"
                       "AP aktif dengan ap-rahasia-99\n"),
    }, "include/secrets.h\n")
    code, out = jalankan(r1, "--list-sources")
    cek("T1 --list-sources menemukan include/secrets.h otomatis", "secrets.h: 3 nilai" in out and "dicari otomatis" in out, out)
    cek("T1 SSID, placeholder, dan nilai pendek tidak dimuat", "SSID" not in out.split("(")[-1] and "GEMINI" not in out and "SHORT" not in out, out)
    code, out = jalankan(r1, "logs")
    cek("T1 exit 1 saat ada temuan", code == 1, str(code))
    cek("T1 lima baris bertemuan (password, client secret, refresh token, Bearer, AP_PASS)", "5 baris bertemuan" in out, out)
    cek("T1 slug task-053-... tidak dianggap kunci sk-", "task-053" not in out, out)
    cek("T1 header Basic yang terpotong tidak ditandai", "Basic 4a2e" not in out, out)
    cek("T1 nilai rahasia tidak tercetak", all(s not in out for s in (PASS, CSEC, "ap-rahasia-99", "AQBcdefghijklmnop")), out)

    # ---------- T2: .env, URL berkredensial, pola umum ----------
    DBURL, SKEY = "postgres://kasir:Rahasia123@db:5432/kasir", "s3cr3t-k3y-1234567890"
    r2 = repo_baru(tmp, "env", {
        ".env": (f"DATABASE_URL={DBURL}\nAPI_BASE_URL=https://api.example.com/v1\nSECRET_KEY=\"{SKEY}\"\nDEBUG=true\n"
                 "# komentar\nexport STRIPE_KEY=" + "sk_" + "live_abcdefghijklmnopqrstuvwx\n"),
        ".env.example": "SECRET_KEY=ganti-dengan-kunci\nDATABASE_URL=postgres://user:pass@localhost/db\n",
        "app.log": (f"conn {DBURL}\ncall https://api.example.com/v1/items\nkey {SKEY}\n"
                    "tok " + "eyJ" + "hbGciOiJIUzI1NiJ9." + "eyJ" + "zdWIiOiIxMjM0NTY3ODkwIn0.dBjftJeZ4CVPmB92K27uhbUJU1p1r_wW1gFWFOEjXk\n"
                    "anthropic " + "sk-" + "ant-api03-abcdefghijklmnopqrstuvwxyz0123456789ABCD\n"
                    "gh " + "gh" + "p_abcdefghijklmnopqrstuvwxyz0123456789\nslack " + "xo" + "xb-1234567890-abcdefghij\naws " + "AK" + "IAABCDEFGHIJKLMNOP\n"),
    }, ".env\n")
    code, out = jalankan(r2, "--list-sources")
    cek("T2 .env terbaca: DATABASE_URL, SECRET_KEY, STRIPE_KEY (API_BASE_URL & DEBUG dilewati)",
        ".env: 3 nilai" in out and "API_BASE_URL" not in out and "DEBUG" not in out, out)
    code, out = jalankan(r2, "app.log")
    cek("T2 tujuh baris bertemuan, URL tanpa kredensial tidak ditandai", "7 baris bertemuan" in out and "api.example.com" not in out, out)
    cek("T2 nilai rahasia tidak tercetak", all(s not in out for s in ("Rahasia123", SKEY, "sk-ant-api03-abc", "ghp_abc", "xoxb-123", "AKIAABCD")), out)
    # ---------- T4: --staged + --redact ----------
    git(r2, "add", "app.log")
    code, out = jalankan(r2, "--staged")
    cek("T4 --staged menangkap file yang di-stage (exit 1)", code == 1 and "app.log" in out, out)
    code, out = jalankan(r2, "app.log", "--redact")
    code2, out2 = jalankan(r2, "app.log")
    cek("T4 --redact lalu cek ulang = 0 temuan, exit 0", code == 0 and code2 == 0 and "0 baris bertemuan" in out2, out + out2)

    # ---------- T3: JSON + file secret yang tidak di-ignore ----------
    JSEC = "abcdef1234567890abcdef"
    r3 = repo_baru(tmp, "json", {
        "secrets.json": f'{{"spotify": {{"client_secret": "{JSEC}"}}, "name": "kasir"}}',
        "run.log": f"secret={JSEC}\nnama kasir\n",
    }, "")
    code, out = jalankan(r3, "run.log")
    cek("T3 nilai dari secrets.json tertangkap", "nilai client_secret" in out and code == 1, out)
    cek("T3 peringatan file secret yang tidak di-ignore", "TIDAK di-ignore" in out, out)

    # ---------- T5: --redact mempertahankan CRLF dan byte non-UTF-8 ----------
    f5 = r1 / "logs" / "crlf.log"
    f5.write_bytes(b"line1\r\npass=" + PASS.encode() + b"\r\n\xff\xfe end\r\n")
    jalankan(r1, "logs/crlf.log", "--redact")
    cek("T5 CRLF dan byte non-UTF-8 utuh setelah redact", f5.read_bytes() == b"line1\r\npass=<REDACTED>\r\n\xff\xfe end\r\n", repr(f5.read_bytes()))

    # ---------- T6: tanpa argumen ----------
    code, _ = jalankan(r1)
    cek("T6 tanpa argumen → exit 2", code == 2, str(code))

    # ---------- T7: SECRET_FILES diisi saat dipasang ----------
    tools = r1 / "handoff" / "tools"
    tools.mkdir(parents=True)
    t = SKRIP.read_text(encoding="utf-8").replace("SECRET_FILES = []", 'SECRET_FILES = ["include/secrets.h"]', 1)
    (tools / "check_secrets.py").write_text(t, encoding="utf-8")
    code, out = jalankan(r1, "--list-sources", skrip=tools / "check_secrets.py")
    cek("T7 SECRET_FILES terpakai (bukan deteksi otomatis)", "dari SECRET_FILES" in out and "secrets.h: 3 nilai" in out, out)

    # ---------- T8 (v3.9.1): token bot Telegram, termasuk di URL Bot API yang dicatat httpx ----------
    if "token bot Telegram" in SKRIP.read_text(encoding="utf-8"):
        TG = "AAH" + "palsuTokenBot_0123456789-abcdefghij"[:32]  # palsu; A + 34 karakter
        assert len(TG) == 35
        r8 = repo_baru(tmp, "tg", {"bot.log": (
            f"TELEGRAM_BOT_TOKEN=7123456789:{TG}\n"
            f'HTTP Request: POST https://api.telegram.org/bot7123456789:{TG}/getUpdates "HTTP/1.1 200 OK"\n'
            "12:34:56 polling mulai\n"
            f"pendek 7123456789:{TG[:-1]}\npanjang 7123456789:{TG}x\nbukan-A 7123456789:B{TG[1:]}\n"
            f"menempel abc7123456789:{TG}\nid empat digit 1234:{TG}\n")}, "")
        code, out = jalankan(r8, "bot.log")
        cek("T8 token Telegram di baris env dan di URL bot<token> tertangkap (2 baris), kasus mirip tidak",
            code == 1 and "2 baris bertemuan" in out and "bot.log:1:" in out and "bot.log:2:" in out, out)
        cek("T8 nilai token Telegram tidak tercetak", TG not in out and TG[:20] not in out, out)
        jalankan(r8, "bot.log", "--redact")
        isi = (r8 / "bot.log").read_text(encoding="utf-8")
        cek("T8 --redact: URL menjadi bot<REDACTED>/getUpdates, kasus mirip tidak diubah",
            "api.telegram.org/bot<REDACTED>/getUpdates" in isi and isi.count("<REDACTED>") == 2 and f"abc7123456789:{TG}" in isi, isi)
    else:
        print("LEWAT T8: skrip ini belum punya pola token bot Telegram (sebelum v3.9.1)")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\nHASIL: {sum(hasil)}/{len(hasil)} lolos")
sys.exit(0 if all(hasil) else 1)
