# Struktur File Project

Dibaca dari `SKILL.md` saat BOOTSTRAP, AUDIT, dan mode STRUKTUR. Tujuannya dua:
- Build dan tool tidak rusak karena file berada di tempat yang salah.
- Orang dan agen lain cepat paham letak setiap jenis file.

Standar bisa berubah antar versi tool. Untuk aturan WAJIB, cek dokumentasi resmi versi yang dipakai project; sumber di bawah adalah titik awal.

## Tiga Tingkat Aturan

| Tingkat | Artinya | Contoh | Bila dilanggar |
|---|---|---|---|
| **WAJIB** | Dituntut tool/framework atau platform hosting. Tanpa itu build/tool gagal, atau file diam-diam diabaikan | `.ino` utama harus bernama sama dengan folder sketch; suite test PlatformIO harus di folder `test_*`; GitHub menolak file > 100 MiB | FIX |
| **STANDAR** | Kesepakatan luas yang didokumentasikan atau dipakai kebanyakan project sejenis | Hasil build dan dependensi tidak di-commit; lockfile di-commit; dokumen di `docs/` | Item STRUKTUR di ROADMAP |
| **SELERA** | Bebas, asal konsisten dan tertulis | `tools/` atau `scripts/`; bahasa nama file | Ditulis di peta, bukan temuan |

- **Default tool yang bisa diubah di konfigurasi** (mis. `src_dir` di `platformio.ini`) tetap WAJIB. Ikuti default-nya, atau tulis pengubahannya di file konfigurasi.
- **Label WAJIB harus disertai sumber**: URL dokumentasi, atau perilaku tool yang bisa diperiksa. Tanpa sumber, turunkan ke STANDAR.
- **Jangan menaikkan SELERA menjadi WAJIB.**
- **Keputusan sadar user** dicatat di register keputusan beserta syarat "buka ulang jika", lalu tidak dilaporkan ulang sebagai pelanggaran. Contohnya: hasil generate yang sengaja di-commit karena dipakai agen.

## Menilai Temuan
Setiap temuan disaring dengan §Kualitas Rekomendasi di `SKILL.md`. Untuk struktur, urutan prioritasnya:
1. WAJIB yang merusak build atau tool.
2. Keamanan: secret atau data sensitif yang ter-track, termasuk yang tercetak di log.
3. Hal yang membuat agen salah baca atau salah edit: kode lama yang mirip kode aktif, salinan file, folder dengan fungsi sama, dan path yang hanya berlaku di satu mesin.
4. Ukuran yang benar-benar mengganggu: mendekati batas GitHub, atau clone dan pencarian jadi lambat.
5. Kerapian lain. Cukup dicatat di peta sebagai SELERA, tanpa task.

Selalu bandingkan dengan opsi "biarkan":
- Memindah ratusan file dari folder yang namanya sudah jelas hanya menambah rujukan yang harus diperbarui. Catat sebagai SELERA.
- Git memadatkan file teks, jadi ukuran file saja bukan alasan memindah. Contoh dari robot meja: isi repo 41,9 MB, tetapi seluruh `.git` beserta riwayatnya hanya 15 MB.

## Survei (hanya membaca)

- **Jenis project** dari file penanda: `platformio.ini`, `*.ino`, `CMakeLists.txt` + `main/` (ESP-IDF), `pyproject.toml`/`requirements.txt`, `package.json`, `go.mod`, `Cargo.toml`, `pubspec.yaml`. Monorepo bisa punya beberapa sekaligus.
- **Komposisi tingkat atas:** `git ls-files | awk -F/ '{print (NF>1 ? $1"/" : $1)}' | sort | uniq -c | sort -rn`
- **File ter-track yang besar** (> 1 MB). Nilai tiap file: memang perlu, hasil generate, atau sering berubah? Besar saja bukan pelanggaran.
  `git ls-files -z | xargs -0 du -k 2>/dev/null | sort -rn | head -20`
- **Hasil build, dependensi, atau keluaran generate yang ter-track:** `.pio/`, `build/`, `dist/`, `node_modules/`, `__pycache__/`, `managed_components/`, `*.bin`, `*.elf`, folder `*-out/`.
- **Berkas yang berubah sendiri:** hook git yang aktif (`ls .git/hooks | grep -v sample`, `git config core.hooksPath`) dan tool yang menulis ulang file ter-track tanpa disentuh task (mis. hook `post-commit` graphify → `graphify-out/`). Catat di §Berubah Sendiri peta struktur (T9), supaya `git status` di Periksa Diri executor dan commit task tidak tersandung.
- **File ter-track yang cocok dengan pola `.gitignore`:** `git ls-files -ci --exclude-standard`.
- **File secret yang ter-track:** `.env`, `secrets.*` selain file contoh, `*.pem`, `*.key`. Sebut nama file saja, jangan nilainya.
- **Nilai secret yang bocor ke file lain**, terutama log. Scan pola saja tidak cukup, karena token tanpa awalan khas akan lolos. Cari nilai asli dari file secret lokal tanpa mencetaknya dengan `python <folder skill>/scripts/cek_secret.py <folder...>` dari root project, atau `handoff/tools/cek_secret.py` bila sudah terpasang. `--list-sources` menunjukkan file secret yang terbaca.
- **Path yang hanya berlaku di satu mesin** (`file:///`, `C:\Users\`, `/home/<nama>/`) di docs, rule, dan skrip. Path seperti ini rusak di mesin lain dan di sesi cloud; ganti dengan path relatif.
- **Salinan file yang sama** di beberapa tempat (`git ls-files -z | xargs -0 sha1sum | sort | uniq -D -w40`), dan rujukan ke path yang tidak ada.
- **Tanda struktur tumbuh liar:**
  - folder dengan fungsi sama (mis. `tools/` dan `scripts/`);
  - file aset atau dokumen yang lepas di root;
  - kode lama yang disimpan sebagai folder (`archive/`, `old/`, `backup/`).
- **Folder tak lazim yang dijelaskan di docs atau rule project** (mis. keluaran tool yang dibaca agen) dinilai sebagai keputusan sadar. Konfirmasikan ke user bila ragu.
- **Risiko pindah:** grep nama folder di kode, skrip, konfigurasi build/CI, docs, dan `handoff/`.

## Standar per Jenis Project

### Semua project
| Aturan | Tingkat | Sumber |
|---|---|---|
| File > 100 MiB ditolak GitHub; file > 50 MiB memicu peringatan | WAJIB (GitHub) | [GitHub: large files](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github) |
| Repo idealnya < 1 GB. Biner besar memakai Git LFS atau release asset | STANDAR | sama |
| `README` di root: tujuan, cara build/run, struktur singkat | STANDAR | |
| `.gitignore` mencakup hasil build, dependensi, file lokal editor, dan secret | STANDAR | |
| Secret hanya lewat file contoh (`.env.example`, `secrets.example.h`); file aslinya di-ignore | STANDAR (keamanan) | |
| Dokumen di `docs/`. Aset di satu folder yang namanya jelas (mis. `assets/`, `docs/images/`, `design/`); folder aset di root dengan nama jelas sudah memenuhi ini | STANDAR | |
| Kode lama tidak disimpan sebagai folder. Agen bisa membacanya sebagai kode aktif, dan riwayat git sudah menyimpannya | STANDAR | |
| Satu folder untuk skrip bantu | SELERA (asal satu) | |

### PlatformIO (`platformio.ini`)
Semua lokasi bisa diubah di bagian `[platformio]` (mis. `src_dir`). Kalau tidak diubah, default di bawah yang berlaku.

| Isi | Lokasi | Tingkat |
|---|---|---|
| Kode program | `src/` | WAJIB (default `src_dir`) |
| Header project | `include/` | STANDAR (default `include_dir`; header di `src/` tetap ikut ter-build) |
| Library milik project | `lib/<Nama>/`, satu folder per library; sumbernya di root folder itu atau di `lib/<Nama>/src/` | WAJIB |
| Library pihak ketiga yang tidak dimodifikasi | `lib_deps` di `platformio.ini` dengan versi ditulis eksplisit (mis. `@^2.0.1`, atau `@2.0.1` bila harus persis sama), bukan disalin ke `lib/`. Salinan di `lib/` wajar bila library-nya dimodifikasi; tulis asal dan versinya | STANDAR |
| Unit test (`pio test`) | `test/`, dengan tiap suite di folder berawalan `test_` | WAJIB |
| Isi file system (LittleFS/SPIFFS) | `data/` | WAJIB (default `data_dir`) |
| Board kustom | `boards/` | WAJIB (default `boards_dir`) |
| Hasil build dan dependensi | `.pio/`, di-ignore | STANDAR |

Sumber: [opsi direktori](https://docs.platformio.org/en/latest/projectconf/sections/platformio/options/directory/index.html), [`lib_dir`](https://docs.platformio.org/en/latest/projectconf/sections/platformio/options/directory/lib_dir.html), [hierarki test](https://docs.platformio.org/en/latest/advanced/unit-testing/structure/hierarchy.html).

### Arduino IDE/CLI (`*.ino` tanpa `platformio.ini`)
- **WAJIB:** file `.ino` utama bernama sama dengan folder sketch-nya.
- **WAJIB:** kode tambahan ditaruh di root sketch (muncul sebagai tab IDE) atau di `src/` (dikompilasi rekursif). File `.ino` di dalam `src/` tidak didukung.
- `data/` berisi file tambahan yang tidak dikompilasi.
- Sumber: [Arduino sketch specification](https://arduino.github.io/arduino-cli/1.5/sketch-specification/).

### ESP-IDF (`CMakeLists.txt` di root + `main/`)
- **WAJIB:** `CMakeLists.txt` di root. Kode project ada di komponen `main/`, yang punya `CMakeLists.txt` sendiri. Komponen project lain di `components/`, atau didaftarkan lewat `EXTRA_COMPONENT_DIRS`.
- **STANDAR:** `build/` dan `managed_components/` tidak di-commit.
- **Keputusan:** `sdkconfig` boleh di-commit atau tidak. Pilih satu, lalu catat di register keputusan. `sdkconfig.defaults` dipakai saat membuat konfigurasi baru.
- Sumber: [ESP-IDF build system](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/build-system.html).

### Python
- **STANDAR:** `pyproject.toml` di root untuk paket. Test di `tests/`. `.venv/`, `__pycache__/`, `*.egg-info/`, dan `dist/` di-ignore.
- **SELERA, dengan rekomendasi:** flat layout (`<paket>/` di root) atau src layout (`src/<paket>/`). Src layout mencegah salinan development ter-import tanpa sengaja, tetapi project harus di-install dulu untuk dijalankan. Pilih satu.
- Sumber: [src layout vs flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/).

### Node/web (`package.json`)
- **STANDAR:** lockfile (`package-lock.json`, `pnpm-lock.yaml`, atau `yarn.lock`) di-commit. Menurut npm, `package-lock.json` "is intended to be committed into source repositories".
- **STANDAR:** `node_modules/` dan hasil build (`dist/`, `build/`, `.next/`) di-ignore. `.env` di-ignore, `.env.example` di-commit.
- Sumber: [npm package-lock.json](https://docs.npmjs.com/cli/v10/configuring-npm/package-lock-json).

### Backend web (FastAPI, Express, Django, dll.)
- Framework seperti FastAPI dan Express tidak mewajibkan struktur. Ikuti contoh struktur di dokumentasinya sebagai STANDAR, dan tulis pilihan project di peta.
- Framework yang punya generator (Django `startproject`/`startapp`, Rails) memakai struktur hasil generator sebagai STANDAR.
- Migrasi DB di folder milik tool migrasinya. Konfigurasi lewat environment.

### Monorepo (mis. firmware + dashboard web)
- **STANDAR:** tiap bagian di foldernya sendiri bersama file penandanya. Root hanya berisi file lintas bagian.
- **SELERA:** PlatformIO boleh tetap di root, dan folder web diberi nama yang jelas (`web/`, `dashboard/`).

### Jenis lain
- Cari "project structure" atau "project layout" di dokumentasi resmi tool-nya.
- Bila tidak ada standar resmi, tulis "tidak ada standar resmi". Pola yang sudah dipakai project dicatat sebagai SELERA yang tertulis.

## Log Bukti (`handoff/logs/`)
Protokol ini menyimpan log sebagai bukti. Log yang di-commit bisa diperiksa dari mesin lain dan dari sesi cloud, yang hanya melihat file ter-commit. Git juga memadatkan teks, jadi log berukuran beberapa MB murah. Contoh dari robot meja: 23,2 MB log dalam 148 file, sementara seluruh `.git` beserta semua riwayatnya hanya 15 MB.
- **Default: log yang dirujuk report di-commit utuh.**
- **Cek secret dulu.** Firmware dan server sering mencetak token, password Wi-Fi, atau kunci saat debug. Sebelum commit, jalankan `cek_secret.py <file-log> --redact` (§Survei), yang mengganti temuan dengan `<REDACTED>`. Contoh dari robot meja: refresh token Spotify tercetak utuh di log uji, lalu ikut ter-commit dan ter-push.
- **Log > ±10 MB:** log mentah disimpan di `handoff/logs/raw/` (di-ignore).
  - Yang di-commit adalah potongan di `handoff/logs/` yang memuat **semua baris yang dikutip report**, ditambah konteks secukupnya.
  - Baris pertama potongan menyebut path log mentah, jumlah barisnya, dan rentang waktunya.
- **Rekam secukupnya.** Mulai merekam tepat sebelum uji dan berhenti setelahnya, supaya log tetap fokus.
- **Integritas bukti** (Pelajaran 15) dicek terhadap file yang di-commit.
- **Log besar yang sudah terlanjur masuk riwayat** tidak perlu dihapus dari riwayat. Menulis ulang riwayat (mis. `git filter-repo`) merusak clone lain; itu keputusan user dan biasanya tidak sepadan.
- Tinjau ulang aturan ini bila total log mendekati ±100 MB.

## Memindahkan File dengan Aman
Memindahkan file mudah memutus banyak hal: include/import, path di skrip, konfigurasi build/CI, tautan docs, dan rujukan di `handoff/`. Karena itu:
1. **Satu kelompok per task** (jenis STRUKTUR), mis. "satukan `scripts/` ke `tools/`". Tidak ada "rapikan semua sekaligus".
2. **Sebelum pindah,** grep path lama di seluruh repo, lalu tulis daftar hasilnya di task.
3. **Pindahkan dengan `git mv`** supaya riwayat file tetap terlacak. Commit pemindahan terpisah dari perubahan isi file.
4. **Perbarui semua rujukan**, kecuali report dan log lama. Keduanya catatan sejarah; cukup tulis catatan pemindahan di NOTES.
5. **Verifikasi:**
   - build dan test lulus;
   - grep path lama memberi 0 hasil di luar catatan sejarah;
   - SMOKE singkat, bila artefak build-nya dipasang ke perangkat atau server.
6. **Jangan memindahkan** file yang dipakai task OPEN, file yang dirujuk tool di luar repo (CI, skrip deploy, upload file system), atau file yang lokasinya WAJIB.

## Item STRUKTUR di ROADMAP
- Pelanggaran WAJIB yang merusak build atau tool menjadi FIX biasa. Sisanya menjadi item berjenis `STRUKTUR`.
- Task STRUKTUR tidak dihitung sebagai FIX/FEATURE di gerbang ritme. Maksimal 1 task STRUKTUR per 5 task, kecuali user meminta lebih.
- Kerjakan saat retrospektif, atau saat task lain memang menyentuh area itu.
