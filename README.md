# Flask API Dummy — Kredit & Budget Mobil Baru

API lokal siap dijalankan, bukan API resmi BCA. Tidak memerlukan Playwright, sesi browser, atau akses website saat menghitung. Model dikalibrasi dari hasil simulasi yang diberikan dalam percakapan. Angka di luar sampel dapat berbeda dari website. Baca PATTERN.md.

## Field minimum

| Endpoint | Wajib | Opsional |
|---|---|---|
| POST /v1/simulations/credit | harga_kendaraan, uang_muka, wilayah | tenor_bulan, tipe_konsumen, kategori_kendaraan, asuransi |
| POST /v1/simulations/budget | harga_kendaraan, jenis_budget, nominal_budget, wilayah | tenor_bulan, tipe_konsumen, kategori_kendaraan, asuransi |

Semua nominal berupa integer Rupiah; DP persen harus dikonversi menjadi Rupiah sebelum pemanggilan. Jangan menafsirkan `30` sebagai 30%. `jenis_budget`: `angsuran` atau `pembayaran_pertama`. Tenor opsional: 12/24/36/48/60/72 bulan; bila tidak diberikan API mengembalikan semua tenor.

Parameter profil:

| Field | Nilai | Default |
|---|---|---|
| wilayah | jakarta_jawa_barat_banten / sumatera / lainnya | Wajib, tanpa default |
| tipe_konsumen | perorangan / badan_usaha | perorangan |
| kategori_kendaraan | non_ev / ev | non_ev (termasuk hybrid) |
| asuransi | comprehensive / kombinasi | comprehensive |

Default diterapkan backend jika field dihilangkan. Nilai null, string kosong, atau pilihan di luar enum ditolak (422). Semua profil dikembalikan melalui `profil` dan `input` yang sudah dinormalisasi.

**Batas dummy:** parameter baru belum mengubah tarif. Semua pilihan menggunakan koefisien acuan yang sama karena tarif antarprofil belum tersedia. `penyesuaian_tarif_profil=false` menyatakan keterbatasan ini. Profil kalibrasi lama ditampilkan sebagai `profil_acuan_tarif`, bukan profil pengguna. EV + kombinasi diterima untuk uji kontrak dummy saja, bukan klaim bahwa produk resmi mendukungnya. Prioritas/TLP/PA/promo tetap di luar input.

Perubahan v2 memerlukan `wilayah` pada setiap request lama dan mengganti response `profil_tetap` menjadi `profil` dan `profil_acuan_tarif`. Impor ulang OpenAPI dan perbarui prompt agent.

## Menjalankan

Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Simpan secret yang dihasilkan sebagai API_KEY di `.env`. Jangan gunakan nilai contoh. Isi PUBLIC_BASE_URL dengan URL deployment milik Anda; untuk uji lokal boleh `http://localhost:8000`.

```bash
python app.py
```

Server Waitress berjalan pada port 8000 atau PORT dari environment. Debug tidak diaktifkan. Health check: GET `/health`. Spesifikasi: GET `/openapi.json` (URL server diambil dari environment).

Contoh Kredit:

```bash
curl -X POST http://localhost:8000/v1/simulations/credit \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: GANTI_DENGAN_API_KEY_ANDA' \
  -d '{"wilayah":"jakarta_jawa_barat_banten","harga_kendaraan":300000000,"uang_muka":90000000}'
```

Budget Angsuran:

```json
{"wilayah":"jakarta_jawa_barat_banten","harga_kendaraan":300000000,"jenis_budget":"angsuran","nominal_budget":5000000}
```

Budget Pembayaran Pertama:

```json
{"wilayah":"jakarta_jawa_barat_banten","harga_kendaraan":300000000,"jenis_budget":"pembayaran_pertama","nominal_budget":100000000}
```

Gunakan endpoint budget dan header yang sama. Contoh respons lengkap tersedia dalam `examples/`. Jika hasil kosong, periksa `tidak_tersedia`; jangan mengarang tenor yang lolos.

## Hubungkan ke Azure Foundry

1. Deploy folder ini sebagai Python Web App di Azure App Service, atau container/service HTTP lain yang bisa dijangkau Foundry. Install requirements.txt; startup command `python app.py`. Atur API_KEY, PUBLIC_BASE_URL, dan PORT sesuai hosting. HTTPS diterminasi oleh platform hosting. Paket ini belum dideploy.
2. Pastikan GET https://DOMAIN-ANDA/health berhasil dan POST Kredit berhasil dengan X-API-Key. Localhost pada komputer Anda tidak bisa dipanggil oleh agent cloud.
3. Isi PUBLIC_BASE_URL dengan URL HTTPS API Anda (bukan URL website KKB, bukan endpoint proyek Foundry, dan bukan wss Playwright).
4. Ekspor spesifikasi untuk deployment:
   `python app.py --export-openapi openapi.azure.json`
   Alternatif: unduh GET /openapi.json dari deployment. openapi.json bawaan masih memakai domain placeholder; ganti sebelum impor.
5. Tambahkan tool berjenis OpenAPI melalui menu Tools/Add atau toolbox yang tersedia di portal Anda. Impor openapi.azure.json. Dua operationId: simulateKredit dan simulateBudget. Ini bukan Remote MCP Server yang menerima endpoint Flask langsung.
6. Pilih autentikasi API key / project connection. Buat connection dengan custom key bernama `X-API-Key` dan nilai yang sama dengan API_KEY server. Skema ApiKeyAuth sudah dicantumkan pada OpenAPI. Jangan menaruh secret di prompt atau file OpenAPI.
7. Hubungkan tool/toolbox itu ke agent, tempel agent_instructions.txt, Save, lalu uji di Playground: “Simulasi Kredit mobil Rp300 juta, uang muka Rp90 juta, wilayah Jakarta.”
8. Pastikan trace memanggil simulateKredit atau simulateBudget dan respons mengandung is_dummy=true.

Title tool: **Simulasi Mobil Baru — Kredit dan Budget (Dummy)**
Description tool: **Menghitung simulasi dummy mobil baru berdasarkan harga dan uang muka atau budget. Menyajikan semua tenor, pokok hutang, pembayaran pertama, serta seluruh periode angsuran dengan profil yang dipilih dan tarif dummy acuan. Bukan hasil live website atau tarif resmi BCA.**

Dokumentasi Foundry: https://learn.microsoft.com/en-us/azure/foundry/agents/how-to/tools/openapi
OpenAPI 3.0.3, application/json, satu security scheme API key, dan operationId alfabetis disediakan sesuai kebutuhan integrasi.

## Konfigurasi dan validasi

Koefisien, profil, serta biaya acuan ada di rates.json. Hanya edit dengan data kalibrasi yang dipahami. API membatasi nominal sampai Rp10 miliar; ini batas teknis demo, bukan batas produk BCA. Tidak ada pemeriksaan kelayakan kredit, usia kendaraan, minimum DP resmi, atau approval.

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

Tes memeriksa angka acuan, invers budget, batas jumlah, semua periode, JSON/schema, request invalid, dan auth. Pengujian ini tidak membuktikan kesamaan dengan rumus resmi. Untuk penggunaan produksi diperlukan sumber tarif tervalidasi, pengelolaan secret, pembatasan traffic dan observabilitas sesuai hosting.
