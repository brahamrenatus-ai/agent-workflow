---
name: agent-workflow
description: Siapkan atau audit alur kerja dua-agen (head/perencana + executor/pelaksana) untuk project apa pun, termasuk head bermodel pintar dengan executor murah atau AI lokal. Membuat skill head & executor khusus project, folder handoff (tasks, reports, NOTES, ROADMAP), jenis task sesuai kapasitas executor, pilihan model executor per task (juga lewat Orca), alat cek bukti dan secret, aturan agar project tidak macet di loop analisis, serta peta struktur file sesuai standar framework. Gunakan saat user ingin membuat skill pengembangan untuk project-nya, menyiapkan head/executor atau protokol handoff antar-model, mengevaluasi atau meng-upgrade skill agen yang ada, mengeluh agennya kaku atau project-nya jalan di tempat, menanyakan susunan folder project, atau menilai apakah sebuah model layak menjadi executor, walau tidak menyebut kata "skill". EN: set up or audit a planner/executor (head/executor) agent workflow with file-based handoff, evidence checks, and tasks tuned to the executor model's capacity.
---

# Agent Workflow — Head + Executor untuk Project Apa Pun

**Versi skill: 3.16.** Riwayat perubahan dan penanda tiap versi ada di `references/changelog.md`.

Skill ini memasang atau memperbaiki alur kerja dua peran yang berkomunikasi lewat file di repo:
- **Head** (perencana) menjaga arah, menganalisis hasil, memutuskan, mendesain, menulis task, dan memverifikasi.
- **Executor** (pelaksana) mengimplementasikan, mengukur, menjalankan pekerjaan panjang, dan menulis report.

Pola yang lazim: head memakai model paling pintar, executor memakai model yang lebih murah atau AI lokal. Karena itu protokol disetel ke **kapasitas executor** (§Kapasitas Executor), bukan satu ukuran untuk semua. Hasil akhirnya adalah **file di project user** (instruksi peran, protokol, ROADMAP), bukan nasihat umum. Tulis file dalam bahasa yang dipakai user; skill ini sendiri berbahasa Indonesia, dan tag penanda serta kata kunci alat membuat protokol berbahasa lain tetap terbaca skrip (§3, Isi file).

File pendukung di folder skill ini dibaca hanya saat dibutuhkan:
- `references/templates.md`: template T1–T10 dan penyesuaian per jenis project.
- `references/structure.md`: standar struktur file per jenis project, survei, log bukti, dan cara memindah file dengan aman.
- `references/enforcement.md`: resep penegakan per tool.
- `scripts/check_secrets.py`, `scripts/check_evidence.py`, dan `scripts/record.py`: alat cek secret generik (pola umum + nilai asli dari file secret lokal, tanpa mencetak nilainya), pemeriksa bukti report (kutipan `file:baris`, status OK terhadap harapan, asal log, kelengkapan kriteria), dan pembungkus perintah yang menyimpan log bukti beserta catatan asalnya. Ketiganya disalin ke project oleh BOOTSTRAP/AUDIT.
- `scripts/screenshot.py`: tangkapan layar halaman web di beberapa ukuran layar dengan emulasi perangkat, ditambah pengukur halaman dan elemen yang lebih lebar dari layar. Disalin ke project ber-UI.
- `references/changelog.md` dan `scripts/check_version.py`: perubahan per versi (file sasaran, cara patch, penanda), dan skrip yang membandingkan penanda itu dengan isi project, termasuk apakah instruksi tiap peran bisa ditemukan tool-nya. Dipakai jalur upgrade di AUDIT; skripnya dijalankan dari folder skill, tidak disalin ke project.
- `references/low-capacity.md` dan `scripts/calibrate.py`: executor RENDAH (bukti dari skrip, ukuran task, rantai task) dan uji kalibrasi model baru. Skrip kalibrasi dijalankan dari folder skill; seed-nya disimpan di luar folder project, dan hasil penilaiannya diarsipkan ke `handoff/logs/`.
- `references/orca.md` dan `scripts/orca_wait.py`: head yang menjalankan executor lewat Orca, yaitu peluncuran per task dengan model pilihan head, setelan izin agen, kalibrasi lewat Orca, dan uji sebelum dipakai, ditambah alat tunggu yang meng-ack heartbeat worker tanpa membangunkan head (disalin ke `handoff/tools/`). Dibaca bila project memakai Orca.

Aturan di sini lahir dari kegagalan nyata di tiga project lapangan, yang disebut menurut jenisnya:
- **Robot meja** (firmware ESP32): sekitar 30 dari 42 task berupa pengukuran ulang, dan bug kritis yang sudah tertulis di dokumen audit baru ditemukan 11 hari kemudian.
- **IoT SCADA** (pengendali motor lewat radio): report "lulus" dengan bukti yang tidak cocok, dan secret tertulis di ROADMAP.
- **Aplikasi budidaya** (web + bot Telegram, executor model murah): pengamatan user yang dikarang, kapasitas executor yang naik lalu gagal di task pertamanya, dan cacat tampilan yang lolos test.

Bagian **Pelajaran** menjelaskan alasan tiap aturan. Pahami alasannya supaya bisa menyesuaikan, bukan menyalin mentah.

## Pilih Mode

| Mode | Kapan | Hasil |
|---|---|---|
| BOOTSTRAP | Project belum punya protokol head/executor | Instruksi head + executor, folder `handoff/`, ROADMAP awal yang diverifikasi di kode, peta struktur, TASK-001 SMOKE baseline |
| AUDIT | Sudah ada skill/aturan agen/handoff; user mengeluh agen kaku atau project stagnan, minta evaluasi, atau tool/model berganti, atau protokolnya lebih lama dari versi skill ini | Diagnosis berbukti → rencana → (setelah disetujui) protokol diperbarui tanpa kehilangan riwayat. Untuk upgrade: patch minimal per penanda changelog |
| LITE | Project kecil, satu tool, user tidak meminta dua agen | Satu skill `<prefix>-dev` + ROADMAP + NOTES |
| STRUKTUR | User hanya ingin mengecek atau menetapkan struktur file project | Peta struktur (T9) + temuan berlabel WAJIB/STANDAR/SELERA; tidak ada file project yang dipindah |

Jelaskan mode yang dipilih beserta alasannya. Dua agen menambah latensi, karena setiap siklus melewati task → report → triase. Itu sepadan bila ada pekerjaan mekanis atau lama yang layak didelegasikan, atau bila user sengaja memakai model berbeda (misalnya executor murah/lokal untuk menghemat biaya).

**Jika user secara eksplisit meminta head + executor, ikuti.** Untuk project kecil, buat versi ringkas (§3), jelaskan trade-off-nya, dan tawarkan LITE sebagai alternatif. LITE dipakai hanya bila user tidak meminta dua agen dan project-nya kecil.

## Pelajaran yang Membentuk Aturan

1. **Head yang hanya bereaksi pada report terakhir akan menggali satu anomali selamanya.** Beri head dokumen arah (`ROADMAP.md`) dan *gerbang arah* sebelum membuat task.
2. **Executor yang dilarang berpikir membuang pengamatan terbaiknya.** Beri kanal resmi "Hipotesis & Usulan" di report.
3. **"Hemat token" yang diartikan "jangan membaca" membuat head buta.** Head tetap membaca dokumen arah dan kode bila perlu. Yang didelegasikan adalah pekerjaan mekanis, bukan berpikir. Bacaan luas yang hanya mengumpulkan fakta juga bisa didelegasikan sebagai task FAKTA: executor menunjuk `file:baris`, head membaca kutipannya.
4. **Satu jenis task untuk semua pekerjaan membuat fitur ditulis seperti eksperimen.** Bedakan MEASURE, FIX, FEATURE, SPIKE, dan SMOKE.
5. **Investigasi tanpa batas, ditambah fitur yang digantung pada masalah di luar jangkauan software, berujung deadlock.** Batasi 3 task per pertanyaan. Sesudahnya: eskalasi, terima sebagai batasan, atau rumuskan ulang. Metrik yang tidak stabil dinilai terhadap baseline sesi yang sama.
6. **Instruksi yang disalin ke banyak file akan saling bertentangan.** Pegang satu sumber per hal. File lain cukup menjadi penunjuk, dan rule merujuk spec alih-alih menyalinnya.
7. **NOTES yang menjadi log akan membengkak dan membekukan keputusan lama.** NOTES berisi keadaan sekarang. Setiap keputusan diberi syarat **"buka ulang jika"**.
8. **Tanpa smoke test end-to-end, fitur inti bisa mati berhari-hari tanpa ketahuan.** Jadwalkan SMOKE berkala di lingkungan atau data uji yang terisolasi. TASK-001 adalah SMOKE baseline. SMOKE yang hanya menuntut "tercetak" juga meloloskan kerusakan: di robot meja, IMU yang mencetak gravitasi ±3 G saat diam lolos seminggu, karena Harapan task lebih lemah dari checklist project. Harapan menuntut nilai yang benar.
9. **User akan melewati protokol yang terlalu kaku.** Resmikan jalur task ad-hoc, kecuali untuk executor RENDAH.
10. **Perbaikan bisa membuka bahaya baru.** Contoh dari robot meja: memperbaiki motor yang tak pernah jalan akan membuat robot berkeliling meja padahal sensor jurangnya mati. Periksa interaksinya dengan setelan default dan pengaman lain, lalu tandai TUNGGU-USER.
11. **Disiplin fakta tetap berharga.** "Jangan klaim penyebab tanpa pembanding" berlaku untuk *klaim*. *Hipotesis* diberi tempat sendiri yang berlabel.
12. **Ruang gerak harus mengikuti kapasitas executor.**
    - Aturan "literal, berhenti saat ambigu" tepat untuk executor kecil, tetapi mencekik executor yang mampu.
    - Sebaliknya, executor kecil yang diberi kebebasan desain cenderung mengarang dan melaporkan "lulus" tanpa bukti.
13. **Batasan "fisik" sering bisa dicek terhadap spesifikasi.** Contoh dari robot meja: HDS meminta pull-up 4,7 kΩ, sedangkan kode hanya memakai pull-up internal. Selisih seperti ini dijadikan **Tugas User**, bukan task ukur berikutnya.
14. **Penolakan alat bukan rintangan untuk diakali.** Jika hook, izin, atau sandbox menolak sebuah aksi, jangan ulangi lewat tool lain. Laporkan, lalu cari jalan yang disetujui.
15. **Report bisa "lulus" tanpa bukti yang cocok.**
    - Contoh dari IoT SCADA: OK ditulis dengan kutipan log yang tidak ada di file log tersimpan, dan nilai harapan yang tidak terpenuhi tetap ditulis OK. Head meloloskannya dua kali. Robot meja mengulangnya di REPORT-054 walau aturannya sudah tertulis; kutipannya tidak disalin dari file mana pun. Di aplikasi budidaya, baris log ditulis tangan (TASK-006) dan pengamatan user dikarang dengan menyalin teks kriteria (REPORT-035). Robot meja mengulangnya di bagian Anomali REPORT-075, yang belum dicek alat; sejak v3.15 kutipan di prosa juga dicocokkan.
    - Cocokkan setiap OK dengan nilai harapan dan setiap kutipan dengan file log. Aturan saja tidak cukup: executor menyimpan output lewat `record.py` (log yang diedit tangan ketahuan dari hash-nya), menjalankan `check_evidence.py` sebelum DONE, dan menyusun report dari file tersimpan, satu sesi per task. Head menjalankan alat yang sama saat triase.
    - Urutan kekuatan bukti: yang bisa dijalankan ulang, lalu kutipan dari file tersimpan, lalu klaim.
16. **File protokol bukan tempat secret.**
    - Contoh dari IoT SCADA: nilai kunci radio tertulis di ROADMAP.
    - Rujuk secret dengan nama atau lokasinya, bukan nilainya, dan grep sebelum commit.
    - Cari juga **nilai asli** dari file secret lokal (mis. `include/secrets.h`, `.env`) di file ter-track, tanpa mencetak nilainya. Scan pola saja meloloskan refresh token Spotify yang tercetak di log uji robot meja dan sudah ter-push. Alatnya: `scripts/check_secrets.py`, yang dipasang ke `handoff/tools/`.
    - Secret yang terlanjur masuk git menjadi Tugas User: ganti kuncinya.
17. **Project tumbuh tanpa peta struktur, dan tidak ada yang sadar karena build tetap jalan.**
    - Contoh dari robot meja: kode lama di `archive/legacy/` yang bisa terbaca agen sebagai kode aktif, skrip terpecah di `tools/` dan `scripts/`, dan 23 MB log bukti tanpa aturan ukuran maupun cek secret. Yang terakhir efek samping aturan bukti skill ini sendiri.
    - Contoh dari IoT SCADA: library pihak ketiga disalin ke `lib/`, aset di root, dan tanpa test.
    - Tetapkan peta sejak awal dengan label WAJIB/STANDAR/SELERA. Label WAJIB harus bersumber dokumentasi tool.
    - Pindahkan file hanya bertahap lewat task STRUKTUR, karena rujukan mudah putus.
18. **Praktik umum belum tentu yang terbaik untuk project ini.**
    - Contoh dari pengembangan skill ini: resep penegakan sempat menulis "aturan ask/deny berlaku langsung" tanpa sumber, padahal uji lapangan IoT SCADA menunjukkan aturan baru itu belum aktif sampai sesi berikutnya.
    - Saran umum seperti Git LFS, menulis ulang riwayat git, atau memindah ratusan file demi rapi bisa lebih mahal daripada masalahnya, terutama untuk project solo.
    - Setiap rekomendasi lolos uji di §Kualitas Rekomendasi, dan selalu dibandingkan dengan opsi "biarkan".
19. **Kapasitas melekat pada model, dan model sering tidak tahu namanya sendiri.**
    - Contoh dari robot meja: di Antigravity user berganti model per task (Opus, Gemini Flash). REPORT-054 hanya menulis pelaksana "<Project> Executor (Antigravity)", dan baru 8 dari 15 report yang mencatat model, padahal kapasitas Gemini Flash diturunkan berdasarkan report itu.
    - Nilai kapasitas per model. Nama model datang dari prompt pembuka user, bukan dari tebakan executor.
    - Contoh dari aplikasi budidaya: Gemini Flash dua kali naik ke TINGGI dan dua kali gagal di task TINGGI pertamanya (klaim penyebab di REPORT-009, pengamatan user dikarang di REPORT-035). Masa percobaan yang diverifikasi sedalam tingkat lama menangkap keduanya. Aturan turunnya dibedakan: OK palsu menurunkan kapasitas, sedangkan klaim tanpa dasar di luar status dicatat sebagai Kebiasaan gagal.
20. **Commit head bisa membawa perubahan kode tanpa sengaja.**
    - Contoh dari robot meja: commit berlabel `handoff:` mengembalikan `src/` ke versi lama, sehingga perbaikan keep-alive OLED hilang dari HEAD tanpa ada yang sadar.
    - Periksa daftar file yang di-stage sebelum commit handoff. Perubahan kode dijadikan commit terpisah beserta alasannya.
21. **Model kecil gagal saat menilai sendiri, dan lolos saat skrip yang menilai.**
    - Contoh dari robot meja: Gemini Flash 3.8 menulis `err=0` yang tidak ada di log saat harus menafsirkan log sendiri (REPORT-054), tetapi lolos bersih di task atomik dengan test acceptance dari head (TASK-060). Soak 48 jam baru bisa ditulis untuk model itu setelah alat pemantaunya dibuat mandiri dan tabelnya dicetak skrip (TASK-064).
    - Untuk RENDAH, semua angka dan keputusan lolos/gagal berasal dari skrip, dan penantian panjang ditangani alat.
22. **Rantai task butuh prasyarat yang sudah diverifikasi dan sumber daya yang dikunci.**
    - Contoh dari robot meja: TASK-058 dimulai karena TASK-064 berstatus DONE, padahal report-nya belum ditriase head. Triase berikutnya juga berisiko menjalankan ulang uji yang memakai port serial di tengah soak 48 jam.
    - Prasyarat menunggu tanda triase head, dan task menyatakan sumber daya eksklusifnya.
    - Contoh dari aplikasi budidaya: sesi head yang dipanggil sebagai executor menjalankan ulang SMOKE yang sudah selesai, sehingga log bukti executor tertimpa dan satu panggilan API berbayar terpakai lagi. Karena itu executor bertanya dulu sebelum mengerjakan task yang bukan OPEN atau sudah punya report, dan `record.py` menolak menimpa log task yang sudah DONE/BLOCKED.
23. **Sesi head yang ikut mengerjakan task mencatat model dari header task.**
    - Contoh dari robot meja: REPORT-059 menulis Claude Sonnet 5.5 sesuai header, padahal yang mengerjakan sesi head Opus 5.5 (high). Hasilnya lalu ditriase sesi yang sama dan dicatat di riwayat kapasitas Sonnet.
    - Model dan effort diambil dari setelan sesi, dan task seperti itu tidak dihitung sebagai bukti kapasitas.
24. **Protokol yang benar di atas kertas bisa gagal di mesin nyata.**
    - Contoh dari robot meja: langkah penutup `graphify update .` gagal di empat report karena perintahnya tidak ada di PATH (yang jalan `python -m graphify`). `git status` di Periksa Diri hampir tidak pernah bersih karena hook graphify menulis ulang `graphify-out/` setelah setiap commit. `/<prefix>-head` juga tidak pernah terdaftar di Claude Code, karena instruksinya hanya ada di `.agents/skills/`; head tetap jalan selama ada yang menyuruhnya membaca file itu.
    - Jalankan setiap perintah protokol sekali saat menulisnya, catat berkas yang berubah sendiri, dan pastikan setiap tool yang menjalankan sebuah peran bisa menemukan instruksinya. Uji jalan juga bisa meleset dari pemakaian nyata. Contoh dari aplikasi budidaya: loop tunggu Orca v3.14 lolos uji jalan, tetapi setiap heartbeat worker tetap membangunkan head yang konteksnya ±456 ribu token. Head menganggapnya wajar dan tidak mencatatnya, jadi celah itu baru ketahuan dari transkrip sesi. Karena itu head mencatat celah skill di `handoff/SKILL-FEEDBACK.md` saat menemukannya.
25. **Test yang lulus tidak membuktikan tampilan.**
    - Contoh dari aplikasi budidaya: audit peramban head menemukan cacat di 4 dari 5 task UI yang lolos test. Tiga di antaranya cacat tampilan: tombol terlalu kecil, tab keluar layar, dan panel terlalu lebar. Dua task lolos fungsi tetapi meleset dari mockup.
    - Kriteria tampilan ditulis bisa dicek: rujukan mockup dan ukuran layar sasaran. Yang terukur dinilai skrip audit peramban; yang butuh mata dinilai head dari tangkapan layar (`head:`) atau oleh user (`user:`).
    - Untuk komponen yang perilakunya sulit diduga, implementasi rujukan head yang diuji sebelum task ditulis menemukan jebakan desain lebih murah daripada satu siklus koreksi.
    - Alat fotonya juga harus diverifikasi. Contoh dari pengembangan skill ini: `chrome --headless --window-size=375,812` menata halaman selebar ±500 px lalu memotong fotonya, sehingga dasbor robot meja tampak terpotong di "HP" padahal muat. Temuan palsu itu sempat ter-commit ke ROADMAP. `scripts/screenshot.py` memakai emulasi perangkat dan mencetak lebar layar yang benar-benar dipakai.
26. **Alat yang meluncurkan executor ikut menentukan izin dan modelnya.**
    - Contoh dari pengembangan skill ini: uji coba Orca di aplikasi budidaya dinyatakan berhasil, padahal setelan izin Orca (`Full access`) meluncurkan executor Antigravity dengan `--dangerously-skip-permissions`. Terminal Claude Code yang disiapkan sebagai cadangan juga macet di dialog persetujuan mode bypass, dan tidak ada yang tahu sampai pemeriksaan berikutnya.
    - Periksa flag izin yang ditambahkan peluncur sebelum task berisiko didelegasikan. Ambil model dan effort dari bukti peluncuran (receipt), bukan dari yang diminta, dan jalankan uji pertama dengan task baca-saja.

## Langkah Kerja

### 1. Kenali Project (semua mode)
Baca secukupnya untuk menjawab empat hal: apa produknya dan ke mana arahnya, bagaimana build/test/run, operasi apa yang berisiko, dan seperti apa keadaannya sekarang.
- `README*`, `docs/`, dokumen rencana/roadmap/audit/spec, `TODO`/`FIXME` (grep), dan issue.
- File build/test/CI dan skrip deploy.
- `git log --oneline -50`, `git status`, dan `git check-ignore -v .claude/skills .agents/skills` untuk mengetahui folder tool mana yang di-ignore.
- File agen yang sudah ada: `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.claude/`, `.agents/`, `.agent/`, `.cursor/`, `.clinerules`, `CONVENTIONS.md`, folder handoff.
- **Struktur:** jenis project dari file penandanya, komposisi folder tingkat atas, file ter-track > 1 MB, serta hasil build/generate atau secret yang ter-track. Perintahnya ada di `references/structure.md` §Survei.
- **Antarmuka:** bila project punya UI (web, mobile, desktop), cara melihatnya di mesin ini (peramban headless, alat peramban agen, emulator), ukuran layar sasaran, dan rancangan atau mockup yang berlaku.

Perintah yang tidak ada di repo jangan dikarang; tulis "belum diketahui" dan jadikan pertanyaan. File yang sudah ada dibaca dulu sebelum diubah, lalu diintegrasikan, bukan dihapus.

### 2. Tanyakan & Konfirmasi
Gabungkan jadi satu kali bertanya (pakai alat tanya-jawab bila ada). Keempat butir ini **selalu** masuk putaran itu, termasuk saat AUDIT:
1. **Tool, model, dan effort** untuk head dan untuk executor. Ini menentukan lokasi instruksi (§3) dan kapasitas executor (§Kapasitas Executor). Untuk AI lokal, tanyakan juga perkiraan panjang konteksnya. Bila executor berganti model per task di satu tool, catat setiap model yang dipakai. Model tanpa riwayat di project ditawari uji kalibrasi. Tanyakan juga apakah head menjalankan executor lewat Orca, dan urutan pilihan model bila head memilih model per task (`references/orca.md`).
   - **Model dan effort per jenis sesi** (saran awal, dikonfirmasi user): head (BOOTSTRAP, AUDIT, triase, SPIKE) memakai model terkuat dengan effort high; pekerjaan mekanis tanpa keputusan (ekspor, menjalankan alat) memakai model lebih murah dengan effort medium; executor mengikuti §Kapasitas Executor. Sesi yang dibuka dari sesi lain bisa mewarisi setelan sesi asalnya, jadi cek model dan effort setiap sesi baru begitu dibuka.
2. Operasi yang tidak boleh dilakukan agen tanpa izin eksplisit, misalnya deploy produksi, migrasi DB, flash hardware, upload/OTA, menghapus data, mengirim pesan ke orang lain, atau mengeluarkan biaya.
3. Dokumen arah yang berlaku dan prioritas 1–2 bulan ke depan.
4. Aturan kerja khusus user, dikutip apa adanya.

Butir yang belum terjawab diajukan sebagai pertanyaan. Jawaban yang sudah tercatat di repo (mis. profil executor di README, brief executor, register keputusan) atau sudah diberikan user **jangan dilewati diam-diam**. Gabungkan semuanya menjadi **satu** pertanyaan **konfirmasi satu klik** yang meringkas jawaban lama, dengan opsi pertama "Ya, masih berlaku". Jangan dijadikan pertanyaan terbuka lagi. Dengan satu pertanyaan gabungan, masih ada ruang untuk keputusan lain, karena alat tanya-jawab biasanya membatasi jumlah pertanyaan (mis. maksimal 4).

Jika user tidak bisa ditanya, pakai pilihan teraman. Kapasitas executor yang tidak diketahui dianggap SEDANG. Catat asumsinya di `ROADMAP.md` §Pertanyaan Terbuka dan di ringkasan akhir.

### 3. BOOTSTRAP
**Baca `references/templates.md` sebelum menulis file apa pun.** Struktur default:
```
<instruksi head>          T1, di lokasi tool head (mis. .claude/skills/<prefix>-head/SKILL.md)
<instruksi executor>      T2, brief executor kanonis, di lokasi yang otomatis dimuat tool executor
handoff/
├── README.md             protokol bersama + format task & report (T3)
├── ROADMAP.md            arah (T4)
├── NOTES.md              keadaan sekarang + register keputusan (T5)
├── STRUCTURE.md          peta struktur file project (T9)
├── SKILL-FEEDBACK.md     celah skill yang dicatat head, dibaca saat upgrade (T10)
├── PROMPT_*.md           prompt pembuka head dan executor untuk tool tanpa dukungan skill (T7)
├── tasks/                TASK-NNN-<slug>.md, mulai dari TASK-001 SMOKE
├── reports/              REPORT-NNN.md (REPORT_TEMPLATE.md = T6)
├── logs/                 bila ada log mentah
└── tools/                skrip pendukung: `check_evidence.py`, dan `check_secrets.py` bila project punya file secret
```
- `<prefix>` adalah nama pendek project (huruf kecil). `NOTES_ARCHIVE.md` baru dibuat bila NOTES melewati batasnya.
- **Project kecil (± di bawah 300 baris kode) → versi ringkas: maksimal 7 file baru dan sekitar 300 baris teks protokol.** Isinya:
  - Dua instruksi peran. Instruksi head versi ringkas tanpa SPIKE dan tanpa retrospektif panjang.
  - README, yang sudah memuat format task & report serta §Struktur (T9).
  - ROADMAP, ditambah §Keadaan & Keputusan sebagai pengganti NOTES.
  - TASK-001.
  - `CLAUDE.md`/rule, hanya bila ada larangan yang harus berlaku juga di luar sesi head/executor.
  - Skrip SMOKE, hanya bila memudahkan executor cukup menjalankan satu perintah.

  Lewati file pengisi (`.gitkeep`), PROMPT_*, logs/, dan NOTES_ARCHIVE.
- **BOOTSTRAP hanya menulis file protokol** (ditambah skrip SMOKE bila perlu). Kode dan test yang sudah ada tidak diubah. Test acceptance ditulis head nanti, saat membuat task FIX/FEATURE.
- **Peta struktur** (T9) disusun dari survei di langkah 1 dan standar di `references/structure.md`, termasuk §Berubah Sendiri: berkas ter-track yang ditulis ulang hook atau tool (mis. `graphify-out/`). Penyimpangan masuk ROADMAP sebagai item STRUKTUR; pelanggaran WAJIB yang merusak build menjadi FIX. File project tidak dipindah.
- **Alat cek secret.** Bila project punya file secret lokal (mis. `secrets.h`, `.env`, `secrets.json`; cari file ter-ignore bernama mencurigakan dengan `git status --ignored`), salin `scripts/check_secrets.py` dari folder skill ini ke `handoff/tools/check_secrets.py`. Isi `SECRET_FILES` dengan path file secret project, lalu jalankan `python handoff/tools/check_secrets.py --list-sources` untuk memastikan nilainya terbaca. Yang tercetak hanya nama, bukan nilai. File secret yang namanya tidak lazim wajib ditulis di `SECRET_FILES`, karena deteksi otomatis hanya mengenal nama umum. Skrip ini tidak dihitung dalam batas 7 file versi ringkas, karena disalin apa adanya.
- **Alat cek bukti.** Salin `scripts/check_evidence.py` dan `scripts/record.py` ke `handoff/tools/` untuk setiap project yang punya executor. Format bukti yang dicek ada di REPORT_TEMPLATE (T6). Executor menyimpan output bukti lewat `record.py` (asal log tercatat di `handoff/logs/provenance.jsonl`) dan menjalankan `check_evidence.py` sebelum DONE; head menjalankannya lagi saat triase. Kedua skrip ini juga tidak dihitung dalam batas 7 file.
- **Perintah dicek jalan.** Setiap perintah yang ditulis ke protokol (build, test, alat di `handoff/tools/`, langkah penutup seperti `graphify update`) dijalankan sekali di mesin ini, dan yang ditulis adalah bentuk yang jalan. Perintah di file aturan agen buatan tool lain (mis. `.agents/rules/graphify.md`) ikut dicek; bila gagal, bentuk yang jalan ditambahkan sebagai catatan di file itu. Perintah yang tidak boleh dijalankan agen (flash, deploy, migrasi) ditandai `belum dicek`.
- **Cek tampilan.** Project ber-UI: salin `scripts/screenshot.py` ke `handoff/tools/`, tulis perintahnya beserta ukuran layar sasaran di README §Lingkungan (T3, baris **Cek tampilan**), lalu jalankan sekali dan lihat hasilnya. Halaman yang butuh server (mis. `vite preview`) atau perangkat ditulis dengan langkah menyalakannya; layanan live diblokir dengan `--offline`. Jangan memotret lebar HP dengan `chrome --headless --window-size` biasa: Chrome desktop menata halaman minimal ±500 px lalu memotong fotonya. Tanpa Chrome, Chromium, atau Edge, jadikan Tugas User: cek di perangkat nyata (`user:`).
- **Executor lewat Orca.** Bila head menjalankan executor lewat Orca, ikuti `references/orca.md`. Profil Executor mencatat peluncuran Orca per model, setelan izin agen dipilih bersama user (untuk project yang punya operasi berisiko, `Full access` hanya bila user menerima risikonya, dan task yang menyentuh operasi itu tidak lewat Orca), satu dispatch baca-saja dijalankan sebelum task pertama, dan head menunggu tanpa bangun berkala atau bekerja paralel di wilayah file lain. Salin `scripts/orca_wait.py` ke `handoff/tools/`; head menunggu dengan alat itu, sehingga heartbeat worker tidak membangunkannya. Tanpa Orca, bagian **Executor lewat Orca** (T1) dan **Dijalankan lewat Orca** (T2a/T2b) dihapus.

**Lokasi instruksi per tool**

| Tool | Lokasi | Catatan |
|---|---|---|
| Claude Code | `.claude/skills/<nama>/SKILL.md` | dipanggil `/<nama>` |
| Antigravity | folder skill yang sudah dipakai di project/tool user (mis. `.agents/skills/<nama>/SKILL.md`) | ikuti konvensi repo; cek dokumentasi bila ragu |
| Tool lain & AI lokal (Cline, Continue, Aider, OpenCode, Codex, Gemini CLI, dll.) | file instruksi yang otomatis dimuat tool itu (mis. `.clinerules`, `CONVENTIONS.md`, `AGENTS.md`, `GEMINI.md`) | cek dokumentasi tool |

- **Lokasi kanonis** adalah lokasi yang **ter-commit** dan dibaca tool utama peran itu. Setiap peran punya satu salinan kanonis; tool lain cukup diberi penunjuk tipis (T7).
- Bila folder tool di-ignore git (cek `git check-ignore`), atau peran berpindah tool, simpan salinan kanonis di lokasi yang ter-commit, lalu beri penunjuk di lokasi lain. Alternatifnya, tawarkan pengecualian di `.gitignore` (mis. `.claude/*` + `!.claude/skills/`).
- **Setiap tool yang menjalankan sebuah peran harus bisa menemukan instruksinya**, sebagai salinan kanonis atau penunjuk di folder skill tool itu. Tool tiap peran ditulis di README (baris Head dan Profil Executor), dan `check_version.py` memeriksanya (penanda K1/K2).
- Untuk executor RENDAH, brief kanonis sebaiknya berada di file yang otomatis dimuat tool. Jangan sampai model kecil harus membuka file lain dulu untuk tahu aturannya.

**Isi file**: mulai dari template, lalu:
- Isi semua placeholder `{{...}}` dengan fakta project. Bagian yang tidak relevan dihapus.
- Brief executor ditulis sesuai kapasitas: T2a untuk TINGGI/SEDANG, T2b untuk RENDAH.
- Pagar pengaman diturunkan dari langkah 1–2, yaitu operasi berisiko nyata di project ini. Pagar ini hanya ditulis di brief executor (sumber tunggal); README cukup merujuknya.
- SMOKE berisi 5–10 alur end-to-end terpenting, dengan nilai harapan konkret, di lingkungan/data uji yang terisolasi. Jangan pernah memakai data produksi.
- Rujukan kode ditulis sebagai **fungsi + `file:baris`**, karena nomor baris bergeser setelah perbaikan.
- **Rantai task:** prasyarat menunggu tanda `Triase head: lolos` di task-nya, dan task yang memegang port, perangkat, atau layanan bersama diberi header `Memakai:` (T1, T3; Pelajaran 22).
- **Nilai secret** (key, token, PIN, kunci radio, password) tidak ditulis di file protokol. Rujuk dengan nama atau lokasinya saja.
- **Penanda versi:** tulis versi skill ini di kepala `handoff/README.md` (T3; LITE: T8). Nama jenis task dipertahankan apa adanya. Dalam bahasa Indonesia, nama aturan yang dicetak tebal (mis. **Integritas bukti**, **Mutu keputusan**) juga dipertahankan, termasuk di versi ringkas, karena jalur upgrade mengenali aturan dari nama itu.
- **Tag penanda dan kata kunci alat.** Tag `<!-- aw: ID -->` di template disalin apa adanya bersama aturannya, juga saat file ditulis dalam bahasa lain; `check_version.py` mengenali aturan dari tag itu. Kata yang dibaca skrip (judul report, kolom tabel Data, status, `hitung`) ditulis persis dalam bahasa Indonesia atau Inggris sesuai `references/templates.md` §Kata kunci alat.

**ROADMAP awal**:
- Kumpulkan item dari dokumen arah, TODO/FIXME, issue, dan jawaban user.
- **Verifikasi setiap item di kode** sebelum menulis statusnya: BELUM / SEBAGIAN / DONE, plus fungsi + `file:baris`.
- Item yang perbaikannya mengubah perilaku berisiko → TUNGGU-USER.
- Tindakan yang hanya bisa dilakukan user dicatat di §Tugas User.

**Task pertama**: `TASK-001` jenis SMOKE untuk baseline. Untuk executor RENDAH, tulis secara atomik: tiap langkah punya perintah persis dan output yang diharapkan, dan hasilnya dinilai skrip (`references/low-capacity.md`). Model executor yang belum punya riwayat diuji kalibrasi dulu.

### 4. AUDIT
Diagnosis dulu, ubah setelah disetujui.

1. **Kumpulkan bukti berupa angka dan kutipan:**
   - **Versi protokol.** Jalankan `python <folder skill>/scripts/check_version.py` dari root project, atau dengan path root project sebagai argumen. Hasilnya: penanda versi yang tertulis, versi efektif, dan penanda yang hilang. Penanda K1/K2 juga memeriksa apakah instruksi tiap peran bisa ditemukan tool yang tercatat di README.
   - Komposisi task (ukur vs bangun) dan rantai investigasi terpanjang.
   - Apakah dokumen arah pernah dirujuk (grep nama filenya).
   - Aturan yang mematikan inisiatif, dan apakah template report punya kanal usulan.
   - **Integritas bukti.** Ambil 1–2 report SMOKE/MEASURE terakhir dan jalankan `python <folder skill>/scripts/check_evidence.py <report>`. Cocokkan sisanya: tiap OK dengan nilai harapannya, dan tiap kutipan log dengan file log tersimpan (grep). OK yang bertentangan dengan log adalah temuan prioritas. Report lama yang belum memakai format bukti wajar banyak ditandai; yang dinilai adalah klaim yang bertentangan dengan log. Untuk report lama, jalankan juga dengan `--at-report`, yang mencocokkan kutipan dengan isi file saat report di-commit. MASALAH yang muncul di kedua mode adalah temuan; yang hanya muncul di salah satu biasanya artefak perubahan file sesudah report ditulis.
   - **Secret di file protokol dan log.** Grep pola kunci, token, PIN, dan password di `handoff/` (termasuk log) dan file instruksi agen. Jalankan `python <folder skill>/scripts/check_secrets.py handoff <file instruksi agen>` dari root project. Skrip itu mencari pola dan nilai asli dari file secret lokal tanpa mencetaknya.
   - **Struktur.** Bandingkan repo dengan peta struktur (T9), atau dengan `references/structure.md` bila belum ada peta: file salah tempat, folder baru di root, file besar yang tidak perlu ada di git, hasil generate atau secret yang ter-track, dan berkas yang berubah sendiri tanpa catatan di §Berubah Sendiri. Beri label WAJIB/STANDAR/SELERA, lalu saring dengan §Kualitas Rekomendasi.
   - **Perintah di protokol.** Jalankan sekali setiap perintah yang tertulis di README, brief executor, langkah penutup, dan file aturan agen buatan tool lain (mis. `.agents/rules/`). Perintah yang gagal (mis. tidak ada di PATH) adalah temuan, dan bentuk yang jalan ditulis ulang; di file buatan tool, bentuk itu ditambahkan sebagai catatan supaya baris asli tool tidak diubah.
   - **Kapasitas executor vs buktinya.** Apakah ruang geraknya sesuai? Apakah kenaikan kapasitas dulu didasarkan pada task berformat kapasitas target (§Kapasitas Executor)? Model tanpa riwayat → tawarkan uji kalibrasi. Task RENDAH yang menyuruh executor menghitung atau menafsirkan sendiri adalah temuan.
   - Instruksi duplikat dan kontradiksi, baik antar-file maupun antara rule/spec dan kode.
   - Fitur yang ditunda karena menunggu masalah lain.
   - Item dokumen arah/audit lama: apakah masih ada di kode? (fungsi + `file:baris`)
   - Batasan yang sudah lama diinvestigasi: bandingkan spec dengan keadaan nyata (Pelajaran 13).
   - Jalan pintas user, sebagai tanda protokol terlalu kaku, dan celah yang dicatat head di `handoff/SKILL-FEEDBACK.md`.
   - **Tool/model yang berganti sejak bootstrap.** Bila ada, jalankan checklist migrasi di bawah.
2. **Sampaikan** akar masalah beserta buktinya, hal yang dipertahankan, dan rencana perubahan. Template sasaran ada di `references/templates.md`.
   - Putaran tanya AUDIT (§2) berisi satu konfirmasi gabungan untuk jawaban yang sudah tercatat, termasuk tool/model yang dipakai sekarang. Ditambah maksimal 3 keputusan hasil diagnosis, mis. kapasitas, fokus baru, atau penegakan.
3. **Ubah file setelah user setuju**, atau bila user sudah setuju di muka. Saat menerapkan:
   - Kode sumber tidak disentuh dan file project tidak dipindah. Bug dan penyimpangan struktur masuk ROADMAP; peta struktur dibuat atau diperbarui.
   - Bila NOTES sudah menjadi log (lebih dari ±10 baris per topik), riwayat dipindah **verbatim** ke `NOTES_ARCHIVE.md` lewat skrip, lalu dicek identik dengan versi git. Bila NOTES masih ringkas, cukup dirapikan.
   - Aturan user dipertahankan apa adanya. Klarifikasi yang menggeser maknanya, termasuk perubahan pembagian peran yang melonggarkan aturan lama (misalnya head kini boleh build atau menulis patch), ditandai "perlu persetujuan user".
   - **Pagar pengaman lama dipertahankan** dan disebutkan ulang di protokol baru. Instruksi basi atau bertentangan yang ditemukan **diperbaiki**, termasuk rule always-on.
   - Alat cek secret dipasang ke `handoff/tools/` bila belum ada dan project punya file secret (cara di §3). Alat cek bukti dan `record.py` juga dipasang bila belum ada, begitu juga `orca_wait.py` bila head memakai Orca.
   - Secret yang ditemukan dihapus dari file protokol. Bila sudah terlanjur masuk riwayat git, buat Tugas User untuk mengganti kuncinya.
   - Pekerjaan user yang belum di-commit dibiarkan. Commit hanya file protokol, setelah user setuju.
   - Penolakan hook/izin tidak diakali (Pelajaran 14).

**Checklist migrasi tool/model:**
- [ ] Profil executor di README (tool, model, kapasitas)
- [ ] Lokasi instruksi kanonis dan penunjuknya (§3)
- [ ] Penegakan per tool (`references/enforcement.md`)
- [ ] Header `Butuh executor` di task OPEN
- [ ] Prompt pembuka, `CLAUDE.md`/rule, dan memori tool
- [ ] Bila memakai Orca: peluncuran per model di Profil Executor, setelan izin agen, dan dispatch baca-saja (`references/orca.md`)

**Jalur upgrade.** Dipakai bila user hanya meminta upgrade, atau bila versi efektif project lebih lama dari versi skill ini.
1. Jalankan `python <folder skill>/scripts/check_version.py` dari root project (atau dengan path-nya sebagai argumen). Bila lebih dari dua penanda dasar (v2.1) hilang, lakukan audit penuh, bukan upgrade per baris. Baca juga `handoff/SKILL-FEEDBACK.md` (LITE: di samping NOTES): entri yang dijawab versi ini ditangani bersama patch-nya, dan entri lain disampaikan ke user sebagai usulan untuk skill.
2. Untuk setiap penanda yang hilang, baca baris ID-nya di `references/changelog.md`: file sasaran, cara patch, dan perlu-tidaknya persetujuan.
3. Saring dengan §Kualitas Rekomendasi. Yang tidak sepadan untuk project ini dilewati, dan alasannya ditulis.
4. Patch seminimal mungkin di file sasaran, mengikuti bahasa dan gaya file project.
   - Jangan menulis ulang file. Aturan user dan pagar lama dipertahankan.
   - Aturan yang dipatch membawa tag `<!-- aw: ID -->` dari template. Aturan lama yang sudah dikenali lewat teksnya tidak perlu ditambahi tag.
   - Skrip yang disalin ke project (`check_evidence.py`, `check_secrets.py`, `record.py`, `orca_wait.py`) dibandingkan dulu dengan versi skill. Salinan bernama lama (sebelum v3.12, mis. `cek_bukti.py`) di-`git mv` dulu ke nama barunya (padanan di changelog v3.12). Tambalan lokal dibawa ke skill atau dipertahankan, jangan ditimpa. Contohnya tambalan kutipan user karangan di `check_evidence.py` aplikasi budidaya, yang masuk skill di v3.9, dan pola token bot Telegram `check_secrets.py` aplikasi budidaya (v3.9.1). Isi `SECRET_FILES` dibawa dari salinan lama.
   - Patch yang menggeser makna aturan user ditandai "perlu persetujuan user".
5. Perbarui penanda versi di kepala README (LITE: skill dev), lalu jalankan `check_version.py` lagi. Penanda yang dipatch harus berstatus "ada".
6. Ringkasan berisi patch yang dipasang, yang dilewati beserta alasannya, yang menunggu persetujuan, dan entri `SKILL-FEEDBACK.md` beserta Status barunya (`ditangani v<versi>` atau `ditolak: <alasan>`). Commit setelah user setuju.

### 5. LITE
Buat satu skill `<prefix>-dev` (T8) ditambah `ROADMAP.md` dan `NOTES.md`. Gerbang arah, verifikasi item di kode, hipotesis berlabel, dan SMOKE ringan tetap dipakai. Tawarkan naik ke dua agen bila nanti muncul pekerjaan panjang, atau bila user ingin executor yang lebih murah.

### 6. STRUKTUR
Untuk permintaan seperti "cek struktur project ini", tanpa audit protokol penuh.
1. Jalankan langkah 1, termasuk survei di `references/structure.md`. Tentukan jenis project dan standarnya; aturan WAJIB diambil dari dokumentasi resmi versi yang dipakai.
2. Tanyakan hanya yang tidak bisa dibaca dari repo, dalam satu putaran; keempat butir §2 tidak wajib di mode ini. Contohnya: apakah hasil generate sengaja di-commit, folder mana yang tidak boleh dipindah, dan izin mengubah file protokol (langkah 3).
3. Tulis peta struktur (T9):
   - protokol sudah ada → `handoff/STRUCTURE.md`. Mengisi ROADMAP dan menambah penunjuk ke peta di brief executor, instruksi head, dan README handoff adalah perubahan protokol, dan aturan repo sering melarangnya di luar sesi head. Mintalah izinnya di putaran tanya (langkah 2). Bila diizinkan, penyimpangan masuk ROADMAP sebagai item STRUKTUR, dan penunjuk satu baris ditambahkan (pola "Letak file" di T2a/T2b dan "Drift struktur" di T1). Bila tidak, tulis rencana dan teks penunjuk yang diusulkan di STRUCTURE.md;
   - belum ada protokol → `docs/STRUCTURE.md`, dengan bagian Penyimpangan.
4. Jangan memindah, menghapus, atau mengganti nama file project. Perapian dikerjakan nanti secara bertahap lewat task STRUKTUR, atau saat user memintanya secara eksplisit, dengan prosedur di `references/structure.md` §Memindahkan File dengan Aman.

### 7. Verifikasi Sebelum Selesai
- Semua path yang dirujuk ada, setiap perintah di protokol sudah dicek jalan (atau ditandai `belum dicek`), dan tidak ada placeholder `{{` yang tersisa.
- Ada satu sumber per instruksi (grep frasa kunci).
- **Tidak ada nilai secret di file protokol maupun log** (`check_secrets.py` atas `handoff/` dan file instruksi). Bila alat terpasang, `--list-sources` menunjukkan file secret project terbaca.
- README mendefinisikan status SMOKE: OK hanya bila nilai teramati memenuhi nilai harapan. `handoff/tools/check_evidence.py` dan `handoff/tools/record.py` terpasang, dan REPORT_TEMPLATE memakai format bukti yang dicek alat itu.
- **Bacaan wajib executor muat di konteksnya.** Untuk RENDAH: brief ±80 baris ditambah task.
- **Project kecil:** jumlah file baru dan total baris masih dalam batas versi ringkas (§3).
- **Peta struktur** ada: file sendiri, §Struktur di README, atau `NOTES.md` §1 untuk LITE. Setiap aturan WAJIB punya sumber, dan pola Tidak Masuk Git sudah ada di `.gitignore` atau selisihnya dicatat.
- **Tidak ada file project yang dipindah, dihapus, atau diganti nama** (cek `git status`), kecuali atas permintaan eksplisit user.
- **Penanda versi** ada di README (LITE: skill dev), dan `check_version.py` tidak melaporkan penanda yang hilang untuk versi skill ini. Tag `<!-- aw: ... -->` ikut tersalin, termasuk bila protokol ditulis dalam bahasa lain.
- **Project ber-UI:** baris Cek tampilan di README sudah dicek jalan, atau ditulis sebagai Tugas User.
- **Setiap rekomendasi lolos §Kualitas Rekomendasi**: bersumber atau terverifikasi, dibandingkan dengan "biarkan", aman, dan bisa dikerjakan. Ringkasan menaruh rekomendasi utama di depan beserta alasannya.
- **Dry-run head**: baca instruksi head seolah memulai sesi, lalu tulis 3 langkah pertamanya. Hasilnya harus memajukan ROADMAP atau menjalankan SMOKE baseline.
- **Dry-run executor** (SEDANG/RENDAH): baca TASK-001 seolah model kecil. Apakah task itu bisa dikerjakan tanpa menjelajah codebase? Untuk RENDAH: maksimal ±8 langkah, dan setiap angka atau OK berasal dari output perintah atau skrip.
- Ringkasan ke user berisi file yang dibuat/diubah, kapasitas executor yang dipakai, jawaban yang dikonfirmasi user, terpisah dari asumsi dan dari keputusan yang masih perlu dikonfirmasi, kekurangan yang tersisa, penegakan yang ditawarkan, dan cara memulai.
- Jangan commit sebelum user setuju.

## Kualitas Rekomendasi
Berlaku untuk semua yang disarankan skill ini: rencana AUDIT, item ROADMAP, peta struktur, penegakan, dan ringkasan ke user. Aturan ini juga diturunkan ke instruksi head (T1) dan skill LITE (T8). Setiap rekomendasi harus:
1. **Benar.** Bersumber dari dokumentasi versi yang dipakai project, atau terverifikasi di repo (perintah, kutipan, `file:baris`). Yang belum terverifikasi ditulis "perlu dicek", bukan sebagai fakta.
2. **Perlu.** Menyelesaikan masalah nyata di project ini, dengan buktinya. Alasan "praktik umum" saja tidak cukup.
3. **Terbaik untuk konteks ini.** Bandingkan minimal dua opsi, termasuk "biarkan" atau "tunda". Timbang dampak, biaya, risiko, dan konteks project: solo atau tim, hardware, kapasitas executor, tenggat. Tulis alasannya dan opsi yang ditolak.
4. **Aman.** Bisa dibalik, atau risikonya dan cara mundurnya disebut. Yang berisiko menjadi TUNGGU-USER.
5. **Bisa dikerjakan.** Ada langkah konkret dan cara verifikasinya.

Urutkan rekomendasi dari dampak terbesar dibanding biayanya, dan tandai satu rekomendasi utama. Sedikit rekomendasi yang kuat lebih baik daripada daftar panjang. Rekomendasi yang gagal salah satu uji dibuang, atau diturunkan menjadi catatan atau pertanyaan.

## Kapasitas Executor

| Kapasitas | Contoh | Task dari head | Ruang gerak executor | Bacaan wajib executor | Bukti di report | Verifikasi oleh head |
|---|---|---|---|---|---|---|
| TINGGI | Model setara head | Tujuan + kriteria terima; FEATURE boleh terbuka | Mendesain FIX/FEATURE/SPIKE | Brief + task | Fakta + kutipan dari file log | `check_evidence.py`; baca report, cocokkan sampel OK dan kutipan |
| SEDANG | Model cepat/murah | + sketsa desain (file, fungsi, antarmuka) dan test acceptance yang bisa dijalankan | Detail implementasi di file yang disebut, diulang sampai test lulus; tanpa SPIKE | Brief + task | + output test/perintah utama | `check_evidence.py`, cek diff, jalankan test; cocokkan semua OK |
| RENDAH | AI lokal kecil, konteks pendek | Atomik & mandiri: satu perubahan, fungsi + `file:baris`, potongan kode disalin ke task, perintah persis, output yang diharapkan | Literal untuk semua jenis; ambigu atau gagal 2× → BLOCKED | Brief ringkas (±80 baris) + task | Output perintah ditempel apa adanya | `check_evidence.py`; baca seluruh diff termasuk file baru, lalu jalankan ulang skrip penilai |

- **Kapasitas awal:**
  - Model setara head → TINGGI.
  - Model lain yang belum punya riwayat di project → **uji kalibrasi** (±15 menit, `scripts/calibrate.py`, cara di `references/low-capacity.md`; seed disimpan skrip di luar project, hasilnya diarsipkan ke `handoff/logs/`): lolos K1–K3 → SEDANG; lolos K1 dan K3 → RENDAH; gagal K1 atau K3 → jangan dipakai sebagai executor.
  - Tanpa kalibrasi: model cepat/murah (mis. varian Flash, Haiku, mini) → SEDANG dengan verifikasi penuh; model lokal kecil (± ≤14B) → RENDAH.
  - Indeks benchmark publik (mis. Artificial Analysis) dan mode "high reasoning" tidak otomatis menaikkan tier; pakai untuk memilih model yang dicoba. Kalibrasi berlaku per model dan effort.
- **Naik hanya dari bukti berformat kapasitas target.** Contoh untuk SEDANG→TINGGI: minimal 1 FIX/FEATURE yang ditulis tanpa sketsa rinci, ditambah 1 SMOKE/MEASURE dengan bukti log yang terverifikasi, semuanya lolos tanpa koreksi. Task yang ditulis sangat rinci tidak dihitung. Contoh untuk RENDAH→SEDANG: 2 task berturut-turut tanpa koreksi, minimal 1 berformat SEDANG (tujuan, kriteria, sketsa; tanpa langkah atomik), dipilih yang pendek dan berisiko rendah. Uji kalibrasi hanya menentukan kapasitas awal. Model yang punya **Kebiasaan gagal** baru naik setelah 2 report berturut-turut bebas dari kebiasaan itu. Setelah naik, 2 task pertama adalah **masa percobaan**: diverifikasi sedalam tingkat lama, dan pelanggaran di masa itu mengembalikan model ke tingkat lama.
- **Turun satu tingkat** bila ada **OK palsu**, yaitu status OK yang buktinya tidak ada, bertentangan dengan nilai harapan, atau dikarang (kutipan yang tidak ada di file log, baris log yang bukan output perintah, pengamatan user yang tidak pernah diberikan user), atau bila pagar pengaman dilanggar. Klaim penyebab sebagai fakta, angka tanpa pengukuran, dan Batasan task yang dilanggar tanpa dilaporkan dicatat sebagai **Kebiasaan gagal**, dan task itu tidak dihitung untuk naik. Kapasitas tidak diturunkan karenanya, karena di SEDANG/RENDAH head memverifikasi setiap status.
- **Saat kapasitas berubah**, perbarui header `Butuh executor` di task OPEN, dan tulis ulang task yang formatnya tidak lagi cocok. Catat perubahannya di README §Profil Executor dan di register keputusan.
- Task yang butuh desain bebas atau eksplorasi diberi header `Butuh executor: TINGGI`. Task itu dikerjakan model kuat atau head sendiri.
- **Satu tool, beberapa model.** Bila user berganti model per task (mis. Antigravity dengan Opus dan Gemini Flash), atau model executor tersebar di beberapa tool, kapasitas dinilai **per model**. Profil Executor berisi satu baris per model beserta tool-nya, header `Butuh executor` menentukan model yang boleh dipakai, dan naik/turun dicatat per model. Nama model dan effort diambil dari prompt pembuka (T7), bukan tebakan executor.
- **Pilihan model per task.** Head memilih model untuk setiap task: yang termurah dengan kapasitas cukup, mengikuti urutan pilihan user di Profil Executor, kecuali model itu punya Kebiasaan gagal yang mengenai task tersebut. Alasannya ditulis di header task. Model yang belum punya kapasitas tercatat di Profil Executor tidak menerima task sampai kapasitas awalnya ditetapkan, biasanya lewat kalibrasi.
- **Task yang dikerjakan sesi head** (atas permintaan user) dicatat `sesi head · <model> (<effort>)` dari setelan sesi, bukan dari header task, dan tidak dihitung sebagai bukti kapasitas executor. Task yang pendek dan murah lebih baik dibuka di sesi baru dengan model sesuai header.
- **Kebiasaan gagal per model.** Kegagalan yang khas untuk satu model (mis. menulis OK tanpa mencocokkan log) dicatat di Profil Executor beserta penangkalnya, dan head menuliskan penangkal itu di setiap task untuk model tersebut. Dengan begitu model tetap bisa dipakai dengan pagar yang tepat, tidak hanya diturunkan kapasitasnya. Hanya OK palsu dan pelanggaran pagar pengaman yang menurunkan kapasitas (**Turun satu tingkat**).
- Untuk SEDANG/RENDAH, head yang mendesain. Biaya token head jadi naik; itu harga dari executor yang murah. Jangan biarkan head kembali pasif. Kurangi biaya itu dengan memindahkan ke executor apa yang bisa diverifikasi murah: bacaan luas lewat task FAKTA, dan pemeriksaan lewat **Periksa diri** sebelum DONE. Token executor yang murah paling berguna untuk membaca dan memeriksa.

**Executor RENDAH** (rincian, contoh, dan pengaman AI lokal di `references/low-capacity.md`):
- **Bukti dari skrip.** Setiap angka dan keputusan lolos/gagal di report berasal dari output skrip yang ditulis head: penilai (test acceptance) untuk FIX/FEATURE, penganalisis log untuk MEASURE/SMOKE. Head menjalankan skrip itu dulu pada data contoh dan mengambil nilai harapan dari hasilnya; verifikasi head = menjalankan ulang skrip.
- **Ukuran task.** Selesai dalam satu sesi kerja: maksimal ±8 langkah, cabang hanya dalam tabel jika–maka (maks. 3). Penantian dan dialog panjang (soak, menemani user saat uji) dipindah ke alat; executor cukup menjalankan alat lalu penganalisisnya.
- **Yang tetap dijaga:** test acceptance tidak diubah executor, review head mencakup file baru (`git status --porcelain`), dan brief menolak task di atas kapasitas tanpa jalur ad-hoc.

## Template, Struktur & Penegakan
- **Template** T1–T10, placeholder, dan penyesuaian per jenis project ada di `references/templates.md`. Baca file itu sebelum BOOTSTRAP/LITE, dan saat AUDIT bila butuh struktur sasaran.
- **Standar struktur** per jenis project, survei, aturan log bukti, dan cara memindah file ada di `references/structure.md`. Baca file itu saat BOOTSTRAP, AUDIT, dan mode STRUKTUR.
- **Alat cek secret** generik ada di `scripts/check_secrets.py`. Cara memasangnya ada di §3.
- **Changelog dan cek versi** (`references/changelog.md` + `scripts/check_version.py`) dipakai jalur upgrade di §4.
- **Resep penegakan per tool** ada di `references/enforcement.md`: Claude Code `permissions`, Antigravity, setelan izin agen di Orca, Cline, dan hook git. Tawarkan ke user; pasang hanya setelah disetujui.

## Batasan Skill Ini
- **Instruksi, bukan penegakan.** Untuk operasi kritis, tawarkan penegakan nyata (`references/enforcement.md`). Jangan mengubah setelan tanpa izin.
- **Kemampuan model murah dan AI lokal sangat bervariasi.** Kalibrasi dulu, mulai dari task kecil, lalu naikkan setelah terbukti.
- **Konvensi folder tiap tool dan standar struktur file berubah antar versi tool.** Cek dokumentasi tool bila ragu; label WAJIB harus bersumber dokumentasi versi yang dipakai project. Perintah Orca juga berubah: `references/orca.md` ditulis untuk Orca 1.4.243 (dicek ulang dengan 1.4.244), dan panduan yang cocok dengan versi terpasang dicetak `orca skills get orchestration`.
- **Hasil hanya sebaik bahannya.** Tanpa dokumen arah atau jawaban user, ROADMAP awal akan tipis. Tulis sebagai Pertanyaan Terbuka, jangan mengarang.
- **Skill yang dihasilkan tidak memperbarui dirinya sendiri.** Jalankan mode AUDIT secara berkala, saat project terasa macet, atau saat skill ini naik versi. Jalur upgrade (§4) memasang aturan baru sebagai patch minimal.
- **Untuk dipakai di tool lain**, lampirkan `SKILL.md` beserta folder `references/` dan `scripts/`.
