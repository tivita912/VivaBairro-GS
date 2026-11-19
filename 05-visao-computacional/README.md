# VivaBairro | CitizenTech: Visão Computacional para Manutenção Urbana

Global Solution 2026.2, Turma 2TIA.

Módulo do protótipo CitizenTech que identifica **fissuras em concreto** (muros, paredes, viadutos e calçadas) em fotos, sequências de fotos e vídeos curtos. O resultado mostra onde está a possível fissura e a confiança do modelo, e sugere o local para inspeção técnica. É uma ferramenta de triagem: quem decide sobre a gravidade e a segurança da estrutura é um engenheiro.

## Integrantes

- Rafael de Paiva Ramos (RM 563978)
- Thiago Santana Danyluk (RM 562286)
- Gustavo Civita Gonçalves (RM 561932)

## Resultados

| Item | Resultado |
|---|---|
| Base | Concrete Crack Images for Classification (Özgenel, 2018), amostra de 12.000 imagens |
| Modelo | MobileNetV2 pré-treinada na ImageNet, com ajuste fino |
| Teste (1.800 imagens) | precisão 1,000, recall 0,998 e F1 0,999 |
| Limiar de confiança | 0,95 (escolhido na validação para recall ≥ 99%) |
| Latência por foto | ~8 ms na GTX 1660 Super e ~14 ms na CPU i7-10700KF |
| Vídeo 908x680 (12 blocos por quadro) | 40,9 FPS na GTX 1660 Super |
| Fotos reais de rua (48, fora do domínio) | 81% de acerto e F1 0,877 (alarmes falsos com vegetação e objetos) |

Detalhes, análise de erros e justificativas estão no relatório (`entrega/Relatorio_GS_Visao_Computacional.docx`).

## Estrutura

```
app/app.py                  App Streamlit (módulo Manutenção Urbana do CitizenTech)
src/detector.py             Inferência: foto, varredura em blocos e vídeo
src/dataset.py              Dataset e interferências (sombra, luz, ruído, desfoque, riscos)
notebooks/                  Notebook com preparação, treino, avaliação e desempenho
models/                     Modelo treinado (.pt) e metadados (limiar, métricas)
outputs/                    Gráficos, tabelas de métricas, desempenho e vídeo processado
data/demo/                  Vídeo e sequência de imagens para demonstração
data/teste_rua/             Teste com fotos reais de rua (créditos, resultados e prancha)
data/Positive, Negative     Base de imagens (não vai no pacote, baixar abaixo)
```

## Como executar

1. Instale as dependências (Python 3.10 ou mais novo):

   ```
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126   # com GPU NVIDIA
   pip install -r requirements.txt
   ```

2. Abra o app (o modelo treinado já está em `models/`, não precisa treinar):

   ```
   streamlit run app/app.py
   ```

3. Para refazer o treino e a avaliação, baixe a base em https://data.mendeley.com/datasets/5y9wdsg2zt/1, extraia as pastas `Positive` e `Negative` dentro de `data/` e rode:

   ```
   python -m nbconvert --to notebook --execute --inplace notebooks/deteccao_fissuras.ipynb
   ```

   Com a GTX 1660 Super, o notebook inteiro leva uns 15 minutos (3 modelos de 4 épocas).

## Uso responsável

- As fotos são processadas na hora e não são guardadas. Só o resultado entra na fila de inspeção.
- Evite fotografar pessoas e placas de veículos (LGPD).
- Todo resultado passa pela confirmação de uma pessoa antes do registro.
