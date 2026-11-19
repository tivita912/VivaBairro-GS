# Estado atual, histórico de execução e pendências — VivaBairro Voz

**Data de referência:** 17/11/2026. Números extraídos de arquivos realmente existentes no projeto após a rodada STT de R07. Para estado atualizado, execute scripts.gs_preflight --dry-run.

## 1. O que já foi construído

O VivaBairro Voz é um assistente CitizenTech em português para orientar relatos verificáveis de calçadas e acessibilidade, buracos em vias, iluminação pública, descarte irregular de resíduos e alagamentos. Não abre protocolo em órgão público e não promete atendimento municipal.

- Backend FastAPI, entrada por microfone e upload; decodificação/normalização de áudio por PyAV; STT gpt-transcribe.
- LLM com system prompt, domínio, base de conhecimento versionada e memória contextual.
- Adaptação textual para fala e saída de TTS com voz sintética pronta, texto também exibido.
- Interface com player, controle de sessão, consentimento, tempos de cada componente e proxy de início de reprodução.
- Scripts para comparar Whisper local (whisper.cpp, modelo base multilíngue Q5_1) com STT remoto.
- Validação do pipeline em um teste técnico com três uploads de gravações humanas previamente existentes. A primeira tentativa falhou no segundo turno TTS; a segunda concluiu 3/3 turnos com áudio. **Esse ensaio não é uma das dez conversas acadêmicas interativas.**
- Vídeo narrado final de 199,9 segundos, mostrando três turnos, continuidade e recusa.
- PDF acadêmico preliminar atualizado, ainda não é entrega final.
- Menu PowerShell e ferramentas portáteis para importar evidências, calcular métricas e só emitir entrega final após cumprir todos os bloqueios.
- Testes previamente reportados: 101 Python e quatro JavaScript, ambiente restaurado e verificado fora do OneDrive. Consulte o relatório de nova verificação neste pacote para saber o resultado desta execução.

## 2. Números verificáveis

| Série | Realizado | Ainda necessário |
| --- | --- | --- |
| STT | 13 áudios originais, sete de Rafael e seis de Thiago; **13 transcrições**; latência média **1,242 s** (entre 0,688 e 1,963 s) | Sete áudios G08–G14 de Gustavo, referências humanas literais conferidas, ruídos reais verificados, WER |
| LLM | 30 respostas reais e 30 classificações **feitas por IA**, identificadas como tal. A triagem classificou 28 adequadas/30 (93,33%) e 5/5 recusas adequadas | Revisão independente recomendada para Q19 e Q23; não apresentar julgamento por IA como julgamento humano |
| TTS | 10 WAVs reais gerados e hashes conferidos, com falha/reexecução de T05 documentada | 30 avaliações humanas: 10 notas de clareza e naturalidade por cada uma de três pessoas |
| Ponta a ponta | Fluxo técnico comprovado por ensaio e vídeo | 10 conversas **interativas** com ao menos três turnos, eventos playing e latências de cada etapa |
| Comparação STT | Dois modelos instaláveis; rascunhos locais para 13 entradas | 20 pares com referências humanas verificadas, comparação de WER/latência e justificativa de escolha |
| Ética e retenção | Consentimento na interface, registros de autorização por declaração do responsável, arquivos separados do Git | Confirmar transferência e entrega de vozes ao professor, retenção, acesso e riscos de viés |
| Relatório | Versão preliminar com arquitetura, sistema e resultados parciais | Inserir métricas de todas as séries, verificar diagramação e confirmar edição com professor |

**R07:** Rafael foi autorizado segundo declaração escrita de Thiago em 17/11/2026; arquivo e origem do aceite estão identificados. R07 foi transcrito com sucesso; isso não é autorização irrestrita de publicação.

**WER:** não existe número válido porque 0/20 referências foram marcadas como revisadas por pessoa. Não usar a transcrição do modelo ou o roteiro original como 'verdade' sem ouvir o áudio.

**Ruído:** 0/5 confirmados; cinco arquivos têm apenas indicação de ruído *planejado*: R04, R07, G11, G14 e T18. A marcação depende de escuta e o arquivo pode não conter o ruído esperado.

## 3. Tarefas que não dependem das gravações de Gustavo

1. Thiago e Rafael ouvem as 13 gravações já existentes, escrevem as frases **literais**, preservando diferenças em relação ao roteiro; cada um confere gravações do outro, registra o identificador da revisão e estado de ruído.
2. Thiago e Rafael realizam C01–C07 (quatro + três) com três turnos cada, aguardando que o participante ouça a resposta antes de formular a seguinte. Salvar as evidências no navegador e importar JSON de cada turno. **Não reutilizar três perguntas prontas como conversa simulada.**
3. Thiago (P01) e Rafael (P02) ouvem o kit completo de dez WAVs, atribuem duas notas por áudio e devolvem CSV individual.
4. Conferir Q19/Q23 e demais julgamentos LLM se desejado; marcar a revisão como humana somente quando houver avaliador humano real, preservando dados da IA.
5. Recalcular métricas parciais com o que já estiver verificado; o relatório deve continuar preliminar.

**Nenhuma dessas atividades humanas pode ser executada por uma automação que finja ter ouvido e julgado como integrante da equipe.**

## 4. O que Gustavo fará depois

1. Restaurar o código e o pacote privado autorizados, sem copiar credenciais de Thiago.
2. Importar G08–G14, conferir ID de cada gravação, literalidade, ruído e consentimento.
3. Obter revisão humana cruzada de todo o corpus para fechar 20/20 e executar somente STT novos e autorizados.
4. Avaliar os dez WAVs como P03 e devolver o CSV; incorporar as três fichas.
5. Executar C08–C10, três turnos reais por sessão, ouvindo cada resposta e registrando latências e WAVs.
6. Comparar os dois STT com referência revisada, justificar escolha de configuração e gerar PDF final após auditoria.

## 5. Pendências acadêmicas não relacionadas a áudio

- O professor nomeia o enunciado GS 2027, mas a pasta do grupo aponta 2026.2. Conferir edição e prazo no ambiente de aula.
- Confirmar nomes completos e RMs do grupo na capa; o PDF atual identifica Thiago Santana Danyluk RM 562286, Rafael de Paiva Ramos RM 563978, Gustavo Civita Gonçalves RM 561932. Validar junto aos integrantes.
- Validar autorizações específicas de inclusão e compartilhamento de gravações no link final com o professor. A declaração de envio interno a Gustavo não substitui o consentimento para o docente.
- Verificar permissões efetivas de acesso e política de retenção do OneDrive. O ZIP de evidências tem hashes, mas hash não é criptografia.
- Verificar consistência final entre resumo, gráficos, tabelas, planilhas, código, vídeo e enunciado. Não declarar que nota 100 está garantida.

## 6. Fontes internas para a auditoria

- Documento original: ENUNCIADO_OFICIAL_GS_2TIAPY.pdf
- Professor, requisito a requisito: ORIENTACOES_DO_PROFESSOR.md
- Rubrica + responsável: CHECKLIST_ENTREGA_FINAL.md
- Rodada STT real: evaluation/results/stt_relatorio_parcial.md e evaluation/stt_manifest.csv (privado)
- LLM: evaluation/llm_ratings.csv (privado) e docs/academic/AUDITORIA_LLM.md
- TTS: evaluation/tts_samples.csv (privado) e kit_tts_avaliadores.zip
- Ponta a ponta: evaluation/coleta_e2e_upload.md
- Verificação portátil: scripts/gs_preflight.py e scripts/finalizar_gs.py
- Instruções de recuperação: GUIA_GUSTAVO.md e GUIA_OPERACIONAL_COMPLETO.md
