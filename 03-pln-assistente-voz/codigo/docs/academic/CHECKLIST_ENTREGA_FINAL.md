# Checklist de entrega · VivaBairro Voz

Os valores da coluna “Rubrica” são máximos do enunciado. A conferência não atribui nota.

| Critério | Rubrica | Evidência e resultado observado | Estado, próxima ação e responsável |
| --- | ---: | --- | --- |
| STT | 10 | `evaluation/stt_manifest.csv`, `results/stt_historico/` e página de revisão. 13 originais, **13 transcrições** e 0 referências verificadas. | Parcial. Gustavo grava G08–G14. O consentimento informado para R07 foi registrado e seu STT concluído; confirmar escopo de compartilhamento com professor. Os três revisam referências, confirmam cinco ruídos reais e apuram WER. |
| LLM e diálogo | 20 | `src/conversation.py`, `evaluation/llm_ratings.csv` e `AUDITORIA_LLM.md`. 30 respostas, 28 adequadas e 5/5 recusas por IA. | Evidência da avaliação por IA disponível. Grupo pode confirmar independentemente com a ficha humana opcional. |
| TTS | 10 | `src/speech_text.py`, `evaluation/tts_samples.csv` e ZIP de escuta. Dez WAVs reais e recuperação documentada de T05. | Parcial. Thiago, Rafael e Gustavo avaliam os mesmos dez WAVs. Importar 30 pares de notas. |
| Integração e interface | 20 | `src/web.py`, `tests/test_app.py`, `evaluation/coleta_e2e_upload.md`. Fluxo demonstrado no MP4 e por um ensaio técnico. | Parcial. Thiago conduz C01–C04, Rafael C05–C07 e Gustavo C08–C10, cada um com ao menos três turnos contextuais e latência medida. |
| Testes e métricas | 20 | `scripts/verify.py`, `evaluation/academic_metrics.py`, `evaluation/compare_stt.py`. Engenharia offline validada. Zero pares A/B com referência verificada na origem. | Parcial. Grupo completa a coleta e executa comparação, registra WER/latências por fronteira e justifica a escolha. |
| Ética e LGPD | 10 | `src/privacy.py`, controles de sessão e `evaluation/consents/README.md`. Termos de processamento para as 12 chamadas históricas. | Parcial. Thiago confirma com os titulares os escopos de envio e compartilhamento. Grupo inspeciona acesso, retenção e descrição de viés, sem alegar conformidade integral. |
| Relatório e vídeo | 10 | `scripts/finalizar_gs.py`, preliminares em `docs/academic/` e MP4 narrado de 199,9 s na origem. | Parcial. Docente confirma edição. Grupo consolida métricas, confere PDF renderizado e organiza um único link restrito com os artefatos autorizados. |
| Total | 100 | Máximo da rubrica. | Entrega final bloqueada enquanto existirem pendências. |

Rode `python -m scripts.finalizar_gs --dry-run` para verificar o estado dos arquivos locais. Em um computador que recebeu apenas o pacote base, a contagem local de STT e a presença do MP4 podem divergir da origem. Os hashes e os escopos ficam no registro da transferência.
