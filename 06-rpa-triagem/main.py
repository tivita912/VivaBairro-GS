"""VivaBairro - robo de triagem de relatos de zeladoria (GS 2026.2, RPA + IA).

Ponto de entrada unico:

    python main.py            roda o fluxo completo com os arquivos de dados/entrada
    python main.py avaliar    mede a IA no conjunto de teste rotulado
    python main.py falhas     provoca falhas e registra como o robo se comporta
"""
import argparse
import shutil
import sys

from robo import avaliacao, config, falhas, fluxo

ARQUIVOS_DE_EVIDENCIA = ["relatorio_execucao.md", "relatorio_execucao.json", "robo.log",
                         "fila_priorizada.csv", "revisao_humana.csv"]


def rodar() -> int:
    resumo = fluxo.executar()
    destino = config.EVIDENCIAS / "execucao"
    destino.mkdir(parents=True, exist_ok=True)
    for nome in ARQUIVOS_DE_EVIDENCIA:
        origem = config.SAIDA / nome
        if origem.exists():
            shutil.copy(origem, destino / nome)
    email = config.SAIDA / "emails" / "resumo.eml"
    if email.exists():
        shutil.copy(email, destino / "resumo.eml")
    print()
    print(f"Status: {resumo['status']}")
    print(f"Linhas lidas: {resumo['linhas_lidas']} | validas: {resumo['validas']} | "
          f"invalidas: {resumo['invalidas']} | novos no banco: {resumo['novos']}")
    print(f"API de clima: {resumo['api_clima']}")
    print(f"E-mail: {resumo['email']}")
    print(f"Resultados em: {config.relativo(config.SAIDA)}/")
    print(f"Copia das evidencias em: {config.relativo(destino)}/")
    return 0 if not resumo["status"].startswith("falha") else 1


def avaliar() -> int:
    r = avaliacao.avaliar()
    print(f"Categoria: {r['acertos_categoria']} de {r['total']} certos")
    print(f"Prioridade: {r['acertos_prioridade']} de {r['total']} certos")
    print(f"Prioridade alta encontrada: {r['altas_achadas']} de {r['altas']}")
    print(f"Enviados para revisao humana: {r['revisao']} de {r['total']}")
    print("Detalhes em: evidencias/avaliacao.md")
    return 0


def demonstrar_falhas() -> int:
    cenarios = falhas.demonstrar()
    print()
    for numero, c in enumerate(cenarios, start=1):
        print(f"{numero}. {c['titulo']}: {c['observado']}")
    print("Detalhes em: evidencias/falhas.md")
    return 0


def main() -> int:
    analisador = argparse.ArgumentParser(description="Robo de triagem do VivaBairro")
    analisador.add_argument("comando", nargs="?", default="rodar",
                            choices=["rodar", "avaliar", "falhas"])
    comando = analisador.parse_args().comando
    config.carregar_env()
    return {"rodar": rodar, "avaliar": avaliar, "falhas": demonstrar_falhas}[comando]()


if __name__ == "__main__":
    sys.exit(main())
