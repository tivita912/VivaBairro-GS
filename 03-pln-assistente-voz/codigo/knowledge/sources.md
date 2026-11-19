# Fontes da base 1.0.0

Consulta em 11/11/2026 (America/Sao_Paulo). A base foi preparada nesta etapa e
ainda precisa de revisão humana do grupo antes da integração real do LLM.
Nenhum município foi selecionado; não há telefones, prazos ou procedimentos locais.

## Orientações editoriais

As entradas `buracos-relato`, `calcadas-relato`, `iluminacao-relato` e `lixo-relato`
são sugestões editoriais do projeto para organizar um rascunho, com base no
escopo da especificação fornecida pelo usuário. Não foram publicadas por uma
prefeitura nem constituem normas, diagnóstico, atribuição de responsabilidade
ou promessa de atendimento. A proveniência interna é explícita no JSON.

## Orientação oficial

`alagamentos-seguranca`: [Governo Federal — medidas de autoproteção em casos de alagamento](https://www.gov.br/pt-br/noticias/transito-e-transportes/2022/07/conheca-medidas-de-autoprotecao-que-a-populacao-deve-tomar-em-casos-de-alagamento).
Fonte nacional consultada; sustenta evitar contato com a água e não atravessar
vias alagadas. A afirmação sobre as limitações do assistente é política editorial.
A entrada é uma síntese; não copia integralmente a publicação.

## Atualização e confiabilidade

Para acrescentar informação municipal: registrar município/UF, URL oficial,
título, data de consulta, orientação exata e responsável pela revisão. Revisar
antes de cada entrega. Não extrapolar orientações de um município para outro.
Fontes indisponíveis ou conflitantes exigem sinalização de incerteza.
Versionar o JSON, atualizar esta lista e executar `test_knowledge`.
O contexto completo cabe no prompt desta fundação; não há necessidade atual de
RAG vetorial, indexação, banco de dados ou fine-tuning. Reavaliar tamanho por tokens
quando o tokenizer do modelo for integrado.
