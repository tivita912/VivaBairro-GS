# Coleta ponta a ponta por upload

Nos turnos bem-sucedidos, confirme `interactive_confirmed` no JSON. Nos turnos 2 e seguintes, confirme `heard_previous_response` somente se o participante de fato ouviu a resposta e formulou a pergunta depois. Um replay de áudios roteirizados fica fora da planilha acadêmica.

Use os cenários C01–C10 em `roteiros_tts_e2e.md`. Confirme consentimento para enviar áudio e texto à OpenAI, para usar o corpus na avaliação e para guardar evidências conforme prazo combinado. Obtenha autorização para o consumo da rodada. Use identificadores pseudônimos e guarde termos, áudios e textos em área restrita.

1. Abra uma sessão nova e identifique-a na coleta com um código próprio, por exemplo `C01-A`. Use o mesmo código, aba e consentimento até concluir a conversa. Combine antes como o participante vai receber a resposta de cada turno.
2. Receba a pergunta de voz no WhatsApp, preserve o original e faça upload. Acione o player assim que puder e espere a reprodução. Deixe o participante ouvir a resposta real. Receba depois a pergunta seguinte, relacionada ao que foi respondido.
3. Antes de enviar o próximo arquivo, salve o WAV da resposta pelo player (opção do navegador **Salvar áudio como**). Guarde-o em `evaluation/results/e2e/C01-A/`, com nome que indique a tentativa. Copie da interface a transcrição, a resposta e o JSON em **Métricas do atendimento → Detalhes técnicos** após o evento `playing`. Se não houver `playing` ou algum campo não estiver disponível, registre a lacuna.
4. Faça uma cópia de `e2e_capture_template.json` e preencha os campos. Cole o objeto exato no campo `metrics`. `logical_turn` representa a pergunta corrente na mesma conversa. `turn_id` cresce a cada tentativa de coleta. Se o erro impediu o turno de entrar no histórico, uma repetição usa outro `turn_id` e o mesmo `logical_turn`. Se o turno entrou no histórico mas faltou a medição, preserve essa tentativa como `incomplete` e avance a sequência lógica. Use `failed` quando um componente ou o envio falhar. Registre o texto visível, a etapa e o motivo disponível. Use `consent_document` com o caminho do termo aplicável e `audio_evidence_path` relativo a `evaluation/`.
5. Importe a captura na raiz do projeto e confira a linha registrada antes de repetir os passos.

   ```powershell
   & ./.venv/Scripts/python.exe -m evaluation.import_e2e caminho-da-captura.json
   ```

Marque `consent_scope_confirmed` como `true` depois de conferir o termo. Guarde o JSON original com o WAV em área privada. Use outro código de sessão e continue a numeração de tentativas do cenário se for necessário recomeçar em outra aba.

`playback_start_seconds` vai da seleção do arquivo ao primeiro `playing`, incluindo esperas do usuário. `send_to_playing_seconds` começa no envio. `playing` aproxima o início da reprodução no navegador. O horário da pergunta original no WhatsApp e o momento de emissão física do som estão fora dessa medição. `input_audio_duration_seconds` é duração da mídia. Reporte etapas e esperas com os marcos disponíveis.

Registre pelo menos 10 sessões com 3 ou mais turnos reais consecutivos, mantendo o vínculo de contexto. Se já faltar uma medição em um turno comprometido, mantenha o cenário e as tentativas incompletas para auditoria. A sessão precisa de uma série completa verificável para entrar nas dez. O vídeo e os ensaios de desenvolvimento têm finalidade de demonstração.
