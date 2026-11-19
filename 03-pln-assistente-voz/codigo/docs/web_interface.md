# VivaBairro Voz | Interface web própria

O atendimento agora abre em uma página com identidade visual cívica, um fluxo de
quatro etapas e um painel de informações. A captura é liberada após três aceites.
Quem usa o microfone pode ouvir a prévia antes de enviar. Os resultados apresentam
transcrição, orientação e player de voz sintética, com ações de nova tentativa e
limpeza da conversa. O painel lateral reúne temas e fontes da base, histórico e
métricas recolhíveis.

## Como executar

Dentro da pasta do projeto, no PowerShell:

~~~powershell
& ./.venv/Scripts/python.exe app.py
~~~

Abra [127.0.0.1:7860](http://127.0.0.1:7860). Se a porta estiver ocupada, defina
$env:VIVABAIRRO_PORT = '17863' antes de executar e abra
[127.0.0.1:17863](http://127.0.0.1:17863). Para outro ambiente, instale
requirements.txt no ambiente virtual. app.py --check continua disponível.

## Arquitetura e decisões de UX

- FastAPI e Uvicorn no mesmo processo servem HTML, CSS, JavaScript e recursos locais.
  O navegador usa MediaRecorder e File API. O envio ao FastAPI começa quando a
  pessoa aciona **Enviar áudio**.
- As rotas /api/info, /api/consent, /api/turn, /api/audio/{name} e /api/clear
  adaptam o HTTP ao VoiceController. O servidor limita tamanho e duração,
  exige os aceites vigentes e restringe WAV e histórico à sessão de origem.
  O token aleatório fica apenas em memória da aba e é enviado por cabeçalho.
- O VoiceController, pipeline, STT, LLM, TTS, prompt, base, regras de consentimento,
  histórico, descarte e orçamentos da Etapa 02 continuam operando. A nova camada
  chama os contratos Python existentes.
- A direção visual usa verde institucional, fundo claro, tipografia Segoe UI
  com fallback local, bordas suaves e uma ilustração editorial do bairro.
  O layout organiza a tarefa principal à esquerda e empilha o apoio abaixo em
  telas estreitas. Foco visível, labels, regiões de status e erro, alvos de 44 px
  nos controles principais e player nativo dão suporte à operação por teclado.
- O conceito guiou cabeçalho e ordem da cópia, proporções das colunas, tipografia,
  paleta, ilustração e hierarquia dos controles. O texto dos três aceites acompanha
  o aviso vigente. A ação de salvar registro que apareceu no conceito foi omitida,
  pois exportação de dados estava fora do fluxo solicitado.

## Arquivos

| Tipo | Arquivos |
| --- | --- |
| Criados | src/web.py, web/index.html, web/assets/site.css, web/assets/site.js, web/assets/icon.svg, web/assets/bairro.webp, docs/web_interface.md e docs/web_validation_evidence.json |
| Alterados | app.py, requirements.txt, README.md, scripts/smoke_ui.py, scripts/verify.py, tests/test_app.py, tests/test_ui_layout.py, docs/architecture.md, docs/dependencies.md, docs/consent_template.md e docs/manual_voice_test.md |

## Verificação

~~~powershell
& ./.venv/Scripts/python.exe scripts/verify.py --ui
~~~

A suíte passou com 81 testes. A validação HTTP checou a página e os recursos,
três consentimentos e versão do aviso, upload limitado, resposta com WAV,
histórico, isolamento e revogação. Os testes do fluxo HTTP usam adaptadores
sintéticos. As evidências completas estão em
web_validation_evidence.json (na cópia de trabalho da equipe).

No navegador integrado, a página abriu com a identidade e os controles esperados.
Foram conferidos desktop, largura de 390 px e a grade sem rolagem horizontal.
A confirmação revelou os controles e moveu o foco para a captura. A limpeza
restaurou os aceites desmarcados, bloqueou a captura e moveu o foco para o aviso.
A captura de desktop foi comparada visualmente ao conceito e o console verificado
durante a inspeção. A aplicação foi pré-visualizada na porta 17863 porque as
portas 7860 e 7862 estavam ocupadas.

Próximo refinamento: validar gravação e escuta com uma pessoa autorizada em
dispositivos reais, incluindo Safari móvel e leitor de tela. O tempo de início
de reprodução continua sem instrumentação. A validação desta entrega consumiu
zero chamadas pagas.
