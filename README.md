# TrialFlow 2.0 — Dynamic Multi-Gmail & Multi-Application Automation

Aplikasi lokal untuk satu pemilik dengan banyak akun Gmail dan banyak konfigurasi aplikasi. FastAPI + Playwright + Gmail API read-only + SQLite + Fernet. Dashboard berbahasa Indonesia.

## Yang sudah diimplementasikan

- Gmail Manager: tambah akun lewat Google OAuth dari dashboard, daftar akun, cek akses langsung, pilih akun, hapus token lokal, dan random selection dari akun yang lolos pemeriksaan API.
- Application Manager: tambah nama + URL sebagai draft, baca/edit konfigurasi JSON dari dashboard, validasi adapter, hapus aplikasi custom tanpa riwayat. Tidak perlu mengubah source untuk menambah workflow yang sesuai interpreter.
- Worker registrasi, email verification (OTP/link), pengecekan eligibility, aktivasi tanpa pembayaran, validator keberhasilan, status dan activity log.
- Token OAuth dan password aplikasi terenkripsi. OAuth menggunakan PKCE, state kedaluwarsa 10 menit dan hanya dapat dipakai sekali. Scope hanya `gmail.readonly`.
- Pencegahan klaim ulang lintas Gmail untuk layanan yang sama; tidak ada rotasi email saat eligibility gagal.

**Batas status implementasi:** komponen backend dan dashboard nyata, bukan simulasi. Namun belum ada adapter trial produksi yang diaktifkan. Nama + URL membuat draft; bukan penemuan otomatis selector, izin automation, atau eligibility. Empat preset terkenal disertakan dengan alasan berhenti, bukan klaim dukungan aktivasi nyata.

## Instalasi baru

Python 3.11+; jalankan dari folder `trialflow` setelah mengekstrak ZIP.

```bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell sebagai alternatif:
# .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
python setup_local.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Buka **http://127.0.0.1:8000**. Masukkan `APP_TOKEN` dari `.env`. Token hanya ada di memori tab. Baca `.env` secara lokal; jangan kirim isinya ke chat.

Linux yang belum punya library browser: `python -m playwright install --with-deps chromium`. Browser default terlihat (`HEADLESS=false`). Untuk server tanpa desktop set `HEADLESS=true` di `.env`. Jika Chromium sudah terpasang, opsional set `BROWSER_EXECUTABLE=/path/to/chromium`.

**Satu proses server saja**, tanpa `--workers` dan tanpa `--reload` untuk job nyata. Maksimal 3 job bersamaan. Ini aplikasi lokal, belum didesain untuk hosting publik/multi-user. Bind tetap 127.0.0.1. Worker membutuhkan runtime Python/browser; dashboard saja tidak cukup di-deploy ke static hosting.

### Upgrade dari versi pertama

Backup `.env`, `credentials.json` dan folder `data` secara aman. Ganti source, pertahankan ketiga item tersebut, lalu install requirements lagi. Jangan menjalankan ulang `setup_local.py` atau mengganti master key. Tabel baru dibuat otomatis tanpa menghapus history. Job lama diimpor menjadi reservation bila konfigurasi aplikasinya masih tersedia; job running/queued ditandai interrupted dan tidak diulang.

Tambahkan `OAUTH_REDIRECT_URI=http://127.0.0.1:8000/oauth/callback` ke `.env` lama bila diperlukan. Nilai ini sudah menjadi default. Setelah upgrade, akun Gmail yang pernah tersambung akan tampil dari secret registry lama.

## Menghubungkan banyak Gmail

1. Di Google Cloud milik Anda, aktifkan Gmail API dan konfigurasi OAuth consent screen. Untuk mode Testing, tambahkan semua Gmail milik Anda yang akan dipakai sebagai test users.
2. Buat OAuth client **Desktop app**, simpan file unduhan sebagai `credentials.json` di root proyek. File ini tidak disertakan dalam ZIP. Desktop client memakai loopback redirect. Jika memakai client **Web application**, daftarkan redirect persis `http://127.0.0.1:8000/oauth/callback` di Google Cloud.
3. Jalankan server. Di Gmail Manager klik **Hubungkan Gmail**, pilih akun pada halaman resmi Google, dan beri izin baca Gmail. Setelah halaman menampilkan berhasil, tutup tab itu lalu klik **Refresh Gmail**.
4. Ulangi untuk setiap Gmail milik sendiri. Tidak perlu menghentikan server. Tidak ada pembuatan email baru.
5. Klik **Periksa** untuk mengecek identitas OAuth dan akses endpoint daftar pesan. Status dapat berubah setelah pengecekan jika token dicabut, jaringan putus, atau Google meminta autentikasi ulang.

Jangan login menggunakan password Google di dashboard. Persetujuan hanya dilakukan di domain resmi Google. Aplikasi tidak mengubah recovery email, password, pengaturan keamanan, atau mengirim/menghapus pesan.

Jika popup diblokir, dashboard menampilkan tautan otorisasi. Flow OAuth pending disimpan di memori; jika server restart, mulai OAuth lagi. Jangan membagikan URL callback. Default access log dimatikan; aplikasi juga meredaksi query callback pada logger Uvicorn standar.

Alternatif CLI tetap tersedia: `python connect_gmail.py` pada komputer lokal, kemudian Refresh Gmail. CLI memakai OAuth Desktop dengan callback port acak. Untuk OAuth Web client, gunakan tombol dashboard dan redirect terdaftar.

**Hapus koneksi** menghapus token lokal saja dan ditolak jika akun sedang digunakan job. Riwayat tidak dihapus. Jika ingin mencabut akses di Google, lakukan di pengaturan keamanan akun Google. Refresh token terenkripsi dan diperbarui otomatis bila memungkinkan; Google dapat mencabut/mengakhiri akses, jadi koneksi sekali tidak dijanjikan berlaku selamanya.

Pemeriksaan API membuktikan akses saat itu, bukan jaminan semua platform menerima email atau mengirim OTP. Random selection hanya memilih di antara akun yang dapat diakses, bukan mencari akun untuk menghindari batas trial.

## Menambahkan aplikasi secara dinamis

1. Application Manager → isi nama, ID unik (huruf kecil/angka/tanda hubung/underscore), URL HTTPS resmi → Tambah.
2. Aplikasi menjadi **draft/stopped**. Klik Edit adapter untuk melengkapi JSON berdasarkan alur resmi platform.
3. Cantumkan bukti izin automation, tanggal peninjauan dan alasan. Jika kebijakan melarang atau belum diketahui, pertahankan `policy.automation:forbidden` atau `unknown`. Jangan mengganti menjadi allowed hanya karena ingin proses berjalan.
4. Setelah seluruh alur ditinjau, set `reviewed:true`, `policy.automation:allowed`, sumber kebijakan resmi, tanggal ISO dan alasan. Review kedaluwarsa setelah 30 hari; tanggal mendatang ditolak.
5. Simpan. Validator menolak workflow yang tidak lengkap; dashboard menampilkan alasannya. Aplikasi custom dapat dihapus sebelum punya job. Aplikasi dengan riwayat tidak bisa diubah/dihapus agar audit dan scope trial tetap konsisten. Preset bawaan tidak bisa dihapus.

Nama dan URL **tidak otomatis membuat adapter berfungsi**. Selector dan ketentuan berbeda pada setiap aplikasi. Menambah tipe interaksi baru di luar fill/click/check/wait (misalnya registrasi native mobile) memerlukan pengembangan engine, bukan hanya JSON.

### Kontrak adapter

`adapters/example.json` adalah template konfigurasi lengkap, sengaja nonaktif. Konfigurasi dashboard disimpan di SQLite dan mengambil prioritas atas file ber-ID sama. Setiap aplikasi memiliki dokumen adapter terpisah.

| Handler | Field konfigurasi |
|---|---|
| URL dan izin | `signup_url`, `trial_url`, `terms_url`, `policy` |
| Registrasi | `registration`: langkah fill/click/check/wait, `registration_success` |
| Verifikasi email | `senders`, `subject_pattern`, `verification_hosts`, `verification_mode`, `otp_pattern`, `otp_steps`, `verification_success` |
| Eligibility | `eligibility_url`, `eligibility_timing`, `eligibility_selector`, `ineligible_selector`, `ineligible_reason` |
| Aktivasi | `activation`, `trial_evidence`, `no_payment_required` |
| Validasi hasil | `trial_success`, `duration` |
| Error/guard | `block_selectors`, `allowed_hosts`; alasan ineligible dan log jenis kegagalan |

- Semua URL target harus HTTPS publik pada port standar; hostname harus ada di `allowed_hosts`. Host aset/API/SSO yang diperlukan harus ditinjau dan ditambahkan secara eksplisit. Permintaan HTTP(S) ke host lain diblokir. Tidak mendukung target jaringan privat. Jangan mengizinkan domain yang tidak dipercaya.
- Setiap click/check harus `reviewed_safe:true` setelah meninjau konsekuensi tombol. Tidak ada aksi execute-JavaScript arbitrer dari konfigurasi.
- Mode verifikasi `link` menggunakan satu URL HTTPS host yang diizinkan dan tidak ambigu. Beberapa link berbeda memerlukan penanganan manual. Mode `otp` memakai capture group pertama `otp_pattern` dan langkah `otp_steps`.
- Gmail yang dibaca selalu Gmail terpilih untuk job. Pesan wajib cocok pada pengirim persis, penerima, pola subjek dan waktu sesudah pendaftaran. Tidak ada fallback ke inbox lain. Matching ini bukan autentikasi kriptografis pengirim.
- `eligibility_timing:before_registration` memeriksa indikator sebelum membuat akun. Jika platform hanya bisa menentukan eligibility setelah login, pilih `after_verification`; sistem menjelaskan hal ini di log dan memeriksa sebelum aktivasi. Jangan mengklaim eligibility akun sudah dipastikan sebelum platform memberikannya.
- Indikator `ineligible_selector` menghentikan dengan status `ineligible` beserta alasan. Jika indikator kelayakan tidak bisa dipastikan, status `manual_required`. Selector tidak menggantikan ketentuan resmi; harus sesuai penawaran yang benar-benar terlihat pada akun.
- `no_payment_required:true` hanya untuk alur yang benar-benar bebas pembayaran dan komitmen langganan berbayar. Jika false atau hilang, aktivasi otomatis berhenti. Tidak ada tombol auto-approve pembayaran/berlangganan.
- Isi `block_selectors` untuk CAPTCHA, pembayaran, consent sensitif dan kendala spesifik platform. Guard bukan pendeteksi universal semua desain web; adapter perlu diuji/diperbarui ketika situs berubah.
- `duration` adalah metadata penawaran yang ditinjau, bukan hasil deteksi universal. `activated` adalah waktu konfirmasi sistem; bukan tanggal billing otoritatif.

## Preset aplikasi dan alasan berhenti

| Aplikasi | Status bawaan | Alasan |
|---|---|---|
| CapCut | Forbidden | Terms resmi melarang skrip otomatis berinteraksi dengan layanan. |
| Alight Motion | Manual/review required | Langganan dikelola dalam aplikasi melalui Google Play/App Store; engine web ini tidak mengelola alur native store. |
| ChatGPT | Review required | Tidak mengasumsikan trial universal. Promosi bergantung undangan, kampanye dan eligibility akun; belum ada adapter produksi yang ditinjau. |
| Canva | Review required | Izin automation dan eligibility spesifik akun belum dikonfirmasi; belum ada adapter produksi yang ditinjau. |

Sumber resmi yang ditinjau pada 30 Oktober 2026:

- CapCut: https://www.capcut.com/clause/terms-of-service
- Alight Motion: https://support.alightmotion.com/hc/en-us/articles/10537456625681-How-do-I-subscribe-to-Alight-Motion
- ChatGPT: https://help.openai.com/en/articles/8381046-chatgpt-promotional-subscriptionsfree-trial-invites-faq
- Canva (rujukan untuk review lanjutan; belum dikonfirmasi): https://www.canva.com/policies/terms-of-use/

Tidak ada bukti bahwa keempatnya dapat diklaim otomatis dengan sistem ini. Preset memberikan status dan alasan yang jujur. Sistem tidak mencoba situs yang belum diizinkan.

## Menjalankan proses

Pilih aplikasi dengan adapter enabled → pilih Gmail atau klik Pilih Gmail acak → masukkan nama asli dan password akun aplikasi → baca ketentuan → konfirmasi eligibility dan persetujuan → Mulai proses.

Gmail dicek lagi sebelum job dibuat. Data dan konfigurasi dipisahkan per job. Backend juga mendukung random saat start melalui `random_selection:true` tanpa `email`, tetapi tombol dashboard memilih acak terlebih dahulu agar alamatnya dapat dilihat sebelum mulai.

Status: queued → running → completed / ineligible / manual_required / failed / interrupted. completed hanya sesudah indikator trial aktif terdeteksi. Monitor polling 2 detik, log berisi timestamp. Notifikasi berupa pesan di dashboard selama tab terbuka; tidak ada WhatsApp/email/push eksternal.

CAPTCHA, pembayaran atau consent sensitif menutup browser dan menghentikan worker. Selesaikan alur resmi secara manual jika diperlukan; tidak ada bypass atau resume otomatis. Job parsial perlu pemeriksaan manual, bukan retry.

### Batas satu pemilik dan klaim ulang

Reservation SQLite dibuat atomik bersama job dan password terenkripsi, sebelum browser dijalankan. Satu pemilik hanya memiliki satu percobaan per hostname layanan, meskipun menggunakan Gmail atau ID adapter berbeda. Alias domain untuk empat layanan preset dikelompokkan. Reservation bertahan setelah job gagal atau Gmail dilepas. Tidak ada reset eligibility otomatis dan tidak ada pemilihan Gmail baru saat gagal.

Untuk layanan custom, hostname berbeda tidak otomatis diketahui sebagai produk yang sama. Jangan membuat alias adapter untuk mengulang trial. Penegakan otoritatif eligibility tetap milik platform; sistem lokal ini bukan sistem identitas/anti-fraud lintas seluruh internet.

## API lokal

Semua `/api/*` membutuhkan header `Authorization: Bearer APP_TOKEN`.

| Endpoint | Fungsi |
|---|---|
| GET `/api/emails` | Daftar akun terhubung (tanpa token) |
| POST `/api/oauth/start` | URL otorisasi Google dan state/PKCE internal |
| GET `/oauth/callback` | Callback Google, state sekali pakai, tidak memerlukan token dashboard |
| POST `/api/emails/{email}/check` | Cek identitas dan akses Gmail langsung |
| DELETE `/api/emails/{email}` | Hapus token lokal jika tidak ada job aktif |
| POST `/api/emails/select` | Pilih/check akun, atau `{ "random_selection": true }` |
| GET `/api/adapters` | Aplikasi, status dan alasan |
| POST `/api/applications` | Draft dari `{ "id", "name", "url" }` |
| GET/PUT/DELETE `/api/applications/{id}` | Baca/update `{ "config": {...} }`/hapus custom tanpa riwayat |
| POST `/api/jobs` | Jalankan adapter tervalidasi dan Gmail yang dapat diakses |
| GET `/api/jobs` | Process monitor, history dan activity logs |

Gunakan `/docs` lokal untuk skema request. Akses OAuth memerlukan persetujuan pemilik akun di Google. Tidak ada API yang mengirim email.

## Struktur dan keamanan

```text
app/main.py            API, manager endpoints, lifecycle, auth
app/accounts.py        health checks dan random selection
app/oauth.py           OAuth dashboard, state, PKCE, token terenkripsi
app/adapters.py        registry dan validasi workflow/policy
app/engine.py          worker Playwright dan eligibility handler
app/mail.py            Gmail API, MIME parsing, OTP/link
app/store.py           SQLite, enkripsi dan reservation atomik
app/static/index.html  dashboard dan editor konfigurasi
adapters/*.json        template serta preset per aplikasi
connect_gmail.py       alternatif OAuth Desktop CLI
setup_local.py         generator key dan token lokal
requirements.txt       versi dependencies
.env.example           contoh environment
 tests/                tes modul, manager, OAuth dan browser fixture
```

Dashboard → API autentikasi → worker Playwright → situs resmi; worker membaca mailbox yang sesuai lewat Gmail API dan menulis hasil ke SQLite. Konfigurasi manager di database, fallback preset dari file. Satu konteks browser baru tanpa kartu/cookies tersimpan per job.

`data/trialflow.db` menyimpan token/password terenkripsi dengan Fernet. Email, nama platform, konfigurasi serta activity log tidak terenkripsi. `.env` memuat master key dan token akses; `credentials.json` adalah konfigurasi OAuth lokal. Jangan bagikan file tersebut atau folder data. Batasi akses OS. Simpan backup key terpisah dan aman; key yang hilang tidak dapat memulihkan secret. Token, OTP, password dan verification URL tidak ditulis ke activity log. Jangan menyalakan debug HTTP library untuk alur nyata.

Worker berada dalam proses server, bukan antrean terdistribusi. Restart mengakhiri job dan menandainya interrupted, tidak mengulang. Koneksi dapat berubah setelah health check; kegagalan diproses sebagai error, tidak dipindahkan ke Gmail lain. Untuk produksi hosted dibutuhkan deployment Python/browser, autentikasi pengguna, isolasi tenant dan worker durable yang belum disertakan.

## Testing dan batas verifikasi

```bash
python -m pytest -q
```

Lihat `TEST_RESULTS.md`. Tes unit/API memakai fixture untuk Google, tidak mengakses Gmail asli. Tes Playwright memakai website lokal dan mailbox fixture. Lima tes browser akan di-skip bila Chromium belum terpasang; hasil itu **bukan bukti end-to-end browser lulus**.

Belum diuji dengan OAuth akun Anda atau platform trial nyata karena belum ada kredensial/izin/adapter produksi. Unduhan Chromium dan headless shell gagal di lingkungan pembuatan. Instal browser secara lokal dan jalankan ulang seluruh tes sebelum menjalankan adapter nyata.

Dokumentasi resmi OAuth: https://developers.google.com/identity/protocols/oauth2/web-server

## Hosted preparation (2.1)

Hosting files and HTTPS OAuth support are included; see `HOSTING.md` for deployment-agent steps. Hosted deployment, Railway connection and Google OAuth Web client configuration are not completed yet. Do not treat these files as a live service. Cookie sessions and private-fragment access support have been added so normal use after deployment does not require copying an API token. Local bearer login remains supported.

### Pembukaan lokal praktis

Setelah dependensi terpasang, jalankan `python run_local.py`. Launcher membuat kunci lokal hanya jika `.env` belum ada, membuka dashboard dengan akses pribadi, dan mengikat server hanya ke komputer sendiri. Jangan membagikan `.env` atau URL yang masih mengandung token. Gunakan **Kesiapan sistem** pada dashboard untuk melihat prasyarat yang belum tersedia; status ini bukan bukti koneksi Gmail aktif atau keberhasilan trial.
