# Auditoria final · VivaBairro | CitizenTech FIAP 2026.2

Turma 2TIAPY · Generative AI & Advanced Nets · 11/11/2026

## Escopo verificado

A proposta apresentada descreve o VivaBairro, o público previsto e o alinhamento aos ODS 11 e 16. A busca por nome e conteúdo nos materiais FIAP, Downloads, área de desenvolvimento e workspace não localizou registro de aprovação nem protótipo separado. A entrega integra o assistente à interface VivaBairro construída sobre a última versão auditada, em recorte demonstrativo de São Paulo (capital). O [contrato de integração](codigo/docs/INTEGRACAO.md) documenta como outro protótipo pode consumir a API.

A base técnica veio de CitizenTech_GS_GenAI_2026_2_ENTREGA_FINAL.zip, SHA-256 `6823881c363665cab5c9d1ae9ce1afa8c4f38b54fc957a7b5a8bf127c5392def`. O ZIP anterior permanece no workspace como arquivo histórico do experimento gov.br. As métricas desta entrega foram produzidas no corpus municipal.

## Matriz do enunciado

| Critério | Peso | Evidência | Estado |
|---|---:|---|---|
| Chunking | 1,0 | `codigo/citizentech/chunking.py`, metadados por trecho e cinco configurações em `evidencias/baseline/comparativo.json`. O padrão 65/10 produziu 14 trechos com zero transições sobrepostas. | Comprovado no recorte |
| Retriever | 1,0 | BM25, LSA e híbrido com ranking e scores por caso. Hit@4 e Recall@4 por fonte de 0,7273 no híbrido global. | Comprovado no recorte |
| Generator | 1,0 | Qwen2.5 3B Instruct em llama.cpp, prompt e configuração registrada, saída restrita aos IDs recuperados ou à abstenção. | Comprovado no recorte |
| Implementação e integração | 1,0 | FastAPI e interface integrada nesta entrega. Relato revisável e copiável, categoria, prioridade, canal, confirmação de município e alerta de urgência. | Parcial até confirmar a aprovação e o protótipo externo |
| Avaliação dos componentes | 1,5 | Recuperação anotada em 11 consultas e geração controlada em seis casos, com **6/6** na rodada final. | Comprovado no recorte |
| Avaliação end-to-end | 1,5 | 23 cenários, **22/23** na rodada final, incluindo dois turnos. Respostas, contexto e julgamento esperado em `evidencias/qwen-final/end_to_end.json`. | Comprovado no recorte |
| Mitigação de vulnerabilidades | 1,0 | Casos V21 e S02, **2/2**. Validação de referências, remoção de trecho sintético, privacidade, confirmação de município e emergência antes do LLM. | Comprovado no recorte |
| Interpretação dos resultados | 2,0 | Relatório e [revisão crítica](evidencias/REVISAO_QUALITATIVA.md). Distingue busca global do roteamento e explica a abstenção em alagamento. | Comprovado no recorte, com revisão humana pendente |

O vídeo registra a interface desta entrega com Qwen local. O enunciado exige o assistente integrado à solução CitizenTech do grupo. A disponibilidade de um protótipo separado e a aprovação da proposta permanecem dependências externas. A avaliação acadêmica pertence ao professor.

