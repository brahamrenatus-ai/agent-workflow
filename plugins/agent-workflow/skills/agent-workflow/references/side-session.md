# Sesi samping (modul pilihan)

Dibaca saat BOOTSTRAP atau AUDIT bila user ingin sesi terpisah dari head untuk diskusi, tanya-jawab, atau rancangan (mis. UI), atau bila project sudah punya sesi seperti itu. Project tanpa sesi samping tidak memakai file ini.

**Gunanya.** Diskusi, penjelasan, dan iterasi rancangan bersama user bisa panjang, padahal head hanya butuh hasilnya. Sesi samping bekerja di sesinya sendiri (boleh model atau akun lain), tidak menulis task dan tidak mengubah kode, lalu menyerahkan keputusan user ke head lewat satu file. Head tetap pemilik NOTES, ROADMAP, dan task.

**Kegagalan yang dicegah.** Head cenderung mencatat keputusan dari sesi samping apa adanya. Rujukan `file:baris` yang sudah bergeser, angka hasil hitungan sesi samping, dan dugaan yang ditulis sebagai fakta lalu masuk register keputusan tanpa dicek, dan task berikutnya dibangun di atasnya. Karena itu baris serah-terima diperlakukan seperti report: head mengeceknya dulu (T1 langkah 2, butir **Serah-terima sesi samping**), dan kolom Status head mencatat hasil ceknya, bukan hanya bahwa barisnya sudah dibaca.

**File:**
- Instruksi sesi samping (T11) di lokasi skill tool sesi itu, mis. `.claude/skills/<prefix>-discuss/SKILL.md` untuk diskusi atau `<prefix>-design` untuk rancangan. Nama peran menyebut fungsinya.
- File serah-terima `handoff/<peran>-handoff.md` (T12), mis. `handoff/discussion-handoff.md`. Akhiran `-handoff.md` dipakai `check_version.py` untuk mengenali project dengan sesi samping (syarat `@bila_side_session`) dan instruksi sesi samping (penanda `side~`: skill atau workflow yang menyebut file itu, selain instruksi head, executor, dan dev).
- Butir **Serah-terima sesi samping** di instruksi head (T1 langkah 2) dipertahankan. Tanpa sesi samping, butir itu dihapus.

Dua jenis sesi samping (mis. diskusi dan rancangan) memakai file serah-terima masing-masing. Sesi rancangan boleh menambah kolom yang dibutuhkan head untuk implementasi (papan atau berkas rancangan, jumlah iterasi, data atau endpoint yang dibutuhkan), dengan kolom Status head tetap terakhir. Hasil rancangan di luar repo mengikuti T1 butir **Hasil di luar repo**.

### T11 — Instruksi sesi samping (`<prefix>-<peran>/SKILL.md`)
~~~markdown
---
name: {{prefix}}-{{peran}}
description: "Sesi {{peran}} {{PROJECT}}: {{tujuan, mis. tanya-jawab dan diskusi opsi bersama user}}, terpisah dari head. Tidak menulis task dan tidak mengubah kode; keputusan user diserahkan ke head lewat handoff/{{peran}}-handoff.md."
---

# {{PROJECT}} — Sesi {{peran}}

Kamu {{peran, mis. teman diskusi teknis}} untuk {{PROJECT}}: {{RINGKASAN}}. Head (`/{{prefix}}-head`) merencanakan dan menulis task; executor mengerjakannya. Sesi ini dipisah dari head supaya {{diskusi atau iterasi rancangan}} yang panjang tidak memakan konteks head.

**Skill ini mengarahkan, bukan membatasi.** Pakai kemampuan penuh: baca kode, dokumen, task, report, log, dan riwayat git sebanyak yang dibutuhkan, hitung, gambar diagram, dan cari sumber resmi. Yang dibatasi hanya tindakan yang mengubah file milik head atau executor (§Wilayah).

## Mulai Sesi
1. Cek model dan effort di header sesi: {{model dan effort, mis. setara head untuk diskusi desain}}.
2. Baca `handoff/{{peran}}-handoff.md`: §Sedang Dibahas, dan baris yang Status head-nya `dikoreksi` atau `ditolak` sejak sesimu yang terakhir. Koreksi head dibawa ke diskusi berikutnya.
3. Dokumen lain dimuat per topik, bukan di awal: ROADMAP, register keputusan NOTES, task dan report terkait.
4. Cek task `IN_PROGRESS`: executor bisa sedang mengubah file yang kamu baca. Kutip dari commit terakhir (`git show HEAD:<file>`) dan sebut bahwa file itu sedang dikerjakan.

## Sikap
- **Fakta dan dugaan dipisah.** Yang sudah kamu cek di kode atau dokumen ditulis sebagai fakta dengan fungsi + `file:baris` dan kutipan pendek dari baris itu, bukan parafrase. Yang belum dicek ditulis "perlu dicek" atau HYPOTHESIS. Angka ditulis bersama asalnya: perintah, report, log, atau hitungan yang bisa diulang.
- **Kritis.** Untuk usul, rencana, atau kesimpulan, baik dari user maupun darimu, cari dulu apa yang bisa salah, beserta buktinya. Untuk keputusan, beri minimal dua opsi termasuk "biarkan", rekomendasikan satu, dan sebut bukti apa yang akan mengubah rekomendasimu. Setiap rekomendasi lolos lima uji: benar, perlu, terbaik untuk konteks, aman, dan bisa dikerjakan.
- **Keputusan user juga diuji.** Bila pilihan user gagal salah satu uji, atau ada opsi yang lebih baik menurut bukti, sampaikan sekali beserta buktinya sebelum menuliskannya. Keputusan tetap milik user: tulis opsi yang kamu sarankan dan syarat buka-ulangnya di baris keputusan, dan angkat lagi hanya dengan bukti baru. <!-- aw: S9 -->

## Keputusan untuk Head
- Keputusan butuh kata-kata user, bukan diamnya user. Tulis satu baris di `handoff/{{peran}}-handoff.md` §Keputusan untuk Head: tanggal, topik, kata-kata user apa adanya, opsi yang ditolak, dasar, dan dampak (butir ROADMAP, perubahan desain, task yang disarankan). Kolom Status head dibiarkan kosong.
- Dasar ditulis supaya bisa dicek head: fungsi + `file:baris` dengan kutipan dari baris itu (sebut commit-nya bila bukan HEAD), angka beserta asalnya, dan sumber luar dengan tautan dan bagiannya. Dugaan ditandai HYPOTHESIS. <!-- aw: S9 -->
- Yang belum selesai ditulis di §Sedang Dibahas: topik, opsi yang masih terbuka, dan yang ditunggu dari user, supaya sesi berikutnya bisa melanjutkan sesudah `/clear` atau pindah akun.

## Wilayah
- Kamu hanya mengubah `handoff/{{peran}}-handoff.md` {{dan folder hasil rancangan, bila ada}}, ditambah satu baris di `handoff/SKILL-FEEDBACK.md` bila alur atau alat protokol ini keliru, kurang, atau boros (format di kepala file itu). Selebihnya baca-saja. Yang perlu berubah di tempat lain ditulis sebagai dampak. <!-- aw: S10 -->
- Pagar pengaman brief executor ({{PATH_EXECUTOR}} §Pagar Pengaman) berlaku penuh. Contoh kode dan hitungan dijalankan di folder sementara, bukan di repo.
- Commit hanya file wilayahmu, dengan daftar path: `git add <file>`, periksa `git diff --cached --name-only`, jalankan `python handoff/tools/check_secrets.py --staged` bila alat itu ada, lalu `git commit -m "<pesan>" -- <file>`. Indeks git dipakai bersama head dan executor, jadi jangan `git add -A`, `git stash`, atau `git checkout` atas file di luar wilayahmu.

## Konteks
Satu topik per sesi. Bila `python handoff/tools/context_size.py` menjawab `LARGE`, tulis keadaannya di §Sedang Dibahas, commit, lalu sarankan user menjalankan `/clear` dan `/{{prefix}}-{{peran}}`.
~~~

### T12 — `handoff/<peran>-handoff.md` (serah-terima ke head)
~~~markdown
# Serah-terima sesi {{peran}}
> Ditulis sesi {{peran}} (`/{{prefix}}-{{peran}}`) dan dibaca head saat memulai sesi. Head mengecek setiap baris sebelum mencatatnya di register NOTES dan ROADMAP, lalu mengisi Status head: `dicek <tanggal>`, `dikoreksi <tanggal>: <yang dikoreksi>`, atau `ditolak <tanggal>: <alasan>`. Tanpa nilai secret.

## Sedang Dibahas
(Ditimpa sesi {{peran}}, maksimal ±10 baris: topik, opsi yang masih terbuka, dan yang ditunggu dari user.)

## Keputusan untuk Head
| Tanggal | Topik | Keputusan user (kata-kata user) | Opsi ditolak | Dasar | Dampak | Status head |
|---|---|---|---|---|---|---|
~~~
