# Dependências e fontes — Etapa 02

Verificação em 12/11/2026 (America/Sao_Paulo). Registro anterior: stage01/dependencies.md.

| Dependência | Versão instalada | Uso |
| --- | --- | --- |
| Python | 3.14.7 | Runtime local Windows |
| FastAPI | 0.162.5 | Rotas HTTP e arquivos estáticos |
| Uvicorn | 0.54.0 | Servidor ASGI local |
| HTTPX | 0.28.1 | TestClient nos testes HTTP |
| OpenAI SDK | 3.49.0, extra realtime | SDK oficial para HTTP e WebSocket |
| python-dotenv | 1.2.4 | Leitura isolada do arquivo privado |
| PyAV | 19.0.2 | Validação/conversão de áudio sem FFmpeg global |
| jiwer | 4.0.0 | Avaliação WER |

requirements.txt contém dependências de execução diretamente utilizadas e testadas.
environment.freeze.txt registra também transitivas e ferramentas presentes no venv;
não é um lock portátil para outro sistema/Python. pypdf foi usado na etapa 01 para
ler o enunciado. SoundFile foi instalado durante a inspeção, mas não é usado pelo
aplicativo nem exigido no requirements; o decodificador adotado é PyAV.

Modelos efetivamente requisitados: **gpt-transcribe**, **gpt-6-luna** e
**gpt-realtime-2.1-mini**, voz **marin**. São modelos via serviço OpenAI, não pesos
baixados com licença open source. A licença do SDK não substitui as condições da API.
Os identificadores retornados são aliases; o STT não informou revisão de pesos.
Não foram usados Qwen, faster-whisper ou edge-tts nesta etapa.

## Fontes oficiais consultadas

- [SDK OpenAI](https://developers.openai.com/api/docs/libraries): biblioteca oficial.
- [Transcrição de arquivos](https://developers.openai.com/api/docs/guides/speech-to-text): endpoint de arquivos gpt-transcribe.
- [Guia de transcrição](https://developers.openai.com/api/docs/guides/transcription): gpt-transcribe usa languages, não o antigo language.
- [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna): modelo e esforço none utilizado.
- [Responses](https://developers.openai.com/api/docs/guides/text): mensagens e output_text.
- [TTS](https://developers.openai.com/api/docs/guides/text-to-speech): Realtime é necessário para gpt-realtime-2.1-mini; não usar esse ID em audio/speech.
- [Realtime](https://developers.openai.com/api/docs/guides/realtime-conversations): eventos de áudio, sessão e geração sem contexto.
- [GPT-Realtime-2.1 mini](https://developers.openai.com/api/docs/models/gpt-realtime-2.1-mini): modelo solicitado.
- [Descontinuações](https://developers.openai.com/api/docs/deprecations): não foi adotado fallback para modelos legados de voz/transcrição com retirada anunciada.
- [Controles de dados](https://developers.openai.com/api/docs/guides/your-data): store=False não é retenção zero; regras variam por endpoint/conta.

As assinaturas usadas também foram conferidas no SDK instalado: languages em STT,
Responses e realtime.connect(max_retries=0), além dos tipos de eventos Realtime.
A disponibilidade de conta foi confirmada com models.list e com inferências reais;
a listagem sozinha não foi tratada como comprovação do funcionamento.

## Licenças e recursos

FastAPI: MIT. Uvicorn: BSD-3-Clause. HTTPX: BSD-3-Clause. jiwer: Apache-2.0.
Licenças dos novos pacotes instalados constam em package_metadata.json, extraídas
por importlib.metadata do próprio ambiente, sem consultar qualquer segredo.
Para distribuição, revisar também licenças das bibliotecas nativas incluídas pelo PyAV.

Não há necessidade de GPU local no fluxo atual. A GTX 1060 3 GB permanece disponível,
mas não foi usada. Colab e inferência local de modelos continuam sem validação.
Internet e API paga são requisitos; não prometer disponibilidade, preço fixo,
qualidade humana ou latência garantida. Foram registrados tokens/duração quando
informados; não foi consultada a fatura nem calculado um valor como se fosse cobrado.
