# VivaBairro Voz · guia do Gustavo

**Leia também GUIA_OPERACIONAL_COMPLETO.md e o enunciado original ENUNCIADO_OFICIAL_GS_2TIAPY.pdf. Este guia conserva o roteiro resumido de configuração.**

O VivaBairro é um assistente em português para preparar relatos de infraestrutura urbana. A aplicação e o vídeo demonstrativo estão prontos. Na origem havia 13 áudios gravados, por duas vozes (Rafael e Thiago), com 13 transcrições remotas reaproveitáveis, 30 respostas LLM e dez sínteses TTS. A tabela `CHECKLIST_ENTREGA_FINAL.md` mostra o que ainda exige trabalho humano.

## Abrir em outro computador

1. Use **Windows x64, Python 3.14 x64 e PowerShell**. Foi validado Python **3.14.7 x64** com as dependências pinadas. Instale Node.js se for executar a suíte JavaScript. Extraia `VivaBairro_GS_Codigo.zip` para uma pasta local, por exemplo `C:\Projetos\VivaBairro`. Abra o PowerShell nessa pasta.
2. Instale as duas listas de dependências com `./instalar_gs.ps1`. Se necessário, passe `-PythonExe` com o caminho da instalação local do Python. O script cria `.venv` no computador do Gustavo. A instalação de bibliotecas precisa de internet. Os testes e a importação são offline depois da instalação.
3. Compare o SHA-256 do ZIP de evidências com o valor recebido de Thiago por canal confiável. O ZIP é um contêiner de transferência, sem criptografia. Use canal privado e armazenamento restrito. Mantenha o ZIP separado da pasta do código e não faça upload de evidências ao GitHub.

   ```powershell
   Get-FileHash -Algorithm SHA256 'C:\Recebidos\VivaBairro_GS_Evidencias_Privadas.zip'
   $zip = 'C:\Recebidos\VivaBairro_GS_Evidencias_Privadas.zip'
   $sha = 'COLE_AQUI_O_SHA256_CONFIRMADO'
   & ./.venv/Scripts/python.exe -m scripts.transferir_gs restaurar $zip --sha256 $sha --dry-run
   & ./.venv/Scripts/python.exe -m scripts.transferir_gs restaurar $zip --sha256 $sha
   & ./.venv/Scripts/python.exe -m scripts.gs_preflight --dry-run
   ./iniciar_avaliacao_gs.ps1
   ```

O restaurador confere cada arquivo, reaproveita bytes idênticos e para diante de divergências. Guarde cópias locais mais recentes e compare-as antes de qualquer substituição. Para restaurar um pacote integral novo, prefira uma cópia limpa do código. O resumo `evaluation/results/estado_transferencia.json` distingue a situação na origem da evidência efetivamente recebida.

### Escopo de transferência

**Nesta nova transferência, o Pacote B contém os 13 áudios existentes e as 13 transcrições históricas para o integrante Gustavo, com escopo de uso acadêmico interno registrado pelo responsável.** Não é o pacote base sem áudios usado em algumas simulações anteriores.

Quando a geração é feita sem escopo explícito, o ZIP base leva LLM, TTS e metadados sem fala humana. Uma reserva por SHA-256 bloqueia chamadas duplicadas se um áudio já transcrito chegar sem a sua hipótese. Solicite ao responsável o lote integral quando o compartilhamento restrito estiver confirmado. Para criar o lote integral, Thiago salva fora do Git um JSON com `confirmado` igual a `true`, `destinatario` identificado, `stt` mapeando IDs aos comprovantes privados, `e2e` mapeando cenários aos comprovantes de compartilhamento e `video` apontando ao comprovante correspondente. Os caminhos podem ser relativos a `evaluation/consents/` ou absolutos na máquina que gera o pacote. Use `python -m scripts.transferir_gs criar --saida pasta-nova --escopo caminho.json`. Os comprovantes permanecem com o responsável. Envie apenas a confirmação mínima do escopo para o destinatário autorizado. Consentimento para OpenAI e consentimento para compartilhar evidência têm escopos distintos.

### Rodar a aplicação

Use `./.venv/Scripts/python.exe app.py --check` para diagnóstico e `./.venv/Scripts/python.exe app.py` para abrir a interface. Acesse `http://127.0.0.1:7860`. Para chamadas reais pagas, use credenciais próprias autorizadas em `%LOCALAPPDATA%\VivaBairroVoz\.env`. Consulte `config.example.env` para os limites da aplicação e `README.md` para as variáveis `OPENAI_*`. Nenhuma chave foi transferida. O menu 1 testa o ambiente e o HTTP offline.

## Inserir G08 a G14 e revisar

1. Grave os sete roteiros de `evaluation/roteiros_stt.md`, preservando a fala natural. Planeje ruído seguro em G11 e G14. Separe somente as gravações em uma pasta, mantendo os originais.
2. Use a opção 3 ou `python -m evaluation.importar_gustavo caminho-da-pasta` com o Python do venv. O importador confere duração, integridade, compatibilidade e SHA-256, evita duplicações e atualiza a lista. As gravações ficam sem ID acadêmico até a confirmação pela fala.
3. Abra a opção 4. Ouça cada arquivo, associe ao roteiro certo, transcreva literalmente e registre ruído observado. Uma segunda pessoa confere a referência e identifica-se como revisora. Há 20 IDs reservados. A página mostra os arquivos presentes. Exporte o JSON e importe pela mesma opção. A página de escuta não contém hipóteses.
4. Confirme e registre o aceite específico do participante para envio à OpenAI e vincule o comprovante e o `consent_id` na página de revisão. R07 já foi transcrito após autorização informada por Thiago em 17/11/2026; para usos e compartilhamentos adicionais, confirme o consentimento específico. Se um áudio estiver marcado `PENDENTE_RESTAURAR_HISTORICO`, obtenha a chamada já paga e seu vínculo de consentimento. Use a opção 5 somente para IDs faltantes elegíveis, depois de conferir o custo e obter autorização da rodada. A transcrição histórica é reaproveitada com o SHA-256 original e o consentimento de origem, mesmo em outro computador.
5. Use a opção 6 para WER e demais métricas. Execute `./preparar_whisper.ps1` para instalar o binário e pesos verificados, então a opção 8. O comparador só usa pares com referência humana e o mesmo WAV por hash. A latência A inclui rede. B registra inferência, carga e processo local. Registre a decisão após a coleta.

## Julgamentos LLM e TTS

As 30 respostas LLM estão prontas. A avaliação GPT-6 permaneceu explicitamente identificada como IA. A revisão humana é opcional. Abra `evaluation/results/llm_revisao_para_preencher.csv`, julgue os casos pelo catálogo e use `python -m evaluation.revisar_llm importar caminho.csv` para criar uma versão separada. Q19 e Q23 merecem atenção especial.

Thiago envia o `kit_tts_avaliadores.zip`. Cada integrante extrai com todos os WAVs, abre `avaliar_tts.html`, escuta as dez amostras, registra duas notas de 1 a 5 e devolve somente o CSV no WhatsApp. IDs P01 para Thiago, P02 para Rafael e P03 para Gustavo. Importe os três CSVs juntos com a opção 7. A mesma ficha pode ser reimportada sem duplicar notas.

## Conversas C01 a C10

Use a interface atual e o protocolo `evaluation/coleta_e2e_upload.md`. Thiago conduz C01–C04, Rafael C05–C07 e Gustavo C08–C10. Confirme o termo, mantenha a aba e só peça a pergunta seguinte depois de o participante ouvir a resposta anterior. Antes do próximo turno, salve o WAV, os textos e o JSON de detalhes após `playing`. Preencha `e2e_capture_template.json`, confirmando `interactive_confirmed` e, nos turnos seguintes, `heard_previous_response`. A opção 9 importa o turno. Registre falhas e repetições. Tempo de espera no WhatsApp fica fora das latências do aplicativo.

## Preparar a pasta final

Use a opção 11 para simular sem editar arquivos. A opção 10 gera outro preliminar. Após completar todas as séries, confirme com o professor a edição diante de GS 2027 e 2026.2. Prepare o escopo restrito para o avaliador e um TXT justificando a escolha STT com os resultados. Execute a opção 12 ou:

```powershell
& ./.venv/Scripts/python.exe -m scripts.finalizar_gs --dry-run
& ./.venv/Scripts/python.exe -m scripts.finalizar_gs --saida entrega_gs_final --edicao 'Edição confirmada pelo docente' --escopo caminho.json --decisao escolha-stt.txt
```

Confirme as páginas PNG, os nomes e RMs, o MP4 intacto, os arquivos restritos e o índice `ABRIR_ENTREGA.md`. Compartilhe somente uma pasta de entrada com o professor e permissões verificadas. A preparação local não envia, publica nem cria um link.
