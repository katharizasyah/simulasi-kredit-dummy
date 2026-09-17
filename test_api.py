import json
from pathlib import Path
import pytest
from jsonschema import validate
from openapi_spec_validator import validate_spec
from app import create_app
from calculator import simulate, row

@pytest.fixture
def client():
    return create_app({'TESTING':True,'API_KEY':'test-only'}).test_client()

def post(client,path,payload):
    return client.post('/v1/simulations/'+path,json=payload,headers={'X-API-Key':'test-only'})

def test_reference(client):
    r=post(client,'credit',{'wilayah':'jakarta_jawa_barat_banten','harga_kendaraan':300000000,'uang_muka':90000000})
    assert r.status_code==200
    assert [x['total_bayar_pertama'] for x in r.json['hasil']]==[117954100,116940200,121734300,127784100,133603700,139196700]
    assert r.json['hasil'][-1]['angsuran'][-1]['nominal_per_bulan']==4051000

def test_period_budget(client):
    rows=post(client,'budget',{'wilayah':'jakarta_jawa_barat_banten','harga_kendaraan':300000000,'jenis_budget':'angsuran','nominal_budget':5000000}).json['hasil']
    assert [r['semua_periode_dalam_budget'] for r in rows]==[True,True,True,True,False,False]

@pytest.mark.parametrize('price',[100,123456789,300000000,10000000000])
@pytest.mark.parametrize('budget',[1,100,10000000,100000000,10000000000])
def test_inverse(price,budget):
    for kind in ['angsuran','pembayaran_pertama']:
        data=simulate({'wilayah':'jakarta_jawa_barat_banten','harga_kendaraan':price,'jenis_budget':kind,'nominal_budget':budget},'budget')
        assert len(data['hasil'])+len(data['tidak_tersedia'])==6
        for r in data['hasil']:
            assert 0<r['pokok_hutang']<=price
            assert r['pokok_hutang']+r['uang_muka']==price
            if kind=='angsuran':
                assert r['angsuran'][0]['nominal_per_bulan']<=budget
            else:
                assert r['total_bayar_pertama']<=budget
                if r['pokok_hutang']>100:
                    assert row(price,r['pokok_hutang']-100,r['tenor_bulan'])['total_bayar_pertama']>budget

@pytest.mark.parametrize('payload',[{},[],{'wilayah':'jakarta_jawa_barat_banten','harga_kendaraan':True,'uang_muka':1},{'wilayah':'jakarta_jawa_barat_banten','harga_kendaraan':300000000,'uang_muka':300000000},{'wilayah':'jakarta_jawa_barat_banten','harga_kendaraan':300000000,'uang_muka':1,'tenor_bulan':True},{'wilayah':'jakarta_jawa_barat_banten','harga_kendaraan':300000000,'uang_muka':1,'promo':'X'}])
def test_invalid(client,payload):
    assert post(client,'credit',payload).status_code==422

def test_transport(client):
    assert client.post('/v1/simulations/credit',json={}).status_code==401
    assert client.post('/v1/simulations/credit',data='{',content_type='application/json',headers={'X-API-Key':'test-only'}).status_code==400
    assert client.post('/v1/simulations/credit',data='x',headers={'X-API-Key':'test-only'}).status_code==415

def test_contract(client):
    spec=json.loads(Path('openapi.json').read_text())
    validate_spec(spec)
    for path,payload in [('credit',{'wilayah':'jakarta_jawa_barat_banten','harga_kendaraan':300000000,'uang_muka':90000000}),('budget',{'wilayah':'jakarta_jawa_barat_banten','harga_kendaraan':300000000,'jenis_budget':'pembayaran_pertama','nominal_budget':100000000})]:
        validate(post(client,path,payload).json,spec['components']['schemas']['SimulationResponse'])
    assert client.get('/openapi.json').status_code==200

@pytest.mark.parametrize('path,extra',[('credit',{'uang_muka':90000000}),('budget',{'jenis_budget':'angsuran','nominal_budget':5000000})])
def test_profile_defaults_and_required(client,path,extra):
    payload={'harga_kendaraan':300000000,**extra}
    assert post(client,path,payload).status_code==422
    payload['wilayah']='sumatera'
    response=post(client,path,payload)
    assert response.status_code==200
    assert response.json['profil']=={'wilayah':'sumatera','tipe_konsumen':'perorangan','kategori_kendaraan':'non_ev','asuransi':'comprehensive'}
    assert response.json['penyesuaian_tarif_profil'] is False

@pytest.mark.parametrize('field', ['wilayah','tipe_konsumen','kategori_kendaraan','asuransi'])
@pytest.mark.parametrize('value', [None, '', [], 'invalid'])
def test_invalid_profile(client,field,value):
    payload={'harga_kendaraan':300000000,'uang_muka':90000000,'wilayah':'sumatera',field:value}
    assert post(client,'credit',payload).status_code==422

@pytest.mark.parametrize('path,extra',[('credit',{'uang_muka':90000000}),('budget',{'jenis_budget':'pembayaran_pertama','nominal_budget':100000000})])
def test_explicit_profile(client,path,extra):
    profile={'wilayah':'lainnya','tipe_konsumen':'badan_usaha','kategori_kendaraan':'ev','asuransi':'kombinasi'}
    response=post(client,path,{'harga_kendaraan':300000000,**extra,**profile})
    assert response.status_code==200
    assert response.json['profil']==profile
    assert response.json['input']['asuransi']=='kombinasi'
    spec=json.loads(Path('openapi.json').read_text())
    validate(response.json,spec['components']['schemas']['SimulationResponse'])
