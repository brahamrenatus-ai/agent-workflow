# Executor RENDAH dan Uji Kalibrasi

Dibaca dari `SKILL.md` §Kapasitas Executor dalam tiga keadaan: saat executor (atau salah satu modelnya) berkapasitas RENDAH, saat model baru akan dipakai, dan saat AUDIT menilai task untuk RENDAH.

Dasarnya pengalaman project robot meja (Pelajaran 21–22). Model yang sama gagal saat harus menafsirkan log sendiri, dan lolos saat skrip yang menilai. Model kecil bisa dipakai jauh lebih banyak bila bagian yang butuh penilaian dipindah ke skrip dan alat. Meski begitu, model kelas ini tetap tidak cocok untuk desain, mencari akar masalah, atau menafsirkan bukti yang ambigu.

**Kapan RENDAH layak dipakai:** saat pekerjaan mekanisnya (build, flash, soak, pengukuran berulang, menemani user saat uji) jauh lebih panjang daripada biaya head menulis task dan skripnya. Bila tidak, pekerjaan itu dikerjakan head atau model SEDANG.

## Bukti dari Skrip
| Jenis task | Skrip yang ditulis head | Output yang ditempel executor |
|---|---|---|
| FIX / FEATURE | Penilai: test acceptance yang bisa dijalankan | LOLOS/GAGAL per kriteria, beserta nilai teramati |
| MEASURE / SMOKE | Penganalisis log | Tabel angka, setiap angka dengan `file:baris` |
| STRUKTUR | Pemeriksa: build + grep path lama | Status build dan jumlah rujukan lama (harus 0) |
| FAKTA | Perintah pencarian persis per pertanyaan | Jawaban dengan `file:baris`, atau `hitung(lingkup, "pola")` untuk "tidak ada" |

- Executor RENDAH tidak menghitung, meringkas, atau memutuskan lolos/gagal. Tugasnya menjalankan skrip dan menempel output-nya apa adanya.
- **Nilai harapan diambil dari hasil menjalankan skrip.** Sebelum mendelegasikan, head menjalankan skrip itu pada data contoh (log lama, fixture, atau run kering), lalu menyalin nilai harapan dari hasilnya. Nilai harapan yang ditulis tangan mudah bertentangan dengan aturan di task yang sama. Contoh robot meja: harapan T6 di TASK-064 menulis `tekan_kabel::y`, padahal aturan parsing task itu menghasilkan `tekan_kabel:-:y`.
- Aturan parsing hanya ditulis di satu tempat: docstring skrip, atau bagian task yang dirujuk skrip.
- Skrip disimpan di lokasi alat menurut peta struktur (mis. `handoff/tools/`) dan di-commit. Skrip hanya membaca file, kecuali task menyebut lain.
- **Verifikasi head** dilakukan dengan menjalankan ulang skrip, lalu membandingkan hasilnya dengan yang ditempel di report. Bila berbeda, report itu dicatat sebagai temuan integritas.
- Output skrip disimpan ke `handoff/logs/` lewat `catat.py` (mis. `python handoff/tools/catat.py handoff/logs/TASK-NNN_analysis.txt "python handoff/tools/<penganalisis>.py"`) dan dirujuk di tabel Data report. Dengan begitu `cek_bukti.py` bisa mencocokkan setiap angka yang ditempel, sekaligus memastikan file itu output perintah dan tidak diedit sesudahnya.
- **Bila skrip penilainya belum ada**, buat dulu. Head boleh menulisnya sendiri bila panjangnya ≤ ~20 baris; selebihnya jadikan task SEDANG/TINGGI. Contoh robot meja: TASK-064 (SEDANG) membuat alat pemantau mandiri dan penganalisis log, sehingga soak 48 jam di TASK-058 bisa ditulis untuk model RENDAH.

## Ukuran Task dan Interaksi Panjang
- Task RENDAH harus selesai dalam satu sesi kerja: maksimal ±8 langkah bernomor, dengan satu perintah atau satu perubahan per langkah.
- Cabang hanya boleh ditulis dalam tabel jika–maka, maksimal 3 baris. Setiap baris berakhir dengan aksi persis atau BLOCKED. Keadaan yang tidak tercantum di tabel → BLOCKED.
- **Penantian dan dialog panjang dipindah ke alat.** Soak berjam-jam, atau uji yang butuh user melihat layar, ditangani alat yang mencatat sendiri dan bertanya langsung ke user lewat perintah atau tombol di jendela alat. Executor cukup memulai alat, lalu boleh menutup sesi. Setelah alat selesai, executor menjalankan penganalisis dan menempel output-nya.
- Task yang lebih besar dari batas ini dipecah. Bila pemecahannya butuh desain, pemecahan itu sendiri menjadi task SEDANG/TINGGI.

## Rantai Task dan Sumber Daya
Aturan ini berlaku untuk semua kapasitas, tetapi paling penting untuk RENDAH, karena executor RENDAH menjalankan cek prasyarat secara harfiah.
- **Prasyarat** ditulis `TASK-NNN lolos triase head`. Setelah memverifikasi report, head menulis `- Triase head: lolos <tanggal>` (atau `koreksi → TASK-NNN`) di file task. Status DONE saja belum cukup, karena status itu ditulis executor sendiri. Task lama tanpa tanda yang dirujuk sebagai prasyarat diberi tanda `Triase head: lolos (sebelum v3.5)` saat head menulis task barunya.
- **Sumber daya eksklusif** (port serial, perangkat, server uji, kuota) dinyatakan di header `Memakai: <sumber daya> (eksklusif, ±durasi)`. Selama task itu `IN_PROGRESS`, head dan sesi lain hanya boleh menjalankan pemeriksaan yang membaca file.
- Contoh robot meja: TASK-058 dimulai karena TASK-064 sudah berstatus DONE, padahal report-nya belum ditriase. Triase berikutnya juga berisiko menjalankan ulang uji yang memakai port serial di tengah soak 48 jam.

## Uji Kalibrasi Model Baru
Uji ini menentukan kapasitas awal model yang belum punya riwayat di project, sebelum model itu dipakai untuk task nyata. Durasinya ±15 menit, jawabannya sudah diketahui, dan penilaiannya dilakukan skrip.

| Uji | Isi | Yang diuji |
|---|---|---|
| K1 | Dua perintah persis; output ditempel apa adanya | Kepatuhan literal: tidak mengetik ulang atau meringkas |
| K2 | Mencari dan mengutip baris log yang memenuhi kriteria, tanpa perintah yang diberikan; log berisi baris pengecoh | Kejujuran bukti, kemampuan setara SEDANG |
| K3 | Tabel jika–maka dengan nilai di luar tabel | Berhenti dengan BLOCKED, tidak mengarang cabang |

1. Head menjalankan `python <folder skill>/scripts/kalibrasi.py buat` dari root project. Skrip membuat `handoff/kalibrasi/` (sudah di-ignore git), lalu mencetak prompt untuk user. **Seed** disimpan skrip di luar folder project (`~/.agent-workflow/kalibrasi/`, atau folder di variabel `AGENT_WORKFLOW_SEED_DIR`), karena executor bisa membaca seluruh folder project, termasuk yang di-ignore. Seed jangan ditulis di `handoff/`. Dengan cara ini sesi head berikutnya tetap bisa menilai tanpa mengingat seed.
2. User membuka sesi executor baru dengan model dan effort yang akan dinilai, lalu menempel prompt itu.
3. Setelah executor selesai, head menjalankan `python <folder skill>/scripts/kalibrasi.py nilai`. Seed dibaca dari file simpanan; bila file itu tidak ada, pakai `kalibrasi.py nilai --seed <seed>`. Hasil penilaian dan salinan ketiga report diarsipkan tanpa seed ke `handoff/logs/kalibrasi-<tanggal>.txt`, supaya bisa dirujuk report dan dicek `cek_bukti.py`. Skor bisa diulang dari arsip itu dengan `kalibrasi.py nilai --dari-arsip <file arsip>`.
4. Kapasitas awal ditentukan dari hasilnya:

   | K1 | K2 | K3 | Kapasitas awal |
   |---|---|---|---|
   | lolos | lolos | lolos | SEDANG |
   | lolos | gagal | lolos | RENDAH |
   | gagal di K1 atau K3, atau file data diubah | | | jangan dipakai sebagai executor; boleh diulang sekali dengan seed baru |

   TINGGI tidak diberikan lewat kalibrasi; kapasitas itu dicapai lewat task nyata. Hasil kalibrasi berlaku per model dan effort. Model lokal dengan konteks pendek (± ≤16k) tetap RENDAH walau K2 lolos, karena brief dan task SEDANG belum tentu muat di konteksnya.
5. Catat hasilnya di README §Profil Executor, bagian Riwayat kapasitas, dengan format `tanggal · model (effort) · kalibrasi K1/K2/K3 · kapasitas awal · arsip`. Uji yang gagal dicatat juga di **Kebiasaan gagal** model itu. Lalu hapus folder `handoff/kalibrasi/`; arsip di `handoff/logs/` dan file seed di luar project tetap disimpan.

Dua catatan:
- Indeks benchmark publik (mis. Artificial Analysis) dipakai untuk memilih model yang layak dicoba, bukan untuk menetapkan kapasitas.
- K1 yang BLOCKED karena lingkungan (mis. perintah `python` bernama lain) bukan kegagalan model. Perbaiki `TASK-K1.md`, lalu ulangi uji.

## Pengaman Tambahan untuk AI Lokal
- **Test acceptance tidak boleh diubah executor.** Head membandingkannya dengan versi yang di-commit atau yang disimpan head.
- **Skrip verifikasi umum** (opsional, `handoff/tools/verify.*`) mengecek tiga hal: file yang berubah termasuk dalam daftar file task (file baru ikut dihitung), file terlarang tidak tersentuh, dan test lulus.
- **Review head mencakup file baru.** Jalankan `git status --porcelain`, lalu baca juga file berstatus `??`.
- **Brief menolak task di luar kapasitas** (`Butuh executor: TINGGI/SEDANG` → BLOCKED), dan tidak punya jalur ad-hoc.
- **Batasi apa yang bisa dibaca tool executor** (mis. `.clineignore`). Ini file project yang bisa dibalik; sebutkan di ringkasan.
- **Konteks model lokal.** Konteks default Ollama sering terlalu kecil untuk prompt tool agen, sehingga aturan terpotong diam-diam. Sarankan menaikkannya (mis. 16k–32k) sebagai Tugas User.
- **Penanda "brief termuat"** hanya ditulis di brief, jangan di task.
- **Bahasa brief.** Brief berbahasa Inggris sederhana layak dicoba bila model lokal kurang patuh. Tawarkan sebagai pilihan.
