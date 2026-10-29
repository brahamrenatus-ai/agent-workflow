# Executor lewat Orca

Dibaca dari `SKILL.md` saat BOOTSTRAP, AUDIT, atau upgrade, bila head menjalankan executor lewat Orca. Orca adalah aplikasi yang meluncurkan agen CLI (Claude Code, Antigravity, Codex, …) di terminal yang diawasinya. Dalam susunan ini head menjadi **koordinator**: ia memilih model per task, meluncurkan executor, menunggu `worker_done`, lalu mentriase report seperti biasa. File di `handoff/` tetap sumber kebenaran; Orca hanya jalur peluncuran dan kabar.

Ditulis dengan Orca 1.4.243 dan dicek ulang dengan 1.4.244. Panduan yang cocok dengan versi terpasang dicetak oleh `orca skills get orchestration`; bila isinya berbeda dengan file ini, panduan itulah yang benar. Di Linux, `orca` di luar terminal Orca biasanya pembaca layar GNOME, jadi pakai `orca-ide` (dijelaskan di panduan itu).

## Kapan dipakai
- **Sepadan** bila executor memakai lebih dari satu model atau tool, dan head yang memilih model per task. User tidak perlu membuka sesi executor dan mengetik prompt pembuka untuk setiap task. Waktu user mahal, sedangkan peluncuran oleh head bisa diperiksa dari receipt-nya.
- **Tidak perlu** bila hanya ada satu model executor dan user nyaman membuka sesinya sendiri. Bandingkan dengan opsi "biarkan" (§Kualitas Rekomendasi).

## Susunan
- **Head = koordinator.** Satu Run per sesi head. Run itu menjadi kotak masuk `worker_done`, pertanyaan, dan eskalasi dari executor.
- **Executor = pekerja.** Satu task per dispatch. Sesudah report ditulis dan status task diubah, executor mengirim `worker_done`, lalu diam. Worker bekerja di folder project yang sama dengan head, jadi hanya satu worker yang mengubah file boleh berjalan pada satu waktu; task FAKTA yang hanya membaca boleh berjalan bersamaan.
- **Sesi head bukan pekerja Orca**, karena head adalah sesi interaktif user. Sesi lain, mis. pengembang skill, boleh membaca terminal head atau mengirim kabar lewat Orca, tetapi tidak mengawasinya.

## Profil Executor sebagai tabel pilihan
Contoh baris (T3 §Profil Executor):

| Model | Tool | Kapasitas | Peluncuran Orca |
|---|---|---|---|
| Gemini 3.8 Flash (high) | Antigravity | SEDANG | `--agent antigravity --model gemini-3.8-flash-high` |
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
3. **Dispatch baca-saja**, satu untuk setiap agen yang akan dipakai. Spec-nya menjalankan `check_evidence.py` atas report terakhir dan `git status --porcelain`, tanpa mengubah file apa pun. Sesudah worker selesai:
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
Setiap kali head bangun, seluruh konteks sesinya dibaca ulang. Di satu project lapangan, head dengan konteks ±175 ribu token yang bangun tiap 2 menit memakai 32 panggilan API dalam 19 menit pemantauan, setara ±1 juta token input, sementara kode task-nya ditulis executor tanpa token Claude. Di project yang sama, satu task yang dikerjakan head sendiri dengan konteks rata-rata ±480 ribu token memakai 169 panggilan, setara ±10,6 juta token input.
- Head menunggu dengan satu loop latar belakang yang baru selesai bila ada pesan, galat, atau sesudah empat putaran (T1 butir **Tunggu tanpa bangun berkala**). Dicek jalan 2026-10-30: tanpa pesan, loop berputar diam; pesan atau galat membuatnya langsung selesai. Heartbeat cukup di-ack.
- Selama worker bekerja, head boleh terus bekerja di wilayah file lain (T1 butir **Kerja paralel head dan worker**). Executor mengabaikan wilayah itu saat Periksa Diri, dan sumber daya bersama (DB uji, port, perangkat) dipegang task worker.
- Bila wilayahnya tidak bisa dipisah, worker dijalankan di worktree sendiri (`--worktree new-child`) dan digabung sesudah triase. Worktree baru belum berisi dependensi (mis. `node_modules`) dan file yang tidak ter-track, termasuk file secret, jadi siapkan dulu atau tuliskan di task.
- Sesi head baru sesudah triase memangkas biaya bila konteks sudah besar; keadaan project ada di `handoff/`.

## Batas
- Orca tidak menggantikan bukti. `worker_done` hanya kabar; triase tetap memakai `check_evidence.py` dan verifikasi sesuai kapasitas.
- Terminal executor tidak dipakai ulang untuk task lain, karena satu task dikerjakan dalam satu sesi executor (H1).
- Antrean dan rantai task tetap memakai tanda `Triase head: lolos` dan header `Memakai:` di file task. Ketergantungan task di Orca (`--deps`) tidak menggantikan tanda itu.
- Perintah Orca berubah antar versi. Setelah Orca diperbarui, cocokkan perintah di instruksi head dengan `orca orchestration <perintah> --help`.
