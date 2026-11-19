# VivaBairro Voz

Para instalar em outro computador, restaurar evidências e conduzir a coleta, use o
[guia do Gustavo](docs/academic/GUIA_GUSTAVO.md) e o [checklist final](docs/academic/CHECKLIST_ENTREGA_FINAL.md).

Assistente acadêmico em português para relatos de buracos, calçadas e acessibilidade,
iluminação, lixo irregular e alagamentos. O projeto ajuda a preparar relatos; não
abre solicitações, não gera protocolos e não aciona equipes públicas.

O painel web usa FastAPI, HTML, CSS e JavaScript próprios. O fluxo começa com
consentimento, libera microfone e upload e apresenta transcrição, orientação,
áudio sintético, histórico e métricas. Veja a [entrega da interface](docs/web_interface.md).

## Abrir a aplicação

No PowerShell, a partir da pasta que contém `vivabairro-voz`:

```powershell
Set-Location -LiteralPath 'vivabairro-voz'
& ./.venv/Scripts/python.exe app.py --check
& ./.venv/Scripts/python.exe app.py
```

Abra [o painel local](http://127.0.0.1:7860). Encerre com Ctrl+C.
Se a porta estiver ocupada, escolha outra na mesma janela do PowerShell:

~~~powershell
$env:VIVABAIRRO_PORT = '17863'
& ./.venv/Scripts/python.exe app.py
~~~

Nesse caso, abra [o painel na porta 17863](http://127.0.0.1:17863).
O ambiente virtual já está instalado nesta máquina. Para outra instalação Windows:

```powershell
python -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r requirements.txt
& ./.venv/Scripts/python.exe -m pip check
```

Ambiente verificado: Python 3.14.7, FastAPI 0.162.5, Uvicorn 0.54.0, OpenAI SDK 3.49.0,
python-dotenv 1.2.4, PyAV 19.0.2 e jiwer 4.0.0. Não precisa de GPU para as APIs.
São necessários internet, acesso aos modelos e saldo/limites adequados na OpenAI.
Não foram feitos deploy, commit, push ou publicação.

## Configuração privada

O backend lê **somente** `%LOCALAPPDATA%\VivaBairroVoz\.env`, usando
`os.environ["LOCALAPPDATA"]`, `Path` e python-dotenv sem interpolação.
O arquivo existente não é sobrescrito. A chave nunca é devolvida ao navegador.
Não coloque esse arquivo no projeto, no OneDrive, em logs ou na conversa.

Variáveis esperadas no arquivo privado:

| Variável | Valor/uso |
| --- | --- |
| OPENAI_API_KEY | Chave já cadastrada pelo usuário; nunca exibida |
| OPENAI_STT_MODEL | gpt-transcribe |
| OPENAI_LLM_MODEL | gpt-6-luna |
| OPENAI_TTS_MODEL | gpt-realtime-2.1-mini |
| OPENAI_TTS_VOICE | marin |

Os modelos acima foram usados efetivamente nas verificações. Não há troca silenciosa
de modelo ou provedor. Identificadores configuráveis não garantem compatibilidade:
validar outro modelo explicitamente antes de usá-lo. O TTS atual usa **Realtime**,
pois o modelo solicitado não é aceito no endpoint `/audio/speech`.

`app.py --check` é diagnóstico local e não chama a API. Ausência de chave, marcador
não preenchido ou configuração inválida produz mensagem segura e bloqueia a captura.
A autenticação mínima real está em `scripts/live_check.py --run --auth-only`;
esse comando consome uma tentativa do orçamento técnico, mas não faz inferência.

## Como usar

1. Abra **Como seus dados são usados** para consultar o aviso. Marque os três aceites.
2. Clique em **Confirmar consentimento** para liberar os controles de captura.
3. Grave pelo microfone ou escolha um arquivo. Use a prévia para conferir e clique em **Enviar áudio**.
4. Revise a transcrição e a orientação. Use o player para ouvir a voz sintética.
5. Use **Nova tentativa** para gravar uma pergunta de continuação. **Limpar conversa** apaga o histórico e retira os aceites da sessão.

WAV PCM de 16 bits mono/estéreo é validado diretamente. MP3, M4A, MP4, WebM, OGG
ou FLAC são decodificados com PyAV para WAV mono de 16 kHz. O limite padrão é
60 segundos e 10 MiB. O gravador tem um temporizador de parada. O servidor valida a duração\ndecodificada antes de chamar a OpenAI.
Não fale nomes, documentos, telefone ou endereço residencial completo.

## Arquitetura e comportamento

```text
HTML / MediaRecorder -> FastAPI -> VoiceController
  -> validação e conversão -> OpenAISTT
  -> histórico da sessão + base curada + system prompt v1
  -> OpenAILLM (Responses, store=False)
  -> PortugueseSpeechAdapter (normalização conservadora para voz)
  -> OpenAIRealtimeTTS (leitura literal, sessão independente)
  -> WAV + texto + histórico + métricas
```

A base e o prompt da etapa 01 foram preservados. Histórico limitado a seis pares
de turnos, sem banco de dados. Cada sessão tem estado, contador e pasta próprios.
STT, LLM e TTS continuam substituíveis por contratos independentes do provedor.

O TTS acumula PCM e a transcrição da síntese. Se essa transcrição divergir do texto
autorizado, o áudio não é liberado. Essa checagem não substitui escuta humana nem
comprova que a transcrição declarada pelo próprio modelo coincide com cada som.
O texto original do LLM continua na interface e no histórico. O adaptador aplica ao
texto de fala regras para Markdown, links, emojis, números, datas, horários e siglas.
Preserva identificadores e formatos ambíguos e sinaliza ambiguidades e trechos longos
sem pausa segura. Os testes locais cobrem a transformação. A escuta formal segue pendente.

Se uma etapa posterior falhar, a transcrição e eventual resposta já recebidas ficam
visíveis, com mensagem de erro. O turno incompleto não entra no histórico contextual.
A solicitação do cidadão continua sujeita à sua revisão humana.

## Custos e limites

`config.example.env` contém apenas limites públicos. Opcionalmente copie para `.env`
e execute `app.py --env-file .env`. Esse arquivo não é o arquivo privado da chave.
Variáveis VIVABAIRRO_ do ambiente prevalecem sobre esse arquivo.

| Configuração | Padrão |
| --- | ---: |
| VIVABAIRRO_MAX_AUDIO_SECONDS / MAX_AUDIO_MB | 60 / 10 |
| VIVABAIRRO_SESSION_REQUESTS | 30 tentativas por sessão |
| VIVABAIRRO_MAX_OUTPUT_TOKENS / MAX_RESPONSE_CHARS | 300 / 900 |
| VIVABAIRRO_TIMEOUT_SECONDS | 45 por chamada |
| VIVABAIRRO_RETRIES | 0 |
| VIVABAIRRO_AUTO_TEST_CALLS | 12, máximo permitido pelo verificador |
| VIVABAIRRO_RETENTION_SECONDS | 600 |
| VIVABAIRRO_TTS_MAX_TOKENS | 1500 |

Os nomes completos de todas as variáveis estão em `config.example.env`.
Retries e reconexões automáticas do SDK estão desligados. Se configurar retries
na aplicação, cada tentativa conta. Falhas também podem gerar cobrança.
Limpar a conversa não reinicia seu contador. Uma nova sessão/reinício pode criar
novo orçamento; esses limites locais não são um teto financeiro da conta.

O verificador pago guarda um contador persistente em `.runtime/live_budget.json`
e uma trava de execução. Consulte o registro atual antes de repetir ensaios pagos.
A interface mostra consumo quando a API o informa. `cost_charged=null` indica que
não consultamos faturamento; tokens e estimativas não são cobranças efetivas.

## Privacidade e retenção

O servidor escuta em 127.0.0.1. A aplicação usa uma sessão local isolada por aba
e um identificador opaco mantido em memória no navegador.
A chave fica exclusivamente no backend e os destinos HTTP/WebSocket da OpenAI são explícitos.

Áudios operacionais ficam no temporário do usuário, fora do OneDrive.
O arquivo enviado ao FastAPI e a cópia de preparação são descartados após
transcrição, falha ou interrupção do envio. A saída pertence à sessão e expira
junto com ela. O próximo turno substitui a saída anterior. O histórico fica em
memória. **Limpar conversa** remove o conteúdo local e retira o consentimento.

Fechar à força o processo pode deixar arquivos no temporário; não há promessa de
apagamento seguro de SSD, backups, cópias do navegador ou limpeza em falha abrupta.
O painel remove texto e áudio da tela no fim do temporizador de inatividade.
A retenção do provedor é separada: `store=False` não equivale a Zero Data Retention.
Consulte [a política oficial de dados](https://developers.openai.com/api/docs/guides/your-data).

## Verificação e avaliação

```powershell
& ./.venv/Scripts/python.exe scripts/verify.py --ui --evidence evaluation/results/verify_nova_rodada.json
```

Esse comando não chama modelos nem gasta API. Executa testes locais, importações,
compilação, diagnóstico, pip check e inicialização HTTP. O registro da auditoria
corretiva está em verificacao_corretiva.json (na cópia de trabalho da equipe).
Use `--evidence` com um nome novo para preservar verificações anteriores.

Testes reais pagos são separados e exigem `--run`. stage02_live.json (na cópia de trabalho da equipe)
registra chamadas realizadas, inclusive duas saídas TTS recusadas antes da correção.
Esse registro técnico usa entradas de desenvolvimento. O vídeo narrado de 199,9 s
mostra três turnos reais, com continuação e recusa. A interface registra `playing`
como aproximação de início de reprodução e distingue seleção de arquivo de captura.

Na atualização de 17/11/2026, o corpus STT contém 13 gravações
identificadas e **13 transcrições remotas** (sete de Rafael e seis de Thiago);
autorização de R07 registrada por declaração do responsável. Faltam
sete arquivos de Gustavo e as referências humanas verificadas para calcular WER. O LLM executou os 30 casos reais; o avaliador GPT-6 foi registrado explicitamente como IA, classificando 28/30 respostas adequadas e 5/5 recusas. Recomenda-se revisão humana independente, principalmente Q19 e Q23. O TTS gerou
dez WAVs reais, que ainda precisam de avaliação individual de três pessoas.
Um ensaio técnico de três turnos por replay de uploads passou na segunda tentativa;
ele não substitui as dez conversas humanas requeridas.
Consulte [resultados verificados](docs/academic/resultados.md), a
[metodologia](docs/academic/metodologia.md) e o
[PDF preliminar atualizado com 13 STT](docs/academic/relatorio_global_solution_preliminar_STT13_20261117.pdf).
Para reproduzir a geração e inspeção do PDF, instale também os pacotes opcionais de
[requirements-academic.txt](requirements-academic.txt).

## Documentação e próximos passos

- [Arquitetura e contratos](docs/architecture.md).
- [Rastreabilidade R01–R13](docs/checklist.md).
- [Dependências, modelos e fontes](docs/dependencies.md).
- Relatório da execução (na cópia de trabalho da equipe).
- [Roteiro de demonstração humana](docs/manual_voice_test.md).
- [Instrumentos de avaliação](evaluation/README.md).
- [Relatório acadêmico preliminar atualizado](docs/academic/relatorio_global_solution_preliminar_STT13_20261117.pdf).
- [PDF original do professor](docs/academic/ENUNCIADO_OFICIAL_GS_2TIAPY.pdf).
- [Resumo das exigências do professor](docs/academic/ORIENTACOES_DO_PROFESSOR.md).
- [Estado e pendências reais](docs/academic/ESTADO_ATUAL_E_PENDENCIAS.md).
- [Guia operacional completo para Gustavo](docs/academic/GUIA_OPERACIONAL_COMPLETO.md).
- Vídeo final narrado (na cópia de trabalho da equipe).

Integram o grupo Thiago Santana Danyluk, Rafael de Paiva Ramos e Gustavo Civita Gonçalves.
Os RMs constam no relatório acadêmico. A documentação interna usa 2026.2 e o
enunciado traz GS 2027. Confirme a edição e o calendário com o docente.
Documentos e evidências anteriores foram preservados em `docs/stage01/`.
