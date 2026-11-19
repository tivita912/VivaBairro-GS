"""Testes automatizados do robo. Rodar com: python -m pytest -q

Nenhum teste usa a internet: as respostas da API de clima sao simuladas no
formato documentado pela Open-Meteo.
"""
import pandas as pd
import pytest
import requests

from robo import banco, classificador, clima, config, fluxo, leitura, logs


@pytest.fixture(autouse=True)
def log_em_pasta_temporaria(tmp_path):
    logs.configurar(tmp_path / "teste.log")


class RespostaFalsa:
    def __init__(self, corpo, status=200):
        self.corpo, self.status_code = corpo, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self.corpo


def resposta_com_chuva(mm):
    return RespostaFalsa({"daily": {"time": ["2026-11-18"], "precipitation_sum": [mm]}})


def lote(linhas):
    df = pd.DataFrame(linhas, columns=["data", "bairro", "descricao"])
    df["arquivo"], df["linha"] = "teste.csv", range(2, len(df) + 2)
    return df


TEXTO_BOM = "Buraco grande no asfalto em frente ao mercado, os carros desviam."


def test_validacao_separa_linhas_invalidas_com_motivo():
    validos, invalidos = leitura.validar(lote([
        ("2026-11-18", "Lapa", TEXTO_BOM),
        ("2026-11-18", "Lapa", "Curto."),
        ("2026-11-18", "", TEXTO_BOM),
        ("18/11/2026", "Lapa", TEXTO_BOM),
    ]))
    assert len(validos) == 1
    assert len(invalidos) == 3
    assert all(invalidos["motivo"] != "")


def test_dados_pessoais_sao_mascarados():
    texto, mudou = leitura.mascarar_dados_pessoais(
        "Meu CPF e 000.000.000-00, telefone (11) 90000-0000 e e-mail fulano@exemplo.com.")
    assert mudou
    assert "000.000.000-00" not in texto and "90000-0000" not in texto and "@" not in texto


def test_id_do_relato_e_estavel_e_ignora_acento_e_maiuscula():
    a = leitura.gerar_id("2026-11-18", "Butantã", "Calçada quebrada na esquina")
    b = leitura.gerar_id("2026-11-18", "BUTANTA", "calcada quebrada na esquina")
    assert a == b


def test_arquivo_sem_colunas_e_rejeitado_e_o_lote_bom_e_lido(tmp_path):
    (tmp_path / "a_ruim.csv").write_text("nome,valor\nx,1\n", encoding="utf-8")
    (tmp_path / "b_corrompido.csv").write_bytes(bytes(range(128, 256)))
    (tmp_path / "c_bom.csv").write_text(
        f'data,bairro,descricao\n2026-11-18,Lapa,"{TEXTO_BOM}"\n', encoding="utf-8")
    validos, invalidos, rejeitados = leitura.carregar_lotes(tmp_path)
    assert len(rejeitados) == 2
    assert len(validos) == 1 and invalidos.empty


def test_clima_le_resposta_no_formato_da_api():
    chuva = clima.buscar_chuva(-23.55, -46.63, requisitar=lambda *a, **k: resposta_com_chuva(12.4))
    assert chuva.ok and chuva.mm == 12.4 and chuva.tentativas == 1


def test_clima_tenta_de_novo_com_espera_crescente_e_recupera():
    chamadas, esperas = [], []

    def requisitar(*a, **k):
        chamadas.append(1)
        if len(chamadas) < 3:
            raise requests.ConnectionError("fora do ar")
        return resposta_com_chuva(3.0)

    chuva = clima.buscar_chuva(0, 0, requisitar=requisitar, dormir=esperas.append, espera=1.0)
    assert chuva.ok and chuva.tentativas == 3
    assert esperas == [1.0, 2.0]


def test_clima_usa_timeout_em_toda_chamada():
    vistos = []

    def requisitar(url, params, timeout):
        vistos.append(timeout)
        return resposta_com_chuva(0.0)

    clima.buscar_chuva(0, 0, requisitar=requisitar)
    assert vistos == [config.CLIMA_TIMEOUT_S]


@pytest.mark.parametrize("resposta", [
    RespostaFalsa({"daily": {}}),
    RespostaFalsa({"daily": {"precipitation_sum": [None]}}),
    RespostaFalsa({"daily": {"precipitation_sum": ["muita"]}}),
    RespostaFalsa({}, status=500),
])
def test_clima_resposta_invalida_vira_caminho_seguro(resposta):
    chuva = clima.buscar_chuva(0, 0, requisitar=lambda *a, **k: resposta, dormir=lambda s: None)
    assert not chuva.ok and chuva.mm is None


def test_clima_nao_insiste_em_todos_os_bairros_depois_de_falha_total():
    chamadas = []

    def requisitar(*a, **k):
        chamadas.append(1)
        raise requests.Timeout("sem resposta")

    resultado = clima.chuva_por_bairro(["Lapa", "Penha", "Mooca"], requisitar=requisitar,
                                       tentativas=2, dormir=lambda s: None)
    assert len(chamadas) == 2
    assert not any(c.ok for c in resultado.values())


def test_prioridade_por_regras():
    assert classificador.prioridade_por_regras("Um cadeirante não consegue passar")[0] == "alta"
    assert classificador.prioridade_por_regras("Pichação no muro, sem urgência")[0] == "baixa"
    assert classificador.prioridade_por_regras("Poste apagado na esquina faz dez dias")[0] == "media"


def test_classificador_acerta_exemplos_claros():
    modelo = classificador.treinar()
    previsoes = classificador.classificar(modelo, [
        "Bueiro entupido, a rua alaga quando chove",
        "Poste com a lâmpada queimada, rua no escuro",
    ])
    assert [c for c, _ in previsoes] == ["Drenagem e alagamentos", "Iluminação pública"]
    assert all(0.0 <= p <= 1.0 for _, p in previsoes)


def test_chuva_forte_sobe_prioridade_so_de_drenagem():
    validos, _ = leitura.validar(lote([
        ("2026-11-18", "Lapa", "Bueiro entupido na esquina, a água da chuva fica parada e não escoa."),
        ("2026-11-18", "Lapa", "Poste com a lâmpada queimada na esquina, a rua fica no escuro à noite."),
    ]))
    resumo = fluxo.resumo_vazio("2026-11-18 08:00:00")
    tratados = fluxo.tratar_relatos(validos, {"requisitar": lambda *a, **k: resposta_com_chuva(25.0)}, resumo)
    drenagem = tratados[tratados["categoria"] == "Drenagem e alagamentos"].iloc[0]
    luz = tratados[tratados["categoria"] == "Iluminação pública"].iloc[0]
    assert drenagem["prioridade"] == "alta" and "chuva prevista" in drenagem["motivo_prioridade"]
    assert luz["prioridade"] == "media"
    assert resumo["prioridades_alteradas_pela_chuva"] == 1
    assert resumo["api_clima"].startswith("ok")


def test_banco_nao_duplica_relato(tmp_path):
    validos, _ = leitura.validar(lote([("2026-11-18", "Lapa", TEXTO_BOM)]))
    validos = validos.assign(categoria="Vias e buracos", confianca=0.9, prioridade="media",
                             motivo_prioridade="teste", chuva_mm=None, precisa_revisao=False)
    conexao = banco.conectar(tmp_path / "t.db")
    assert banco.inserir_relatos(conexao, validos, "2026-11-18 08:00:00") == (1, 0)
    assert banco.inserir_relatos(conexao, validos, "2026-11-18 09:00:00") == (0, 1)
    assert len(banco.fila(conexao)) == 1
    conexao.close()


def test_fluxo_sem_arquivo_encerra_com_relatorio_e_sem_banco(tmp_path):
    entrada, saida = tmp_path / "entrada", tmp_path / "saida"
    entrada.mkdir()
    resumo = fluxo.executar(entrada, saida)
    assert resumo["status"] == "sem arquivo de entrada"
    assert (saida / "relatorio_execucao.md").exists()
    assert not (saida / "vivabairro.db").exists()


def test_fluxo_completo_com_api_simulada(tmp_path):
    saida = tmp_path / "saida"
    opcoes = {"requisitar": lambda *a, **k: resposta_com_chuva(0.0)}
    primeira = fluxo.executar(config.ENTRADA, saida, opcoes)
    segunda = fluxo.executar(config.ENTRADA, saida, opcoes)
    assert primeira["status"] == "concluido"
    assert primeira["linhas_lidas"] == primeira["validas"] + primeira["invalidas"] + primeira["repetidos_no_lote"]
    assert primeira["novos"] == primeira["validas"] and segunda["novos"] == 0
    assert primeira["api_clima"].startswith("ok")
    for nome in ("fila_priorizada.csv", "revisao_humana.csv", "relatorio_execucao.json", "emails/resumo.eml"):
        assert (saida / nome).exists()
    fila = pd.read_csv(saida / "fila_priorizada.csv")
    assert "000.000.000-00" not in " ".join(fila["descricao"])
