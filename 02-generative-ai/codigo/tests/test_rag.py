import json
from pathlib import Path

import pytest

from citizentech.chunking import chunk_corpus, load_corpus
from citizentech.retrieval import Retriever
from citizentech.vivabairro import VivaBairro, select_chunk

ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT/'tests/casos.json').read_text(encoding='utf8'))


@pytest.fixture(scope='module')
def assistant():
    return VivaBairro(provider='baseline')


def test_chunking_preserva_metadados_e_overlap():
    docs = load_corpus(ROOT/'corpus/fontes.json')
    chunks = chunk_corpus(docs)
    assert len(docs) == 10 and len(chunks) == 14
    assert all(item['municipality']=='São Paulo (SP)' and item['limitations'] for item in chunks)
    assert all(item['overlap_words']==0 for item in chunks)
    assert any(item['overlap_words']==8 for item in chunk_corpus(docs,size=32,overlap=8))


def test_busca_respeita_dominio_e_ranking(assistant):
    hybrid = Retriever(assistant.chunks,'hybrid')
    rows = hybrid.retrieve('buraco no asfalto em via pública',4,domain='vias')
    assert rows and rows[0]['doc_id']=='F02'
    assert all(row['domain']=='vias' for row in rows)


@pytest.mark.parametrize('case',CASES,ids=lambda case:case['id'])
def test_casos_baseline(assistant,case):
    out = assistant.ask(case['question'],municipality=case['municipality'],
                        context_doc_id=case.get('context_doc_id'),debug=True)
    assert out['trace']['reason']==case['reason']
    assert (out['category'] or {}).get('id')==case['category']
    assert set(case['sources']).issubset(s['doc_id'] for s in out['sources'])
    assert out['submitted'] is False


def test_proposta_revisavel_e_municipio(assistant):
    out = assistant.ask('Uma calçada quebrada está impedindo a passagem.',municipality='sao_paulo',location='Praça de exemplo')
    assert out['category']['id']=='calcadas' and out['priority']['level']=='elevada'
    assert 'Praça de exemplo' in out['draft']
    assert any('vinculada a um imóvel' in q for q in out['clarifications'])
    assert out['channel']['url'].endswith('/portal/servicos')
    outside = assistant.ask('Uma calçada está quebrada.',municipality='outro')
    assert outside['draft'] and not outside['channel'] and not outside['sources']


def test_risco_imediato_nao_aguarda_modelo(assistant):
    out = assistant.ask('Há pessoas ilhadas e a água está subindo rápido.',municipality='sao_paulo',debug=True)
    assert out['urgent'] and not out['draft'] and not out['channel']
    assert out['sources'][0]['doc_id']=='F10' and not out['trace']['generator_called']
    assert 'acione agora' in out['answer']


def test_seletor_valida_identificador(assistant):
    row = assistant.chunks[0]
    assert select_chunk(json.dumps({'trecho':row['id']}),[row])[0]==row
    assert select_chunk('{"trecho":"F99-S01-C01"}',[row])[1]=='citacao_invalida'
    assert select_chunk('texto extra {"trecho":null}',[row])[1]=='formato_invalido'


def test_entrada_sensivel_sintetica(assistant):
    out = assistant.ask('Buraco na rua. Meu e-mail é teste@example.invalid',municipality='sao_paulo',debug=True)
    assert out['blocked'] and not out['draft'] and not out['trace']['generator_called']
    assert 'teste@example.invalid' not in out['answer']


def test_api_sem_diagnostico(monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv('GENERATOR_PROVIDER','baseline')
    from app import app
    with TestClient(app) as client:
        assert client.get('/health').json()['generator']=='baseline'
        assert 'VivaBairro' in client.get('/').text
        result = client.post('/api/ask',json={'question':'Tem buraco no asfalto.','municipality':'sao_paulo'}).json()
        assert result['category']['id']=='vias' and result['sources'][0]['doc_id']=='F02'
        assert 'trace' not in result and 'evidence' not in result and not result['submitted']
        r = client.post('/api/ask',json={'question':'Tem buraco no asfalto.','municipality':'invalido'})
        assert r.status_code==422 and 'invalido' not in r.text

