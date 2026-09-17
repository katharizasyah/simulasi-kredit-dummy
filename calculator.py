"""Deterministic demo, calibrated to supplied snapshots; not an official calculator."""
import json
from fractions import Fraction
from pathlib import Path

CONFIG = json.loads(Path(__file__).with_name('rates.json').read_text())
MAX_AMOUNT = 10_000_000_000

def ceil100(value):
    value = Fraction(value)
    return -(-value.numerator // (value.denominator * 100)) * 100

def validate(data, mode):
    required = {'harga_kendaraan', 'uang_muka'} if mode == 'kredit' else {'harga_kendaraan', 'jenis_budget', 'nominal_budget'}
    required = required | {'wilayah'}
    if not isinstance(data, dict):
        raise ValueError('Body harus JSON object.')
    missing = required - data.keys()
    if missing:
        raise ValueError('Field wajib belum diisi: ' + ', '.join(sorted(missing)))
    extra = data.keys() - required - {'tenor_bulan', 'tipe_konsumen', 'kategori_kendaraan', 'asuransi'}
    if extra:
        raise ValueError('Field tidak dikenal: ' + ', '.join(sorted(extra)))
    for field, options in CONFIG['input_options'].items():
        if field in data and (not isinstance(data[field], str) or data[field] not in options):
            raise ValueError(f'{field} harus salah satu: {", ".join(options)}.')
    for field in required - {'jenis_budget', 'wilayah'}:
        value = data[field]
        minimum = 0 if field == 'uang_muka' else 1
        if type(value) is not int or not minimum <= value <= MAX_AMOUNT:
            raise ValueError(f'{field} harus integer Rupiah antara {minimum} dan {MAX_AMOUNT}.')
    if data['harga_kendaraan'] < 100:
        raise ValueError('harga_kendaraan minimal Rp100.')
    if 'tenor_bulan' in data and (type(data['tenor_bulan']) is not int or str(data['tenor_bulan']) not in CONFIG['tenors']):
        raise ValueError('tenor_bulan harus 12, 24, 36, 48, 60, atau 72.')
    if mode == 'kredit' and data['uang_muka'] >= data['harga_kendaraan']:
        raise ValueError('uang_muka harus lebih kecil dari harga_kendaraan.')
    if mode == 'budget' and data['jenis_budget'] not in ('angsuran', 'pembayaran_pertama'):
        raise ValueError('jenis_budget harus angsuran atau pembayaran_pertama.')

def row(price, principal, months):
    cfg = CONFIG['tenors'][str(months)]
    amounts = [ceil100(Fraction(principal * a, CONFIG['reference_principal'])) for a in cfg['reference_installments']]
    fees = ceil100(Fraction(price * cfg['reference_initial_cost'], CONFIG['reference_price']))
    return dict(tenor_bulan=months, uang_muka=price-principal, pokok_hutang=principal,
                biaya_awal_agregat_dummy=fees,
                total_bayar_pertama=price-principal+fees+amounts[0],
                angsuran=[{'periode': i+1, 'nominal_per_bulan': a} for i,a in enumerate(amounts)])

def simulate(data, mode):
    validate(data, mode)
    data = {**CONFIG['input_defaults'], **data}
    price = data['harga_kendaraan']
    tenors = [data['tenor_bulan']] if 'tenor_bulan' in data else [int(n) for n in CONFIG['tenors']]
    results, excluded = [], []
    for months in tenors:
        if mode == 'kredit':
            principal = price-data['uang_muka']
        elif data['jenis_budget'] == 'angsuran':
            # Budget targets period 1, as in supplied website samples.
            budget = data['nominal_budget'] // 100 * 100
            factor = CONFIG['tenors'][str(months)]['reference_installments'][0]
            principal = min(price//100*100, (budget*CONFIG['reference_principal']//factor)//100*100)
        else:
            # On a Rp100 principal grid, first payment is monotonically decreasing.
            # Find smallest principal meeting the maximum first-payment budget.
            lo, hi = 1, price//100
            while lo < hi:
                mid = (lo+hi)//2
                if row(price, mid*100, months)['total_bayar_pertama'] <= data['nominal_budget']:
                    hi = mid
                else:
                    lo = mid+1
            principal = lo*100
        if principal <= 0:
            excluded.append({'tenor_bulan': months, 'alasan': 'Budget terlalu kecil untuk pembulatan demo.'})
            continue
        result = row(price, principal, months)
        if mode == 'budget':
            budget = data['nominal_budget']
            if data['jenis_budget'] == 'pembayaran_pertama' and result['total_bayar_pertama'] > budget:
                excluded.append({'tenor_bulan': months, 'alasan': 'Budget pembayaran pertama tidak cukup untuk biaya dan angsuran pertama.'})
                continue
            if data['jenis_budget'] == 'angsuran':
                result['semua_periode_dalam_budget'] = all(a['nominal_per_bulan'] <= budget for a in result['angsuran'])
                result['selisih_budget_periode_pertama'] = budget-result['angsuran'][0]['nominal_per_bulan']
            else:
                result['sisa_budget_pembayaran_pertama'] = budget-result['total_bayar_pertama']
        results.append(result)
    return dict(is_dummy=True, sumber_perhitungan='rumus_lokal_dummy', versi_model=CONFIG['version'],
                profil={k: data[k] for k in CONFIG['input_options']},
                penyesuaian_tarif_profil=False, profil_acuan_tarif=CONFIG['reference_profile'], input=data, hasil=results, tidak_tersedia=excluded,
                catatan=['Pilihan profil diterima, tetapi belum mengubah tarif; semua kombinasi menggunakan koefisien acuan yang sama. EV kombinasi diterima hanya untuk dummy, bukan validasi produk resmi.',
                         'Bukan API resmi BCA dan tidak mengakses website secara langsung.',
                         'Biaya awal agregat dan koefisien dikalibrasi dari contoh, bukan tarif resmi.',
                         'Batas bulan setiap periode belum diketahui; periode tidak boleh digabung atau dirata-ratakan.',
                         'Budget angsuran menargetkan periode pertama; periksa semua_periode_dalam_budget.',
                         'Model demo mengizinkan uang muka nol; ini bukan ketentuan kelayakan kredit resmi.',
                         'Hasil simulasi bukan persetujuan kredit.'])
