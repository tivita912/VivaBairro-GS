# VivaBairro · Sua Voz na Cidade

FIAP · Global Solution 2026.2 · Generative AI & Advanced Nets · 2TIAPY

- Gustavo Civita Gonçalves · RM 561932
- Rafael de Paiva Ramos · RM 563978
- Thiago Santana Danyluk · RM 562286

O assistente recebe descrições de problemas urbanos, sugere categoria e prioridade, prepara um rascunho editável e indica referências oficiais quando o município informado é São Paulo (capital). A prioridade é preliminar. O cidadão revisa, copia e encaminha o relato pelo canal oficial.

## Executar no Windows

Entre em codigo/ e use Python 3.12 x64. Os comandos usam o executável do ambiente virtual diretamente.

```powershell
py -3.12 -m venv .venv
$python = ".\.venv\Scripts\python.exe"
& $python -m pip install -r requirements.txt
$env:GENERATOR_PROVIDER = 'baseline'
& $python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Abra [a interface local](http://127.0.0.1:8000). Selecione o município da ocorrência, descreva um problema e informe uma referência pública quando possível. O baseline apresenta o primeiro trecho recuperado. Em perigo imediato, a interface orienta acionar os serviços locais sem aguardar a inferência.

## Qwen local

Obtenha os [binários llama.cpp b12255](https://github.com/ggml-org/llama.cpp/releases/tag/b12255) e os [pesos oficiais do Qwen2.5 3B Instruct Q4_K_M](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/blob/7dabda4/qwen2.5-3b-instruct-q4_k_m.gguf). O SHA-256 dos pesos conferidos é 626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d. No terminal dos binários:

```powershell
.\llama-server.exe -m .\qwen2.5-3b-instruct-q4_k_m.gguf --alias qwen2.5-3b-instruct-q4_k_m --host 127.0.0.1 --port 18081 -c 4096 -np 1 -t 8 -ngl 0
```

Em outro terminal, na pasta codigo/:

```powershell
Invoke-RestMethod http://127.0.0.1:18081/health
$python = ".\.venv\Scripts\python.exe"
$env:GENERATOR_PROVIDER = 'llamacpp'
$env:LLAMACPP_URL = 'http://127.0.0.1:18081/v1/chat/completions'
& $python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

O provedor Ollama também possui adaptador local. A rodada acadêmica verificou llama.cpp. O seletor usa temperatura 0,1, seed 42 e até 64 tokens. A saída é restringida pelo esquema JSON aos IDs recuperados ou à abstenção. A API publica a paráfrase curada do trecho selecionado com sua referência.

## Reprodução e evidências

```powershell
$python = ".\.venv\Scripts\python.exe"
$env:GENERATOR_PROVIDER = 'baseline'
$run = Get-Date -Format yyyyMMdd-HHmmss
& $python -m pytest -q
& $python evaluate.py --provider baseline --output "../evidencias/reexec-baseline-$run"
& $python evaluate.py --provider llamacpp --output "../evidencias/reexec-qwen-$run" --runtime llama.cpp-b12255 --weights-sha256 626b4a6678b86442240e33df819e00132d3ba7dddfe1cdc4fbb18e0a9615c62d
& $python -m pip install -r requirements-docs.txt
& $python make_notebook.py
& $python build_report.py
```

A última avaliação exige o modelo rodando na porta 18081. O notebook aceita VIVABAIRRO_NOTEBOOK_LLM=1 no ambiente do kernel para reproduzir uma consulta real. Cada avaliação escreve em uma pasta nova.

- [Corpus e metadados](corpus/fontes.json) e [documentação das fontes](docs/CORPUS.md)
- [Contrato de integração](docs/INTEGRACAO.md)
- [Auditoria do barema](../AUDITORIA_FINAL.md)
- [Notebook](../notebook/VivaBairro_GS_2026_2.ipynb)

O protótipo externo e um registro de aprovação da proposta ainda precisam ser confirmados com o grupo. A demonstração integra o assistente à interface VivaBairro entregue neste pacote.

