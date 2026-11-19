"""Gera dados/treino_relatos.csv: relatos SINTÉTICOS para treinar o classificador.

Os textos sao montados combinando trechos escritos pelo grupo. Nenhum relato real
de cidadao foi usado. A semente fixa faz o arquivo sair igual em toda execucao.

Uso: python scripts/gerar_treino.py
"""
import csv
import random
from pathlib import Path

DESTINO = Path(__file__).resolve().parent.parent / "dados" / "treino_relatos.csv"
POR_CATEGORIA = 60

ABERTURAS = [
    "Tem", "Há", "Existe", "Apareceu", "Faz semanas que tem", "Desde o mês passado tem",
    "Os moradores reclamam de", "Quero avisar sobre", "Venho relatar", "Preciso informar sobre",
    "Já reclamei várias vezes de", "Ninguém resolve",
]
LOCAIS = [
    "na minha rua", "em frente à escola do bairro", "perto do ponto de ônibus",
    "na esquina da padaria", "ao lado da praça", "na avenida principal", "na rua de trás do mercado",
    "em frente ao posto de saúde", "na travessa perto da feira", "na entrada da comunidade",
    "na rua da igreja", "próximo ao terminal",
]
FECHOS = [
    "Já faz mais de um mês.", "Até agora ninguém veio ver.", "A situação piora a cada dia.",
    "Peço providências.", "Os vizinhos também estão incomodados.", "Isso atrapalha quem passa por aqui.",
    "Gostaria de saber quem resolve.", "Acontece todo ano.", "Obrigado pela atenção.", "",
]

PROBLEMAS = {
    "Vias e buracos": [
        "um buraco enorme no asfalto", "vários buracos na pista", "uma cratera no meio da rua",
        "o asfalto afundando", "um remendo de asfalto que já soltou", "a rua toda esburacada",
        "uma lombada sem pintura", "a faixa de pedestrês apagada no asfalto",
        "uma valeta funda que estraga os carros", "o asfalto cedendo perto da guia",
        "buracos que os motoristas desviam o tempo todo", "a pista cheia de ondulações",
        "um buraco que furou o pneu de vários carros", "o recapeamento malfeito da via",
        "a rua de terra cheia de valas", "um trecho da via sem pavimento",
    ],
    "Calçadas e acessibilidade": [
        "a calçada toda quebrada", "o piso da calçada solto", "uma raiz que levantou a calçada",
        "a calçada sem rampa de acesso", "um degrau alto no meio da calçada",
        "um poste bem no meio da calçada", "o piso tátil arrancado", "a calçada estreita demais",
        "a rampa de acessibilidade destruída", "um desnível grande no passeio",
        "a calçada com lajotas soltas", "um trecho sem calçada onde o pedestre anda na rua",
        "a calçada bloqueada por uma obra", "o passeio público cheio de buracos",
        "uma calçada onde carrinho de bebê não passa", "a guia rebaixada quebrada",
    ],
    "Iluminação pública": [
        "um poste com a luz apagada", "a lâmpada do poste queimada", "a luz do poste piscando a noite toda",
        "a rua inteira no escuro", "uma luminária quebrada", "a praça sem iluminação",
        "três postes seguidos sem luz", "uma lâmpada acesa durante o dia",
        "a iluminação fraca demais", "o poste de luz apagado há dias",
        "o trecho escuro a noite", "a luminária pendurada no poste",
        "a quadra sem nenhuma luz", "a lâmpada que acende e apaga",
        "o braço da luminária torto e apagado", "a iluminação pública que não funciona",
    ],
    "Lixo e limpeza": [
        "lixo acumulado", "um monte de entulho descartado", "descarte irregular de lixo",
        "sacos de lixo rasgados", "mato alto tomando conta", "a coleta de lixo que não passou",
        "um ponto viciado de descarte", "móveis velhos abandonados", "um mau cheiro forte de lixo",
        "ratos por causa do lixo", "um sofa e colchões jogados", "restos de obra largados",
        "a lixeira pública transbordando", "o terreno baldio cheio de lixo",
        "galhos e podas largados há semanas", "a varrição que não acontece",
    ],
    "Drenagem e alagamentos": [
        "um bueiro entupido", "a boca de lobo cheia de folhas", "a rua que alaga quando chove",
        "água empocada que não escoa", "um ponto de alagamento", "o córrego transbordando",
        "a galeria de água pluvial obstruída", "a água da chuva que não tem para onde ir",
        "a enxurrada que entra nas casas", "um bueiro sem tampa cheio de água",
        "a sarjeta entupida de terra", "água parada depois da chuva",
        "o ralo da rua entupido", "a rua que vira um rio com qualquer chuva",
        "o escoamento da água que não funciona", "a tubulação de drenagem rompida",
    ],
    "Outros": [
        "uma árvore com galhos caindo", "muito barulho de madrugada", "pichação no muro da praça",
        "um semáforo que não funciona", "um carro abandonado há meses", "cachorros soltos",
        "o banco da praça quebrado", "o ponto de ônibus sem cobertura", "uma placa de rua caida",
        "um bar com som alto", "o parquinho com brinquedo quebrado", "uma árvore que precisa de poda",
        "um veículo estacionado em local proibido", "a quadra esportiva abandonada",
        "um comércio ocupando a rua com mesas", "uma placa de trânsito virada",
    ],
}


def main() -> None:
    sorteio = random.Random(2026)
    linhas = []
    for categoria, problemas in PROBLEMAS.items():
        vistos = set()
        while len(vistos) < POR_CATEGORIA:
            texto = " ".join(parte for parte in [
                sorteio.choice(ABERTURAS), sorteio.choice(problemas),
                sorteio.choice(LOCAIS) + ".", sorteio.choice(FECHOS),
            ] if parte).strip()
            if texto not in vistos:
                vistos.add(texto)
                linhas.append({"descricao": texto, "categoria": categoria})
    sorteio.shuffle(linhas)
    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    with DESTINO.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=["descricao", "categoria"])
        escritor.writeheader()
        escritor.writerows(linhas)
    print(f"{len(linhas)} relatos sinteticos gravados em {DESTINO}")


if __name__ == "__main__":
    main()
