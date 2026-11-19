# Casos de falha provocados e o que o robo fez

Gerado por `python main.py falhas`. Cada cenario roda o fluxo completo em `saida/demo_falhas/`.

## 1. Arquivo de entrada ausente

- Falha provocada: A pasta de entrada esta vazia.
- Comportamento esperado: Registrar o erro, nao criar nem alterar nada e encerrar com relatorio.
- Observado: Status: sem arquivo de entrada. Banco criado: False.

Trecho do log:

```
2026-11-19 10:45:49 | ERROR   | Nenhum arquivo .csv em saida/demo_falhas/1_arquivo_ausente/entrada. Caminho seguro: nada e alterado e o robo encerra com relatorio.
2026-11-19 10:45:49 | INFO    | Fim. Status: sem arquivo de entrada. Relatorio em saida/demo_falhas/1_arquivo_ausente/saida/relatorio_execucao.md
```

## 2. Arquivo corrompido e arquivo sem as colunas obrigatorias

- Falha provocada: Dois arquivos ruins chegam junto com um lote valido.
- Comportamento esperado: Rejeitar os dois arquivos, registrar o motivo e processar o lote valido.
- Observado: Arquivos rejeitados: 2. Arquivos lidos: 1. Relatos novos no banco: 17.

Trecho do log:

```
2026-11-19 10:45:49 | ERROR   | Arquivo rejeitado: a_corrompido.csv (nao foi possivel ler (UnicodeDecodeError)). O robo segue para o proximo.
2026-11-19 10:45:49 | ERROR   | Arquivo rejeitado: b_sem_colunas.csv (colunas ausentes: data, bairro, descricao). O robo segue para o proximo.
2026-11-19 10:45:49 | INFO    | Arquivo lido: relatos_2026-11-18.csv (22 linhas)
2026-11-19 10:45:49 | INFO    | Banco: 17 relato(s) novo(s), 0 ja existente(s).
```

## 3. Linhas com dado invalido

- Falha provocada: O lote tem descricao curta, descricao vazia, bairro vazio e data fora do formato.
- Comportamento esperado: Nao gravar essas linhas no banco e manda-las para revisao humana com o motivo.
- Observado: Linhas invalidas: 4. Repetidas no lote: 1. Linhas validas: 17.

Trecho do log:

```
2026-11-19 10:45:49 | WARNING | 1 relato(s) repetido(s) dentro do lote foram ignorados.
2026-11-19 10:45:49 | WARNING | Linha invalida: relatos_2026-11-18.csv linha 20 (descricao com menos de 30 caracteres). Vai para revisao humana.
2026-11-19 10:45:49 | WARNING | Linha invalida: relatos_2026-11-18.csv linha 21 (bairro ausente ou com tamanho invalido). Vai para revisao humana.
2026-11-19 10:45:49 | WARNING | Linha invalida: relatos_2026-11-18.csv linha 22 (data ausente ou fora do formato AAAA-MM-DD). Vai para revisao humana.
2026-11-19 10:45:49 | WARNING | Linha invalida: relatos_2026-11-18.csv linha 23 (descricao com menos de 30 caracteres). Vai para revisao humana.
2026-11-19 10:45:49 | INFO    | Fila priorizada: 17 relato(s). Revisao humana: 5 item(ns).
```

## 4. API de clima fora do ar

- Falha provocada: O endereco da API nao responde (dominio inexistente).
- Comportamento esperado: Tentar 3 vezes com espera crescente (0,5 s e 1 s), registrar e seguir sem o dado de chuva.
- Observado: API de clima: indisponivel (robo seguiu sem o dado de chuva). Relatos novos no banco: 17. Status: concluido.

Trecho do log:

```
2026-11-19 10:45:50 | WARNING | API de clima falhou (tentativa 1 de 3): ConnectionError
2026-11-19 10:45:50 | WARNING | API de clima falhou (tentativa 2 de 3): ConnectionError
2026-11-19 10:45:52 | WARNING | API de clima falhou (tentativa 3 de 3): ConnectionError
2026-11-19 10:45:52 | ERROR   | API de clima indisponivel. Caminho seguro: o robo segue sem o dado de chuva e nao altera prioridades.
2026-11-19 10:45:52 | INFO    | Banco: 17 relato(s) novo(s), 0 ja existente(s).
2026-11-19 10:45:52 | INFO    | Fim. Status: concluido. Relatorio em saida/demo_falhas/4_api_fora_do_ar/saida/relatorio_execucao.md
```

## 5. API responde com dado invalido (resposta simulada)

- Falha provocada: A API devolve HTTP 200, mas sem o campo precipitation_sum.
- Comportamento esperado: Validar o JSON, tratar como falha e seguir sem o dado de chuva.
- Observado: API de clima: indisponivel (robo seguiu sem o dado de chuva). Status: concluido.

Trecho do log:

```
2026-11-19 10:45:52 | WARNING | API de clima falhou (tentativa 1 de 2): KeyError
2026-11-19 10:45:52 | WARNING | API de clima falhou (tentativa 2 de 2): KeyError
2026-11-19 10:45:52 | ERROR   | API de clima indisponivel. Caminho seguro: o robo segue sem o dado de chuva e nao altera prioridades.
2026-11-19 10:45:53 | INFO    | Fim. Status: concluido. Relatorio em saida/demo_falhas/5_api_resposta_invalida/saida/relatorio_execucao.md
```

## 6. Falha no envio do e-mail

- Falha provocada: O servidor SMTP configurado nao existe.
- Comportamento esperado: Registrar a falha e salvar o e-mail em arquivo .eml para envio manual.
- Observado: E-mail: falha no envio, salvo em arquivo. Arquivo salvo: True.

Trecho do log:

```
2026-11-19 10:45:54 | ERROR   | Falha no envio do e-mail (gaierror). Caminho seguro: copia salva em resumo.eml
```

## 7. Mesmo lote processado duas vezes

- Falha provocada: O robo e executado de novo sem que o lote tenha mudado.
- Comportamento esperado: Nao duplicar relatos no banco.
- Observado: Primeira execucao: 17 novos. Segunda execucao: 0 novos e 17 ja existentes.

Trecho do log:

```
2026-11-19 10:45:55 | INFO    | Banco: 0 relato(s) novo(s), 17 ja existente(s).
```
