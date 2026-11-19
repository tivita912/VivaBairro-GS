"""Calcula acertos e matrizes de confusão a partir dos CSVs em dados/."""

import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
CLASSES = ["ambiente_rua", "buzina", "sirene"]
INCERTO = "uncertain"
CLASSE_AMBIENTE = "ambiente_rua"

TESTES = [
    ("teste_arquivos.csv", "Teste com áudios inéditos (Model testing)", "matriz_teste_arquivos.png"),
]


def normalizar(rotulo: str) -> str:
    r = rotulo.strip().lower().replace(" ", "_")
    apelidos = {"ambiente": "ambiente_rua", "incerto": INCERTO, "uncertain": INCERTO}
    return apelidos.get(r, r)


def ler_planilha(caminho: Path) -> tuple[list[tuple[str, str]], list[str]]:
    """Devolve os pares (real, previsto) preenchidos e uma lista de avisos."""
    pares, avisos = [], []
    with caminho.open(encoding="utf-8-sig", newline="") as arq:
        leitor = csv.DictReader(arq)
        faltando = {"real", "previsto"} - set(leitor.fieldnames or [])
        if faltando:
            raise ValueError(f"colunas faltando em {caminho.name}: {', '.join(sorted(faltando))}")
        for n, linha in enumerate(leitor, start=2):
            real = normalizar(linha.get("real") or "")
            previsto = normalizar(linha.get("previsto") or "")
            if not real or not previsto:
                avisos.append(f"linha {n}: sem classe real ou prevista, ignorada")
                continue
            if real not in CLASSES:
                avisos.append(f"linha {n}: classe real desconhecida '{real}', ignorada")
                continue
            if previsto not in CLASSES + [INCERTO]:
                avisos.append(f"linha {n}: classe prevista desconhecida '{previsto}', ignorada")
                continue
            pares.append((real, previsto))
    return pares, avisos


def matriz_confusao(pares: list[tuple[str, str]]) -> np.ndarray:
    colunas = CLASSES + [INCERTO]
    m = np.zeros((len(CLASSES), len(colunas)), dtype=int)
    for real, previsto in pares:
        m[CLASSES.index(real), colunas.index(previsto)] += 1
    return m


def tabela_markdown(m: np.ndarray) -> str:
    colunas = CLASSES + [INCERTO]
    linhas = ["| | " + " | ".join(f"Previsto: {c}" for c in colunas) + " |",
              "| --- |" + " --- |" * len(colunas)]
    for i, real in enumerate(CLASSES):
        linhas.append(f"| **Real: {real}** | " + " | ".join(str(v) for v in m[i]) + " |")
    return "\n".join(linhas)


def salvar_png(m: np.ndarray, titulo: str, destino: Path) -> None:
    colunas = CLASSES + [INCERTO]
    fig, ax = plt.subplots(figsize=(6.4, 4.2), dpi=150)
    ax.imshow(m, cmap="Blues", vmin=0, vmax=max(1, int(m.max())))
    ax.set_xticks(range(len(colunas)), colunas, rotation=20)
    ax.set_yticks(range(len(CLASSES)), CLASSES)
    ax.set_xlabel("Classe prevista")
    ax.set_ylabel("Classe real")
    ax.set_title(titulo, fontsize=11)
    limite = m.max() / 2 if m.max() else 0.5
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            ax.text(j, i, str(m[i, j]), ha="center", va="center",
                    color="white" if m[i, j] > limite else "black", fontsize=12)
    fig.tight_layout()
    destino.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destino)
    plt.close(fig)


def relatorio(pares: list[tuple[str, str]], titulo: str, png: Path) -> str:
    total = len(pares)
    acertos = sum(r == p for r, p in pares)
    m = matriz_confusao(pares)
    salvar_png(m, titulo, png)

    saida = [f"### {titulo}", ""]
    saida.append(f"Acertos: **{acertos} de {total}** ({100 * acertos / total:.1f} %)")
    saida.append("")
    saida.append("| Classe | Acertos | Tentativas | Percentual |")
    saida.append("| --- | --- | --- | --- |")
    for c in CLASSES:
        da_classe = [(r, p) for r, p in pares if r == c]
        ok = sum(r == p for r, p in da_classe)
        pct = f"{100 * ok / len(da_classe):.1f} %" if da_classe else "-"
        saida.append(f"| {c} | {ok} | {len(da_classe)} | {pct} |")
    saida.append(f"| **Total** | **{acertos}** | **{total}** | **{100 * acertos / total:.1f} %** |")
    saida.append("")
    saida.append("Matriz de confusão (quantidade):")
    saida.append("")
    saida.append(tabela_markdown(m))
    saida.append("")

    ambiente = [p for r, p in pares if r == CLASSE_AMBIENTE]
    falsos = [p for p in ambiente if p in ("buzina", "sirene")]
    if ambiente:
        detalhe = ", ".join(f"{falsos.count(c)}x {c}" for c in ("sirene", "buzina") if falsos.count(c))
        saida.append(f"Falsos positivos em {CLASSE_AMBIENTE}: **{len(falsos)} de {len(ambiente)}**"
                     + (f" ({detalhe})" if detalhe else ""))
    incertos = sum(p == INCERTO for _, p in pares)
    if incertos:
        saida.append(f"Resultados uncertain (contam como erro): {incertos}")
    saida.append(f"Imagem da matriz: img/{png.name}")
    saida.append("")
    return "\n".join(saida)


def main() -> int:
    partes = []
    for nome, titulo, png in TESTES:
        caminho = RAIZ / "dados" / nome
        if not caminho.exists():
            print(f"[AVISO] {caminho} não existe, pulando.")
            continue
        try:
            pares, avisos = ler_planilha(caminho)
        except ValueError as erro:
            print(f"[ERRO] {erro}")
            return 1
        for aviso in avisos:
            print(f"[AVISO] {nome}, {aviso}")
        if not pares:
            print(f"[AVISO] {nome} ainda não tem nenhuma linha preenchida.")
            continue
        if len(pares) != 15:
            print(f"[AVISO] {nome} tem {len(pares)} linha(s) válidas; a GS pede 15 (5 por classe).")
        partes.append(relatorio(pares, titulo, RAIZ / "img" / png))

    if not partes:
        print("\nNada para calcular. Preencha a coluna 'previsto' nas planilhas em dados/.")
        return 1

    texto = "\n".join(partes)
    destino = RAIZ / "resultados.md"
    destino.write_text("# Resultados calculados\n\n" + texto, encoding="utf-8")
    print("\n" + texto)
    print(f"Resultados salvos em {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
