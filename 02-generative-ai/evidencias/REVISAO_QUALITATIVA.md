# Revisão dos resultados · VivaBairro

A revisão assistida por IA comparou pergunta, domínio, trechos, referência e resposta. A expectativa de cada cenário consta na trilha. Uma avaliação independente com o grupo e o público-alvo está pendente.

## Recuperação

Nas 11 consultas anotadas, o híbrido global recuperou a fonte esperada em oito consultas no top-4. V02, V04 e V05 exigiam uma referência geral após identificar falta de informação. A busca por similaridade, sem roteamento, não recuperou F01 nesses casos. A consulta em produção filtra pelo domínio e acrescenta seu título à busca. O desempenho global mede o recuperador isolado. O desempenho ponta a ponta mede a aplicação com esses filtros.

O empate entre BM25 e híbrido nesta amostra não permite atribuir ganho à LSA. A versão curta criou mais janelas e reduziu a cobertura por fonte. A configuração padrão preservou as seções curadas. Os rótulos de seção correspondem a S01 de cada documento selecionado para a orientação principal.

## Geração controlada

G01, G02, G04 e G06 selecionaram o trecho rotulado de buraco, iluminação, descarte público e obstáculo na calçada. G03 e G05 selecionaram null diante de pergunta fora do tema ou prazo ausente. Os seis casos passaram em ambas as rodadas do Qwen.

## Fluxo completo

- V01 e V22 selecionaram F02 no primeiro turno e na retomada. A seção exata escolhida pode variar dentro da mesma fonte. A página do serviço fornece o próximo passo oficial.
- V02 e V04 responderam com F01 como orientação geral. O sistema perguntou respectivamente o tipo de calçada e a natureza da área. O bloqueio de passagem justificou prioridade elevada em V02.
- V03 e V12–V16 usaram as referências específicas esperadas. A regra de drenagem exigiu um sinal textual de obstrução antes de indicar limpeza.
- V05 ficou abaixo da expectativa de mostrar o portal geral. O Qwen retornou null mesmo com F01 no contexto. A resposta pública informou ausência de evidência específica, preservou o rascunho e pediu frequência ou indício observável em segurança. Essa falha de cobertura permaneceu na rodada final.
- V06, V07 e V20 pediram esclarecimento. V08 e V18 permitiram elaborar o relato sem indicar um canal da capital para local ainda desconhecido ou outro município.
- V09 informou que o cidadão encaminha o texto. V10 recusou um prazo garantido. V19 manteve a distinção entre luminária pública e energia doméstica.
- V11 melhorou de formato inválido para seleção de F03 quando o servidor passou a restringir o formato e os IDs. A primeira rodada permanece em `evidencias/qwen/`.
- V17 orientou acionar emergência local imediatamente e não produziu rascunho. V21 bloqueou a solicitação sintética antes da geração. S02 removeu o trecho suspeito e excluiu o marcador da resposta.

## Limitações

O conjunto é pequeno, em português e conhecido durante a implementação. Os padrões de categoria e perigo podem perder descrições indiretas ou reagir a menções negadas. A prioridade organiza o relato pelo impacto informado. A aplicação não faz avaliação técnica do risco. O texto do corpus é verificável por URL e a escolha pode ser relevante apenas em parte. A restrição do modelo impede texto arbitrário na orientação municipal, mas não assegura a pertinência da seleção.

