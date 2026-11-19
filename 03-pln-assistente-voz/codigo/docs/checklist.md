# Rastreabilidade da Global Solution — atualizada após rodadas reais

Fonte de exigências: enunciado oficial GS 2027, três páginas. A documentação interna usa 2026.2, a confirmar com o professor. Estado observado em 16/11/2026 (São Paulo), com timestamps UTC de 17/11.

| ID | Requisito e estado | Evidência | Para concluir |
| --- | --- | --- | --- |
| R01 | Microfone e upload implementados | src/audio_input.py, src/web.py, tests/test_audio_input.py | Validar com coleta humana de dez conversas |
| R02 | STT real: 13 transcrições e 13 áudios recebidos | evaluation/stt_manifest.csv; results/stt_relatorio_parcial.md | Obter G08–G14 e calcular WER após revisão humana de 20 referências; R07 já transcrito |
| R03 | LLM: 30/30 chamadas reais concluídas e 30 avaliações por IA identificadas (28/30 adequadas) | evaluation/llm_ratings.csv | Recomenda-se auditoria humana independente, sobretudo Q19 e Q23 |
| R04 | Memória e cinco continuações executadas | src/conversation.py, Q21–Q25 em evaluation/llm_ratings.csv | Conferir qualitativamente as continuações |
| R05 | Base com cinco temas implementada | knowledge/urban_guidance.json, knowledge/sources.md | Revisar fontes e limitações de cobertura municipal |
| R06 | Adaptação pt-BR implementada e testada | src/speech_text.py, testes unitários, TTS WAVs reais | Conferir fidelidade e naturalidade na escuta |
| R07 | TTS 10/10 WAVs reais e validados tecnicamente | evaluation/tts_samples.csv; results/kit_tts_whatsapp_real.zip | Coletar 30 avaliações humanas de duas dimensões |
| R08 | Interface exibe texto, transcrição e player | src/web.py, web/index.html, teste de UI e vídeo | Conferir acessibilidade e diversidade de dispositivos |
| R09 | Métricas por etapa e evento playing instrumentados | src/metrics.py; web/assets/latency.mjs; testes | Dez sessões humanas com medições reais de reprodução |
| R10 | Consentimento e controles implementados, escopo parcial | src/privacy.py; evaluation/consents/README.md | Escopo adicional para sessões, autorização Gustavo, compartilhamento com professor e retenção no OneDrive |
| R11 | Recusas e limites: cinco casos reais registrados e avaliados por IA (5/5 adequados) | prompts/system_v1.txt; Q26–Q30 | Avaliação humana independente recomendada |
| R12 | Engenharia: 101 Python e 4 JS passaram | tests/; docs/academic/resultados.md | Concluir coletas humanas e relatório final |
| R13 | Comparação local/remota preparada; zero pares revisados | evaluation/compare_stt.py; results/stt_comparacao.json | Completar referências e executar comparação pareada |

**Ensaio técnico separado:** três turnos por upload com gravações pré-existentes de Thiago passaram na segunda tentativa; a primeira registrou um erro real do TTS. Não contar como uma das dez conversas humanas interativas.

[Resultados detalhados](academic/resultados.md) · [Rubrica e condição de entrega](academic/revisao_final.md) · [PDF preliminar atualizado](academic/relatorio_global_solution_preliminar_STT13_20261117.pdf).
