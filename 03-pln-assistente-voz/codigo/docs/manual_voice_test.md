# Teste humano de três turnos — preparado, ainda não executado

Este roteiro não é evidência de avaliação. Use um participante autorizado, sem
nomes, endereços residenciais, telefones ou outros dados pessoais no conteúdo.
Defina consentimento para uso operacional, eventual gravação da demonstração,
acesso pelo professor e retenção do corpus antes de capturar voz humana.

1. Inicie app.py, leia o aviso e confirme os três consentimentos. Verifique que os
   controles de captura estavam ocultos antes do aceite.
2. Turno 1: relate com suas palavras uma calçada quebrada perto de uma praça que
   dificulta a passagem de cadeirantes. Envie pelo microfone. Confira transcrição,
   resposta, áudio sintético, histórico e tempos. Registre o que realmente aconteceu.
3. Turno 2: pergunte “E onde eu faço isso?”. Confira se usa o contexto e admite que
   não há canal municipal verificado. Não deve inventar telefone, prazo ou protocolo.
4. Turno 3: peça uma receita de bolo. Confira se recusa e explica os temas atendidos.
5. Faça um teste separado por upload. Use áudio autorizado, verifique duração/tamanho.
6. Abra outra sessão e confirme ausência do histórico anterior. Não trate isso como
   autenticação: a aplicação é uma demonstração local.
7. Use Limpar conversa. Confira campos, histórico, player
   e bloqueio de novos envios. O contador de chamadas deve continuar consumido.

Registrar navegador, microfone, áudio audível após acionar o player, erros, tempo
por etapa e marco de reprodução. playback_start_seconds fica vazio enquanto não
houver instrumentação; não preencher com processing_total_seconds.

A API Realtime pode divergir do texto. Nesse caso o áudio é descartado e o texto
permanece visível com erro. Não apresentar esse turno como sucesso de ponta a ponta.
A transcrição declarada pela síntese pode não garantir fidelidade do áudio real;
ouça e confira. Teste números, datas e siglas após implementar a normalização R06.

Depois do ensaio funcional, seguir o plano formal em evaluation/README.md.
O vídeo final de até cinco minutos precisa de conversa real, três turnos,
continuação e recusa. Nada desse roteiro deve ser preenchido retrospectivamente
com dados inventados ou com áudio sintético apresentado como voz humana.
