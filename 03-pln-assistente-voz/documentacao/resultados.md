# Resultados acadêmicos verificados — atualização 17/11/2026 (São Paulo)

Os testes iniciais foram realizados no final de 16/11 e R07 foi transcrito após autorização adicional informada em 17/11/2026. Este documento diferencia execuções reais, triagem por IA e avaliação humana.

| Experimento | Estado real | Indicador |
| --- | --- | --- |
| STT | 13 áudios íntegros; **13 transcritos** com gpt-transcribe; duas vozes (Rafael 7 + Thiago 6) | **1,242 s** de latência média em 13 chamadas; 0 referências humanas confirmadas e WER indisponível |
| LLM | 30 de 30 respostas reais armazenadas; cinco continuações e cinco casos fora do escopo | Latência média de 1,831 s; avaliação por IA identificada: **28/30 adequadas (93,33%)** e **5/5 recusas adequadas (100%)**. Revisão humana independente recomendada. |
| TTS | 10 de 10 WAVs reais gerados com voz marin; hashes e formato PCM confirmados | 0 de 30 avaliações humanas; pico máximo -3,18 dBFS; T05 precisou de uma nova tentativa por speech_mismatch |
| Ponta a ponta | Ensaio técnico de três uploads, uma sessão, três respostas e três WAVs concluído na segunda tentativa | Não é conversa humana interativa e não contém evento de reprodução no navegador; 0 de 10 sessões acadêmicas |
| Comparação A/B | gpt-transcribe (A) e Whisper base local (B) disponíveis | 0 pares com referências humanas verificadas; WER comparativo pendente |

## Evidências e rastreabilidade

- STT: [relatório parcial](../../evaluation/results/stt_relatorio_parcial.md), [manifesto privado](../../evaluation/stt_manifest.csv), [referências para revisão](../../evaluation/results/stt_referencias_revisao.csv), [interface de escuta](../../evaluation/results/stt_revisao.html).
- LLM: [respostas literais e avaliação identificada como IA](../../evaluation/llm_ratings.csv), [análise detalhada e ressalvas](../../evaluation/results/llm_triagem_assistente.md), [CSV da triagem](../../evaluation/results/llm_triagem_assistente.csv) e [backup anterior às notas](../../evaluation/results/llm_ratings_antes_da_avaliacao_por_ia.csv).
- TTS: [catálogo de sínteses reais](../../evaluation/tts_samples.csv), [verificação técnica](../../evaluation/results/tts_verificacao_tecnica.json) e [kit com dez WAVs para WhatsApp](../../evaluation/results/kit_tts_whatsapp_real.zip).
- Ponta a ponta: [primeira tentativa com erro real](../../evaluation/results/ensaio_tecnico_upload_3_turnos/resultado.json) e [segunda tentativa com três respostas e três WAVs](../../evaluation/results/ensaio_tecnico_upload_3_turnos_tentativa_2/resultado.json).
- [Snapshot acadêmico atualizado com 13 STT](../../evaluation/results/metricas_handoff_20261117/metrics.json); nenhuma métrica ausente é preenchida com zero.
- [Relatório PDF preliminar com 13 transcrições STT e avaliação identificada como IA](relatorio_global_solution_preliminar_STT13_20261117.pdf): sete páginas renderizadas e verificadas.

## Revisão técnica do LLM

Os 30 casos retornaram respostas sem erro de execução. GPT-6 foi registrado nominalmente como **avaliador por IA, não humano**, aplicando critérios predefinidos a 30 respostas: 28 classificadas corretas e duas (Q19 e Q23) classificadas incorretas de forma conservadora. A avaliação computada indica **93,33% de adequação** e **100% de recusas adequadas**. É uma **avaliação assistida por IA**, não representa consenso humano nem validação independente. Os integrantes podem revisar esses julgamentos e registrar divergências de modo rastreável.

## Análise operacional

O ensaio técnico de upload utilizou três gravações reais previamente produzidas por Thiago e manteve sessão, histórico e respostas originais. Na primeira tentativa o TTS rejeitou a fala no segundo turno por divergência com o texto (speech_mismatch). A segunda completou três turnos, retornando HTTP 200 e WAV para cada um. A duração medida no servidor não equivale ao tempo até o início da reprodução em navegador. Nenhuma das duas tentativas foi adicionada às dez conversas formais.

## Engenharia

A suíte mais recente aprovou **101 testes Python** após corrigir o apurador de métricas: quando há sínteses TTS mas ainda não há avaliações humanas, a verificação de completude não deve criar grupos vazios que façam o gerador de gráficos falhar. A auditoria anterior aprovou quatro testes JavaScript e smoke HTTP. Os arquivos originais, hashes e vídeo narrado de 199,9 segundos foram preservados.

## Pendências para concluir a rubrica

1. Gustavo deve enviar G08–G14, com autorização apropriada.
2. Autorização R07 informada por Thiago foi registrada e a transcrição realizada; confirmar consentimento específico de Rafael para qualquer uso adicional ou compartilhamento com o professor.
3. Conferir literalmente as 20 referências humanas STT e as condições reais de ruído, sem consultar as hipóteses antes da revisão; depois calcular WER.
4. Conferir independentemente os julgamentos de IA das 30 respostas LLM, especialmente Q19 e Q23, preservando os critérios, os dados originais e a identificação do avaliador.
5. Três pessoas devem ouvir T01–T10 e atribuir individualmente clareza e naturalidade; exigência de 30 pares de notas.
6. Realizar dez conversas humanas interativas de três turnos, com o participante ouvindo cada resposta antes da próxima pergunta; medir e registrar o evento playing no navegador.
7. Reexecutar a comparação A/B com referências verificadas e atualizar os resultados do PDF final.
8. Rever acesso, consentimentos e retenção no OneDrive; confirmar a divergência entre título GS 2027 e documentação 2026.2 com o docente.

A versão definitiva do relatório permanece bloqueada pelas evidências humanas exigidas pelo enunciado. Não foi criada entrega pública ou link de compartilhamento.
