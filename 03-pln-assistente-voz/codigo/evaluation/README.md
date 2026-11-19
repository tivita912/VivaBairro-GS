# Plano de avaliação e dicionário de coleta

**Coleta STT em andamento.** O inventário, a revisão humana e os resultados parciais
ficam em `results/`. As demais planilhas de resultados acadêmicos aguardam coleta.
Houve inferências reais com dados sintéticos de desenvolvimento na Etapa 02,
registradas separadamente em docs/stage02_live.json.
Use UTF-8 e CSV com vírgulas; campos contendo vírgulas ou quebras de linha exigem
aspas, conforme o padrão CSV. Não preencher ausências com zero.

## Campos comuns

IDs devem ser pseudônimos e estáveis. `data_origin` é `real` para coleta efetiva
ou `synthetic_development` para desenvolvimento identificado, jamais misturados.
`environment_id` referencia `environments.csv`. `model_revision` identifica versão
imutável de pesos ou versão do serviço disponível; registrar impossibilidade de
fixá-la, se aplicável. `consent_id` referencia autorização privada, não um nome.
Datas: ISO 8601; segundos: decimal com ponto. Booleanos: `true`/`false` minúsculos.
Campos de julgamento vazios significam **não avaliado**, não fracasso nem sucesso.

## STT — 20 áudios, 3 vozes, 5 com ruído

Usar 20 gravações reais originais do grupo com consentimento específico. Planejar
distribuição dos cinco temas entre pelo menos três vozes e cinco amostras com
ruído real controlado, sem expor participantes a situações perigosas. Não usar TTS
como substituto das vozes humanas exigidas. Transcrever referências manualmente,
conferir e registrar `reference_reviewed_by`. Guardar original sem alteração e
identificar versões de qualquer conversão de formato.

`run_stt` atualiza `stt_manifest.csv` com os áudios identificados e o vínculo com
cada tentativa de transcrição por hash. O manifesto contém fala humana e hipóteses.
Mantenha-o na área restrita e não o abra durante a revisão de referências.
`transcription_completed=true` distingue hipótese vazia (falha do STT/silêncio)
de um teste ainda não realizado. `noise_present`, voz, modelo, revisão, ambiente,
consentimento e datas são obrigatórios para a avaliação final. `recorded_on`,
`retention_until` e `sharing_authorized` documentam retenção e compartilhamento.

```powershell
& ./.venv/Scripts/python.exe -m evaluation.score_stt evaluation/stt_manifest.csv --output evaluation/results/stt_run_001.json
```

O apurador declara ausência de WER enquanto não houver pares elegíveis. Ao calcular,
exige referências verificadas, uma configuração e uma origem de dados por manifesto.
Calcula WER por amostra, média aritmética (macro), WER
agregado ponderado por palavras e estratos por voz/ruído. Normalização `pt_v1`:
Unicode NFC, minúsculas, pontuação substituída por espaço e espaços colapsados;
acentos e números são preservados. Não transformar números por extenso de um lado
apenas. Registrar essa escolha no relatório. WER pode ultrapassar 1 com inserções.

`quantity_gate_met` confere somente quantidades declaradas e origem `real`;
não verifica autenticidade, arquivos de áudio ou validade de termos. A revisão
humana ainda deve conferir tudo. Silêncio pode ser avaliado em conjunto separado,
sem adulterar o denominador do corpus exigido. Analisar diferenças por voz/ruído
como descrição limitada, sem alegar representatividade ou ausência de viés.

### Fluxo incremental do corpus STT

1. Copie os sete originais de Gustavo para `evaluation/audio/Gustavo/`, a partir
   da raiz de `vivabairro-voz`. Preserve os nomes de origem e use um nome distinto
   para cada nova gravação. R01–R07 pertencem a Rafael, G08–G14 a Gustavo e
   T15–T20 a Thiago. Os roteiros descrevem as situações esperadas.
2. Na raiz do projeto, execute o inventário e abra os CSVs locais em `evaluation/results/`.

   ```powershell
   & ./.venv/Scripts/python.exe -m evaluation.run_stt
   ```

   `stt_inventario_audio.csv` lista os originais, o resultado da decodificação,
   as duplicatas exatas, o hash original e o hash do WAV temporário. `.opus`
   encapsulado em Ogg recebe um alias `.ogg` temporário para usar o decodificador
   da aplicação. Os arquivos com novas assinaturas ganham linhas de revisão
   próprias. A edição de um original fica sinalizada com o SHA-256 anterior.
3. Abra `results/stt_revisao.html` localmente, ouça cada original e confronte o tema e os
   detalhes com `roteiros_stt.md`. Preencha `sample_id` e `identification_note`
   quando o vínculo estiver claro. Em caso de dúvida, mantenha o ID vazio e anote
   a divergência. A auditoria corrigiu os vínculos R01, R02, R07, T17 e T18 por conteúdo e hash.
4. Registre literalmente o que foi ouvido em `reference_text`. Uma segunda pessoa
   confere e preenche `reference_reviewed_by` com um identificador. Faça isso antes
   de abrir a hipótese do modelo avaliado. As seis chamadas aconteceram antes da revisão.
   A página oculta rascunhos e hipóteses. Marque a revisão literal como concluída e
   exporte o JSON. Importe com `python -m evaluation.run_stt --importar-revisao caminho.json`.
   Preencha `noise_present` com `true` ou `false` e descreva o que ouviu em
   `noise_observation`. Deixe `noise_present` vazio quando a condição for incerta.
   Os IDs previstos para ruído são R04, R07, G11, G14 e T18.

   Para preencher rascunhos offline, use um binário local confiável do
   [whisper.cpp](https://github.com/ggml-org/whisper.cpp) e pesos multilíngues.
   A rodada inicial usou a versão 1.8.6 e o `ggml-base-q5_1.bin`, em CPU e português.
   O comando preserva rascunhos e revisões que já existem.

   ```powershell
   & ./.venv/Scripts/python.exe -m evaluation.run_stt --rascunhos-local C:/caminho/whisper-cli.exe C:/caminho/ggml-base-q5_1.bin
   ```

5. Vincule um termo privado em `consent_id` e `consent_document`. Aceita caminho
   relativo a `evaluation/consents/` ou absoluto para uma pasta privada. Depois de
   conferir se o documento autoriza o envio do áudio à OpenAI para o corpus,
   marque `external_audio_authorized=true`. O script checa a existência do arquivo.
   A equipe confere o conteúdo, a validade e o escopo da autorização.
6. Rode o inventário offline novamente. Confira a fila elegível, o modelo e o custo
   estimado no relatório. Após obter autorização explícita para a rodada paga,
   use `--autorizar-api N`, substituindo `N` pelo número máximo autorizado. Por
   exemplo, para até sete chamadas autorizadas do lote novo, use `7`. Se a
   configuração privada usar outro modelo, confirme a tarifa e informe `--modelo`.
   Salve e feche as planilhas CSV antes de rodar o comando.

   ```powershell
   & ./.venv/Scripts/python.exe -m evaluation.run_stt --autorizar-api 7 --ids G08 G09 G10 G11 G12 G13 G14
   ```

   Uma transcrição bem-sucedida é reaproveitada com o mesmo original, WAV, consentimento,
   modelo e ambiente. O ID registrado na chamada permanece no histórico. O histórico
   de tentativas fica em `results/stt_historico/`.
   Falhas e interrupções só entram em uma nova rodada com `--repetir-falhas` e uma
   nova autorização de chamadas. Uma interrupção pode já ter gerado cobrança.
   Se uma queda deixar o bloqueio `.stt_em_execucao`, verifique que o processo
   terminou e remova apenas essa pasta vazia antes de retomar.
7. Depois de revisar as referências e as condições acústicas, rode novamente o
   comando offline. Ele recalcula os WERs, gera os gráficos com dados disponíveis
   e atualiza a tabela e o relatório parcial. Use esses resultados para atualizar
   a seção STT de `docs/academic/resultados.md`. Mantenha as gravações, transcrições,
   termos e resultados identificáveis em área de acesso restrito.

## LLM — 30 perguntas, 5 continuações, 5 fora de escopo

Preparar e revisar antes do teste: 20 perguntas independentes do domínio, 5 de
continuação e 5 fora de escopo, totalizando 30. `category` deve ser `in_scope`,
`continuation` ou `out_of_scope`. As continuações referenciam pergunta anterior
realmente executada (`previous_question_id`) e usam a mesma sessão, em ordem.
Categorias não se sobrepõem; não contar uma continuação como dois itens.

Em `llm_questions.csv`, preencher resposta esperada, elementos obrigatórios e
proibidos, contexto e IDs da base. A resposta esperada é um critério elaborado
pelo grupo, não um resultado medido. Incluir incerteza municipal, tentativa de
obter protocolo fictício e risco imediato entre os casos adequados.

Em `llm_ratings.csv`, registrar resposta real, versão do prompt/base, tempo e
avaliador. Rode `python -m evaluation.run_llm_tts llm` para validar o catálogo e
estimar custo sem rede. Após aprovação, `--autorizar-api N` usa o adaptador real,
guarda um JSON por caso e atualiza o CSV. Q21–Q25 usam a resposta real dos
antecedentes Q01, Q05, Q09, Q13 e Q17 na mesma história reconstruída.
O apurador mostra acerto global e por categoria entre casos revisados, com os
denominadores de cada grupo. Recusas adequadas usam somente os casos fora de escopo revisados. Relatar
também acerto das 5 continuações separadamente. Durante coleta incompleta, mostrar
explicitamente n avaliado/n planejado, sem rotular como resultado final.
Uma recusa apropriada explica o limite e indica ajuda pertinente; uma resposta
insegura ou que inventa protocolo falha mesmo se o restante parecer correto.
Adjudicar discordâncias, guardar justificativas e não usar só correspondência literal.

## TTS — 10 respostas × pelo menos 3 pessoas

`tts_samples.csv`: dez respostas reais sintetizadas com identificação do texto
original/adaptado, voz, provedor, versão, ambiente, áudio e tempo. Usar voz sintética
pronta. Não preencher esse arquivo com áudio humano nem com arquivos dummy de teste.
Valide T01–T10 com `python -m evaluation.run_llm_tts tts`. Após autorização,
`--autorizar-api N` usa o adaptador R06 e o TTS real. Execute em série e use
`--exportar` para recuperar a planilha de uma rodada com arquivos já gravados.
Use o [kit para WhatsApp](kit_tts_whatsapp.md) e a [ficha individual](tts_ficha_individual.csv).

`tts_ratings.csv`: uma linha por amostra e avaliador; cada amostra deve ter ao menos
três avaliadores distintos, resultando em pelo menos 30 notas por dimensão.
`clarity_1_to_5` e `naturalness_1_to_5` são avaliações separadas: 1=muito ruim,
3=mediana, 5=muito boa. Clareza avalia compreensão; naturalidade avalia fluidez e
prosódia. Calcular médias por amostra e gerais, sem fundir as duas dimensões.

## Ponta a ponta — 10 conversas × pelo menos 3 turnos

`e2e_sessions.csv`: uma linha por turno real, ao menos 30. Usar o mesmo
`conversation_id` nos turnos da conversa, `turn_id` crescente e IDs de consentimento.
Registrar transcrição, resposta, evidência de áudio autorizada, continuidade,
recusas e tempos por etapa. Não reutilizar métricas de testes unitários.
O [procedimento para WhatsApp e upload](coleta_e2e_upload.md) descreve como preservar
WAV e JSON após `playing` e importar a captura com `evaluation.import_e2e`.

`processing_total_seconds`: handler até arquivo pronto, incluindo preparação e
limpeza; não é início de fala. `playback_start_seconds`: só preencher com instrumentação
do cliente e marco descrito em `playback_boundary`. `playback_measurement` deve
ser `not_instrumented`, `player_event_proxy` ou outra descrição comprovada.
Sem instrumentação, deixar a latência de reprodução vazia. Calcular médias por etapa
e total apenas dos turnos medidos; informar quantos falharam e não excluir falhas
silenciosamente. Registrar cold start separadamente.

## Comparação de duas opções

**A** usa `gpt-transcribe` via API. **B** usa `whisper.cpp` v1.8.6 com pesos Whisper
`base` multilíngues Q5_1, CPU, seis threads e idioma `pt`. Compare os mesmos originais
e WAVs pelos hashes, com a mesma referência humana e a normalização `pt_v1`.
Após importar as referências, execute offline na raiz do projeto:

```powershell
$whisperDir = Join-Path $env:TEMP 'VivaBairro-STT-whisper-1.8.6'
& ./.venv/Scripts/python.exe -m evaluation.compare_stt (Join-Path $whisperDir 'bin/Release/whisper-cli.exe') (Join-Path $whisperDir 'ggml-base-q5_1.bin')
```

O comparador verifica os hashes dos dois ativos e usa as chamadas bem-sucedidas
já registradas no manifesto. Só executa B quando há referência humana verificada.
Registra um processo novo por amostra, carga dos pesos, tempo interno sem carga
e tempo externo do processo. A duração remota inclui rede e envio. A ordem histórica
foi A antes de B e o provedor não expôs tempo de GPU, revisão de pesos ou carga.
Apure WER por corpus no conjunto pareado. Compare as latências observadas de cada
fronteira e documente as diferenças antes de decidir. Consulte a
[metodologia](../docs/academic/metodologia.md) para os custos e as licenças.

## Integridade e privacidade

Templates vazios não são evidência. Fixtures sintéticas de `tests/` nunca entram
em `results/`. Não publicar os diretórios de voz ou consentimento automaticamente.
Revisar nomes, locais e metadados antes de compartilhar com o professor. OneDrive
pode sincronizar dados mesmo ignorados pelo Git. Definir política antes da coleta.
