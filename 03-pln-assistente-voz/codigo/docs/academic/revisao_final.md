# Revisão da entrega pela rubrica oficial — atualização 17/11/2026

| Critério | Máximo | Evidência atual | Lacuna que impede concluir |
| --- | ---: | --- | --- |
| STT | 10 | Entrada por microfone/upload funcional; 13 arquivos íntegros e **13 transcrições** reais, latência 1,242 s | G08–G14 ausentes; 20 referências literais revisadas, cinco ruídos confirmados e WER pendentes. R07 transcrito após registro de autorização. |
| LLM e diálogo | 20 | System prompt, memória, base, 30 respostas reais e avaliação por IA identificada: 93,33% adequação; 100% recusas | Recomenda-se revisão humana independente de Q19/Q23 e conferência dos critérios; avaliação por IA não é avaliação humana |
| TTS | 10 | Adaptação pt-BR, dez WAVs reais, hashes válidos, pico máximo -3,18 dBFS | Três avaliadores humanos em cada uma das dez amostras |
| Integração e interface | 20 | Fluxo real e vídeo validado; ensaio por replay concluiu três turnos na segunda tentativa | Dez conversas humanas com três turnos, medindo evento de reprodução |
| Testes e métricas | 20 | 101 Python e 4 JS aprovados; 30 casos LLM avaliados com avaliador IA explicitamente identificado | WER, notas humanas TTS, dez latências E2E e comparação pareada; recomenda-se avaliação humana de controle do LLM |
| Ética e LGPD | 10 | Controles de consentimento e descarte, registros de Rafael R01–R06 e Thiago T15–T20 | Consentimento Gustavo e escopos de uso futuro; R07 já transcrito, mas compartilhamento com professor e retenção OneDrive seguem pendentes |
| Relatório e vídeo | 10 | PDF preliminar atualizado de sete páginas, renderizado e verificado; MP4 narrado 199,9 segundos | PDF final com séries completas e confirmação da edição |
| Total da rubrica | 100 | Pontuações máximas previstas no enunciado | Não atribuir nota não oficial sem método explícito |

## Evidências técnicas recentes

- [Resultados acadêmicos](resultados.md)
- Snapshot do apurador (na cópia de trabalho da equipe)
- Triagem por IA do LLM (na cópia de trabalho da equipe)
- Dez WAVs TTS e instruções (na cópia de trabalho da equipe)
- [Relatório preliminar atualizado](relatorio_global_solution_preliminar_STT13_20261117.pdf)
- Vídeo narrado (na cópia de trabalho da equipe)

## Condição da entrega

O trabalho não está pronto para submissão final. O professor exige: 20 STT de três vozes e cinco ruídos, WER com jiwer, 30 LLM avaliados, dez TTS avaliados por três pessoas, dez conversas reais de três turnos e comparação A/B por qualidade e latência.

Não substituir gravação humana, referência revisada, julgamento individual ou início de reprodução no navegador por dados sintéticos ou estimativas. O replay técnico automatizado é evidência de integração e não conta como conversa humana.

Quando o corpus estiver completo, execute a apuração e construa o PDF final com scripts/build_academic_report.py --final, informando a edição confirmada. O roteiro já bloqueia a versão final sem as séries completas.

Prepare uma cópia de submissão em área separada e restrita, com código executável, README, materiais de teste autorizados, relatório final e vídeo. Não publicar gravações sem o consentimento adequado. Confirme a divergência de GS 2027 versus 2026.2 com o docente.
