# Changelog agent-workflow

Dibaca saat AUDIT untuk jalur upgrade (`SKILL.md` §4). Setiap versi mencatat aturan yang **masuk ke file project**, beserta file sasaran, cara patch, dan penandanya. Perubahan yang hanya mengubah cara kerja skill (tanpa jejak di project) cukup disebut di ringkasan versi.

`scripts/check_version.py` membaca blok `penanda` di akhir file ini, lalu memeriksanya di project:
- Penanda yang ada berarti aturannya sudah terpasang, termasuk bila dulu dipasang manual.
- Penanda yang hilang berarti kandidat patch. Setiap patch tetap disaring dengan §Kualitas Rekomendasi sebelum dipasang.

Sejak v3.12 nama file, skrip, dan opsi berbahasa Inggris. Bagian versi lama ditulis dengan nama baru; padanan nama lama ada di bagian v3.12.

**Aturan untuk versi berikutnya:** setiap aturan baru yang masuk ke file project wajib punya baris di tabel versinya dan penanda di blok `penanda`. Teks penandanya harus ada di template yang menghasilkan file itu, dan baris aturan itu membawa tag `<!-- aw: ID -->` di setiap varian template (TINGGI/SEDANG, RENDAH, LITE). Uji di `tests/` memeriksa keduanya.

**Tag penanda (sejak v3.10).** Teks penanda ditulis dalam bahasa Indonesia, sedangkan file project ditulis dalam bahasa user. Karena itu `check_version.py` juga menganggap penanda teks ada bila file sasarannya memuat tag `<!-- aw: ID -->` dengan ID itu. Saat patch dipasang, tag ikut disalin bersama aturannya. Project lama berbahasa Indonesia tidak perlu ditambahi tag, karena teksnya tetap dikenali.

## v2.1 (2026-10-18): dasar
Protokol inti dua agen. Project yang kehilangan lebih dari dua penanda dasar lebih baik diaudit penuh (§4) daripada di-upgrade per baris.

| ID | Perubahan | File sasaran | Cara patch | Persetujuan |
|---|---|---|---|---|
| B1 | ROADMAP sebagai dokumen arah | `handoff/ROADMAP.md` | Buat dari T4; item diverifikasi di kode | – |
| B2 | Gerbang arah: anggaran 3 MEASURE dan ritme | instruksi head | T1 langkah 3 | – |
| B3 | Jenis task MEASURE/FIX/FEATURE/SPIKE/SMOKE | `handoff/README.md` | T3 §Jenis Task | – |
| B4 | Kanal Hipotesis & Usulan di report | `handoff/reports/REPORT_TEMPLATE.md` | T6 | – |
| B5 | Profil dan kapasitas executor | `handoff/README.md` | T3 §Profil Executor; kapasitas dari §Kapasitas Executor | Konfirmasi tool/model executor ke user |

## v3 (2026-10-21): dari uji lapangan IoT SCADA
Juga mengubah cara kerja skill: template dipindah ke `references/`, lokasi kanonis harus ter-commit, ada checklist migrasi tool/model, dan jawaban yang sudah tercatat diajukan sebagai konfirmasi satu klik.

| ID | Perubahan | File sasaran | Cara patch | Persetujuan |
|---|---|---|---|---|
| V3-1 | Integritas bukti saat triase: OK harus memenuhi nilai harapan, dan kutipan log harus ada di file | instruksi head | T1 langkah 2, butir pertama | – |
| V3-2 | Definisi status SMOKE: OK hanya bila nilai teramati memenuhi nilai harapan | `handoff/README.md` | T3 §SMOKE | – |
| V3-3 | Larangan menulis nilai secret di log, report, dan `handoff/` | brief executor | T2a pagar pengaman / T2b Dilarang | – |
| V3-4 | Syarat naik/turun kapasitas dari bukti berformat target | `handoff/README.md` | T3 §Profil Executor | – |
| V3-5 | Rujukan kode ditulis "fungsi + file:baris" | `handoff/README.md` | T3 §Format Task | – |
| V3-6 | Gerbang ritme: bila fokus habis, minta prioritas baru ke user | instruksi head | T1 langkah 3 | – |

## v3.1 (2026-10-22): struktur file dan kualitas rekomendasi
Juga menambah mode STRUKTUR dan `references/structure.md` di skill.

| ID | Perubahan | File sasaran | Cara patch | Persetujuan |
|---|---|---|---|---|
| S1 | Peta struktur berlabel WAJIB/STANDAR/SELERA | `handoff/STRUCTURE.md` (versi ringkas: README §Struktur; LITE: NOTES §1) | T9, dari survei `references/structure.md` | Keputusan struktur ditanyakan ke user |
| S2 | Jenis task STRUKTUR | `handoff/README.md` | T3 §Jenis Task, baris STRUKTUR | – |
| S3 | Pagar letak file: memindah atau menghapus file hanya lewat task STRUKTUR | brief executor (atau README, bila pagar project ada di sana) | T2a pagar / T2b Dilarang | – |
| S4 | Mutu keputusan (lima uji, termasuk opsi "biarkan") | instruksi head | T1 langkah 3 | – |
| S5 | Drift struktur dicek saat retrospektif | instruksi head | T1 langkah 6 | – |
| S6 | Aturan log bukti: ≤ ±10 MB utuh setelah cek secret; lebih besar → `raw/` + potongan | `handoff/STRUCTURE.md` atau README | T9 §Aturan Letak File | – |

## v3.2 (2026-10-22): alat cek secret
Hanya berlaku bila project punya file secret lokal.

| ID | Perubahan | File sasaran | Cara patch | Persetujuan |
|---|---|---|---|---|
| C1 | `check_secrets.py` terpasang, dengan `SECRET_FILES` terisi | `handoff/tools/check_secrets.py` | Salin `scripts/check_secrets.py` (§3 BOOTSTRAP), lalu `--list-sources` | – |
| C2 | Commit head didahului `check_secrets.py --staged` | instruksi head | T1 langkah 5 | – |
| C3 | Executor menjalankan `check_secrets.py` untuk log dan report | brief executor | T2a langkah 4 / T2b langkah 6 | – |

## v3.3 (2026-10-22): penanda versi dan jalur upgrade
Juga menambah changelog ini, `scripts/check_version.py`, dan jalur upgrade di AUDIT.

| ID | Perubahan | File sasaran | Cara patch | Persetujuan |
|---|---|---|---|---|
| U1 | Penanda versi skill di kepala README | `handoff/README.md` (LITE: skill `<prefix>-dev`) | T3 baris kepala (`agent-workflow v...`); tulis versi skill saat ini | – |

## v3.4 (2026-10-23): kapasitas per model, model tercatat, penjaga isi commit head
Berasal dari pemakaian nyata di robot meja. REPORT-054 tidak menulis nama model, padahal kapasitas Gemini Flash diturunkan berdasarkan report itu. Commit `handoff:` sempat mengembalikan `src/` ke versi lama.

| ID | Perubahan | File sasaran | Cara patch | Persetujuan |
|---|---|---|---|---|
| M1 | Kapasitas dinilai per model (satu baris per model di Profil Executor; header `Butuh executor` menentukan model) | `handoff/README.md` | T3 §Profil Executor | Konfirmasi daftar model ke user |
| M2 | Executor menulis model persis dari prompt user, atau `tidak diketahui`; tidak menebak | brief executor | T2a langkah 4 / T2b report + Dilarang | – |
| M3 | Prompt pembuka executor diawali nama model | `handoff/PROMPT_EXECUTOR.md` (bila ada) | T7 | – |
| M4 | Head menanyakan model ke user bila report tanpa model | instruksi head | T1 langkah 2 (Kedalaman verifikasi) | – |
| G1 | Isi commit head diperiksa: hanya file protokol; kode ke commit terpisah | instruksi head | T1 langkah 5 (**Isi commit.**); opsional hook commit-msg di `references/enforcement.md` | Hook: persetujuan user |

## v3.5 (2026-10-24): executor RENDAH lebih berguna, kalibrasi model, rantai task aman
Berasal dari robot meja dan pertanyaan user tentang model berindeks rendah sebagai executor. Gemini Flash 3.8 gagal saat menafsirkan log sendiri (REPORT-054) dan lolos saat skrip yang menilai (TASK-060, TASK-064 → TASK-058). TASK-058 sempat dimulai sebelum prasyaratnya ditriase, dan sesi head mencatat model dari header task (REPORT-059). Juga menambah `references/low-capacity.md` dan `scripts/calibrate.py` di skill.

| ID | Perubahan | File sasaran | Cara patch | Persetujuan |
|---|---|---|---|---|
| R1 | Head menulis skrip penilai/penganalisis untuk task RENDAH, menjalankannya dulu pada data contoh, dan memverifikasi dengan menjalankannya ulang | instruksi head | T1 langkah 2 (RENDAH) dan langkah 4 (RENDAH) | – |
| R2 | Executor RENDAH tidak menghitung atau menyimpulkan sendiri; BLOCKED bila aturan task bertentangan dengan test acceptance | brief executor | T2a paragraf kapasitas / T2b langkah 3–4 | – |
| R3 | Task RENDAH maksimal ±8 langkah dengan cabang dalam tabel jika–maka (maks. 3); penantian dan dialog panjang dipindah ke alat | instruksi head | T1 langkah 4 (RENDAH) | – |
| A1 | Model baru tanpa riwayat diuji kalibrasi dulu | `handoff/README.md` | T3 §Profil Executor (**Model baru**); uji dijalankan dengan `scripts/calibrate.py` dari folder skill | Model yang dikalibrasi: konfirmasi ke user |
| D1 | Tanda triase head di file task; prasyarat menunggu tanda itu, bukan DONE | instruksi head, `handoff/README.md` | T1 langkah 2 (**Tanda triase.**); T3 §Alur dan §Format Task. Task lama yang sudah ditriase dan dirujuk sebagai prasyarat diberi tanda `Triase head: lolos (sebelum v3.5)` | – |
| D2 | Header `Memakai:` untuk sumber daya eksklusif; head hanya memeriksa file selama sumber daya dipakai | `handoff/README.md`, instruksi head | T3 §Format Task; T1 langkah 2 (**Sumber daya eksklusif.**) | – |
| D3 | Executor mengecek prasyarat dan sumber daya sebelum mulai | brief executor | T2a langkah 1 / T2b langkah 1 | – |
| E1 | Task yang dikerjakan sesi head dicatat `sesi head · model (effort)` dari setelan sesi dan tidak dihitung sebagai bukti kapasitas | instruksi head | T1 langkah 4 (**Task yang kamu kerjakan sendiri**) | – |
| E2 | Pelaksana mencatat effort selain model | brief executor, `handoff/PROMPT_EXECUTOR.md`, REPORT_TEMPLATE | T2a langkah 4 / T2b report; T7; T6 | – |
| E3 | Syarat naik RENDAH → SEDANG: minimal 1 task berformat SEDANG | `handoff/README.md` | T3 §Profil Executor | – |

## v3.6 (2026-10-24): pemeriksa bukti, test dulu untuk SEDANG, konteks bersih, kebiasaan gagal per model
Berasal dari pertanyaan user agar model seperti Gemini Flash 3.8 bisa dipakai lebih baik. Aturan integritas bukti sudah tertulis sejak v3, tetapi kegagalannya terulang (IoT SCADA, lalu REPORT-054 robot meja) dan baru tertangkap saat triase. Juga menambah `scripts/check_evidence.py` di skill.

| ID | Perubahan | File sasaran | Cara patch | Persetujuan |
|---|---|---|---|---|
| P1 | `check_evidence.py` terpasang dan disebut di README | `handoff/tools/check_evidence.py`, `handoff/README.md` | Salin `scripts/check_evidence.py` (§3 BOOTSTRAP); T3 §Lingkungan dan §Format Report | – |
| P2 | Executor menjalankan `check_evidence.py` sebelum DONE | brief executor | T2a langkah 5 / T2b langkah 6 | – |
| P3 | Head menjalankan `check_evidence.py` saat triase | instruksi head | T1 langkah 2 (**Integritas bukti.**) | – |
| P4 | Format bukti yang bisa dicek: tabel Harapan/Teramati/Bukti/Status dan blok `bukti` | `handoff/reports/REPORT_TEMPLATE.md` | T6 §Data yang Diminta dan §Bukti Mentah | – |
| F1 | Task SEDANG berisi test acceptance yang bisa dijalankan, dan head menjalankannya dulu | instruksi head | T1 langkah 4 (SEDANG) | – |
| F2 | Executor menjalankan test acceptance sampai lulus (RENDAH: persis seperti tertulis), tanpa mengubah test-nya | brief executor | T2a tabel FIX/FEATURE / T2b langkah 3 | – |
| H1 | Satu task per sesi; report disusun dari file tersimpan; output bukti disimpan dulu ke `handoff/logs/` | brief executor | T2a paragraf **Satu task per sesi** / T2b pembuka | – |
| Q1 | Kebiasaan gagal per model dicatat beserta penangkalnya | `handoff/README.md`, instruksi head | T3 §Profil Executor (**Kebiasaan gagal**); T1 langkah 2 dan 4 | Isi awal: konfirmasi ke user |

## v3.7 (2026-10-24): periksa diri sebelum DONE, task FAKTA untuk head
Berasal dari keputusan user bahwa token executor (mis. Gemini Flash) dianggap tidak terbatas, sedangkan token head, waktu user, dan waktu hardware yang mahal. Pekerjaan yang bisa diverifikasi murah dipindah ke executor. Juga memperluas `scripts/check_evidence.py`: status task FAKTA, `hitung()` atas folder atau pola glob, dan peringatan bila report tanpa bagian Periksa Diri.

| ID | Perubahan | File sasaran | Cara patch | Persetujuan |
|---|---|---|---|---|
| W1 | Executor memeriksa diri sebelum DONE: baca ulang task, ulangi test pada kode akhir, `git status --porcelain`, `check_evidence.py` sampai 0 masalah | brief executor | T2a langkah 5 / T2b langkah 6 | – |
| W2 | Bagian Periksa Diri di report | `handoff/reports/REPORT_TEMPLATE.md` | T6 §Periksa Diri; salin ulang `scripts/check_evidence.py` versi ini ke `handoff/tools/` | – |
| L1 | Jenis task FAKTA: bacaan luas untuk head, diperlakukan seperti MEASURE untuk anggaran dan ritme | `handoff/README.md` | T3 §Jenis Task dan catatan di bawahnya; T4 legenda | – |
| L2 | Head mendelegasikan bacaan luas lewat task FAKTA | instruksi head | T1 langkah 3 (**Task FAKTA**) dan langkah 4 (**Bacaan luas didelegasikan.**) | – |
| L3 | Executor mengerjakan task FAKTA: hanya membaca, setiap jawaban berbukti, TIDAK YAKIN bila ragu | brief executor | T2a tabel jenis (baris FAKTA) / T2b langkah 3 | – |

## v3.8 (2026-10-26): protokol dicek di mesin nyata, sesi dengan model yang tepat
Berasal dari pemakaian di robot meja dan aplikasi budidaya. `graphify update .` gagal di empat report robot meja karena tidak ada di PATH. Hook graphify membuat `git status` di Periksa Diri hampir tidak pernah bersih. `/<prefix>-head` tidak pernah terdaftar di Claude Code karena instruksinya hanya ada di `.agents/skills/`. Sesi yang dibuka dari sesi lain mewarisi model dan effort sesi asalnya. Juga mengubah cara kerja skill (tanpa jejak di project): `scripts/calibrate.py` menyimpan seed di luar folder project, `grade` membacanya sendiri dan mengarsipkan hasilnya tanpa seed ke `handoff/logs/`, dan skor bisa diulang dengan `--from-archive`. `scripts/check_version.py` mendapat jenis penanda `tampak~`. SKILL.md mendapat Pelajaran 24 dan saran model per jenis sesi.

| ID | Perubahan | File sasaran | Cara patch | Persetujuan |
|---|---|---|---|---|
| N1 | Model dan effort per jenis sesi; sesi baru dicek setelannya begitu dibuka | `handoff/README.md` | T3 baris **Sesi** | Model head dan pekerjaan mekanis: konfirmasi ke user |
| O1 | Berkas yang berubah sendiri (ditulis ulang hook/tool) dicatat di peta struktur | `handoff/STRUCTURE.md` (versi ringkas: README §Struktur) | T9 §Berubah Sendiri; isi dari survei `references/structure.md` | – |
| O2 | Periksa Diri executor tidak menghitung berkas yang berubah sendiri | brief executor | T2a langkah 5 / T2b langkah 6 | – |
| J1 | Perintah di protokol sudah dicek jalan di mesin ini; yang tidak boleh dijalankan agen ditandai `belum dicek` | `handoff/README.md` (atau brief executor bila perintah ada di sana) | T3 §Lingkungan / T2a §Perintah, kalimat pembuka. Jalankan dulu setiap perintahnya | – |
| J2 | Head menjalankan sekali setiap perintah baru sebelum menulisnya ke protokol atau task | instruksi head | T1 langkah 5 (**Perintah baru**) | – |
| K1 | Tool head tercatat di README, dan instruksi head (kanonis atau penunjuk) ada di folder skill tool itu | `handoff/README.md`, folder skill tool head | T3 baris Head (`tool: ...`); penunjuk T7 di folder tool yang belum punya | Tool head: konfirmasi ke user |
| K2 | Instruksi executor ada di folder skill setiap tool executor yang tercatat di README | folder skill tool executor | Penunjuk T7 di folder tool yang belum punya | – |

## v3.9 (2026-10-26): aturan turun yang konsisten, bukti yang asalnya tercatat
Berasal dari TASK-034 aplikasi budidaya dan triase TASK-065 robot meja. Dua head memakai aturan turun berbeda: "klaim penyebab → turun" menurut §Kapasitas, atau "cukup Kebiasaan gagal" menurut paragraf Kebiasaan gagal. Gemini Flash di aplikasi budidaya dua kali naik ke TINGGI dan dua kali gagal di task TINGGI pertamanya: klaim penyebab di REPORT-009, pengamatan user dikarang di REPORT-035. Baris log yang ditulis tangan (TASK-006) dan angka tanpa pengukuran (TASK-031/032) lolos `check_evidence`. TASK-033 melewatkan kriteria yang tidak dinilai skrip. Juga menambah `scripts/record.py` di skill, dan `check_evidence.py` sekarang memeriksa:
- asal log terhadap `handoff/logs/provenance.jsonl`: log yang diedit setelah dicatat adalah masalah; log tanpa catatan diberi peringatan, atau masalah dengan `--require-provenance`;
- kutipan user yang menyalin Harapan; ini tambalan aplikasi budidaya (REPORT-035) yang dibawa ke skill;
- kriteria K1..Kn di task yang tidak punya baris di tabel Data;
- angka bersatuan tanpa rujukan di Ringkasan Fakta, Keputusan Implementasi, dan Anomali (peringatan).

| ID | Perubahan | File sasaran | Cara patch | Persetujuan |
|---|---|---|---|---|
| X1 | Turun satu tingkat hanya karena OK palsu atau pelanggaran pagar pengaman; klaim penyebab, angka tanpa pengukuran, dan Batasan yang dilanggar diam-diam menjadi Kebiasaan gagal (task tidak dihitung untuk naik) | `handoff/README.md`, instruksi head | T3 §Profil Executor (**Syarat turun**); T1 langkah 2 dan 6 | Aturan kapasitas berubah: konfirmasi ke user |
| X2 | Naik setelah 2 report bebas Kebiasaan gagal; 2 task pertama sesudah naik adalah masa percobaan | `handoff/README.md` | T3 §Profil Executor (**Syarat naik, semua tingkat**) | Konfirmasi ke user |
| Y1 | `record.py` terpasang; output bukti disimpan lewat skrip ini | `handoff/tools/record.py`, brief executor, README §Lingkungan | Salin `scripts/record.py`; T2a paragraf **Satu task per sesi** / T2b langkah 3; T3 §Lingkungan | – |
| Y2 | `check_evidence.py` versi ini terpasang (asal log, kutipan user, kriteria K, angka tanpa rujukan) | `handoff/tools/check_evidence.py` | Salin ulang `scripts/check_evidence.py`; bandingkan dulu dengan salinan project dan bawa tambalan lokal ke skill (§4 jalur upgrade) | – |
| Y3 | Bukti `user:` hanya kata-kata user; TIDAK DIUJI sampai user menjawab; head mengonfirmasinya ke user | brief executor, REPORT_TEMPLATE, instruksi head | T2a langkah 4 / T2b Dilarang; T6 catatan tabel Data; T1 langkah 2 (**Bukti `user:`**) | – |
| Y4 | Kriteria terima bernomor K1, K2, …; baris tabel Data diawali nomornya | `handoff/README.md`, instruksi head | T3 §Format Task; T1 langkah 4 | – |

## v3.9.1 (2026-10-27): `--redact` tidak merusak asal log, token bot Telegram
Berasal dari putaran upgrade v3.9. `check_secrets.py --redact` menulis ulang log yang berisi secret, sehingga hash-nya tidak lagi cocok dengan `provenance.jsonl` dan `check_evidence` menandainya "berubah setelah dicatat"; sementara itu brief executor aplikasi budidaya menyuruh kasus ini ditulis di Anomali. Pola token bot Telegram lokal di aplikasi budidaya tidak mengenali token di URL `api.telegram.org/bot<token>`, bentuk yang dicetak httpx di level INFO; token project itu tertangkap hanya lewat nilainya di `backend/.env`. Pola di skill mengikuti gitleaks (`<id>:A` + 34 karakter, id 5–16 digit) dan mengizinkan awalan `bot`. Perubahan lain tanpa penanda baru:
- Penanda X2 diperketat menjadi teks butir aturannya (`Syarat naik, semua tingkat`), karena `masa percobaan` juga muncul di riwayat kapasitas. Project yang dulu lolos X2 hanya karena riwayat sekarang mendapat X2 sebagai kandidat.
- BOOTSTRAP dan AUDIT ikut menjalankan perintah di file aturan agen buatan tool lain. Contohnya `.agents/rules/graphify.md` di IoT SCADA masih memakai `graphify`, yang tidak ada di PATH. Bentuk yang jalan ditambahkan sebagai catatan, supaya baris asli tool tidak diubah.

| ID | Perubahan | File sasaran | Cara patch | Persetujuan |
|---|---|---|---|---|
| C4 | `check_secrets.py` versi ini terpasang. `--redact` menambahkan catatan asal berjenis `redact` untuk log dari `record.py`, hanya bila log itu belum diedit sejak dicatat. Pola token bot Telegram juga mengenali bentuk URL Bot API | `handoff/tools/check_secrets.py`, instruksi head, brief executor | Salin ulang `scripts/check_secrets.py`, lalu isi lagi `SECRET_FILES` dari salinan lama. Bandingkan dulu dengan salinan project dan bawa tambalan lokal ke skill (§4 jalur upgrade). Ubah kalimat `--redact` di T1 langkah 5 dan T2a langkah 4 | – |

## v3.9.2 (2026-10-27): log di output `git status` bukan rujukan
Berasal dari survei lapangan pertama. Report wajib memuat output `git status --porcelain` di Periksa Diri, dan `check_evidence` menganggap setiap nama log di report sebagai log yang dirujuk. Di aplikasi budidaya REPORT-041 sampai 048, log `uji_*` ditulis `regresi_uji.py` (yang sendiri dijalankan lewat `record.py`) dan hanya tercantum di output itu. Akibatnya setiap report mendapat 5 peringatan "tidak tercatat di provenance.jsonl", dan peringatan asal yang benar mudah terlewat. Sekarang baris berformat `git status --porcelain`/`-s` (kode status lalu satu path, atau `lama -> baru`, boleh berbacktick) tidak dihitung sebagai rujukan untuk cek asal. Pencarian baris log di blok kode tidak berubah. Uji pada 149 report di ketiga project: 55 peringatan asal palsu hilang (semuanya di aplikasi budidaya, semuanya log yang hanya disebut di baris `git status`), 0 temuan baru, dan temuan lain tidak berubah.

| ID | Perubahan | File sasaran | Cara patch | Persetujuan |
|---|---|---|---|---|
| Y5 | `check_evidence.py` versi ini terpasang: log yang hanya tercantum di output `git status` tidak dicek asalnya | `handoff/tools/check_evidence.py` | Salin ulang `scripts/check_evidence.py`; bandingkan dulu dengan salinan project dan bawa tambalan lokal ke skill (§4 jalur upgrade) | – |

## v3.10 (2026-10-28): penanda netral bahasa, verifikasi tampilan, task milik sesi lain
Berasal dari survei lapangan kedua dan persiapan rilis publik.
- Penanda lama mencocokkan teks berbahasa Indonesia, padahal skill menyuruh file project ditulis dalam bahasa user. Project berbahasa lain akan kehilangan hampir semua penanda. Sekarang setiap aturan di template membawa tag `<!-- aw: ID -->` (lihat **Tag penanda** di atas).
- Di aplikasi budidaya, audit peramban head menangkap cacat yang lolos test di 4 dari 5 task UI; tiga di antaranya cacat tampilan (ukuran tombol, tab keluar layar, lebar panel). Head lalu mencatat bahwa rancangan harus dicocokkan juga untuk tampilan, bukan hanya fungsi. Implementasi rujukan head yang diuji di peramban sebelum task ditulis menemukan dua jebakan desain sebelum executor mulai.
- Di project yang sama, sesi head yang dipanggil sebagai executor menjalankan ulang SMOKE yang sudah selesai, sehingga log bukti executor tertimpa dan satu panggilan API berbayar terpakai lagi.
- Log per-test yang ditulis skrip pelari tidak bisa dicatat `record.py` tanpa mendaftar setiap file, dan `--result` ikut mencatat file lama yang tidak ditulis perintah itu.

Perubahan lain tanpa penanda baru: `check_version.py` mengenali tag dan syarat `@bila_ui`; `check_evidence.py` mengenali kata kunci bahasa Inggris (tabel **Kata kunci alat** di `templates.md`); nama project lapangan di skill disamarkan menjadi jenis project.

| ID | Perubahan | File sasaran | Cara patch | Persetujuan |
|---|---|---|---|---|
| I1 | Task tampilan: kriteria tampilan bisa dicek (rujukan rancangan, ukuran layar sasaran); yang terukur dinilai skrip audit peramban, yang butuh mata ditandai `head:` atau `user:`; saat triase head melihat tampilan di ukuran layar sasaran dan membandingkannya dengan mockup | instruksi head | T1 langkah 2 dan langkah 4 (**Task tampilan**) | – |
| I2 | Executor menyimpan tangkapan layar untuk layar yang diubah; kriteria `head:` ditulis TIDAK DIUJI | brief executor | T2a langkah 4 / T2b langkah 3 | – |
| I3 | Cara melihat tampilan (alat dan ukuran layar sasaran) tercatat dan sudah dicek jalan | `handoff/README.md` | T3 §Lingkungan (**Cek tampilan**); isi dari BOOTSTRAP §3 | Alat dan ukuran layar: konfirmasi ke user |
| F3 | Sketsa yang perilakunya sulit diduga diuji dulu sebagai implementasi rujukan sebelum task SEDANG ditulis | instruksi head | T1 langkah 4 (SEDANG) | – |
| Z1 | Executor tidak menjalankan task yang statusnya bukan OPEN, atau yang report-nya sudah ada, sebelum bertanya ke user | brief executor | T2a langkah 1 (**Task yang mungkin milik sesi lain**) / T2b langkah 1 | – |
| Z2 | `record.py` menolak menimpa log task yang sudah DONE/BLOCKED tanpa `--overwrite` | `handoff/tools/record.py` | Salin ulang `scripts/record.py` | – |
| Y6 | `record.py --result` menerima pola glob, dan hanya mencatat file yang ditulis selama perintah berjalan | `handoff/tools/record.py`, `handoff/README.md` | Salin ulang `scripts/record.py` (sekaligus Z2); T3 §Lingkungan, baris Simpan bukti | – |
| Y7 | `check_evidence.py` versi ini: `--at`/`--at-report` untuk report lama, kata kunci bahasa Inggris | `handoff/tools/check_evidence.py` | Salin ulang `scripts/check_evidence.py`; bandingkan dulu dengan salinan project dan bawa tambalan lokal ke skill | – |

## v3.10.1 (2026-10-28): foto tampilan dengan emulasi perangkat
Berasal dari putaran upgrade v3.10 di robot meja. Cek tampilan memakai `chrome --headless --window-size=375,812 --screenshot`, dan hasilnya menunjukkan tombol dasbor terpotong di lebar HP. Temuan itu dicatat sebagai item FIX di ROADMAP project. Pemeriksaan berikutnya menunjukkan Chrome desktop menata halaman minimal ±500 px (`innerWidth=500` walau jendela diminta 375 px) lalu hanya memotong fotonya. Pada emulasi 375 px yang benar, dasbor itu muat; item FIX-nya dibatalkan. Saran "peramban headless" di v3.10 tidak memperingatkan jebakan ini, jadi setiap project bisa mendapat foto HP yang salah.
- `scripts/screenshot.py` (baru): membuka halaman lewat Chrome DevTools Protocol dengan emulasi perangkat (lebar < 768 px sebagai HP), menyimpan tangkapan layar per ukuran, dan mencetak lebar halaman serta elemen yang keluar dari lebar layar (exit 1 bila ada). `--offline` memblokir host selain localhost. Hanya pustaka standar Python; butuh Chrome, Chromium, atau Edge.
- Templates (T1, T2a, T3, Penyesuaian) dan SKILL.md §3 merujuk alat ini dan memperingatkan jebakan lebar jendela. Pelajaran 25 mendapat contohnya.

| ID | Perubahan | File sasaran | Cara patch | Persetujuan |
|---|---|---|---|---|
| I4 | `screenshot.py` terpasang di project ber-UI, dan baris Cek tampilan di README memakainya (atau audit peramban yang mengemulasikan lebar layar) | `handoff/tools/screenshot.py`, `handoff/README.md` | Salin `scripts/screenshot.py`; perbarui baris Cek tampilan (T3) lalu jalankan sekali. Project yang memotret dengan `--window-size` biasa: ulangi fotonya dan periksa ulang temuan tampilan yang berasal dari foto itu | – |

## v3.10.2 (2026-10-28): `screenshot.py` untuk rute hash dan pembacaan port yang stabil
Berasal dari putaran upgrade v3.10 di aplikasi budidaya, yang memakai router hash (`http://localhost:5174/#/`). Ukuran pertama terfoto, tetapi ukuran kedua gagal "tidak selesai dimuat dalam 30 detik". Navigasi ke URL yang sama dengan fragmen hanya berpindah di dalam dokumen, tanpa event `load`. Uji v3.10.1 tidak menangkapnya karena halaman ujinya tanpa `#`. Sekarang setiap ukuran dimuat dari awal lewat `about:blank` (`buka_halaman`), dan uji punya kasus rute hash di dua ukuran.

Pengulangan uji juga menemukan kegagalan sesekali di Windows (1 dari 6 run): `PermissionError` saat membaca `DevToolsActivePort`, karena Chrome masih memegang file itu saat menulisnya. `baca_port` sekarang menunggu sampai file lengkap (baris port dan path) dan tidak dikunci. Uji meniru kunci itu dengan `msvcrt.locking`.

| ID | Perubahan | File sasaran | Cara patch | Persetujuan |
|---|---|---|---|---|
| I5 | `screenshot.py` versi ini: halaman dengan rute hash termuat di setiap ukuran | `handoff/tools/screenshot.py` | Salin ulang `scripts/screenshot.py` | – |

## v3.11 (2026-10-29): head memilih model per task, executor lewat Orca
Berasal dari permintaan user agar head mengatur sendiri model executor per task, termasuk model Claude saat task melebihi kapasitas Gemini Flash, dan dari uji coba Orca di aplikasi budidaya. Dalam uji coba itu head meluncurkan Gemini 3.8 Flash (high) di Antigravity lewat `orca orchestration worker-start`, dan isi `worker_done` cocok dengan hasil yang diulang. Pemeriksaan sesudahnya menemukan dua hal yang lolos dari uji coba:
- setelan izin agen Orca (`Full access`) meluncurkan executor dengan `--dangerously-skip-permissions`;
- terminal Claude Code siaga macet di dialog persetujuan mode bypass, sehingga tidak pernah siap dipakai.

Model yang diminta juga belum tentu model yang berjalan; Orca mencatat model yang benar-benar dipakai sebagai `launch.effective` di receipt. Perubahan lain tanpa penanda baru: `references/orca.md`, bagian Orca di `references/enforcement.md`, Pelajaran 26, dan syarat `@bila_orca` di `scripts/check_version.py`.

| ID | Perubahan | File sasaran | Cara patch | Persetujuan |
|---|---|---|---|---|
| M5 | Head memilih model per task: yang termurah dengan kapasitas cukup, mengikuti urutan pilihan user, kecuali ada Kebiasaan gagal yang mengenai task itu; alasannya ditulis di header task; model tanpa kapasitas dikalibrasi dulu | instruksi head, `handoff/README.md` | T1 langkah 4 (**Pilihan model per task**); T3 §Format Task (`Model:` + alasan) | – |
| M6 | Profil Executor mencatat tool per model dan urutan pilihan model dari user | `handoff/README.md` | T3 §Profil Executor (kolom Tool, butir **Urutan pilihan model**; baris `Tool:` menyebut semua tool executor) | Urutan pilihan: keputusan user |
| D4 | Head menjalankan executor lewat Orca: satu Run per sesi, satu task per dispatch di folder project, model dicocokkan dengan `launch.effective`, `worker_done` bukan bukti, worker dilepas sesudah triase, prompt izin worker dijawab user | instruksi head | T1 §Executor lewat Orca; cara cek di `references/orca.md` | Pemakaian Orca: konfirmasi ke user |
| D5 | Executor yang dijalankan lewat Orca bertanya lewat `ask`, tidak menganggap balasan head sebagai izin user, dan mengirim `worker_done` sesudah DONE/BLOCKED beserta path report | brief executor | T2a paragraf **Dijalankan lewat Orca** dan langkah 6 / T2b langkah 7 | – |
| D6 | Profil Executor mencatat peluncuran Orca per model dan setelan izin agen di Orca; dispatch baca-saja sudah dicek jalan | `handoff/README.md` | T3 §Profil Executor (kolom Peluncuran Orca, butir **Orca**); pemetaan izin di `references/enforcement.md` §Orca | Setelan izin agen: keputusan user |

## v3.12 (2026-10-29): nama file berbahasa Inggris
Berasal dari permintaan user agar nama file konsisten. Sebelumnya skrip, referensi, dan sebagian file project bernama Indonesia, sedangkan nama lain (`handoff/README.md`, `REPORT_TEMPLATE.md`, `PROMPT_EXECUTOR.md`) bernama Inggris. Sejak versi ini nama yang dibuat skill (file, folder, skrip, opsi perintah) berbahasa Inggris. Isi teks dan kata kunci di dalamnya (TINGGI/SEDANG/RENDAH, STRUKTUR, judul bagian, status) tidak berubah, begitu juga nama fungsi di skrip yang dipakai penanda.

Nama lama tetap diterima skrip selama masa peralihan: opsi lama, `handoff/logs/asal.jsonl` bila `provenance.jsonl` belum ada, pack kalibrasi di `handoff/kalibrasi/`, dan seed di `~/.agent-workflow/kalibrasi/`. Penanda versi lama yang menyebut nama file menerima nama lama maupun baru. Saat upgrade, task yang belum DONE ikut diperbarui; report, task selesai, log, dan arsip kalibrasi tidak diubah karena itu riwayat.

| Lama | Baru |
|---|---|
| `scripts/cek_bukti.py`, `scripts/cek_secret.py`, `scripts/cek_versi.py` | `scripts/check_evidence.py`, `scripts/check_secrets.py`, `scripts/check_version.py` |
| `scripts/catat.py`, `scripts/foto_tampilan.py`, `scripts/kalibrasi.py buat`/`nilai` | `scripts/record.py`, `scripts/screenshot.py`, `scripts/calibrate.py create`/`grade` |
| `references/penegakan.md`, `references/rendah.md`, `references/struktur.md` | `references/enforcement.md`, `references/low-capacity.md`, `references/structure.md` |
| `handoff/STRUKTUR.md` (atau `docs/STRUKTUR.md`), `handoff/kalibrasi/`, `handoff/logs/asal.jsonl`, `handoff/logs/kalibrasi-<tanggal>.txt` | `handoff/STRUCTURE.md` (atau `docs/STRUCTURE.md`), `handoff/calibration/`, `handoff/logs/provenance.jsonl`, `handoff/logs/calibration-<tanggal>.txt` |
| `catat.py --tambah`, `--hasil`, `--timpa` | `record.py --append`, `--result`, `--overwrite` |
| `foto_tampilan.py --ukuran`, `--luring`, `--tunggu` | `screenshot.py --sizes`, `--offline`, `--wait` |
| `kalibrasi.py --ganti`, `--arsip`, `--tanpa-arsip`, `--dari-arsip` | `calibrate.py --replace`, `--archive`, `--no-archive`, `--from-archive` |
| `cek_bukti.py --wajib-asal`, `--pada`, `--pada-report` | `check_evidence.py --require-provenance`, `--at`, `--at-report` |

Perubahan lain tanpa penanda baru: jenis penanda `tiada~` di `scripts/check_version.py`.

| ID | Perubahan | File sasaran | Cara patch | Persetujuan |
|---|---|---|---|---|
| N2 | Salinan `cek_bukti.py` berganti nama menjadi `check_evidence.py` | `handoff/tools/` | `git mv` salinan lama ke nama baru supaya tambalan lokal ikut, lalu bandingkan isinya dengan skrip skill (`SKILL.md` §4, jalur upgrade langkah 4) | – |
| N3 | Salinan `catat.py` berganti nama menjadi `record.py` | `handoff/tools/` | seperti N2 | – |
| N4 | Salinan `cek_secret.py` berganti nama menjadi `check_secrets.py` | `handoff/tools/` | seperti N2 | – |
| N5 | Salinan `foto_tampilan.py` berganti nama menjadi `screenshot.py` | `handoff/tools/` | seperti N2 | – |
| N6 | Peta struktur `handoff/STRUKTUR.md` berganti nama menjadi `handoff/STRUCTURE.md` | `handoff/` | `git mv`, lalu perbarui penunjuknya (N9–N11) | – |
| N7 | Peta struktur `docs/STRUKTUR.md` berganti nama menjadi `docs/STRUCTURE.md` | `docs/` | seperti N6 | – |
| N8 | Catatan asal log `handoff/logs/asal.jsonl` berganti nama menjadi `provenance.jsonl` | `handoff/logs/` | `git mv` dalam commit yang sama dengan N2–N4, karena salinan lama hanya membaca nama lama | – |
| N9 | Instruksi head memakai nama baru | instruksi head | Ganti nama lama di perintah dan penunjuk | – |
| N10 | Brief executor memakai nama baru | brief executor | seperti N9 | – |
| N11 | README handoff memakai nama baru | `handoff/README.md` | seperti N9, juga di REPORT_TEMPLATE dan file aturan agen (mis. `CLAUDE.md`, `AGENTS.md`, `.agents/rules/`) | – |

## v3.12.1 (2026-10-29): perbaikan alat sesudah upgrade lapangan v3.12
Berasal dari upgrade robot meja ke v3.12. Empat hal muncul di sana:
- report lama yang mengutip `handoff/logs/asal.jsonl:80` gagal dicek di working tree karena file itu sudah berganti nama;
- `check_secrets.py --staged` melewatkan file yang berganti nama (status R), sehingga file itu harus dipindai manual;
- peringatan "TIDAK di-ignore git" muncul keliru untuk `--secret-file` dari repo lain, karena status ignore dicek di repo tempat skrip dijalankan;
- `--help` beberapa skrip masih menampilkan placeholder berbahasa Indonesia (mis. `--result HASIL`).

Perubahan lain tanpa penanda baru: placeholder `--help` berbahasa Inggris di `record.py`, `screenshot.py`, dan `calibrate.py`.

| ID | Perubahan | File sasaran | Cara patch | Persetujuan |
|---|---|---|---|---|
| N12 | Kutipan report lama ke `asal.jsonl` atau `STRUKTUR.md` dibaca dari nama barunya; kutipan ke salinan alat lama menyebut nama barunya | `handoff/tools/check_evidence.py` | Salin ulang `scripts/check_evidence.py`, setelah dibandingkan dengan salinan project (tambalan lokal dipertahankan) | – |
| N13 | `--staged` menyertakan file yang berganti nama; status ignore file secret dicek di repo file itu | `handoff/tools/check_secrets.py` | Salin ulang `scripts/check_secrets.py`, dengan `SECRET_FILES` project dipertahankan | – |

## Penanda
Format tiap baris: `versi  ID  penanda [|| penanda lain]  [@bila_secret] [@bila_ui] [@bila_orca]`.
- **Jenis penanda:**
  - `head~teks`, `executor~teks`, `dev~teks`: teks ada di instruksi peran itu;
  - `readme~teks`, `roadmap~teks`, `notes~teks`: teks ada di file `handoff/` yang bersangkutan;
  - `file:path~teks`: teks ada di file tertentu;
  - `ada~path`: file itu ada;
  - `tiada~path`: file itu tidak ada; untuk nama lama yang harus sudah diganti (v3.12);
  - `tampak~peran` (`head`/`executor`): tool peran itu tercatat di `handoff/README.md` (baris Head; untuk executor baris Executor dan `Tool`), dan instruksinya ada di folder skill setiap tool yang dikenali: Claude Code → `.claude/skills/*<peran>*/SKILL.md`, Antigravity → `.agents/skills/` (atau `.agent/skills/`, `.agent/workflows/`). Tool lain tidak diperiksa.
- `...~re:pola`: teks dicocokkan sebagai regex (mis. `head~re:drift.{0,60}struktur`), untuk aturan yang sering ditulis dengan kata lain.
- **Cara mencocokkan:** teks dicocokkan tanpa peduli huruf besar-kecil. `||` berarti cukup salah satu. Penanda teks (`head~`, `readme~`, `file:`, dst.) juga dianggap ada bila file sasarannya memuat tag `<!-- aw: ID -->` dengan ID penanda itu.
- **`@bila_secret`:** penanda itu hanya berlaku bila project punya file secret lokal.
- **`@bila_ui`:** penanda itu hanya berlaku bila project punya antarmuka pengguna: framework UI di `package.json` (React, Vue, Svelte, Angular, Next, Vite, Electron, React Native, …), Flutter, atau file khas UI (`*.html`, `*.vue`, `*.svelte`, `*.jsx`, `*.tsx`, `*.xaml`, `*.storyboard`, `*.qml`, `AndroidManifest.xml`) di luar `handoff/` dan folder hasil build.
- **`@bila_orca`:** penanda itu hanya berlaku bila protokol mencatat bahwa head menjalankan executor lewat Orca, yaitu bila `handoff/README.md` atau instruksi head menyebut kata `Orca`. Project yang baru akan memakai Orca belum mendapat kandidat ini dari `check_version.py`; AUDIT menanyakannya di putaran tanya (SKILL.md §2), lalu memasang D4–D6.

```penanda
2.1  B1    ada~handoff/ROADMAP.md || ada~ROADMAP.md
2.1  B2    head~gerbang arah || dev~gerbang arah
2.1  B3    readme~SPIKE
2.1  B4    file:handoff/reports/REPORT_TEMPLATE.md~Hipotesis & Usulan
2.1  B5    readme~Profil Executor
3    V3-1  head~Integritas bukti || head~OK tanpa bukti yang cocok || head~re:OK.{0,80}nilai harapan
3    V3-2  readme~hanya bila nilai teramati memenuhi nilai harapan || readme~re:OK.{0,40}nilai harapan
3    V3-3  executor~secret
3    V3-4  readme~Syarat naik
3    V3-5  readme~fungsi + file:baris
3    V3-6  head~prioritas baru || dev~prioritas baru
3.1  S1    ada~handoff/STRUKTUR.md || readme~## Struktur || notes~peta struktur || ada~docs/STRUKTUR.md || ada~handoff/STRUCTURE.md || ada~docs/STRUCTURE.md
3.1  S2    readme~| STRUKTUR |
3.1  S3    executor~Letak file mengikuti || executor~memindah/menghapus file || executor~STRUKTUR.md || readme~STRUKTUR.md || executor~STRUCTURE.md || readme~STRUCTURE.md
3.1  S4    head~Mutu keputusan || dev~Mutu keputusan
3.1  S5    head~Drift struktur || head~re:drift.{0,60}struktur
3.1  S6    file:handoff/STRUKTUR.md~10 MB || readme~10 MB || file:handoff/STRUCTURE.md~10 MB
3.2  C1    ada~handoff/tools/cek_secret.py || ada~handoff/tools/check_secrets.py  @bila_secret
3.2  C2    head~cek_secret.py --staged || dev~cek_secret.py --staged || head~check_secrets.py --staged || dev~check_secrets.py --staged  @bila_secret
3.2  C3    executor~cek_secret || executor~check_secrets  @bila_secret
3.3  U1    readme~agent-workflow v || dev~agent-workflow v
3.4  M1    readme~per model
3.4  M2    executor~tidak diketahui || executor~jangan menebak
3.4  M3    file:handoff/PROMPT_EXECUTOR.md~Model:
3.4  M4    head~tidak diketahui
3.4  G1    head~git diff --cached --name-only
3.5  R1    head~skrip penilai
3.5  R2    executor~jangan menghitung
3.5  R3    head~8 langkah
3.5  A1    readme~kalibrasi
3.5  D1    head~Triase head: lolos
3.5  D2    readme~Memakai:
3.5  D3    executor~Triase head: lolos
3.5  E1    head~re:sesi head.{0,40}tidak dihitung
3.5  E2    executor~effort
3.5  E3    readme~berformat SEDANG
3.6  P1    file:handoff/README.md~cek_bukti.py || file:handoff/README.md~check_evidence.py
3.6  P2    executor~cek_bukti || executor~check_evidence
3.6  P3    head~cek_bukti || head~check_evidence
3.6  P4    file:handoff/reports/REPORT_TEMPLATE.md~| Harapan | Teramati |
3.6  F1    head~test acceptance yang bisa dijalankan
3.6  F2    executor~re:test acceptance.{0,40}(sampai lulus|persis)
3.6  H1    executor~satu task per sesi
3.6  Q1    readme~Kebiasaan gagal
3.7  W1    executor~Periksa diri
3.7  W2    file:handoff/reports/REPORT_TEMPLATE.md~Periksa Diri
3.7  L1    readme~| FAKTA | Daftar pertanyaan
3.7  L2    head~task FAKTA
3.7  L3    executor~task FAKTA
3.8  N1    readme~jenis sesi
3.8  O1    file:handoff/STRUKTUR.md~Berubah Sendiri || readme~Berubah Sendiri || file:handoff/STRUCTURE.md~Berubah Sendiri
3.8  O2    executor~Berubah Sendiri
3.8  J1    readme~dicek jalan || executor~dicek jalan
3.8  J2    head~dijalankan sekali
3.8  K1    tampak~head
3.8  K2    tampak~executor
3.9  X1    readme~OK palsu
3.9  X2    readme~Syarat naik, semua tingkat
3.9  Y1    ada~handoff/tools/catat.py || ada~handoff/tools/record.py
3.9  Y2    file:handoff/tools/cek_bukti.py~def cek_asal || file:handoff/tools/check_evidence.py~def cek_asal
3.9  Y3    executor~TIDAK DIUJI sampai user menjawab
3.9  Y4    readme~bernomor K1
3.9.1 C4   file:handoff/tools/cek_secret.py~def perbarui_asal || file:handoff/tools/check_secrets.py~def perbarui_asal  @bila_secret
3.9.2 Y5   file:handoff/tools/cek_bukti.py~STATUS_GIT || file:handoff/tools/check_evidence.py~STATUS_GIT
3.10 I1    head~ukuran layar sasaran  @bila_ui
3.10 I2    executor~tangkapan layar  @bila_ui
3.10 I3    readme~Cek tampilan  @bila_ui
3.10 F3    head~implementasi rujukan
3.10 Z1    executor~milik sesi lain
3.10 Z2    file:handoff/tools/catat.py~--timpa || file:handoff/tools/record.py~--overwrite
3.10 Y6    file:handoff/tools/catat.py~def daftar_hasil || file:handoff/tools/record.py~def daftar_hasil
3.10 Y7    file:handoff/tools/cek_bukti.py~def glob_rx || file:handoff/tools/check_evidence.py~def glob_rx
3.10.1 I4  ada~handoff/tools/foto_tampilan.py || ada~handoff/tools/screenshot.py  @bila_ui
3.10.2 I5  file:handoff/tools/foto_tampilan.py~def buka_halaman || file:handoff/tools/screenshot.py~def buka_halaman  @bila_ui
3.11 M5    head~Pilihan model per task
3.11 M6    readme~Urutan pilihan model
3.11 D4    head~worker-start  @bila_orca
3.11 D5    executor~worker_done  @bila_orca
3.11 D6    readme~Izin agen di Orca  @bila_orca
3.12 N2    tiada~handoff/tools/cek_bukti.py
3.12 N3    tiada~handoff/tools/catat.py
3.12 N4    tiada~handoff/tools/cek_secret.py
3.12 N5    tiada~handoff/tools/foto_tampilan.py
3.12 N6    tiada~handoff/STRUKTUR.md
3.12 N7    tiada~docs/STRUKTUR.md
3.12 N8    tiada~handoff/logs/asal.jsonl
3.12 N9    head~check_evidence
3.12 N10   executor~check_evidence
3.12 N11   readme~check_evidence
3.12.1 N12 file:handoff/tools/check_evidence.py~NAMA_V312
3.12.1 N13 file:handoff/tools/check_secrets.py~--diff-filter=ACMR  @bila_secret
```
