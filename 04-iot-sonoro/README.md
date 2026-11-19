# VivaBairro Sonoro

GS 2026.2 – IoT (2TIAP). Celular reconhece **sirene**, **buzina** e **ambiente de rua** com MFE + CNN no Edge Impulse e mostra o resultado na tela.

| Integrante | RM |
| --- | --- |
| Gustavo Civita Gonçalves | 561932 |
| Rafael de Paiva Ramos | 563978 |
| Thiago Santana Danyluk | 562286 |

Relatório: `relatorio.pdf` (também em `.docx`).

## Uso

```
pip install -r requirements.txt
```

Converter um WAV para 16 kHz, mono, PCM16, em trechos de 5 s:

```
python scripts/preparar_audios.py converter entrada.wav saida/ --rotulo sirene
python scripts/preparar_audios.py verificar saida/
```

Calcular acertos e matriz de confusão a partir de `dados/teste_arquivos.csv`:

```
python scripts/calcular_resultados.py
```

Gera `resultados.md` e as matrizes em `img/`.
