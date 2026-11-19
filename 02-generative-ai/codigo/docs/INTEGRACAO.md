# Contrato de integração VivaBairro

A interface desta entrega consome a API no mesmo domínio. Um protótipo externo pode consumir a mesma interface de dados após revisão das regras de privacidade e autenticação do ambiente.

- `GET /health` informa estado da aplicação, provedor configurado, modelo, documentos e trechos. A primeira resposta do LLM confirma a inferência observada.
- `POST /api/ask` aceita `question` de 4 a 2.000 caracteres, `municipality` com `sao_paulo`, `outro` ou `null`, `location` opcional de até 180 caracteres, `category` opcional e `context_doc_id` opcional no formato FXX.
- Os IDs de categoria são `vias`, `calcadas`, `iluminacao`, `residuos` e `drenagem`. Uma categoria explícita permite reconsultar a orientação após correção.
- A resposta traz `answer`, `abstained`, `mode`, `sources`, `citations_valid`, `blocked` e `removed_injections`, além de `category`, `priority`, `clarifications`, `draft`, `channel`, `urgent`, `notice` e `submitted`. O estado `submitted` é sempre falso.
- Use a fonte primária da última resposta para retomar uma pergunta curta. Ao mudar o município, descarte esse contexto. Renderize os textos como conteúdo literal e associe cada fonte à resposta correspondente.
- HTTP 422 indica formato inválido. HTTP 503 indica falha da inferência ou do processamento. A resposta pública omite rastros internos e trechos recuperados.
- `urgent` prioriza uma orientação imediata de emergência. O sistema não produz rascunho nessa situação. O alerta é conservador e depende das palavras mencionadas.

Para demonstrar integração com um protótipo externo, o grupo precisa disponibilizar seu código, a rota da jornada do cidadão e o critério de aceitação. O contrato acima preserva as rotas FastAPI da implementação auditada.

