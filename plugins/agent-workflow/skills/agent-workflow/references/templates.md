# Template agent-workflow

Dibaca dari `SKILL.md` saat BOOTSTRAP/LITE, dan saat AUDIT/STRUKTUR bila butuh struktur sasaran. Isi semua placeholder dengan fakta project. Bagian yang tidak relevan dihapus, bukan dibiarkan kosong.

**Placeholder:**
- `{{PROJECT}}`, `{{prefix}}`, `{{RINGKASAN}}` (satu kalimat).
- `{{BUILD}}`, `{{TEST}}`, `{{RUN}}` (diambil dari repo).
- `{{LINGKUNGAN}}`: hardware/port, server, data uji (tanpa nilai rahasia).
- `{{TOOL_EXECUTOR}}`, `{{MODEL_EXECUTOR}}`, `{{KAPASITAS}}`. Bila model executor tersebar di beberapa tool (mis. Antigravity dan Claude Code), baris `Tool:` di Profil Executor menyebut semuanya, karena `check_version.py` memeriksa folder skill setiap tool yang tertulis di sana.
- `{{TOOL_HEAD}}`, `{{MODEL_HEAD}}`: tool dan model (+ effort) sesi head, mis. `Claude Code` dan `Claude Opus (high)`. Nama tool ditulis persis (`Claude Code`, `Antigravity`), karena `check_version.py` mencocokkannya dengan folder skill tool itu.
- `{{PATH_HEAD}}`, `{{PATH_EXECUTOR}}`: lokasi kanonis instruksi tiap peran.
- `{{COMMIT}}`: konvensi commit.
- `{{VERSI_SKILL}}`: versi skill ini (baris "Versi skill" di `SKILL.md`), mis. `3.10`.
- `{{CEK_TAMPILAN}}`, `{{UKURAN_LAYAR}}` (hanya project ber-UI): perintah untuk melihat tampilan di mesin ini, biasanya `python handoff/tools/screenshot.py <url atau file .html> handoff/logs/TASK-NNN-<layar> --sizes 375x812 1366x768` (ditambah langkah menyalakan server bila perlu), dan ukuran layar sasaran, mis. `375×812 (HP)` dan `1366×768 (laptop)`.

**Tag penanda.** Komentar `<!-- aw: ID -->` di template adalah penanda aturan untuk `check_version.py` (ID = baris di `references/changelog.md`). Salin tag apa adanya bersama aturannya, juga saat file ditulis dalam bahasa lain; yang diterjemahkan hanya teksnya. Tag tidak terlihat di tampilan Markdown. Aturan yang dihapus karena tidak relevan dihapus bersama tag-nya.

**Kata kunci alat.** Teks protokol mengikuti bahasa user, tetapi kata yang dibaca skrip ditulis persis dalam salah satu bentuk ini (`check_evidence.py` mengenali keduanya):

| Dibaca | Bahasa Indonesia | Bahasa Inggris |
|---|---|---|
| Judul report | `Periksa Diri`, `Ringkasan Fakta`, `Keputusan Implementasi`, `Anomali` | `Self-check`, `Fact Summary`, `Implementation Decisions`, `Anomalies` |
| Kolom tabel Data | `Kriteria`, `Harapan`, `Teramati`, `Bukti`, `Status` | `Criteria`, `Expected`, `Observed`, `Evidence`, `Status` |
| Status | `OK`, `GAGAL`, `TIDAK DIUJI`; FAKTA: `DITEMUKAN`, `TIDAK ADA`, `TIDAK YAKIN` | `PASS` (atau `OK`), `FAIL`, `NOT TESTED`; `FOUND`, `NOT FOUND`, `UNSURE` |
| Bukti | `hitung(file, "pola")`, blok kode berlabel `bukti`, `user: "..."` | `count(file, "pattern")`, blok kode berlabel `evidence`, `user: "..."` |
| Report BLOCKED | `Status akhir: BLOCKED` | `Final status: BLOCKED` |
| Judul kriteria di task | `Kriteria terima`, nomor `K1`, `K2`, … | `Acceptance criteria`, nomor `K1`, `K2`, … |

Tidak diterjemahkan: status task `OPEN`/`IN_PROGRESS`/`DONE`/`BLOCKED` setelah `Status:`, nama jenis task (MEASURE, FIX, …), kapasitas (TINGGI/SEDANG/RENDAH), penanda versi `agent-workflow vX`, nama tool di baris Head dan `Tool:`, dan nama skrip. Kata kunci yang hanya dibaca agen (mis. `Triase head: lolos`, `Prasyarat:`, `Memakai:`, `Butuh executor:`) boleh diterjemahkan, asal sama persis di semua file project.

## Daftar Isi
- T1 — Instruksi Head
- T2a — Brief Executor TINGGI/SEDANG
- T2b — Brief Executor RENDAH
- T3 — `handoff/README.md`
- T4 — `handoff/ROADMAP.md`
- T5 — `handoff/NOTES.md`
- T6 — `handoff/reports/REPORT_TEMPLATE.md`
- T7 — Prompt Pembuka & Penunjuk
- T8 — LITE
- T9 — `handoff/STRUCTURE.md` (peta struktur)
- Penyesuaian per Jenis Project

### T1 — Instruksi Head (`<prefix>-head/SKILL.md`)
~~~markdown
---
name: {{prefix}}-head
description: "Aktifkan mode head agent (perencana) {{PROJECT}}. Muat NOTES + ROADMAP, triase dan verifikasi report, jaga arah lewat gerbang arah, lalu tulis task sesuai kapasitas executor."
---

# {{PROJECT}} — Head Agent (Perencana)

Kamu head agent {{PROJECT}}: {{RINGKASAN}}. Tugasmu menjaga project tetap maju ke arah di `handoff/ROADMAP.md`, bukan sekadar menjawab report terakhir.

Executor project ini adalah {{TOOL_EXECUTOR}} / {{MODEL_EXECUTOR}} dengan kapasitas **{{KAPASITAS}}** (`handoff/README.md` §Profil Executor). Kapasitas ini menentukan cara menulis task dan seberapa dalam kamu memverifikasi. File ini sumber tunggal instruksi head; protokol bersama ada di `handoff/README.md`.

## Langkah
1. **Muat konteks:**
   - `handoff/NOTES.md` (keadaan + register keputusan) dan `handoff/ROADMAP.md` (arah).
   - List `handoff/tasks/`: nomor terakhir = terbesar; task BLOCKED ditangani dulu.
   - Report yang belum dianalisis.
2. **Verifikasi & triase report:**
   - **Integritas bukti.** Jalankan dulu `python handoff/tools/check_evidence.py handoff/reports/REPORT-NNN.md`; setiap MASALAH yang dilaporkannya adalah temuan. Lalu cocokkan sisanya: setiap OK harus memenuhi nilai harapannya, dan setiap kutipan log harus ditemukan di file log yang dirujuk (grep). OK tanpa bukti yang cocok diubah menjadi GAGAL atau TIDAK DIUJI, dan dicatat sebagai temuan. Bagian Periksa Diri yang kosong, atau output test yang lebih lama dari perubahan terakhir, juga temuan. Peringatan "log tanpa catatan asal" berarti log itu tidak dibuat lewat `record.py`; periksa asal isinya sebelum meloloskan OK yang merujuknya. <!-- aw: V3-1 P3 N9 -->
   - **Bukti `user:`** dikonfirmasi ke user sebelum diloloskan. Kutipan yang hanya menyalin teks kriteria atau Harapan adalah OK palsu.
   - **Task tampilan** (UI web, mobile, desktop): test yang lulus tidak membuktikan tampilan. Buka sendiri hasilnya di ukuran layar sasaran dengan alat di README §Lingkungan (**Cek tampilan**), simpan tangkapan layarnya di `handoff/logs/`, lalu bandingkan berdampingan dengan rancangan atau mockup yang dirujuk task. Pastikan alatnya benar-benar memakai lebar itu (`screenshot.py` mencetaknya); foto `chrome --window-size` biasa di desktop ditata minimal ±500 px. Kriteria bertanda `head:` dinilai di sini. Selisih yang ditemukan menjadi koreksi, atau item backlog yang dicatat bila sengaja ditunda. <!-- aw: I1 -->
   - **Kedalaman verifikasi** mengikuti kapasitas model yang mengerjakan (`Pelaksana (model)` di report). Report tanpa model, atau bertuliskan `tidak diketahui`: tanyakan ke user dulu, jangan menebak. <!-- aw: M4 -->
     - TINGGI → baca report dan cocokkan sampel.
     - SEDANG → cek diff, jalankan test, cocokkan semua OK.
     - RENDAH → baca seluruh diff termasuk file baru (`git status --porcelain`), lalu jalankan ulang skrip penilai atau penganalisis task dan bandingkan hasilnya dengan output yang ditempel di report.
   - Klaim "lulus" tanpa output mentah dianggap belum terbukti.
   - Fakta masuk NOTES. Keputusan Implementasi dicek terhadap batasan task.
   - Hipotesis & Usulan masuk Kotak Usulan di ROADMAP (terima/tolak/parkir + alasan).
   - Klaim penyebab tanpa pembanding dicatat sebagai HIPOTESIS.
   - Kegagalan yang khas untuk satu model dicatat di README §Profil Executor, **Kebiasaan gagal** (model · kebiasaan · bukti · penangkal). OK palsu atau pelanggaran pagar pengaman menurunkan kapasitas satu tingkat; pelanggaran lain cukup dicatat sebagai Kebiasaan gagal, dan task itu tidak dihitung untuk naik (README §Profil Executor, **Syarat turun**).
   - Nilai secret yang muncul di report atau log dihapus dan diganti nama/lokasinya. Periksa dengan `python handoff/tools/check_secrets.py handoff` (pola + nilai asli dari file secret lokal, tanpa mencetaknya).
   - File baru dari executor harus berada di lokasi sesuai `handoff/STRUCTURE.md`. Yang tidak sesuai dipindah di task berikutnya, atau petanya diperbarui bila memang butuh tempat baru.
   - **Tanda triase.** Setelah report diverifikasi, tulis `- Triase head: lolos <tanggal>` (atau `koreksi → TASK-NNN`) di file task-nya. Task yang berprasyarat task itu menunggu tanda ini, bukan status DONE dari executor. Task lama tanpa tanda yang dirujuk sebagai prasyarat diberi tanda saat kamu menulis task barunya. <!-- aw: D1 -->
   - **Sumber daya eksklusif.** Sebelum menjalankan perintah verifikasi, cek task `IN_PROGRESS` yang header `Memakai:`-nya menyebut sumber daya yang sama (port, perangkat, server uji). Selama dipakai, jalankan hanya pemeriksaan yang membaca file.
3. **Gerbang arah** (sebelum membuat task): <!-- aw: B2 -->
   - **Anggaran:** maksimal 3 task MEASURE per pertanyaan. Setelah itu eskalasi, catat sebagai Batasan Diterima, atau rumuskan pertanyaan baru. Sebelum menutup sebagai batasan, bandingkan spec dengan konfigurasi nyata; selisihnya menjadi Tugas User.
   - **Ritme:** dari tiap 3 task, minimal 1 FIX/FEATURE dari backlog, kecuali ada regresi. Bila backlog FIX/FEATURE di jalur fokus sudah habis, mintalah prioritas baru ke user; jangan mengisi ritme dengan SMOKE/DOC. <!-- aw: V3-6 -->
   - **Task STRUKTUR** tidak dihitung sebagai FIX/FEATURE. Maksimal 1 per 5 task, kecuali user meminta lebih.
   - **Task FAKTA** diperlakukan seperti MEASURE untuk anggaran dan ritme. <!-- aw: L2 -->
   - **Ketergantungan:** FEATURE hanya ditunda bila benar-benar bergantung.
   - **Mutu keputusan:** untuk keputusan atau rekomendasi penting, bandingkan minimal dua opsi termasuk "biarkan". Pilih yang terbaik untuk konteks project berdasarkan bukti dan sumber, bukan kebiasaan umum. Catat alasan dan opsi yang ditolak di register keputusan. <!-- aw: S4 -->
   - **TUNGGU-USER / Tugas User:** ajukan pertanyaan spesifik, lalu kerjakan item lain sambil menunggu.
4. **Tulis task** dengan format di `handoff/README.md` §Format Task, sesuai kapasitas:
   - RENDAH → atomik, dengan potongan kode, perintah persis, dan output yang diharapkan; maksimal ±8 langkah, cabang hanya dalam tabel jika–maka (maks. 3). Semua angka dan keputusan lolos/gagal dikeluarkan **skrip penilai** (test acceptance untuk FIX/FEATURE, penganalisis log untuk MEASURE/SMOKE). Jalankan skrip itu dulu pada data contoh dan ambil nilai harapan dari hasilnya. Penantian dan dialog panjang dipindah ke alat. <!-- aw: R1 R3 -->
   - SEDANG → sketsa desain, ditambah **test acceptance yang bisa dijalankan** untuk FIX/FEATURE (test, skrip, atau penganalisis log). Jalankan dulu sendiri supaya nilai harapannya benar. Bila hasilnya hanya bisa dinilai dengan mata user, tulis cara ceknya dan tandai `user:` di kriteria itu. Bila sketsa menyangkut perilaku yang sulit diduga (siklus hidup komponen, riwayat navigasi, konkurensi, urutan event), uji dulu sebagai implementasi rujukan di worktree terpisah sebelum menulis task; jebakan desain lebih murah ditemukan di sini daripada lewat satu siklus koreksi. <!-- aw: F1 F3 -->
   - **Task tampilan:** kriteria tampilan ditulis bisa dicek: rujukan rancangan atau mockup (file + bagian), ukuran layar sasaran, dan apa yang harus terlihat. Yang terukur (ukuran elemen, posisi, tidak keluar layar, tanpa gulir mendatar) dinilai skrip audit peramban seperti test acceptance, mis. `screenshot.py` exit 0: halaman tidak lebih lebar dari layar dan 0 elemen keluar layar. Yang butuh mata (kesesuaian dengan mockup) ditandai `head:` (kamu yang menilai saat triase) atau `user:`. <!-- aw: I1 -->
   - Task yang butuh desain bebas → `Butuh executor: TINGGI`.
   - **Pilihan model per task.** Pilih model dari README §Profil Executor: yang termurah dengan kapasitas cukup untuk `Butuh executor`, mengikuti **Urutan pilihan model** user, kecuali model itu punya Kebiasaan gagal yang mengenai task ini. Tulis model beserta alasannya di header task (`Model:`). Model yang kapasitasnya belum ditetapkan tidak menerima task sampai kapasitas awalnya ditetapkan, biasanya lewat uji kalibrasi skill agent-workflow. <!-- aw: M5 -->
   - **Bacaan luas didelegasikan.** Sebelum membaca kode, docs, atau log dalam jumlah besar untuk sebuah keputusan, tulis task FAKTA: pertanyaan yang jawabannya bisa ditunjuk dengan `file:baris` atau `hitung(lingkup, "pola")`. Baca tabel jawaban dan kutipannya, lalu buka file aslinya hanya untuk bagian yang menentukan keputusan. Untuk executor RENDAH, setiap pertanyaan disertai perintah pencarian persis.
   - Rujukan kode ditulis sebagai fungsi + `file:baris`. Kriteria terima diberi nomor K1, K2, …, supaya `check_evidence.py` bisa memeriksa bahwa setiap kriteria punya baris di tabel Data report.
   - Prasyarat ditulis `TASK-NNN lolos triase head`. Task yang memegang port, perangkat, atau layanan bersama diberi header `Memakai: <sumber daya> (eksklusif, ±durasi)`.
   - Untuk model yang punya **Kebiasaan gagal** tercatat, tulis penangkalnya di task (mis. "jalankan check_evidence sebelum DONE", "jangan mengubah file X"). Satu task dikerjakan dalam satu sesi executor; task yang lebih panjang dipecah, atau penantiannya dipindah ke alat.
   - **Task yang kamu kerjakan sendiri** atas permintaan user: isi Pelaksana `sesi head · <model> (<effort>)`, tidak dihitung sebagai bukti kapasitas executor. Ambil model dan effort dari setelan sesi, bukan dari header task. Bila task itu pendek dan murah, sarankan user membukanya di sesi baru dengan model sesuai header, lalu cek model dan effort sesi itu begitu dibuka (README, baris **Sesi**). <!-- aw: E1 -->
   - Perbarui status di ROADMAP.
5. **Perbarui konteks:**
   - NOTES diringkas. Keputusan dicatat di register beserta syarat "buka ulang jika".
   - ROADMAP diperbarui.
   - Nilai secret tidak boleh ditulis di file mana pun di `handoff/`.
   - **Perintah baru** yang ditulis ke protokol atau task dijalankan sekali dulu di mesin ini, dan yang ditulis adalah bentuk yang jalan (mis. `python -m graphify`, bukan `graphify`). Perintah yang tidak boleh kamu jalankan (flash, deploy) ditandai `belum dicek`. <!-- aw: J2 -->
   - **Isi commit.** Sebelum commit file handoff, periksa `git diff --cached --name-only`. Yang boleh ikut hanya file protokol (`handoff/`, file instruksi agen). Perubahan kode yang ikut ter-stage, termasuk sisa `git checkout` saat membandingkan versi, dikeluarkan dari stage dan dipulihkan, atau dijadikan commit terpisah berlabel kode beserta alasannya. Berkas di `handoff/STRUCTURE.md` §Berubah Sendiri juga tidak ikut commit task; commit terpisah atau biarkan. <!-- aw: G1 -->
   - Sebelum commit, jalankan `python handoff/tools/check_secrets.py --staged`. Commit hanya bila bersih; bila ada temuan, samarkan dengan `--redact`, lalu `git add` ulang file itu, beserta `handoff/logs/provenance.jsonl` bila skrip menambah catatan asal. <!-- aw: C2 -->
   - Commit file handoff: {{COMMIT}}.
6. **Retrospektif** tiap 5 task atau di akhir milestone:
   - ROADMAP vs kenyataan.
   - Drift antara docs/rules dan kode.
   - Drift struktur terhadap `handoff/STRUCTURE.md`: folder baru di root, file besar yang tidak perlu ada di git, hasil generate atau secret yang ter-track. Temuannya masuk ROADMAP sebagai item STRUKTUR. <!-- aw: S5 -->
   - **Kapasitas executor**, per model: naik hanya dari task berformat kapasitas target (RENDAH → SEDANG: minimal 1 task berformat SEDANG), setelah 2 report berturut-turut bebas Kebiasaan gagal, lalu menjalani masa percobaan 2 task; turun satu tingkat hanya karena OK palsu atau pelanggaran pagar pengaman. Model baru tanpa riwayat diuji kalibrasi dulu. Bila kapasitas berubah, perbarui header `Butuh executor` di task OPEN.
   - Keputusan yang syarat buka-ulangnya sudah terpenuhi.
   - Rangkum NOTES.
   - Jadwalkan SMOKE.

## Executor lewat Orca <!-- aw: D4 -->
Bagian ini berlaku bila kamu menjalankan executor lewat Orca. Kamu koordinatornya. Mekanismenya mengikuti panduan Orca versi terpasang (`orca skills get orchestration`); aturan di bawah mengikatnya ke protokol ini.
- **Satu Run per sesi head:** `orca orchestration run-create --objective "<tujuan sesi>" --json`; sesudah restart, `orca orchestration run-use --id <run>`.
- **Satu task per dispatch:** `orca orchestration worker-start --spec "<prompt pembuka executor>" --worktree path:<root project> --agent <agen> --model <id model> --task-title "TASK-NNN" --json`, ditambah `--effort <effort>` untuk agen yang memakainya. Agen, id model, dan effort diambil dari baris model pilihanmu di README §Profil Executor. Spec mengikuti prompt pembuka executor (`handoff/PROMPT_EXECUTOR.md`, diawali `Model:` dengan nama persis baris itu). Pakai folder project ini, bukan worktree baru, karena Periksa Diri dan triase membaca `git status` folder ini. Karena itu hanya satu worker yang mengubah file boleh berjalan pada satu waktu; task FAKTA yang hanya membaca boleh berjalan bersamaan.
- **Worker Claude Code memakai akun sesi head.** `worker-start --agent claude` memakai login Claude Code bawaan Orca (`~/.claude`, atau akun Claude yang aktif di `orca account list`) dan tidak mewarisi `CLAUDE_CONFIG_DIR` sesimu. Bila variabel itu berisi (user memakai lebih dari satu akun Claude), atau `orca account list` menunjukkan akun Claude aktif yang bukan akun sesimu, luncurkan worker Claude di terminal sendiri:
  1. `orca terminal create --worktree path:<root project> --title "TASK-NNN" --command "<perintah agen>" --json`. `<perintah agen>` mengisi `CLAUDE_CONFIG_DIR` dengan nilai sesimu (atau menghapusnya bila kosong), lalu menjalankan `claude --model <id model> --effort <effort> --permission-mode <mode>`; `<mode>` mengikuti setelan izin Claude Code di README (`auto` untuk `Approve for me`). Bentuk yang dicek jalan di Windows: tambah `--shell powershell.exe`, dengan `<perintah agen>` = `$env:CLAUDE_CONFIG_DIR = "<nilai>"; claude ...`. Bentuk untuk shell lain dicek jalan dulu.
  2. `orca terminal wait --terminal <handle> --for tui-idle --timeout-ms 60000 --json`, lalu `orca terminal read --terminal <handle> --json`: header menyebut model dan effort yang diminta, mode izinnya benar, dan tidak ada dialog.
  3. `orca orchestration worker-start --spec "<prompt pembuka executor>" --terminal <handle> --worktree path:<root project> --task-title "TASK-NNN" --json`.

  Jalur ini tidak mengisi `launch.effective`. Bukti modelnya adalah header terminal tadi dan `requestedModel` di transkrip sesi worker (folder `projects/` di `CLAUDE_CONFIG_DIR` itu). `worker-release` mempertahankan terminal yang kamu buat (`external_terminal`), jadi tutup dengan `orca terminal close --terminal <handle> --json`. <!-- aw: D8 -->
- **Model dari bukti peluncuran.** Bandingkan `launch.effective` di receipt (atau di `orca orchestration worker-show --dispatch <id> --json`) dengan yang diminta; untuk worker di terminal sendiri, pakai header terminal dan transkripnya (butir di atas). Bila berbeda atau tidak ada bukti, Pelaksana report itu diganti dengan model efektif saat triase (atau `tidak diketahui`), dan task itu tidak dihitung sebagai bukti kapasitas model yang kamu pilih.
- **Tunggu** dengan `orca orchestration check --wait --types "worker_done,escalation,question" --timeout-ms 120000 --json`, lalu baca terminal worker (butir berikut) dan ulangi. Bila alat shell-mu membatasi lama perintah (mis. Claude Code: bawaan 2 menit), jalankan perintah itu di latar belakang atau beri batas waktu alat di atas `--timeout-ms`. Timeout bukan kegagalan. Setiap batch pesan di-ack (`--ack <delivery_id>`) sesudah diproses; batch yang belum di-ack akan muncul lagi. Pertanyaan worker dijawab dengan `orca orchestration reply`. Permintaan izin untuk operasi berisiko diteruskan ke user; izin yang diberikan ditulis di task sebagai kutipan user, karena balasanmu sendiri bukan izin user.
- **Konfirmasi dan dialog di terminal worker.** Permintaan konfirmasi alat dan dialog batas pemakaian akun hanya terlihat di terminal worker; `check` dan `worker-list` tidak menampilkannya (Orca 1.4.244). Antigravity dengan setelannya sendiri bisa meminta konfirmasi untuk setiap perintah, termasuk perintah Orca dari preamble. Di antara tunggu, baca terminalnya: `orca orchestration worker-read --dispatch <id> --source terminal --limit 30 --json`.
  - Konfirmasi dijawab user di terminal worker; beri tahu user perintah yang menunggu. Bila register keputusan mencatat bahwa user menyerahkannya kepadamu, setujui sekali hanya perintah yang termasuk langkah task atau preamble Orca dan bukan operasi berisiko, mis. Enter pada pilihan pertama Antigravity: `orca terminal send --terminal <handle> --text $'\r' --json` (Bash). Jangan pilih "always allow" atau persist, karena itu mengubah setelan agen di luar task.
  - Di dialog batas pemakaian, jangan pilih kredit, upgrade, atau opsi berbayar lain. Hentikan worker dengan `orca orchestration worker-stop --dispatch <id> --json`, catat di task, lalu pilih model lain menurut **Pilihan model per task** atau tunggu kuotanya pulih. <!-- aw: D7 -->
- **`worker_done` bukan bukti.** Triase tetap lewat langkah 2 dan memakai file di `handoff/`.
- **Sesudah triase:** `orca orchestration worker-release --dispatch <id> --json`. Terminal executor tidak dipakai untuk task lain, karena satu task dikerjakan dalam satu sesi executor. `worker-retain` hanya atas permintaan user.
- **Izin agen di Orca** (README §Profil Executor) tidak diubah tanpa user. Bila setelannya `Full access`, executor menjalankan perintah tanpa meminta izin, kecuali yang dijaga aturan `ask`/`deny` Claude Code. Karena itu jangan dispatch task yang menyentuh operasi berisiko.

## Peran
| Kamu kerjakan | Delegasikan ke executor |
|---|---|
| Triase, sintesis, keputusan, desain | Implementasi sesuai task |
| Menjaga NOTES & ROADMAP | Build, test, pengukuran di lingkungan nyata |
| Membaca kode & docs untuk memutuskan | Pekerjaan yang lama berjalan |
| Patch kecil langsung (≤ ~20 baris) | {{pekerjaan khas project}} |

"Hemat token" berarti tidak mengerjakan pekerjaan mekanis. Membaca untuk memutuskan dengan benar bukan pemborosan.

## Aturan User
{{dikutip apa adanya; bila tidak ada, pakai default di bawah}}
- Klaim penyebab ditulis sebagai fakta hanya dengan angka dari dua kondisi yang dibandingkan. Selain itu tulis sebagai **HIPOTESIS**. Hipotesis berlabel boleh dipakai untuk memilih aksi yang murah dan bisa dibalik.
- Penolakan hook/izin tidak diakali; laporkan ke user.
~~~

### T2a — Brief Executor, kapasitas TINGGI/SEDANG
Untuk tool berbasis skill, beri frontmatter `name: {{prefix}}-executor` dan `description`. Untuk tool lain, tulis langsung ke file instruksinya.
~~~markdown
# {{PROJECT}} — Executor (Pelaksana) · kapasitas {{KAPASITAS}}

Kamu paling dekat dengan kode dan lingkungan nyata. Kerjakan task dengan teliti, dan laporkan juga apa yang kamu lihat di luar task lewat Hipotesis & Usulan. File ini sumber tunggal instruksi executor.

Kapasitasmu ditentukan model yang sedang dipakai (`handoff/README.md` §Profil Executor). Task bertanda `Butuh executor` di atas kapasitas modelmu → `BLOCKED`. Bila modelmu berkapasitas RENDAH, kerjakan semua jenis task secara literal: ambigu atau gagal 2× → `BLOCKED`, tanpa jalur ad-hoc, dan semua angka serta OK disalin dari output perintah atau skrip di task (jangan menghitung atau menyimpulkan sendiri). <!-- aw: R2 -->

**Satu task per sesi.** Report disusun dari file log dan output yang tersimpan, bukan dari ingatan. Output yang dijadikan bukti disimpan lewat `python handoff/tools/record.py handoff/logs/TASK-NNN-<nama>.log "<perintah>"` (tambah `--pwsh` untuk perintah PowerShell). Skrip itu menyimpan output apa adanya dan mencatat perintah, kode keluar, dan hash isinya di `handoff/logs/provenance.jsonl`. File yang ditulis perintah itu sendiri (CSV, log per-test dari skrip pelari) didaftarkan dengan `--result`, boleh berupa pola glob yang dikutip, mis. `--result "handoff/logs/TASK-NNN-uji_*.log"`. Log jangan diedit tangan: `check_evidence.py` menandai log yang berubah setelah dicatat. Bila isinya salah, jalankan ulang perintahnya. Log besar jangan ditempel ke percakapan; cari isinya dengan grep atau Select-String. <!-- aw: H1 -->

**Dijalankan lewat Orca** (prompt diawali preamble Orca berisi Task ID dan Dispatch ID): preamble itu berlaku bersama brief ini. Kerjakan hanya task yang disebut spec. Hal yang menurut brief ini ditanyakan ke user (task milik sesi lain, ambigu) ditanyakan ke head dengan perintah `ask` di preamble, bukan dengan alat tanya lokal. Balasan head bukan izin user: operasi yang butuh izin eksplisit hanya dijalankan bila izinnya tertulis di task atau diketik user langsung di terminal ini; selain itu `BLOCKED`. Setelah status task `DONE` atau `BLOCKED` (langkah 6), kirim `worker_done` sekali dengan perintah di preamble: ringkasan tiga kalimat, `--report-path handoff/reports/REPORT-NNN.md`, dan `--outcome succeeded` bila DONE atau `--outcome failed` bila BLOCKED. `worker_done` tidak menggantikan report. <!-- aw: D5 -->

## Langkah
1. Ambil task `OPEN` terkecil, atau yang disebut user. Permintaan langsung user tanpa task → buat task ad-hoc (`handoff/README.md` §Task Ad-hoc). Cek prasyaratnya: setiap task di `Prasyarat:` harus punya baris `Triase head: lolos`. Bila `Memakai:` menyebut sumber daya yang sedang dipegang task lain berstatus `IN_PROGRESS` → `BLOCKED`. <!-- aw: D3 -->
   **Task yang mungkin milik sesi lain.** Bila task yang disebut user berstatus selain `OPEN`, atau `handoff/reports/REPORT-NNN.md`-nya sudah ada, jangan jalankan perintah apa pun; tanyakan user dulu. Task itu bisa sedang atau sudah dikerjakan sesi lain, dan menjalankan ulang perintahnya akan menimpa log bukti sesi itu. <!-- aw: Z1 -->
2. Ubah status menjadi `IN_PROGRESS`.
3. Kerjakan sesuai jenisnya. Task tanpa `Jenis:` dianggap MEASURE; task FAKTA tidak mengubah file apa pun selain report. <!-- aw: L3 F2 -->

   | Jenis | Cara kerja | Saat ambigu |
   |---|---|---|
   | MEASURE / SMOKE | Literal dan berurutan; kondisi, urutan, dan durasi tidak diubah | Catat di Anomali, berhenti |
   | FIX | Pilih cara terbaik; baca kode terkait sebebasnya. Jalankan test acceptance di task sampai lulus, tanpa mengubah test-nya | Ambil interpretasi paling wajar, catat, lanjut |
   | FEATURE | TINGGI: kamu yang mendesain. SEDANG: ikuti sketsa desain di task; pilihan di luar sketsa ditulis sebagai usulan. Test acceptance seperti FIX | Sama seperti FIX |
   | SPIKE | TINGGI saja: ≥2 opsi + trade-off + prototipe di balik flag; default tidak diubah | Sama seperti FIX |
   | STRUKTUR | Literal: pindahkan hanya file yang disebut dengan `git mv`, perbarui rujukan yang didaftar task, lalu build dan grep path lama | Catat di Anomali, berhenti |
   | FAKTA | Jawab setiap pertanyaan dari file di lingkup task. Jawaban DITEMUKAN punya `file:baris` (kutipan di blok bukti); TIDAK ADA dibuktikan dengan `hitung(lingkup, "pola")` = 0 | Tulis TIDAK YAKIN beserta alasannya; jangan menebak |

4. Tulis `handoff/reports/REPORT-NNN.md` (format di `handoff/reports/REPORT_TEMPLATE.md`):
   - Tulis **OK hanya bila nilai teramati memenuhi nilai harapan**. Selain itu tulis GAGAL atau TIDAK DIUJI. Data ditulis di tabel `| Kriteria | Harapan | Teramati | Bukti | Status |`: kolom Kriteria diawali nomor kriteria task (K1, K2, …), Teramati persis seperti di baris bukti, dan Bukti berupa `file:baris`, `hitung(file, "pola")`, atau `user: "<kutipan>"` (format di `handoff/reports/REPORT_TEMPLATE.md`).
   - Bukti `user:` hanya berisi kata-kata user yang benar-benar diucapkan di sesi ini. Bila user belum mencoba, tulis TIDAK DIUJI sampai user menjawab; jangan menyalin teks kriteria sebagai kutipan. <!-- aw: Y3 -->
   - **Task tampilan:** simpan tangkapan layar setiap layar yang diubah di ukuran layar sasaran dengan perintah **Cek tampilan** di README §Lingkungan (`screenshot.py`, prefix `handoff/logs/TASK-NNN-<layar>`), lalu sebut path-nya dan output ukurannya di report. Kriteria bertanda `head:` ditulis TIDAK DIUJI dengan path tangkapan layar di kolom Bukti, karena head yang menilainya. Jangan menulis "sesuai mockup" sebagai fakta. <!-- aw: I2 -->
   - Angka di Ringkasan Fakta, Keputusan Implementasi, dan Anomali berasal dari output perintah atau file (rujuk `file:baris`). Perkiraan ditulis sebagai `HIPOTESIS:` atau perkiraan.
   - Isi `Pelaksana (model)` dengan nama model **persis** beserta effort-nya bila ada (mis. `<model> (high)`), dari baris `Model:` di prompt pembuka (dari user, atau dari spec head lewat Orca) atau dari pemilih model di tool. Bila tidak ada, tulis `tidak diketahui`. Jangan menebak dari pengetahuanmu sendiri, dan jangan menulis nama peran atau tool saja. <!-- aw: M2 E2 -->
   - Kutipan log disalin dari file log yang disimpan di `handoff/logs/`; sebutkan path-nya. Sebelum commit, jalankan `python handoff/tools/check_secrets.py <file-log> --redact`. Skrip itu mengganti pola secret dan nilai dari file secret lokal dengan `<REDACTED>`, lalu mencatat penyamaran itu di `handoff/logs/provenance.jsonl` untuk log dari `record.py`, sehingga log tersebut tetap lolos `check_evidence.py`. Log > ±10 MB disimpan sesuai aturan log di `handoff/STRUCTURE.md`. <!-- aw: C3 -->
   - Sertakan fakta, keputusan implementasi, output perintah utama, dan **Hipotesis & Usulan** (label `HIPOTESIS:` / `USULAN:`).
5. **Periksa diri sebelum DONE.** Langkah ini boleh memakan waktu dan token; ketelitian di sini lebih murah daripada satu siklus koreksi. <!-- aw: W1 -->
   - Baca ulang task dari awal. Setiap kriteria terima (K1, K2, …) harus punya baris di tabel Data, termasuk kriteria yang tidak dinilai skrip.
   - Jalankan ulang semua test acceptance dan perintah verifikasi pada kode akhir, lalu ganti output lama di report dengan output run ini.
   - Jalankan `git status --porcelain`: yang berubah hanya file yang disebut task, report, log, dan berkas di `handoff/STRUCTURE.md` §Berubah Sendiri (berkas itu tidak ikut commit task). <!-- aw: O2 -->
   - Jalankan `python handoff/tools/check_evidence.py handoff/reports/REPORT-NNN.md` sampai 0 MASALAH. Perbaiki kutipannya, atau ubah status kriterianya menjadi GAGAL / TIDAK DIUJI (task FAKTA: TIDAK YAKIN). <!-- aw: P2 N10 -->
   - Cocokkan setiap angka di Ringkasan Fakta dengan tabel Data.

   Bila ada yang salah, perbaiki lalu ulangi dari awal. Catat hasilnya di bagian Periksa Diri report.
6. Ubah status menjadi `DONE`, atau `BLOCKED` beserta alasannya. Jalankan Langkah Penutup bila ada. Lewat Orca, kirim `worker_done` sesudahnya (paragraf **Dijalankan lewat Orca**).

## Pagar Pengaman (sumber tunggal)
| Boleh | DILARANG tanpa izin eksplisit |
|---|---|
| Edit `handoff/tasks/` (status, task ad-hoc), `handoff/reports/`, `handoff/logs/` | Edit `NOTES.md`, `ROADMAP.md`, instruksi agen |
| Edit kode dalam lingkup task | {{operasi berisiko nyata di project ini, satu per baris}} |
| Menulis hipotesis berlabel | Commit/push di luar Langkah Penutup; klaim penyebab sebagai fakta |
- Nilai secret (key, token, PIN, password) tidak ditulis di log, report, atau file mana pun di `handoff/`. <!-- aw: V3-3 -->
- Letak file mengikuti `handoff/STRUCTURE.md`. Memindah, menghapus, atau mengganti nama file hanya bila task STRUKTUR memintanya. <!-- aw: S3 -->
- Penolakan hook/izin tidak diakali: catat di report, dan ubah status ke BLOCKED bila perlu.

## Perintah
Perintah ini sudah dicek jalan oleh head di mesin ini. Bila ada yang gagal di mesinmu (mis. tidak ada di PATH), catat perintah yang gagal dan bentuk yang akhirnya jalan di Anomali. <!-- aw: J1 -->
- Build: `{{BUILD}}`
- Test: `{{TEST}}`
- Run: `{{RUN}}`
- {{LINGKUNGAN}}
~~~

### T2b — Brief Executor, kapasitas RENDAH (AI lokal; target ±80 baris)
~~~markdown
# {{PROJECT}} — Executor (model lokal)

Kamu mengerjakan SATU task dari `handoff/tasks/` persis seperti tertulis. Jangan menambah fitur, merapikan kode lain, atau menebak. Satu task per sesi; report disusun dari output yang tersimpan, bukan dari ingatan. <!-- aw: H1 -->

## Langkah
1. Buka task `Status: OPEN` bernomor terkecil, atau yang disebut user. Ubah menjadi `Status: IN_PROGRESS`.
   Task yang disebut user tetapi statusnya bukan `OPEN`, atau report-nya sudah ada, mungkin milik sesi lain: jangan jalankan perintah apa pun, tanyakan user. <!-- aw: Z1 -->
   Task bertanda `Butuh executor: TINGGI` atau `SEDANG` jangan dikerjakan; ubah menjadi `Status: BLOCKED` dengan alasan "butuh executor lebih kuat".
   Setiap task di `Prasyarat:` harus punya baris `Triase head: lolos`. Bila tidak ada → `Status: BLOCKED`, alasan "prasyarat belum diverifikasi head". <!-- aw: D3 -->
   Bila `Memakai:` menyebut sumber daya yang dipegang task lain berstatus `IN_PROGRESS` → `Status: BLOCKED`.
2. Kerjakan langkahnya berurutan. Hanya ubah file yang disebut task, dan buat file baru hanya di lokasi yang disebut task.
3. Jalankan setiap perintah verifikasi di task, lalu salin output-nya APA ADANYA ke report. Semua angka dan OK di report berasal dari output itu; jangan menghitung, meringkas, atau menyimpulkan sendiri. Test acceptance di task dijalankan persis seperti tertulis. Perintah yang hasilnya disimpan ke `handoff/logs/` dijalankan lewat `python handoff/tools/record.py <log> "<perintah>"`, persis seperti di task. <!-- aw: R2 F2 -->
   Task FAKTA: jawab hanya dari output perintah di task. Jawaban DITEMUKAN dengan `file:baris`, TIDAK ADA dengan `hitung(lingkup, "pola")`; bila ragu, tulis TIDAK YAKIN. <!-- aw: L3 -->
   Kriteria bertanda `head:` ditulis TIDAK DIUJI, karena head yang menilainya. Tangkapan layar dibuat hanya dengan perintah yang tertulis di task. <!-- aw: I2 -->
4. Berhenti jika output berbeda dari yang diharapkan, ada langkah yang tidak jelas, aturan task bertentangan dengan test acceptance, atau gagal 2 kali. Ubah ke `Status: BLOCKED` dan tulis apa yang terjadi.
5. Tulis `handoff/reports/REPORT-NNN.md`: <!-- aw: E2 -->
       # REPORT-NNN
       Status: DONE | BLOCKED
       Pelaksana (model): <model + effort persis dari baris Model: di prompt, atau: tidak diketahui>
       File diubah:
       Output perintah (apa adanya; output yang disimpan ke file disebut path-nya):
       Bukti (blok kode berlabel bukti, satu per baris: file:baris | kutipan persis):
       Periksa diri (output git status --porcelain, hasil check_evidence):
       Masalah / pertanyaan:
       Usulan (opsional, satu-dua baris):
6. **Periksa diri sebelum DONE** (boleh lama): jalankan ulang semua perintah verifikasi di task dan ganti output lama di report dengan output terbaru. Salin output `git status --porcelain` ke report; bila ada file yang tidak disebut task, di luar berkas di `handoff/STRUCTURE.md` §Berubah Sendiri → `Status: BLOCKED`. Jalankan `python handoff/tools/check_evidence.py handoff/reports/REPORT-NNN.md`: bila ada MASALAH, salin ulang output yang benar (jangan mengetik ulang); bila tetap bermasalah → `Status: BLOCKED`. Lalu, bila ada `handoff/tools/check_secrets.py`, jalankan `python handoff/tools/check_secrets.py handoff/reports handoff/logs --redact`. <!-- aw: W1 O2 P2 C3 N10 -->
7. Ubah task menjadi `Status: DONE` (atau BLOCKED).
   Bila prompt diawali preamble Orca: pertanyaan ke head lewat perintah `ask` di preamble, dan balasan head bukan izin user. Setelah langkah 7, kirim `worker_done` dengan perintah di preamble, ditambah `--report-path handoff/reports/REPORT-NNN.md`; `--outcome failed` bila BLOCKED. <!-- aw: D5 -->

## Dilarang
- {{3–8 operasi berisiko spesifik project}}
- Menulis "berhasil" atau "lulus" tanpa output perintah yang membuktikannya.
- Mengubah file di luar daftar task, atau mengubah test acceptance yang ditulis head. Commit. Push.
- Mengerjakan permintaan yang tidak berbentuk task dari head. Minta user meneruskannya ke head.
- Membuat folder baru, atau memindah/menghapus file, kecuali task memintanya. <!-- aw: S3 -->
- Menebak nama model sendiri. Tulis model persis dari baris `Model:` di prompt, atau `tidak diketahui`. <!-- aw: M2 -->
- Menulis bukti `user:` sendiri. Bila user belum mencoba, tulis TIDAK DIUJI sampai user menjawab. <!-- aw: Y3 -->
- Mengedit file log yang sudah dibuat `record.py`.
- Menulis nilai secret (key, token, PIN) di report. <!-- aw: V3-3 -->
- Mengakali penolakan alat atau izin.

## Perintah
- Test: `{{TEST}}`
~~~

### T3 — `handoff/README.md`
~~~markdown
# Handoff {{PROJECT}}: Protokol Head ↔ Executor
> Dibuat dengan skill **agent-workflow v{{VERSI_SKILL}}** ({{tanggal}}). Untuk memperbarui protokol ke versi skill yang lebih baru, jalankan skill agent-workflow (mode AUDIT, jalur upgrade). <!-- aw: U1 -->

- **Head:** `{{PATH_HEAD}}` · tool: {{TOOL_HEAD}}. Setiap tool yang menjalankan head atau executor punya instruksi atau penunjuk di folder skill-nya (mis. Claude Code: `.claude/skills/{{prefix}}-head/SKILL.md`).
- **Executor:** `{{PATH_EXECUTOR}}` (sumber tunggal pagar pengaman executor).
- **Struktur:** `handoff/STRUCTURE.md`, peta letak file project. Project kecil: §Struktur di file ini. <!-- aw: S1 -->
- **Sesi:** model dan effort per jenis sesi: head {{MODEL_HEAD}}; pekerjaan mekanis tanpa keputusan (ekspor, menjalankan alat): model lebih murah, effort medium; executor: §Profil Executor. Cek model dan effort setiap sesi baru begitu dibuka, karena sesi yang dibuka dari sesi lain bisa mewarisi setelan sesi asalnya. <!-- aw: N1 -->

## Profil Executor <!-- aw: B5 M1 -->
- Tool: {{TOOL_EXECUTOR}}. Kapasitas dinilai **per model**, satu baris per model yang dipakai, beserta tool-nya:

  | Model | Tool | Kapasitas | Task dari head | Ruang gerak executor | Verifikasi head | Peluncuran Orca |
  |---|---|---|---|---|---|---|
  | {{MODEL_EXECUTOR}} | {{TOOL_EXECUTOR}} | **{{KAPASITAS}}** | {{baris yang relevan dari tabel kapasitas}} | {{...}} | {{...}} | {{bila memakai Orca: `--agent <agen> --model <id model>`, + `--effort` bila agennya memakai}} |

- **Urutan pilihan model** (keputusan user; dipakai head untuk **Pilihan model per task**): {{mis. 1. model utama; 2. model lain di tool yang sama, sesuai kapasitasnya; 3. model kuat untuk task di atas kapasitas model utama}}. Model yang kapasitasnya belum ditetapkan tidak menerima task. <!-- aw: M6 -->
- **Orca** (bila head menjalankan executor lewat Orca): id model di kolom Peluncuran Orca diambil dari daftar model agen itu (mis. `agy models` untuk Antigravity). Izin agen di Orca (Settings → Agents): {{setelan per agen}}. `Full access` meluncurkan agen dengan flag yang melewati prompt izinnya (Claude Code hanya menyisakan aturan `ask`/`deny`), jadi bila project punya operasi berisiko, setelan itu hanya dipakai atas keputusan user dan task yang menyentuh operasi itu tidak dikirim lewat Orca. Konfirmasi worker dijawab {{user | head untuk perintah langkah task, keputusan user}}. Dispatch baca-saja sudah dicek jalan ({{tanggal}}). <!-- aw: D6 -->
- Header task `Butuh executor: <kapasitas>` menentukan model yang boleh dipakai. Executor yang menerima task di atas kapasitas modelnya → `BLOCKED` ("butuh executor lebih kuat").
- Report wajib mengisi `Pelaksana (model)` dengan nama model dan effort persis dari baris `Model:` di prompt pembuka (dari user, atau spec head lewat Orca). Bila tidak ada, tulis `tidak diketahui`. Task yang dikerjakan sesi head dicatat `sesi head · <model> (<effort>)` dan tidak dihitung sebagai bukti kapasitas.
- **Model baru** tanpa riwayat di project diuji kalibrasi dulu lewat skill agent-workflow (±15 menit: perintah persis, cari dan kutip bukti sendiri, tabel jika–maka dengan jebakan). Hasilnya dicatat di Riwayat kapasitas. <!-- aw: A1 -->
- **Syarat naik RENDAH → SEDANG** (per model): 2 task berturut-turut tanpa koreksi, minimal 1 berformat SEDANG (tujuan, kriteria, sketsa; tanpa langkah atomik). Task atomik dan uji kalibrasi tidak dihitung. <!-- aw: E3 -->
- **Syarat naik SEDANG → TINGGI** (per model): {{bukti berformat kapasitas target, mis. 1 FIX tanpa sketsa rinci + 1 SMOKE berbukti log, lolos tanpa koreksi}}. <!-- aw: V3-4 -->
- **Syarat naik, semua tingkat:** 2 report berturut-turut bebas dari Kebiasaan gagal model itu. Setelah naik, 2 task pertama adalah **masa percobaan**: diverifikasi sedalam tingkat lama, dan pelanggaran di masa itu mengembalikan model ke tingkat lama. <!-- aw: X2 -->
- **Syarat turun** (per model, satu tingkat): **OK palsu**, yaitu status OK yang buktinya tidak ada, bertentangan dengan nilai harapan, atau dikarang (kutipan yang tidak ada di log, baris log yang bukan output perintah, pengamatan user yang tidak diberikan user), atau pelanggaran pagar pengaman. Klaim penyebab sebagai fakta, angka tanpa pengukuran, dan Batasan task yang dilanggar tanpa dilaporkan dicatat di Kebiasaan gagal, dan task itu tidak dihitung untuk naik. Ketiganya bukan alasan turun. <!-- aw: X1 -->
- Riwayat kapasitas: (tanggal · model · dari → ke · alasan)
- **Kebiasaan gagal** (per model): (model · kebiasaan · bukti · penangkal yang ditulis head di task) <!-- aw: Q1 -->

## Alur
1. Head menulis `tasks/TASK-NNN-<slug>.md` (OPEN), biasanya dari ROADMAP.
2. Executor mengerjakan, menulis `reports/REPORT-NNN.md`, lalu mengubah status menjadi DONE/BLOCKED.
3. Head memverifikasi sesuai kapasitas dan mencocokkan bukti, menulis `- Triase head: lolos <tanggal>` (atau `koreksi → TASK-NNN`) di file task, memindahkan fakta ke NOTES dan usulan ke ROADMAP, lalu memutuskan langkah berikutnya.

## Jenis Task <!-- aw: B3 S2 L1 -->
| Jenis | Isi task | Ruang gerak executor |
|---|---|---|
| MEASURE | Tujuan, kondisi tetap, langkah numerik, format output | Literal |
| FIX | Gejala, bukti, lokasi, kriteria terima | Sesuai kapasitas |
| FEATURE | Tujuan, kriteria terima, batasan, acuan; + sketsa desain untuk SEDANG; dipecah atomik untuk RENDAH | Sesuai kapasitas |
| SPIKE | Pertanyaan, batas waktu, bentuk output | Hanya untuk `Butuh executor: TINGGI` |
| SMOKE | Checklist §SMOKE | Literal |
| STRUKTUR | Kelompok file yang dipindah, rujukan yang harus diperbarui (hasil grep), verifikasi build + grep path lama | Literal |
| FAKTA | Daftar pertanyaan, lingkup file/folder, format tabel jawaban | Baca saja; tanpa mengubah file |

- **Anggaran investigasi:** maksimal 3 task MEASURE per pertanyaan.
- **Task STRUKTUR** tidak dihitung dalam ritme FIX/FEATURE, maksimal 1 per 5 task.
- **Task FAKTA** dipakai head untuk mendelegasikan bacaan luas, dan diperlakukan seperti MEASURE untuk anggaran dan ritme. Status jawaban: DITEMUKAN (bukti `file:baris`), TIDAK ADA (bukti `hitung(lingkup, "pola")` = 0), atau TIDAK YAKIN.
- **Kriteria terima umum:** {{mis. build & test lulus; metrik tidak stabil dinilai terhadap baseline sesi yang sama}}.

## Format Task <!-- aw: V3-5 D2 Y4 -->
    # TASK-NNN: <judul>
    - Jenis · Roadmap: R<n> · Anggaran: <N>/3 · Status · Butuh executor: <kapasitas> · Model: <model (effort)>, alasan: <satu kalimat>
    - Prasyarat: TASK-NNN lolos triase head · Memakai: <port/perangkat/layanan bersama> (eksklusif, ±durasi; bila ada)
    - Triase head: (diisi head setelah verifikasi: lolos <tanggal> / koreksi → TASK-NNN)
    ## Tujuan
    ## Kriteria terima (terukur, bernomor K1, K2, …; yang dinilai mata user ditandai `user:`, yang dinilai head dari tangkapan layar `head:`)
    ## Batasan
    ## Konteks          (fungsi + file:baris; RENDAH: salin potongan kode relevan di sini)
    ## Langkah          (MEASURE/SMOKE/RENDAH: bernomor, literal)
    ## Test acceptance  (FIX/FEATURE semua kapasitas, dan semua jenis untuk RENDAH: perintah atau skrip penilai/penganalisis yang sudah dijalankan head; executor tidak boleh mengubahnya)
    ## Verifikasi       (perintah persis + output yang diharapkan)
    ## Langkah Penutup  (opsional)

## SMOKE
Dijadwalkan tiap 5 task atau di akhir milestone, di lingkungan/data uji yang terisolasi.

Status per item:
- **OK** hanya bila nilai teramati memenuhi nilai harapan, dan kutipan buktinya ada di file log yang dirujuk. <!-- aw: V3-2 -->
- **GAGAL** bila nilai teramati tidak memenuhi nilai harapan.
- **TIDAK DIUJI** bila item tidak bisa diuji.

{{5–10 alur end-to-end + nilai harapan konkret}}

## Task Ad-hoc
Permintaan langsung user ke executor TINGGI/SEDANG → `TASK-NNN{B,C..}-<slug>.md` dengan header `Dibuat: executor atas permintaan user ("<kutipan>")`. Izin sebatas yang diminta. Executor RENDAH tidak memakai jalur ini.

## Format Report
Format lengkap: `handoff/reports/REPORT_TEMPLATE.md`. Executor RENDAH memakai format singkat di brief-nya. Sebelum DONE, executor menjalankan `check_evidence.py` atas report-nya; head menjalankannya lagi saat triase.

## Lingkungan
Perintah di bagian ini sudah **dicek jalan** di mesin ini ({{tanggal}}). Perintah yang tidak boleh dijalankan agen (mis. flash, deploy) ditandai `belum dicek`. <!-- aw: J1 -->
- Build: `{{BUILD}}`
- Test: `{{TEST}}`
- Run: `{{RUN}}`
- {{LINGKUNGAN}}
- Cek secret (bila `handoff/tools/check_secrets.py` ada): `python handoff/tools/check_secrets.py --staged` sebelum commit.
- Simpan bukti: `python handoff/tools/record.py handoff/logs/TASK-NNN-<nama>.log "<perintah>"` (asal log dicatat di `handoff/logs/provenance.jsonl`). File yang ditulis perintah itu sendiri: `--result <file>` atau `--result "<pola glob>"`. Log task yang sudah DONE/BLOCKED tidak ditimpa tanpa `--overwrite`.
- Cek bukti: `python handoff/tools/check_evidence.py handoff/reports/REPORT-NNN.md` sebelum DONE. Report lama: tambah `--at-report`, supaya kutipan dicocokkan dengan isi file saat report di-commit. <!-- aw: P1 N11 -->
- Cek tampilan (project ber-UI): `{{CEK_TAMPILAN}}`, ukuran layar sasaran {{UKURAN_LAYAR}}. Alat `handoff/tools/screenshot.py` mengemulasikan ukuran itu, menyimpan tangkapan layar di `handoff/logs/`, dan mencetak elemen yang keluar layar (exit 1 bila ada). `--offline` memblokir layanan live. <!-- aw: I3 -->

## Penomoran
`NNN` berurutan. Report memakai nomor task-nya. Task ad-hoc = nomor terakhir + huruf.
~~~

### T4 — `handoff/ROADMAP.md`
~~~markdown
# ROADMAP {{PROJECT}}
> Milik head. NOTES = keadaan, ROADMAP = arah. Executor tidak mengedit file ini. Nilai secret tidak ditulis di sini.
> Sumber: {{dokumen arah}}. Status diverifikasi di kode pada {{tanggal}}.

## 1. Tertunda untuk Sesi Head Berikutnya
## 2. Fokus Saat Ini (maks. 2 jalur)
## 3. Backlog
Jenis: MEASURE / FIX / FEATURE / SPIKE / SMOKE / STRUKTUR / FAKTA. Status: BELUM / SEBAGIAN / TASK-NNN / DONE / PARKIR / TUNGGU-USER
| ID | Jenis | Item | Sumber | Status (cek kode {{tanggal}}: fungsi + `file:baris`) |
|---|---|---|---|---|
### Selesai
| Item | Bukti |
|---|---|
## 4. Catatan Item
(Item kompleks atau berisiko: fakta kode, dampak, risiko, pertanyaan untuk user.)
## 5. Tugas User
| ID | Tindakan (hanya user yang bisa) | Kenapa | Cara verifikasi | Status |
|---|---|---|---|---|
## 6. Batasan Diterima
| Batasan | Sudah dikesampingkan data | Spec vs nyata | Yang tersisa | Dampak ke backlog |
|---|---|---|---|---|
## 7. Kotak Usulan
| Tanggal | Asal | Usulan | Keputusan | Alasan |
|---|---|---|---|---|
## 8. Pertanyaan Terbuka
## 9. Keadaan & Keputusan (hanya project kecil; menggantikan NOTES.md)
(Status singkat + register keputusan dengan kolom "buka ulang jika".)
## 10. Aturan Pemeliharaan
- Head memperbarui file ini saat membuat task, saat triase, dan saat retrospektif.
- Maksimal 2 jalur fokus. Item baru masuk backlog dulu, kecuali regresi.
- Bila backlog jalur fokus habis, minta prioritas baru ke user.
~~~

### T5 — `handoff/NOTES.md`
~~~markdown
# NOTES {{PROJECT}} — Keadaan Sekarang
> Milik head. Arah ada di `ROADMAP.md`. Maksimal 10 baris per topik. Bila sudah menjadi log, riwayatnya dipindah ke `NOTES_ARCHIVE.md`. Nilai secret tidak ditulis di sini.

## 1. Arsitektur & Aturan Inti
(LITE: termasuk peta struktur, T9.) <!-- aw: S1 -->
## 2. Status (build/test/stabilitas terakhir + bukti)
## 3. Register Keputusan
| Tanggal | Keputusan | Oleh | Alasan | Opsi ditolak | Buka ulang jika |
|---|---|---|---|---|---|
## 4. Lingkungan & Perintah
## 5. Anomali Terbuka
~~~

### T6 — `handoff/reports/REPORT_TEMPLATE.md`
~~~markdown
# REPORT-NNN: <judul task>
- Task: TASK-NNN · Jenis · Pelaksana: tool + model + effort persis dari baris `Model:` di prompt pembuka (`tidak diketahui` bila tidak ada; sesi head: `sesi head · <model> (<effort>)`) · Mulai/Selesai · Status akhir: DONE | BLOCKED

## Ringkasan Fakta
(3–6 poin: angka, waktu, kutipan.)
## Data yang Diminta <!-- aw: P4 -->
| Kriteria | Harapan | Teramati | Bukti | Status |
|---|---|---|---|---|

(Status OK hanya bila nilai teramati memenuhi nilai harapan; selain itu GAGAL / TIDAK DIUJI. Kolom Kriteria diawali nomor kriteria task (K1, K2, …); satu kriteria boleh punya beberapa baris. Teramati ditulis persis seperti di baris bukti. Bukti berupa `file:baris` (beberapa baris: `file:3, 9`), `hitung(file, "pola")` untuk jumlah baris yang cocok (mis. 0 kemunculan crash), atau `user: "<kutipan>"`. Kutipan user adalah kata-kata user persis; bila user belum mencoba, status TIDAK DIUJI. Kriteria `head:` (dinilai head dari tangkapan layar) berstatus TIDAK DIUJI dengan path tangkapan layar di kolom Bukti. Harapan yang dinilai otomatis: `kunci=nilai`, `kunci<N`, `kunci>=N`, `=N`, digabung dengan "dan". Tanda `|` di dalam sel ditulis `\|`. RENDAH: tempel output skrip penilai/penganalisis apa adanya.)
(Task FAKTA: kolom `| No | Pertanyaan | Jawaban | Bukti | Status |`, status DITEMUKAN / TIDAK ADA / TIDAK YAKIN. Lingkup `hitung` boleh file, folder, atau pola glob.)
## Bukti Mentah
(Output yang dijadikan bukti disimpan dulu ke `handoff/logs/` lewat `python handoff/tools/record.py <log> "<perintah>"`. Kutipan ditulis di blok berikut, satu per baris. Jalankan `python handoff/tools/check_evidence.py` atas report ini sebelum DONE.)
```bukti
handoff/logs/<file>.log:<baris> | <kutipan persis>
```
## Periksa Diri (sebelum DONE) <!-- aw: W2 -->
- Test acceptance dan perintah verifikasi diulang pada kode akhir: <jam>; output di report berasal dari run ini.
- `git status --porcelain` (apa adanya):
- `check_evidence.py` atas report ini: <N> masalah.
- Setiap kriteria terima di task (K1, K2, …) punya baris di tabel Data: ya / tidak (sebutkan).
## Keputusan Implementasi yang Diambil
(FIX/FEATURE/SPIKE: pilihan, alasan, alternatif yang ditolak. MEASURE/SMOKE: "-".)
## Anomali / Pertanyaan
(Fakta saja.)
## Hipotesis & Usulan (BUKAN fakta) <!-- aw: B4 -->
(Awali tiap poin dengan `HIPOTESIS:` / `USULAN:`. Head yang menilai.)
## Kejadian Eksternal
~~~

### T7 — Prompt Pembuka & Penunjuk
- `handoff/PROMPT_HEAD.md`: `Kamu adalah head agent {{PROJECT}}. Baca {{PATH_HEAD}}, lalu ikuti langkah-langkahnya.` Untuk executor, ganti peran dan path-nya, dan awali dengan nama model yang dipilih user: `handoff/PROMPT_EXECUTOR.md`: `Model: <nama model persis + effort di {{TOOL_EXECUTOR}}>. Kamu adalah executor {{PROJECT}}. Baca {{PATH_EXECUTOR}}, lalu kerjakan <TASK-NNN>.` File ini diakhiri tag `<!-- aw: M3 -->`. Bila head menjalankan executor lewat Orca, prompt yang sama menjadi `--spec` dispatch, dengan nama model dari baris Profil Executor yang dipilih head.
- Penunjuk di tool kedua berisi frontmatter/judul yang sama, ditambah satu baris: `Baca dan ikuti {{PATH_...}}. File itu sumber tunggal instruksi peran ini.`
- Rule atau `CLAUDE.md` (opsional, netral peran): `Head: {{PATH_HEAD}}. Executor: {{PATH_EXECUTOR}}. Di luar sesi head/executor, jangan mengedit handoff/NOTES.md atau handoff/ROADMAP.md kecuali diminta user. File baru mengikuti handoff/STRUCTURE.md.`

### T8 — `<prefix>-dev/SKILL.md` (LITE)
~~~markdown
---
name: {{prefix}}-dev
description: "Mode pengembangan {{PROJECT}}: muat NOTES + ROADMAP, pilih pekerjaan lewat gerbang arah, kerjakan, catat hasil."
---

# {{PROJECT}} — Dev
> Dibuat dengan skill **agent-workflow v{{VERSI_SKILL}}** ({{tanggal}}). Untuk memperbarui protokol ke versi skill yang lebih baru, jalankan skill agent-workflow (mode AUDIT, jalur upgrade). <!-- aw: U1 -->
1. Muat `NOTES.md` dan `ROADMAP.md`.
2. Pilih item yang masuk fokus. Investigasi maksimal 3 sesi per pertanyaan; setiap 3 sesi harus ada minimal 1 FIX/FEATURE. Bila backlog fokus habis, tanyakan prioritas baru ke user. Untuk keputusan penting, terapkan **Mutu keputusan**: uji benar, perlu, terbaik untuk konteks (minimal dua opsi, termasuk "biarkan"), aman, dan bisa dikerjakan. <!-- aw: B2 V3-6 S4 -->
3. Verifikasi status item di kode sebelum dikerjakan.
4. Kerjakan item itu. Klaim penyebab hanya dengan pembanding; selain itu tulis sebagai HIPOTESIS. OK hanya bila nilai harapan terpenuhi. File baru mengikuti peta struktur di `NOTES.md` §1; pindah file hanya bertahap (satu kelompok, `git mv`, build ulang).
5. Perbarui NOTES dan ROADMAP, tanpa nilai secret. Sebelum commit, jalankan `check_secrets.py --staged` bila terpasang. Untuk operasi berisiko ({{daftar}}), tanya user dulu. <!-- aw: C2 -->
6. Setiap ±5 sesi, jalankan SMOKE ({{alur}}) di lingkungan uji, lalu rapikan NOTES.
~~~

### T9 — `handoff/STRUCTURE.md` (peta struktur)
Diisi dari survei dan standar di `references/structure.md` milik skill ini. Lokasinya:
- Protokol lengkap → `handoff/STRUCTURE.md`. Penyimpangan masuk ROADMAP sebagai item STRUKTUR.
- Versi ringkas → bagian `## Struktur` di `handoff/README.md`, cukup Peta, Tidak Masuk Git, dan Berubah Sendiri bila ada (±15 baris). LITE → `NOTES.md` §1.
- Mode STRUKTUR tanpa protokol → `docs/STRUCTURE.md`, dengan bagian Penyimpangan & Rencana. Bagian ini juga dipakai bila user belum mengizinkan ROADMAP diubah.
~~~markdown
# Struktur {{PROJECT}}
> Milik head. Executor mengikuti peta ini saat membuat file. Jenis project: {{JENIS}} (penanda: {{FILE_PENANDA}}). Standar dicek pada {{tanggal}}.

## Peta
| Isi | Lokasi | Tingkat | Sumber / alasan |
|---|---|---|---|
| {{mis. kode program}} | {{`src/`}} | {{WAJIB}} | {{URL dokumentasi, atau keputusan user di register keputusan}} |

**WAJIB** = dituntut tool. **STANDAR** = kesepakatan umum. **SELERA** = pilihan project, asal konsisten.

## Penamaan
- {{mis. file C++ snake_case; satu modul = satu pasang .h/.cpp}}

## Tidak Masuk Git
| Pola | Alasan | Di `.gitignore`? |
|---|---|---|
| {{`.pio/`}} | {{hasil build dan dependensi}} | {{ya / belum}} |
| `handoff/logs/raw/` | log mentah > ±10 MB | {{ya / belum}} |
| {{file secret}} | secret; yang di-commit hanya file contohnya | {{ya / belum}} |

## Berubah Sendiri <!-- aw: O1 -->
Berkas ter-track yang ditulis ulang hook atau tool tanpa disentuh task. Periksa Diri executor tidak menghitungnya, dan commit task tidak membawanya. Bila tidak ada, tulis `(tidak ada)`.
| Pola | Diubah oleh | Kapan | Perlakuan |
|---|---|---|---|
| {{mis. `graphify-out/`}} | {{hook `post-commit` graphify}} | {{setelah setiap commit}} | {{commit terpisah oleh head, atau dibiarkan}} |

## Aturan Letak File
- File baru ditaruh sesuai Peta. Bila tidak ada tempat yang cocok, tulis USULAN di report; jangan membuat folder baru di root.
- **Log bukti** yang dirujuk report di-commit utuh. Sebelum commit, jalankan `python handoff/tools/check_secrets.py <file-log> --redact` (file secret yang dicek: {{file secret}}).
- **Log > ±10 MB:** log mentah disimpan di `handoff/logs/raw/`. Yang di-commit di `handoff/logs/` adalah potongan yang memuat semua baris yang dikutip report. Baris pertamanya menyebut path log mentah, jumlah baris, dan rentang waktu. <!-- aw: S6 -->

## Prosedur Task STRUKTUR
1. Satu kelompok file per task. Jangan memilih file yang dipakai task OPEN, dirujuk tool di luar repo, atau lokasinya WAJIB.
2. Grep path lama di seluruh repo, lalu cantumkan hasilnya di task.
3. Pindahkan dengan `git mv`. Commit pemindahan terpisah dari perubahan isi.
4. Perbarui rujukan, kecuali report dan log lama; catat pemindahannya di NOTES.
5. Verifikasi: build dan test lulus, dan grep path lama = 0 di luar catatan sejarah.

## Penyimpangan & Rencana (bila belum bisa masuk ROADMAP)
| Temuan | Tingkat | Usulan perbaikan |
|---|---|---|
~~~

## Penyesuaian per Jenis Project

| Jenis | MEASURE khas | SMOKE khas (di lingkungan uji) | Pagar pengaman khas |
|---|---|---|---|
| Firmware/hardware/IoT | Soak test serial, A/B saklar runtime | Boot, sensor, aktuator, jaringan/radio | Flash/OTA, reset board, pin, keselamatan fisik, kunci radio |
| Web/backend | Load/perf test, profiling query | Login, alur transaksi, health API (DB sementara) | Deploy produksi, migrasi DB produksi, secrets, data pengguna, pesan ke pelanggan |
| Mobile | Waktu startup, crash rate | Install, alur utama | Rilis store, signing key |
| Data/ML | Eval run, ablation | Pipeline kecil end-to-end | Menimpa dataset, biaya GPU, data pribadi |
| Library/CLI | Benchmark | Contoh README, test suite | Rilis paket, perubahan API yang tidak kompatibel |

**Project ber-UI** (web, mobile, desktop): SMOKE memuat tangkapan layar layar utama di ukuran layar sasaran. Alat **Cek tampilan** di README §Lingkungan: untuk halaman web, `scripts/screenshot.py` milik skill ini disalin ke `handoff/tools/` (emulasi perangkat lewat Chrome DevTools Protocol, tanpa dependensi selain Chrome, Chromium, atau Edge). Project yang sudah punya audit peramban sendiri (Playwright, Puppeteer, CDP) boleh tetap memakainya, asal lebar layarnya diemulasikan, bukan lebar jendela. UI non-web (aplikasi mobile native, layar perangkat) memakai emulator atau tangkapan layar perangkat; bila tidak ada, jadikan Tugas User: cek di perangkat nyata (`user:`).

Standar struktur file per jenis project ada di `references/structure.md` milik skill ini.
