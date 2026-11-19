# Global Solution de PLN — exigências do professor

**Fonte única desta síntese:** PDF original ENUNCIADO_OFICIAL_GS_2TIAPY.pdf, três páginas, copiado sem edição do arquivo enunciado GS 2TIAPY.pdf. O enunciado está intitulado **GS 2027 — PLN: Assistente de Voz CitizenTech**. A pasta/ documentação interna do grupo menciona 2026.2: **confirmar a edição e o prazo com o professor**, sem alterar o documento original.

Este arquivo é um mapa de verificação. Em caso de divergência, vale o PDF original.

## 1. Objetivo e arquitetura — página 1

Construir assistente em português para o cidadão: capta voz, transcreve por STT, interpreta com LLM e responde por TTS em português, repetindo o fluxo em cada turno. O projeto deve ter domínio CitizenTech delimitado e, no relatório, persona, problema e ODS.

Fluxo obrigatório: microfone -> STT -> LLM -> TTS -> alto-falante. Cada componente deve ser independente e substituível. O documento exige:

1. Captura no microfone e também upload de áudio.
2. STT em português.
3. LLM com system prompt delimitando papel, tom e limites.
4. Histórico de conversa para perguntas de continuação.
5. Base confiável do tema (RAG, contexto no prompt ou fine-tuning, escolha justificada).
6. Adaptação do texto para fala: frases curtas, sem Markdown ou emoji, com pronúncia apropriada de números, siglas e datas.
7. TTS em português brasileiro com voz natural (início da página 2).
8. Interface mostrando transcrição e resposta em texto (página 2).
9. Tempo de cada etapa e tempo total até o início da resposta falada (página 2).

Justificar execução na nuvem ou local em termos de custo, latência, privacidade e disponibilidade de internet.

## 2. Ética e LGPD — página 2

- Consentimento informado antes do primeiro uso, com aviso sobre gravação e processamento.
- Retenção mínima; justificar o armazenamento dos áudios, anonimizar quando aplicável, e informar envio a API de nuvem.
- Recusar questões fora do escopo e orientar procura de profissional ou órgão competente em temas críticos.
- Não inventar respostas quando não houver informação verificável.
- Não clonar voz de pessoa real sem consentimento expresso e documentado. Preferir voz sintética pronta.

A rubrica também inclui análise de viés do STT (página 3); comparar por voz/ruído com as limitações do pequeno corpus. Não declarar ausência de viés sem evidência.

## 3. Experimentos e métricas — página 2

| Parte | Quantidade exigida | Métrica exigida |
| --- | --- | --- |
| STT | 20 gravações do grupo; no mínimo três vozes diferentes; cinco com ruído de fundo | WER com jiwer |
| LLM | 30 perguntas do tema com resposta esperada; pelo menos cinco continuações e cinco fora do escopo | Percentual de respostas corretas e de recusas apropriadas |
| TTS | Dez respostas sintetizadas, cada uma avaliada por pelo menos três pessoas | Média de naturalidade e de clareza separadamente, notas de 1 a 5 |
| Ponta a ponta | Dez conversas completas com pelo menos três turnos | Latência média por etapa e total, em segundos |
| Comparação | Duas opções de pelo menos um dos componentes | Justificar a escolha com qualidade e latência |

As métricas devem estar no relatório, com tabelas. Os resultados técnicos automatizados de testes unitários não substituem a coleta experimental nem os julgamentos humanos quando exigidos.

## 4. Entregáveis e forma de entrega — página 3

**Um único link** (GitHub ou pasta compartilhada) com:

1. Código em notebook ou projeto Python, requirements.txt, executando do início ao fim pelo README.
2. README: arquitetura, modelos com versão e licença, instruções e nomes completos dos participantes.
3. Material de teste: áudios, perguntas e respostas esperadas, planilhas de avaliação.
4. Relatório PDF: problema/persona, ODS, arquitetura com diagrama, justificativas local/nuvem e modelos, métricas, LGPD, limitações, melhorias.
5. Vídeo de até cinco minutos: conversa real de voz com pelo menos três turnos, uma continuação e uma recusa.

O texto original registra **prazo, tamanho do grupo e forma de entrega como 'a definir pelo professor'**. Não assumir um prazo sem confirmação externa.

## 5. Rubrica — página 3

| Critério | Pontos máximos |
| --- | ---: |
| STT (microfone e upload em português) | 10 |
| LLM e diálogo (system prompt, memória, base, recusas) | 20 |
| TTS em português e adaptação | 10 |
| Integração e interface, latência | 20 |
| Testes, métricas, comparação | 20 |
| Ética, consentimento, retenção e viés | 10 |
| Relatório e vídeo | 10 |
| **Total** | **100** |

Os pontos são máximos do professor, não previsão de nota. A correspondência de cada requisito a evidências está no CHECKLIST_ENTREGA_FINAL.md.

## 6. Por que o trabalho ainda não está concluído

A implementação e o vídeo já existem, mas falta o corpus completo com referências realmente revisadas, notas TTS de três pessoas, dez conversas interativas e comparação de WER pareado. O documento ESTADO_ATUAL_E_PENDENCIAS.md mostra exatamente as contagens e os próximos passos.

**Não alterar o PDF original do docente. Não fabricar referências, avaliações ou números para alcançar a meta.**
