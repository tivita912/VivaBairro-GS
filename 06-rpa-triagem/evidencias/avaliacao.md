# Avaliacao da IA do robo no conjunto de teste rotulado

- Treino: 360 relatos sinteticos gerados por combinacao de trechos (scripts/gerar_treino.py).
- Teste: 60 relatos sinteticos escritos a mao, 10 por categoria, com categoria e prioridade rotuladas.
- Nenhum relato de teste foi usado no treino. Nenhum dado real de cidadao foi usado.

## Categoria (NLP: TF-IDF + Regressao Logistica)

Acertos: **45 de 60 (75.0%)**

| Categoria | Relatos | Precisao | Revocacao |
| --- | --- | --- | --- |
| Vias e buracos | 10 | 0.64 | 0.70 |
| Calçadas e acessibilidade | 10 | 0.89 | 0.80 |
| Iluminação pública | 10 | 0.88 | 0.70 |
| Lixo e limpeza | 10 | 1.00 | 0.60 |
| Drenagem e alagamentos | 10 | 0.73 | 0.80 |
| Outros | 10 | 0.60 | 0.90 |

Matriz de confusao (linhas = categoria real):

| Real | Robo: Vias e buracos | Robo: Calçadas e acessibilidade | Robo: Iluminação pública | Robo: Lixo e limpeza | Robo: Drenagem e alagamentos | Robo: Outros |
| --- | --- | --- | --- | --- | --- | --- |
| Vias e buracos | 7 | 0 | 0 | 0 | 1 | 2 |
| Calçadas e acessibilidade | 2 | 8 | 0 | 0 | 0 | 0 |
| Iluminação pública | 2 | 0 | 7 | 0 | 0 | 1 |
| Lixo e limpeza | 0 | 0 | 1 | 6 | 1 | 2 |
| Drenagem e alagamentos | 0 | 1 | 0 | 0 | 8 | 1 |
| Outros | 0 | 0 | 0 | 0 | 1 | 9 |

## Revisao humana (confianca abaixo de 0.4)

- Relatos aceitos automaticamente: 45. Categoria certa em 38 de 45 (84.4%).
- Relatos enviados para revisao humana: 15. Categoria certa em 7 de 15 (46.7%).
- Erros de categoria que a revisao humana pega: 8 de 15.

## Prioridade (regras)

Acertos: **44 de 60 (73.3%)**

Relatos de prioridade alta encontrados pelo robo: 17 de 21.

Matriz de confusao (linhas = prioridade real):

| Real | Robo: alta | Robo: media | Robo: baixa |
| --- | --- | --- | --- |
| alta | 17 | 4 | 0 |
| media | 2 | 23 | 2 |
| baixa | 1 | 7 | 4 |

## Erros de categoria

| descricao | categoria | categoria_robo | confianca | revisao_humana |
| --- | --- | --- | --- | --- |
| Abriu um buracão na Rua das Palmeiras depois da obra da companhia de água, os carros passam raspando o fundo. | Vias e buracos | Drenagem e alagamentos | 0.69 | False |
| Rua de paralelepípedo com várias pedras soltas, já vi ciclista quase cair ali. | Vias e buracos | Outros | 0.3 | True |
| Fizeram um tapa-buraco na semana passada e já abriu tudo de novo com a chuva. | Vias e buracos | Outros | 0.28 | True |
| O passeio está com a pintura da guia apagada, só isso, o resto está bom. | Calçadas e acessibilidade | Vias e buracos | 0.42 | False |
| Um trecho da calçada é de terra e vira lama, as pessoas desviam pelo asfalto. | Calçadas e acessibilidade | Vias e buracos | 0.71 | False |
| Faz duas semanas que os postes da viela estão apagados, já teve assalto e as pessoas têm medo de voltar do trabalho. | Iluminação pública | Vias e buracos | 0.28 | True |
| Trocaram as lâmpadas da rua, mas uma ficou sem acender. | Iluminação pública | Vias e buracos | 0.7 | False |
| Quatro postes apagados na sequência na rua de cima, fica um breu. | Iluminação pública | Outros | 0.21 | True |
| A lixeira da praça está cheia e ninguém esvazia há dias. | Lixo e limpeza | Iluminação pública | 0.29 | True |
| Folhas e galhos da poda ficaram empilhados na rua, não é urgente, mas já faz tempo. | Lixo e limpeza | Drenagem e alagamentos | 0.27 | True |
| Tem vidro quebrado e seringa jogados no parquinho onde as crianças brincam. | Lixo e limpeza | Outros | 0.4 | True |
| Restos de construção despejados de madrugada na beira da pista. | Lixo e limpeza | Outros | 0.42 | False |
| A rua ficou alagada ontem e um carro ficou preso com gente dentro. | Drenagem e alagamentos | Outros | 0.72 | False |
| Bueiro sem grade na calçada, um buraco aberto onde cabe uma perna. | Drenagem e alagamentos | Calçadas e acessibilidade | 0.4 | False |
| Cachorro bravo solto na rua avançando nas pessoas que passam. | Outros | Drenagem e alagamentos | 0.35 | True |

## Erros de prioridade

| descricao | prioridade | prioridade_robo | motivo_prioridade |
| --- | --- | --- | --- |
| A tampa do poço de visita afundou e ficou um degrau no meio da pista, o ônibus bate forte quando passa. | media | alta | termo de risco: afund |
| A pintura da lombada sumiu faz tempo, de noite ninguém enxerga e os carros freiam em cima. | media | baixa | termo de baixa urgencia: pintura |
| A faixa de pedestre em frente ao mercado está quase invisível, toda desbotada. | media | baixa | termo de baixa urgencia: desbotad |
| A luz da praça fica acesa o dia todo, um desperdício de energia. | baixa | media | sem termo de risco nem de baixa urgencia |
| A luminária do poste da esquina está virada para o lado errado e ilumina só o telhado. | baixa | media | sem termo de risco nem de baixa urgencia |
| A iluminação do campinho queimou e o pessoal não consegue mais jogar de noite. | baixa | media | sem termo de risco nem de baixa urgencia |
| A lixeira da praça está cheia e ninguém esvazia há dias. | baixa | media | sem termo de risco nem de baixa urgencia |
| Toda vez que chove forte a água sobe e entra na garagem das casas da parte baixa da rua. | alta | media | sem termo de risco nem de baixa urgencia |
| Bueiro sem grade na calçada, um buraco aberto onde cabe uma perna. | alta | media | sem termo de risco nem de baixa urgencia |
| Depois da chuva fica um pouco de água parada no canto da rua, some em um dia. | baixa | media | sem termo de risco nem de baixa urgencia |
| O semáforo do cruzamento está apagado desde cedo, já quase teve batida. | alta | media | sem termo de risco nem de baixa urgencia |
| Picharam o muro da escola de novo. | baixa | media | sem termo de risco nem de baixa urgencia |
| Ponto de ônibus sem banco e sem cobertura, os idosos esperam em pé no sol. | media | alta | termo de risco: idos |
| A placa com o nome da rua caiu e ninguém acha o endereço. | baixa | alta | termo de risco: caiu |
| Cachorro bravo solto na rua avançando nas pessoas que passam. | alta | media | sem termo de risco nem de baixa urgencia |
| Seria bom ter mais lixeiras e bancos na praça, é só uma sugestão. | baixa | media | sem termo de risco nem de baixa urgencia |
