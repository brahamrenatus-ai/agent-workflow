# Executor lewat Orca

Dibaca dari `SKILL.md` saat BOOTSTRAP, AUDIT, atau upgrade, bila head menjalankan executor lewat Orca. Orca adalah aplikasi yang meluncurkan agen CLI (Claude Code, Antigravity, Codex, …) di terminal yang diawasinya. Dalam susunan ini head menjadi **koordinator**: ia memilih model per task, meluncurkan executor, menunggu `worker_done`, lalu mentriase report seperti biasa. File di `handoff/` tetap sumber kebenaran; Orca hanya jalur peluncuran dan kabar.

Ditulis dengan Orca 1.4.243 dan dicek ulang dengan 1.4.244. Panduan yang cocok dengan versi terpasang dicetak oleh `orca skills get orchestration`; bila isinya berbeda dengan file ini, panduan itulah yang benar. Di Linux, `orca` di luar terminal Orca biasanya pembaca layar GNOME, jadi pakai `orca-ide` (dijelaskan di panduan itu).

## Kapan dipakai
- **Sepadan** bila executor memakai lebih dari satu model atau tool, dan head yang memilih model per task. User tidak perlu membuka sesi executor dan mengetik prompt pembuka untuk setiap task. Waktu user mahal, sedangkan peluncuran oleh head bisa diperiksa dari receipt-nya.
- **Tidak perlu** bila hanya ada satu model executor dan user nyaman membuka sesinya sendiri. Bandingkan dengan opsi "biarkan" (§Kualitas Rekomendasi).

## Susunan
- **Head = koordinator.** Satu Run per sesi head. Run itu menjadi kotak masuk `worker_done`, pertanyaan, dan eskalasi dari executor.
- **Executor = pekerja.** Satu task per dispatch. Sesudah report ditulis dan status task diubah, executor mengirim `worker_done`, lalu diam. Worker bekerja di folder project yang sama dengan head, jadi hanya satu worker yang mengubah file boleh berjalan pada satu waktu; task FACT yang hanya membaca boleh berjalan bersamaan.
- **Sesi head bukan pekerja Orca**, karena head adalah sesi interaktif user. Sesi lain boleh membaca terminal head atau mengirim kabar lewat Orca atas izin user, tetapi tidak mengawasinya. Yang teramati dengan Orca 1.4.244:
  - `orca terminal send --enter` ke terminal Claude Code yang sedang menampilkan dialog (izin, trust, pengaturan) ditolak dengan `agent_prompt_blocked`. `orca terminal read` bisa tidak menampilkan dialog itu bila tampilannya tergulir. Minta user menjawab dialognya, lalu kirim ulang dengan `orca terminal send --retry-request <id>` memakai id dari galat itu.
  - `orca orchestration send --type escalation` hanya diterima dari worker yang memegang dispatch-nya; dari koordinator atau sesi lain ditolak `sender_not_assignee`. Kabar dari sesi lain memakai `--type status`.
  - Orca mengetik pemberitahuan pesan baru ("You have N orchestration message") ke terminal koordinator untuk pesan yang jenisnya tidak ada di filter waiter yang sedang aktif (`check --wait --types`). Selama ada waiter tanpa `--types`, tidak ada pemberitahuan sama sekali. Pemberitahuan ditahan selama sesi koordinator bekerja, lalu dikirim begitu sesinya menganggur, dan membangunkannya.

## Profil Executor sebagai tabel pilihan
Contoh baris (T3 §Profil Executor):

| Model | Tool | Kapasitas | Peluncuran Orca |
|---|---|---|---|
| Gemini 3.8 Flash (high) | Antigravity | MEDIUM | `--agent antigravity --model gemini-3.8-flash-high` |
| Claude Sonnet 5.5 (medium) | Claude Code | belum ditetapkan → kalibrasi | `--agent claude --model claude-sonnet-5-5 --effort medium` |

- **Id model.** Untuk Antigravity, ambil id dari `agy models`; effort sudah termasuk dalam id. Untuk Claude Code, pakai id model ditambah `--effort`. `--effort` butuh `--model`, dan keduanya tidak bisa digabung dengan `--terminal`. Akibatnya model terminal yang dipakai ulang tidak bisa diganti.
- **Nama di kolom Model** sama persis dengan baris `Model:` di spec, karena executor menyalin Pelaksana report dari baris itu.
- **Urutan pilihan model** adalah keputusan user, dicatat di Profil Executor dan register keputusan beserta syarat buka ulangnya. Contoh: model Claude di Antigravity tidak dipakai sebagai executor karena kuotanya terbatas, jadi task yang butuh Claude dijalankan lewat Claude Code. Buka ulang bila kuota itu berubah.
- **Tool baru di tabel** (mis. Claude Code sebagai executor) butuh instruksi executor atau penunjuknya di folder skill tool itu (penanda K2). Baris `Tool:` di README menyebut semua tool executor.

## Setelan izin agen
Orca menambahkan flag izin saat meluncurkan agen, menurut setelannya di **Settings → Agents**. Tabelnya ada di `references/enforcement.md` §Orca. Ringkasnya, `Full access` meluncurkan Claude Code dan Antigravity dengan `--dangerously-skip-permissions`. Antigravity lalu menyetujui semua permintaan izin, dan Claude Code hanya menyisakan aturan `ask`/`deny` project; selebihnya pagar pengaman executor tinggal teks. Untuk project yang punya operasi berisiko, pilih setelan lain bersama user sebelum dispatch pertama.

Untuk Antigravity, hanya `Full access` yang mengubah perilakunya. Dengan setelannya sendiri, Antigravity CLI bisa meminta konfirmasi untuk setiap perintah, dan konfirmasi itu hanya terlihat di terminal worker (T1 butir **Konfirmasi dan dialog di terminal worker**). Pilihan untuk user: setelan sendiri dengan konfirmasi dijawab user atau head, atau `Full access` dengan task berisiko tidak lewat Orca.

## Akun Claude worker
`worker-start --agent claude` memakai login Claude Code bawaan Orca (`~/.claude`, atau akun Claude yang aktif di `orca account list`), bukan akun sesi head. User yang memakai beberapa akun lewat `CLAUDE_CONFIG_DIR` (mis. fungsi shell yang mengisinya sebelum menjalankan `claude`) akan mendapati worker berjalan di akun lain, bisa juga akun yang kuotanya sudah habis. Cara meluncurkan worker dengan akun sesi head ada di T1 (butir **Worker Claude Code memakai akun sesi head**): `orca terminal create` dengan perintah yang mengisi `CLAUDE_CONFIG_DIR`, tunggu TUI siap, lalu `worker-start --terminal`. Dicek jalan 2026-10-29 (Windows, PowerShell): transkrip worker tercatat di folder akun sesi head, mode izinnya `auto`, dan `worker_done` cocok dengan hasil ulang. Akun terkelola Orca (`orca account add`) tidak menggantikan cara ini, karena hanya ada satu akun Claude aktif per runtime untuk semua peluncuran.

## Sebelum task pertama (dicek jalan)
1. `orca status --json`: runtime `ready`. `orca repo list --json` memuat root project. Bila belum, daftarkan dengan `orca repo add --path <root>`; folder tanpa git didaftarkan lewat `orca project setup-existing-folder`.
2. Setelan izin agen dicek bersama user, lalu dicatat di Profil Executor (penanda D6) dan register keputusan.
3. **Dispatch baca-saja**, satu untuk setiap agen yang akan dipakai, ditunggu dengan `handoff/tools/orca_wait.py` (salin dulu `scripts/orca_wait.py` milik skill ini). Spec-nya menjalankan `check_evidence.py` atas report terakhir dan `git status --porcelain`, tanpa mengubah file apa pun. Sesudah worker selesai:
   - isi `worker_done` cocok dengan hasil yang didapat head saat menjalankan ulang perintah yang sama;
   - `launch.effective` di receipt sama dengan yang diminta;
   - mode izin terlihat di terminal worker (Claude Code menampilkannya di baris status), termasuk apakah agen meminta konfirmasi untuk perintah biasa;
   - worker dilepas dengan `orca orchestration worker-release --dispatch <id> --json`.
4. Bila ada yang tidak sesuai, catat bentuk yang jalan, sesuai aturan perintah dicek jalan (Pelajaran 24).

## Kalibrasi lewat Orca
Model baru di tabel diuji kalibrasi dengan model dan effort yang akan dipakai (`references/low-capacity.md` §Uji Kalibrasi Model Baru). Lewat Orca:
1. Dari root project, jalankan `python <folder skill>/scripts/calibrate.py create`. Skrip mencetak prompt kalibrasi.
2. Isi `<nama model + effort persis>` di prompt itu dengan nama baris tabel. Tambahkan kalimat: "Setelah ketiga REPORT-K ditulis, kirim worker_done dengan outcome succeeded, juga bila K3 berstatus BLOCKED." Kirim hasilnya sebagai `--spec` di `worker-start`, dengan agen dan model baris itu. Worker Claude diluncurkan menurut T1 butir **Worker Claude Code memakai akun sesi head**.
3. Selama kalibrasi, pertanyaan worker tentang isi task dijawab "ikuti task persis seperti tertulis". Jawaban yang memberi isi merusak uji.
4. Sesudah `worker_done`, jalankan `calibrate.py grade`. Catat hasilnya di Riwayat kapasitas beserta bukti modelnya (`launch.effective`, atau header dan transkrip untuk worker di terminal sendiri), lalu lepas worker dan tutup terminal yang kamu buat.

## Menunggu dan bekerja paralel
Setiap kali head bangun, seluruh konteks sesinya dibaca ulang, jadi biaya menunggu sebanding dengan ukuran konteks dikali jumlah bangun. Head yang bangun tiap 2 menit bisa memakai lebih banyak token Claude untuk menunggu daripada untuk merancang task-nya, sementara kodenya ditulis executor tanpa token Claude. Task yang dikerjakan head sendiri dengan konteks besar juga mahal, karena setiap panggilan alat membaca ulang konteks yang sama.
- Head menunggu dengan `handoff/tools/orca_wait.py` di latar belakang (salinan `scripts/orca_wait.py`; T1 butir **Tunggu tanpa bangun berkala**). Alat itu menunggu tanpa `--types`, meng-ack sendiri batch yang isinya hanya heartbeat, dan selesai bila ada pesan lain, galat, atau sesudah 36 menit.
- Loop v3.14 menunggu dengan `--types "worker_done,escalation,question"`, sehingga setiap heartbeat worker membangunkan head. Setiap heartbeat memicu beberapa panggilan API yang masing-masing membaca ulang seluruh konteks head. Head bisa menganggapnya wajar dan tidak mencatatnya.
- Dicek jalan 2026-10-31 dengan sesi koordinator yang menganggur. Dengan `orca_wait.py`, 3 heartbeat di-ack tanpa satu pun pemberitahuan, lalu `worker_done` mengakhiri penantian. Dengan loop v3.14, heartbeat diikuti pemberitahuan 1 detik kemudian. `check --wait --json` juga menulis bingkai keepalive ke stderr setiap 15 detik (141 baris untuk loop 36 menit); alat itu membuangnya.
- **Setelan heartbeat** ada di Settings Orca, panel Orchestration: "Worker heartbeats" dan "Heartbeat interval" (1–60 menit, bawaan 5). Setelan ini berlaku untuk worker yang di-dispatch sesudah perubahan, dan preamble worker menyebut intervalnya. Dengan `orca_wait.py`, heartbeat tidak membangunkan head pada interval berapa pun.
- Selama worker bekerja, head boleh terus bekerja di wilayah file lain (T1 butir **Kerja paralel head dan worker**). Executor mengabaikan wilayah itu saat Periksa Diri, dan sumber daya bersama (DB uji, port, perangkat) dipegang task worker.
- Bila wilayahnya tidak bisa dipisah, worker dijalankan di worktree sendiri (`--worktree new-child`) dan digabung sesudah triase. Worktree baru belum berisi dependensi (mis. `node_modules`) dan file yang tidak ter-track, termasuk file secret, jadi siapkan dulu atau tuliskan di task.
- Sesi head baru sesudah triase memangkas biaya bila konteks sudah besar; keadaan project ada di `handoff/`. Head mengukurnya dengan `handoff/tools/context_size.py` dan menyarankan `/clear` ke user (T1 butir **Ukuran konteks**). Tanpa alat itu head tidak tahu konteksnya sudah besar, jadi tidak pernah menyarankannya.
- **Sesi head baru otomatis** (`scripts/head_restart.py`, disalin ke `handoff/tools/`; T1 butir **Sesi head baru otomatis**). Model tidak bisa menjalankan `/clear`, dan mengetiknya ke terminal sendiri di tengah giliran hanya menjadi pesan, sedangkan `/clear` menghentikan tugas latar belakang. Karena itu alat ini melepas proses terpisah, menunggu `orca terminal wait --for tui-idle`, memberi jeda, lalu mengetik `/clear` dan skill head dengan `orca terminal send`. Ia hanya berlaku bila head berjalan di terminal Orca, dan aktif atas keputusan user yang dicatat di README, karena sesi baru melanjutkan ROADMAP §1 tanpa menunggu user.
  - Dicek jalan 2026-11-02 di terminal uji dengan Claude Code 2.1.316 mode `auto`: alur penuh sampai skill termuat di sesi baru, lalu batal saat user mengetik tanpa Enter (2 dari 2, ketikannya utuh) dan saat user mengirim prompt selama jeda.
  - `orca terminal read` memisahkan ketikan user ke kunci `draft`; baris input di `tail` tetap tampak kosong. Pembacaan pertama hanya memeriksa `tail`, sehingga ketikan dan `/clear` terkirim sebagai satu pesan (`halo ini ketikan user/clear`).
  - Git Bash mengubah argumen berawalan `/` menjadi path Windows, sehingga `orca terminal send --text "/clear"` dari Bash menjadi `C:/Program Files/Git/clear`. Alat ini berjalan di Python, jadi tidak terkena; dari Bash, set `MSYS_NO_PATHCONV=1`. Karena itu nama skill ditulis tanpa garis miring.

## Batas
- Orca tidak menggantikan bukti. `worker_done` hanya kabar; triase tetap memakai `check_evidence.py` dan verifikasi sesuai kapasitas.
- Terminal executor tidak dipakai ulang untuk task lain, karena satu task dikerjakan dalam satu sesi executor (H1).
- Antrean dan rantai task tetap memakai tanda `Triase head: lolos` dan header `Memakai:` di file task. Ketergantungan task di Orca (`--deps`) tidak menggantikan tanda itu.
- Perintah Orca berubah antar versi. Setelah Orca diperbarui, cocokkan perintah di instruksi head dengan `orca orchestration <perintah> --help`.
