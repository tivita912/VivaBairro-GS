# Metodologia e coleta · VivaBairro Voz

A documentação interna usa 2026.2. O enunciado oficial traz GS 2027. Edição e calendário aguardam confirmação do docente.

## Organização do grupo

| ID | Identificação disponível | STT | Conversas | Avaliação TTS |
| --- | --- | ---: | --- | --- |
| P01 | Thiago Santana Danyluk | T15–T20 | C01–C04 | T01–T10 |
| P02 | Rafael de Paiva Ramos | R01–R07 | C05–C07 | T01–T10 |
| P03 | Gustavo Civita Gonçalves | G08–G14 | C08–C10 | T01–T10 |

### STT

Use os [roteiros efetivamente enviados](../../evaluation/roteiros_stt.md). Para a coleta restante, use o gravador do telefone ou do Windows e preserve os originais. Planeje fundo audível e seguro para G11 e G14. A escuta confirma a condição real de todos os arquivos, inclusive R04, R07 e T18.

Cada participante transcreve literalmente os próprios áudios na página privada `evaluation/results/stt_revisao.html`. Uma segunda pessoa ouve e registra o ID de revisão. Inclua hesitações e autocorreções audíveis. As seis hipóteses remotas já existiam antes da revisão. Conclua a referência sem abrir as hipóteses nem os rascunhos, exporte e importe o JSON. Vincule a autorização por `consent_id`. O manifesto preserva os hashes, o ID histórico e a tentativa de origem.

A política `pt_v1` já está fixada no código. Usa Unicode NFC, minúsculas, pontuação trocada por espaço e colapso de espaços. Mantém acentos e números. WER por amostra é `(S+D+I)/N`. WER agrupado soma S, D, I e N antes da divisão. Reporte também média das taxas individuais, total de palavras e erros por voz, limpo e ruído. Rede, falhas e transcrições vazias são registradas de forma distinta. Três vozes permitem comparação descritiva no grupo.

### LLM

O [catálogo congelado](../../evaluation/llm_questions.csv) contém Q01–Q30. Os critérios vêm de [casos_llm_30.md](../../evaluation/casos_llm_30.md). Comece com uma sessão isolada por caso de entrada. Q21–Q25 seguem imediatamente Q01, Q05, Q09, Q13 e Q17, respectivamente, dentro da mesma conversa. Preserve a resposta anterior na sessão e registre modelo solicitado, versão informada ou indisponibilidade, prompt v1.0, base 1.0.0 e segundos. Os seis requisitos qualitativos são adequação, contexto, correção, limites, ausência de invenções e recusa quando pertinente.

O executor `evaluation.run_llm_tts llm` reconstrói para cada continuação o par real de pergunta e resposta do antecedente daquela rodada. A saída literal e os hashes do prompt, base e catálogo ficam na evidência. Uma falha no antecedente impede a continuação formal correspondente.

Marque `reviewed` com julgamento booleano e justificativa. A resposta é correta quando atende o critério essencial e respeita limites factuais e de segurança. Use `ambiguous` para adjudicação por outra pessoa e `error_type` para falhas de execução. Relate acerto nos casos revisados, acerto de continuação, recusas adequadas entre os fora de escopo revisados e falhas por categoria. Explicite o denominador e o número de casos ausentes.

**Execução em 16/11/2026:** foram executadas 30 chamadas reais de LLM, e GPT-6 avaliou as respostas com critérios textuais predefinidos, registrando-se como `GPT6_CHATGPT_AVALIADOR_IA_NAO_HUMANO`. A avaliação por IA classificou 28/30 como adequadas (93,33%) e cinco recusas entre cinco casos fora do escopo como adequadas (100%), sinalizando Q19 e Q23 como falhas conservadoras. Isso é uma **avaliação realizada por IA**, não um julgamento de uma pessoa nem consenso humano. O arquivo anterior às notas está preservado em `evaluation/results/llm_ratings_antes_da_avaliacao_por_ia.csv`. Recomenda-se revisão humana independente das respostas e justificativas, e qualquer alteração deverá preservar a versão anterior.

### TTS

Após autorização de uso da API, use `evaluation.run_llm_tts tts` para sintetizar T01–T10 do [catálogo de síntese](../../evaluation/tts_prompts.csv). O executor preserva texto original e adaptado, voz, modelo, ambiente, WAV e falhas. Distribua os mesmos dez arquivos pelo [kit de escuta](../../evaluation/kit_tts_whatsapp.md). Cada participante avalia cada amostra individualmente.

| Nota | Clareza | Naturalidade |
| --- | --- | --- |
| 1 | Muito difícil de compreender | Muito artificial |
| 2 | Compreensão prejudicada | Artificial |
| 3 | Compreensível, com problemas | Razoavelmente natural |
| 4 | Clara | Natural |
| 5 | Muito clara | Muito natural |

Uma linha por amostra e avaliador, com duas notas inteiras e observação opcional. Calcule médias por amostra e globais, distribuições e número de avaliadores. Para a conclusão, obtenha pelo menos três avaliações por amostra.

### Ponta a ponta

Use [C01–C10](../../evaluation/roteiros_tts_e2e.md) com os arquivos de voz recebidos do participante via WhatsApp. Para cada conversa, confirme consentimento, mantenha a mesma aba, dê acesso à resposta real a cada turno e só então receba a próxima pergunta. Após `playing`, salve WAV, transcrição, resposta e detalhes técnicos antes do próximo upload. O [guia de coleta](../../evaluation/coleta_e2e_upload.md) descreve como importar os turnos e preservar falhas.

**Relógios e marcos.** A captura começa no acionamento do MediaRecorder e termina no pedido de parada. O navegador mede com `performance.now()` desde a captura (microfone) ou a seleção do arquivo (upload) até o primeiro evento `playing`. Relate microfone e upload separadamente. O microfone também fornece fim da captura até reprodução. Ao usar upload, `input_audio_duration_seconds` descreve a mídia, e o horário da gravação original fica a cargo do coletor. A espera para enviar e a espera para clicar em play são observáveis. Esses tempos devem constar da interpretação.

O servidor usa `perf_counter` para cada etapa e para a duração de recebimento do corpo e do handler. A transferência da resposta WAV é medida no navegador ao baixar o corpo. `loadeddata` indica preparação do player. Os resíduos HTTP subtraem **durações** de cada ambiente e incluem transporte e sobrecarga de cliente. A transferência de entrada é aproximada pela janela de recebimento e escrita do corpo no servidor. Nenhum timestamp de um relógio é subtraído do timestamp de outro. A marca ISO de início da pergunta identifica a coleta. O evento `playing` é um proxy e pode anteceder o áudio no dispositivo físico.

### Comparação de opções e orçamento

**A** usa `gpt-transcribe`; **B** usa Whisper base multilíngue Q5_1 com `whisper.cpp` v1.8.6, CPU Intel Core i7-8700, 12 processadores lógicos, seis threads usadas pelo comparador. A versão Windows x64 abriu localmente e os hashes do executável e dos pesos foram conferidos. O [motor whisper.cpp](https://github.com/ggml-org/whisper.cpp/blob/v1.8.6/LICENSE) e os [pesos originais Whisper](https://github.com/openai/whisper#license) são MIT. Os pesos convertidos são os do [modelo distribuído pelo projeto](https://huggingface.co/ggerganov/whisper.cpp). A OpenAI serve A como API proprietária e não informou snapshot na rodada realizada.

Compare os mesmos originais e WAVs, com referências humanas verificadas e apuração jiwer `pt_v1`. Reaproveite A com os hashes correspondentes. `evaluation.compare_stt` só executa B para pares elegíveis. Meça a chamada remota do cliente (inclui rede), o tempo do processo local, a carga dos pesos e o tempo interno sem carga. A usa serviço opaco e suas chamadas aconteceram antes do término das referências e de B. B inicia um processo por arquivo; preserve os tempos e as falhas por amostra. Nenhuma opção venceu. O estado atual tem seis chamadas A, zero referências e zero pares comparáveis.

| Série | Chamadas pagas restantes no mínimo | Cenário de custo em US$ |
| --- | ---: | ---: |
| STT formal e comparação A | 14 | 0,0094 com 55,36 s do lote presente e sete arquivos de 10 s |
| LLM | 30 | 0,0285 a 8.000 tokens de entrada e até 300 de saída por caso |
| TTS | 10 | 0,3120 a 2.000 tokens de texto de entrada e até 1.500 tokens de áudio de saída por amostra |
| Ponta a ponta | 90 | 0,9983 em 30 turnos de 15 s, com o mesmo cenário de tokens |
| Total | 144 | Cerca de 1,35 |

As estimativas excluem retentativas, usam tarifas públicas por duração/tokens e não consultam faturamento. Os seis STT anteriores somaram 46 s informados pelo serviço, com valor estimado de US$ 0,00345. O cenário futuro depende da duração e de consumo real. O lote local B é offline. Confirme serviços, termos e autorização do responsável por rodada antes de executar chamadas. [Tarifas da OpenAI](https://developers.openai.com/api/docs/pricing)

## Apuração

Na raiz do projeto:

```powershell
& ./.venv/Scripts/python.exe -m evaluation.score_stt evaluation/stt_manifest.csv
& ./.venv/Scripts/python.exe -m evaluation.academic_metrics --saida evaluation/results/coleta_001
```

Use uma pasta nova por execução. Os scripts não contatam provedores. Quadros vazios retornam resultados indisponíveis e gráficos só são escritos quando um indicador tem dados. Revise outliers, use denominadores explícitos e mantenha os arquivos de saída vinculados à versão de corpus. Conserve origem e consentimento em registros privados. 
