# VivaBairro

Global Solution 2026.2 · FIAP · Tecnólogo em Inteligência Artificial · Turma 2TIAPY

| Integrante | RM |
| --- | --- |
| Gustavo Civita Gonçalves | 561932 |
| Rafael de Paiva Ramos | 563978 |
| Thiago Santana Danyluk | 562286 |

O VivaBairro é a solução CitizenTech do grupo. O morador relata um problema de zeladoria do bairro (buraco, calçada quebrada, falta de iluminação, lixo ou alagamento) e a IA ajuda a organizar o relato. O público principal são moradores com mobilidade reduzida.

Este repositório reúne o que foi desenvolvido e entregue em cada disciplina. É um protótipo acadêmico, com dados sintéticos ou públicos. Ele não envia nada à Prefeitura.

## Pastas

| Pasta | Disciplina | O que tem |
| --- | --- | --- |
| `01-front-end-mobile` | Front End & Mobile | Interface de relato com revisão humana e painel (Streamlit e FastAPI) |
| `02-generative-ai` | Generative AI & Advanced Nets | Assistente que indica o canal oficial, com RAG e modelo local |
| `03-pln-assistente-voz` | Processamento de Linguagem Natural | Assistente de voz (fala, texto, fala) |
| `04-iot-sonoro` | Physical Computing, Embedded AI, Robotics & Cognitive IoT | Reconhecimento de sirene e buzina no celular |
| `05-visao-computacional` | Visão Computacional | Detector de fissuras em concreto em fotos e vídeos |
| `06-rpa-triagem` | AI for Robotic Process Automation | Robô de triagem de relatos em lote |
| `07-cluster` | Cluster Computing, Computação Neuromórfica e Supercomputadores | Simulação de cluster no iSPD |
| `08-computacao-quantica` | Computação Quântica & IA | Relatório com gargalo, capacidade quântica e roadmap |
| `09-governanca` | Governança em IA e Business Analytics | Relatório de integração dos módulos |

Cada pasta tem o próprio README ou relatório, com as instruções e os resultados medidos.

## Como executar os módulos com código

Todos usam Python. Os comandos abaixo são executados dentro da pasta de cada módulo.

Front End & Mobile:

```
pip install -r backend/requirements.txt -r frontend/requirements.txt
uvicorn backend.app.main:app
streamlit run frontend/app.py
```

Generative AI (dentro de `02-generative-ai/codigo`):

```
pip install -r requirements.txt
uvicorn app:app --host 127.0.0.1 --port 8000
```

Visão Computacional:

```
pip install -r requirements.txt
streamlit run app/app.py
```

RPA:

```
pip install -r requirements.txt
python main.py
```

O assistente de voz (`03-pln-assistente-voz/codigo`) e os detalhes de configuração de cada módulo estão nos READMEs das pastas. Nenhuma chave de API está no repositório: onde ela é necessária, há um arquivo de exemplo para copiar.

## Integração

Os módulos tratam do mesmo problema e do mesmo público, mas rodam separadamente. A ligação que existe em código é o contrato do relato: o robô de RPA usa as mesmas categorias e os mesmos limites de campo da interface. O relatório em `09-governanca` descreve o que está integrado e o que não está.

## O que não está no repositório

- Gravações de voz usadas na avaliação do assistente de voz, por conterem voz de pessoas.
- A base de imagens de concreto (Özgenel, 2018), que deve ser baixada do Mendeley Data conforme o README de Visão Computacional.
- Arquivos de vídeo grandes. O vídeo de demonstração está no link abaixo.

## Links

- Vídeo de demonstração: https://youtu.be/KljYfzTRhOA
