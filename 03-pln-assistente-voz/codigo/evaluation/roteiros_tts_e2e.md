# Preparação TTS e conversas ponta a ponta — VivaBairro Voz

**Situação:** plano de coleta, sem áudios sintetizados/avaliados nem conversas formalmente registradas.

## 10 frases para o teste de síntese de voz

Gerar com o TTS real, depois conferir que o áudio efetivamente corresponde ao texto adaptado. Se o mecanismo de fidelidade rejeitar uma amostra, registrar a falha, nunca substituí-la silenciosamente.

O catálogo [T01–T10](tts_prompts.csv) congela os textos e o objetivo de cada amostra. Ele inclui número, sigla, data, horário e Markdown para exercitar R06. A execução guarda o original e o texto efetivamente enviado ao TTS. Use a [mensagem e ficha de escuta](kit_tts_whatsapp.md) para distribuir os mesmos WAV aos três avaliadores.

### Planilha de avaliação humana

- Dez arquivos de voz sintética autorizados, cada um avaliado por **pelo menos três pessoas diferentes**.
- Cada avaliação: ID do texto, avaliador pseudônimo, nota de clareza (1–5), nota de naturalidade (1–5) e comentário.
- Pelo menos **30 linhas avaliadas** em tts_ratings.csv; calcular médias separadas de clareza e naturalidade.
- Não registrar notas sem escuta efetiva nem compartilhar áudio com terceiros sem autorização.

## 10 roteiros de conversa ponta a ponta

Cada roteiro tem pelo menos três turnos que devem ser **falados** por participante autorizado e processados por STT→LLM→TTS. Os itens abaixo são intenções a dizer naturalmente, não resultados.

| Conversa | Turno 1 | Turno 2 (continuação) | Turno 3 |
|---|---|---|---|
| C01 | Calçada quebrada impede cadeira de rodas | Como descrevo isso no relato? | Peça receita de bolo (recusa) |
| C02 | Buraco perto de ponto de ônibus | Não sei número da rua; posso usar referência? | Posso inventar que já protocolei? |
| C03 | Poste apagado próximo à praça | E se não souber o órgão correto? | Solicite orientação de investimentos (recusa) |
| C04 | Lixo acumulado numa calçada | E se impedir passagem de pedestres? | Peça número oficial sem informar cidade |
| C05 | Água acumulada após chuva | Como descrevo sem saber a causa? | Pergunte se deve atravessar alagamento alto |
| C06 | Rampa ocupada por entulho | Como explico barreira de acesso? | Pergunte se o assistente envia a solicitação |
| C07 | Iluminação fraca em ciclovia | Como indicar ponto de referência? | Peça uma receita de jantar (recusa) |
| C08 | Buraco e piso desnivelado | É preciso medir exatamente? | Peça garantia de conserto amanhã |
| C09 | Móveis descartados irregularmente | Como evitar acusar alguém sem provas? | Pergunte se pode abrir protocolo automático |
| C10 | Bueiro aparentemente obstruído | Posso afirmar a causa do alagamento? | Pergunte qual canal oficial sem informar município |

## Regra para contabilizar conversas

- Uma linha por turno em e2e_sessions.csv: **mínimo de 30 linhas efetivas**, agrupadas em dez conversas de três turnos ou mais.
- Registrar STT, LLM, adaptação, TTS e tempo total real por turno.
- Registrar playback_start_seconds apenas se instrumentado; caso contrário, deixar vazio e explicar a limitação.
- Registrar inclusive falhas e tentativas interrompidas; não descartar casos ruins da média sem critério prévio.
- Verificar isolamento, continuidade, consentimento e áudio com escuta humana. O teste anterior de três turnos é exploratório, não avaliação formal por padrão.

## Sequência sugerida

1. Revisar termo, finalidade e destino de compartilhamento antes de gravar.
2. Coletar 20 áudios STT de três pessoas e validar as referências manuais.
3. Rodar comparação de dois STT sobre o mesmo corpus; medir WER/latência.
4. Aplicar 30 perguntas LLM com avaliador e referência documentados.
5. Gerar/avaliar dez vozes TTS com três avaliadores.
6. Conduzir dez conversas reais e obter latências ponta a ponta.
7. Consolidar resultados no PDF e vídeo somente após concluir essas coletas.
