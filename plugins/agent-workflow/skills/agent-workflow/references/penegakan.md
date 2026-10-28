# Resep Penegakan per Tool

Skill ini menulis **instruksi**. Untuk operasi berisiko, misalnya push, deploy, flash/OTA, membuka port serial, menjalankan CLI layanan berbayar, atau membaca file secret, tawarkan juga penegakan nyata di tool.

Pasang hanya setelah user setuju, lalu catat di NOTES (register keputusan). Sintaks bisa berubah antar versi, jadi cek dokumentasi tool bila ragu. Penegakan di satu tool tidak berlaku di tool lain; pasang ulang untuk tiap tool.

## Claude Code
**File:**
- `.claude/settings.json` dibagikan ke tim dan ikut di-commit.
- `.claude/settings.local.json` hanya untuk mesin ini dan tidak di-commit.
- `~/.claude/settings.json` berlaku untuk semua project user.
- Aturan yang hanya untuk mesin user ditulis di `.claude/settings.local.json`. Pastikan file itu tidak ter-commit (cek `git check-ignore`). Jangan menaruh aturan lokal di `.claude/settings.json` lalu meng-ignore file itu, karena menurut konvensi `settings.json` adalah file bersama.

**Cara kerja:**
- Urutan evaluasi: **deny → ask → allow**. Aturan pertama yang cocok yang dipakai.
- Perubahan pada file settings yang sudah ada biasanya dimuat ulang tanpa restart. Bila file settings baru dibuat saat sesi berjalan, anggap aturannya baru aktif di sesi berikutnya (teramati di uji lapangan), dan sampaikan itu ke user. Bila ragu, mulai sesi baru, lalu cek `/status`.
- Aturan Bash mencocokkan teks perintah:
  - `*` cocok dengan teks apa pun di posisi mana pun.
  - ` *` di akhir juga cocok dengan perintah tanpa argumen.
  - Aturan PowerShell berbentuk sama, mengenali alias, dan tidak peka huruf besar-kecil.
- Untuk memblokir pembacaan file, pakai aturan `Read` deny. `.claudeignore` tidak berpengaruh.

**Contoh:**
```json
{
  "permissions": {
    "ask": [
      "Bash(git push *)", "PowerShell(git push *)",
      "Bash(./deploy.sh *)", "PowerShell(./deploy.sh *)",
      "Bash(pio run --target upload *)", "PowerShell(pio run --target upload *)"
    ],
    "deny": [
      "Read(./.env)", "Read(./.env.*)", "Read(./secrets/**)"
    ]
  }
}
```

**Keterbatasan:** aturan hanya mencocokkan teks. `Bash(git push *)` tidak menangkap `git -C . push`, dan `./deploy.sh` tidak sama dengan `bash deploy.sh`. Untuk larangan yang harus kedap, tambahkan hook PreToolUse atau sandbox.

## Antigravity
- Atur eksekusi perintah terminal agar selalu meminta persetujuan (jangan auto-run).
- Bila tersedia, isi daftar perintah yang ditolak untuk operasi berisiko.
- Nama menunya bisa berbeda antar versi; cek setelan Antigravity.

## Cline (dan tool sejenis untuk AI lokal)
- Matikan auto-approve untuk menjalankan perintah, dan untuk edit file bila perlu.
- Pakai `.clineignore` untuk menyembunyikan secret, data produksi, dan skrip berbahaya dari model.

## Git
- **Hook pre-commit:** tolak commit bila file yang di-stage mengandung pola secret (kunci, token, PIN) atau mengubah file terlarang. Hook yang sama bisa menolak file > ±10 MB di luar daftar izin, file yang memuat nilai dari file secret lokal (dibandingkan tanpa dicetak), dan file yang cocok dengan pola Tidak Masuk Git di peta struktur.
  Contoh paling sederhana memakai `handoff/tools/cek_secret.py`. Hook ini berlaku untuk semua tool yang meng-commit, termasuk executor:
  ```sh
  #!/bin/sh
  # .githooks/pre-commit
  python handoff/tools/cek_secret.py --staged || { echo "Commit ditolak: ada secret. Samarkan dengan --redact, lalu git add ulang."; exit 1; }
  for f in $(git diff --cached --name-only --diff-filter=AM -- 'handoff/reports/REPORT-*.md'); do
    python handoff/tools/cek_bukti.py "$f" || { echo "Commit ditolak: bukti di $f belum cocok dengan log."; exit 1; }
  done
  ```
  Baris `cek_bukti` membuat report baru atau yang diubah tidak bisa di-commit selama buktinya tidak cocok. Report lama yang tidak di-stage tidak ikut dicek.
- **Hook commit-msg:** commit berlabel handoff hanya boleh berisi file protokol. Sesuaikan awalan pesan dengan konvensi project (mis. `handoff:` atau `docs(handoff):`):
  ```sh
  #!/bin/sh
  # .githooks/commit-msg
  if head -1 "$1" | grep -q -E '^(handoff:|docs\(handoff\))'; then
    lain=$(git diff --cached --name-only | grep -v -E '^(handoff/|\.agents/|\.claude/)')
    [ -n "$lain" ] && { echo "Commit handoff berisi file non-protokol:"; echo "$lain"; exit 1; }
  fi
  exit 0
  ```
- **Berbagi hook:** simpan di folder ter-commit (mis. `.githooks/`), lalu jalankan `git config core.hooksPath .githooks`.
- **Secret yang sudah terlanjur masuk riwayat git:** penegakan tidak bisa menghapusnya. Buat Tugas User untuk mengganti kuncinya.
