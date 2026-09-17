# Pola perhitungan dan keterbatasan

Sumber alur: https://kreditkerenbanget.com/simulation (menu Mobil Baru > Kredit dan Budget). Sumber angka: hasil snapshot yang diberikan pengguna dalam percakapan, bukan ekstraksi tarif resmi. Harga acuan H0 = Rp300.000.000; DP = Rp90.000.000; pokok P0 = Rp210.000.000. Profil acuan tertera di README.

## Model dummy

H = harga, D = uang muka, P = pokok hutang, A = angsuran, F = biaya awal agregat, T = Total Bayar Pertama.

- P = H − D.
- k[n,j] = angsuran acuan tenor n periode j / P0.
- A[n,j] = ceil100(P × k[n,j]). ceil100 membulatkan ke atas ke Rp100.
- F0[n] = T_acuan[n] − D_acuan − A_acuan[n,1].
- F[n] = ceil100(F0[n] × H/H0).
- T[n] = D + F[n] + A[n,1].

Definisi F sebagai residual serta asumsi proporsional terhadap harga adalah pilihan model demo. Belum terbukti seluruh biaya resmi bergantung linear pada harga. Asumsi T mencakup angsuran pertama juga merupakan asumsi kalibrasi, bukan rincian tagihan yang terverifikasi. F tidak diberi label premi/provisi/admin karena komposisinya belum diketahui.

Budget Angsuran: cari pokok terbesar (kelipatan Rp100, tidak melebihi harga) dengan A periode pertama <= budget. Angsuran periode 2 tetap dihitung dan bisa melampaui budget. Budget Pembayaran Pertama: cari pokok terkecil pada grid Rp100 dengan T <= budget. Sebelum pembulatan, pendekatan inversnya P = (H + F − budget)/(1 − k[n,1]). Implementasi memakai binary search agar batas budget tetap dipenuhi setelah pembulatan.

Grid pokok Rp100, biaya proporsional harga, dan pembulatan ke atas merupakan keputusan demo. Tidak diketahui apakah website memakai aturan pembulatan yang sama. Angka hanya dimaksudkan mendekati pola; bukan implementasi resmi.

## Koefisien dari contoh Kredit

| Tenor bulan | Angsuran periode 1 acuan | Periode 2 acuan | Biaya awal residual | Ekuivalen flat periode 1 (%) |
|---|---:|---:|---:|---:|
| 12 | 17,815,000 | — | 10,139,100 | 1.800000 |
| 24 | 9,143,800 | — | 17,796,400 | 2.250286 |
| 36 | 6,244,600 | — | 25,489,700 | 2.350095 |
| 48 | 4,978,800 | — | 32,805,300 | 3.450286 |
| 60 | 4,375,000 | 4508200 | 39,228,700 | 5.000000 |
| 72 | 3,966,700 | 4051000 | 45,230,000 | 6.000190 |

Ekuivalen flat = (A1 × n/P0 − 1)/(n/12) × 100%. Ini hanya transformasi matematika atas periode pertama, bukan suku bunga resmi; khusus tenor 60/72 bulan tidak merepresentasikan seluruh jadwal pembayaran. Durasi masing-masing periode belum diketahui. Tidak dihitung APR, total bunga, atau total pembayaran sepanjang tenor.

## Pemeriksaan terhadap contoh Budget Angsuran Rp5 juta

Dataset ini tidak dipakai untuk mengatur koefisien. Pembandingan memperlihatkan batas generalisasi model. Kolom delta = dummy − hasil snapshot pengguna; keduanya memakai harga Rp300 juta dan profil acuan.

| Bulan | Pokok website | Pokok dummy | Delta pokok | Bayar pertama website | Bayar pertama dummy | Delta bayar pertama |
|---|---:|---:|---:|---:|---:|---:|
| 12 | 58,939,096 | 58,939,000 | -96 | 255,097,000 | 256,200,100 | +1,103,100 |
| 24 | 114,830,801 | 114,831,900 | +1,099 | 207,043,500 | 207,964,500 | +921,000 |
| 36 | 168,142,508 | 168,145,200 | +2,692 | 161,722,700 | 162,344,500 | +621,800 |
| 48 | 210,893,849 | 210,894,100 | +251 | 126,929,500 | 126,911,200 | -18,300 |
| 60 | 239,999,086 | 240,000,000 | +914 | 104,906,800 | 104,228,700 | -678,100 |
| 72 | 264,705,583 | 264,703,600 | -1,983 | 87,038,200 | 85,526,400 | -1,511,800 |

Kredit acuan cocok karena kalibrasi, bukan validasi independen. Pembayaran Pertama menggunakan invers model yang sama, tetapi belum divalidasi dengan dataset website independen dalam paket ini. Profil/nominal lain belum divalidasi. Untuk replika resmi diperlukan tabel tarif, aturan premi/biaya, promo, periode angsuran, dan pembulatan yang sah.

## Pembaruan v2

Wilayah wajib; tipe konsumen, kategori kendaraan, dan asuransi memiliki default. Parameter ini divalidasi dan dikembalikan pada respons, tetapi belum mengubah koefisien maupun biaya. Seluruh angka tabel di atas tetap memakai profil kalibrasi lama. Tidak ada tarif EV, badan usaha, kombinasi, atau zona lain yang direkayasa. Untuk perbedaan hasil antarprofil, diperlukan tabel tarif/biaya per kombinasi.
