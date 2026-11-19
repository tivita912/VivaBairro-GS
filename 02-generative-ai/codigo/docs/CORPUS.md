# Corpus do VivaBairro

Recorte demonstrativo do Município de São Paulo. As dez fontes foram consultadas em 11/11/2026. Cada texto é uma paráfrase curada, acompanhada de URL, origem, data, categoria e limite. A aplicação ingere o JSON local. O conteúdo permanece vinculado à fonte mesmo após o chunking.

| ID | Fonte e escopo |
|---|---|
| F01 | [Perguntas frequentes do SP156](https://prefeitura.sp.gov.br/web/inovacao/w/acesso_a_informacao/350229). Consulta geral. Cada carta indica os canais e condições do serviço. |
| F02 | [Tapa-buraco](https://sp156.prefeitura.sp.gov.br/portal/servicos/informacao?servico=952). Buracos em asfalto de via pública. A curadoria não cobre calçadas nem prazo de execução. |
| F03 | [Acessibilidade · avaliação de obstáculo na calçada](https://sp156.prefeitura.sp.gov.br/portal/servicos/informacao?servico=2634). Fiscalização de obstáculos físicos. Calçada quebrada requer identificar se é pública ou particular. |
| F04 | [Calçada pública · manutenção](https://sp156.prefeitura.sp.gov.br/portal/servicos/informacao?servico=931). Aplica-se a passeio público conforme a carta. A condição do passeio precisa ser confirmada. |
| F05 | [Calçada particular · denúncia de irregularidade](https://sp156.prefeitura.sp.gov.br/portal/servicos/informacao?servico=906). Fiscalização de calçada particular. A vistoria e eventual regularização cabem ao processo oficial. |
| F06 | [Como solicitar serviços de iluminação pública](https://prefeitura.sp.gov.br/web/spregula/w/iluminacao_publica/noticias/328582). Somente luminárias de ruas, praças e túneis. Orientação de manutenção, sem garantias de prazo. |
| F07 | [Descarte irregular de entulho e resíduos em área pública](https://sp156.prefeitura.sp.gov.br/portal/servicos/informacao?a=572&servico=915&t=561). Área pública. A denúncia de limpeza de terreno particular tem carta própria. |
| F08 | [Falta de limpeza de terrenos e imóveis particulares](https://sp156.prefeitura.sp.gov.br/portal/servicos/informacao?servico=908). Terrenos e imóveis particulares. A classificação do terreno precisa ser confirmada. |
| F09 | [Limpeza de bocas de lobo, galerias e ramais](https://prefeitura.sp.gov.br/web/se/w/zeladoria_urbana/68224). Limpeza de drenagem quando há indício de obstrução. Alagamento isolado não confirma bueiro entupido. |
| F10 | [Telefones úteis da Defesa Civil de São Paulo](https://prefeitura.sp.gov.br/web/defesa_civil/w/noticias/184619). Referência da capital. Atendimento imediato é orientado fora da triagem do VivaBairro. |

O roteiro de classificação aplica os filtros de município e tema antes de montar o contexto do modelo. Calçada sem tipo definido, terreno sem indicação de natureza e alagamento sem indício de obstrução exigem esclarecimento. A base omite preços e prazos para evitar que valores de uma carta sejam atribuídos a outra situação.

