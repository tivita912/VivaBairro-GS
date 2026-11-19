# Guia operacional completo — VivaBairro Voz / Global Solution FIAP

**Objetivo:** permitir que Gustavo (ou Thiago) restaure o projeto em outro Windows, continue a coleta real e gere a entrega final sem refazer chamadas pagas ou adulterar dados. Leia também ENUNCIADO_OFICIAL_GS_2TIAPY.pdf e ORIENTACOES_DO_PROFESSOR.md.

## 1. O que há dentro do ZIP de transferência

O arquivo mestre de transferência é **privado**: inclui gravações de voz e resultados com hashes, não é criptografado. Não colocar no GitHub público nem em grupo de WhatsApp.

Após extrair o arquivo mestre, localize:

- 00_LEIA_PRIMEIRO.txt: mapa dos arquivos e aviso de privacidade.
- DOCUMENTOS_PROFESSOR/ENUNCIADO_OFICIAL_GS_2TIAPY.pdf: enunciado original de três páginas, copiado sem edições.
- DOCUMENTACAO/: estes guias, checklist e estado real.
- PACOTES/VivaBairro_GS_Codigo.zip e seu .sha256: código, scripts, testes e documentação.
- PACOTES/VivaBairro_GS_Evidencias_Privadas.zip e seu .sha256: dados **privados** autorizados para trabalho interno; originais, históricos STT, LLM, TTS e vídeo.
- PACOTES/VivaBairro_GS_Kit_TTS.zip: pacote que pode ser enviado aos três avaliadores, desde que autorizado o compartilhamento.
- PACOTES/manifesto dos arquivos: integridade e rastreabilidade.

Os arquivos de consentimento privados e as credenciais **não** devem ser enviados dentro do pacote. O responsável confere autorizações antes de ampliar o acesso a terceiros.

## 2. Preparar Windows novo (Gustavo)

**Ambiente validado:** Windows x64, PowerShell, Python 3.14 x64. A restauração foi testada em Python 3.14.7; Node.js é recomendado para testes JS. A instalação inicial das bibliotecas exige internet.

1. Extraia o ZIP mestre numa pasta privada, por exemplo C:\Projetos\RecebidosGS.
2. Extraia PACOTES/VivaBairro_GS_Codigo.zip em C:\Projetos\VivaBairro, **não dentro de outra pasta com o mesmo nome**. Ao final deve existir C:\Projetos\VivaBairro\app.py.
3. Abra o PowerShell na pasta C:\Projetos\VivaBairro.
4. Execute:

    .\instalar_gs.ps1

Se PowerShell bloquear o script por política local, execute o seguinte no próprio PowerShell (somente para este processo):

    Set-ExecutionPolicy -Scope Process Bypass
    .\instalar_gs.ps1

Verifique Python e dependências:

    .\.venv\Scripts\python.exe --version
    .\.venv\Scripts\python.exe -m pip check

Se precisar selecionar o Python manualmente, use o parâmetro -PythonExe de instalar_gs.ps1, passando caminho correto para Python 3.14 x64.

**Não copie .venv de Thiago. Não cole tokens em README, terminal compartilhado ou GitHub.**

## 3. Confirmar integridade e restaurar as evidências privadas

O arquivo de hash do pacote privado foi gerado junto ao ZIP. A hash recebida deve ser conferida por canal seguro com Thiago. Execute:

    Get-FileHash -Algorithm SHA256 'C:\Projetos\RecebidosGS\PACOTES\VivaBairro_GS_Evidencias_Privadas.zip'

O resultado precisa ser **idêntico** ao valor do arquivo .sha256. Depois defina as variáveis (copie a hash real):

    $zip = 'C:\Projetos\RecebidosGS\PACOTES\VivaBairro_GS_Evidencias_Privadas.zip'
    $sha = 'COLE_AQUI_OS_64_CARACTERES_DA_HASH'
    .\.venv\Scripts\python.exe -m scripts.transferir_gs restaurar $zip --sha256 $sha --dry-run
    .\.venv\Scripts\python.exe -m scripts.transferir_gs restaurar $zip --sha256 $sha

A restauração valida SHA-256 por arquivo, reaproveita os idênticos e para com erro diante de conflitos. **Nunca sobrescreva arquivos conflitantes sem análise.** Se não houver autorização de acesso às gravações, não restaure o pacote privado até resolver o escopo.

Verifique se os registros realmente chegaram:

    .\.venv\Scripts\python.exe -m scripts.gs_preflight --dry-run

**Atenção:** restaurar o ZIP não transfere as chaves da API OpenAI. O executor reutiliza o histórico de chamadas quando hashes e evidências coincidem, sem consumo novo.

## 4. Abrir a aplicação

Para diagnóstico offline:

    .\.venv\Scripts\python.exe app.py --check

Para usar a interface:

    .\.venv\Scripts\python.exe app.py

Abra no navegador:

    http://127.0.0.1:7860

Para processar voz em nuvem com novos arquivos, configure a sua própria credencial autorizada no local privado orientado em config.example.env e README, não dentro do ZIP.

## 5. Menu de execução fácil

Na raiz do código:

    .\iniciar_avaliacao_gs.ps1

As opções funcionais do menu são:

| Opção | Ação |
| ---: | --- |
| 1 | Verificar ambiente, dependências, HTTP e testes |
| 2 | Mostrar pendências acadêmicas atuais |
| 3 | Importar gravações de Gustavo |
| 4 | Abrir revisão cega STT ou importar JSON revisado |
| 5 | Processar STT novo com confirmação explícita de custo |
| 6 | Recalcular métricas e WER |
| 7 | Importar CSVs de notas TTS |
| 8 | Comparar STT remoto e Whisper local |
| 9 | Importar conversa E2E ou exibir pendências |
| 10 | Gerar PDF preliminar atualizado |
| 11 | Simular o fechamento sem gerar entrega |
| 12 | Gerar entrega final **somente se os requisitos forem atendidos** |
| 0 | Sair |

Prefira o menu para evitar erros de comando. Leia qualquer erro exibido antes de repetir operações pagas.

## 6. Como finalizar as referências STT existentes (Thiago e Rafael)

Já existem **13 gravações transcritas** com hipóteses de STT. Não é necessário enviar essas gravações novamente a uma API para preencher a referência.

- Selecione opção 4 no menu e pressione Enter para abrir a página stt_revisao.html.
- Para cada áudio, **ouça o arquivo original**, confira o ID (R01–R07 ou T15–T20) e transcreva o que a pessoa **realmente pronunciou**.
- Não copie a hipótese do STT nem rascunho do Whisper para reference_text. Consulte o roteiro somente para conferir o tema/ID, nunca como substituto da escuta.
- Uma segunda pessoa confere a referência e se identifica em reference_reviewed_by. Não atribua uma revisão ao colega se ele não ouviu.
- Marque noise_present como true/false **após escuta** e descreva o som ouvido. O ruído planejado não é confirmação de ruído real.
- Confirme consentimento aplicável e exporte o JSON pelo botão da página. Preserve uma cópia privada.
- No menu, opção 4 novamente e informe o caminho do JSON exportado para importar.
- Depois, opção 6 para WER; resultados sem referência permanecerão pendentes.

Nenhuma alteração de original ou histórico pago é necessária.

## 7. Quando Gustavo enviar G08–G14

1. Guarde os sete áudios **originais** juntos numa pasta temporária sem PDFs ou outros arquivos.
2. Grave consentimento para processamento e uso acadêmico e confirme que R07/Thiago/Rafael podem ser compartilhados conforme a finalidade.
3. No menu, opção 3, indique a pasta das sete gravações; o importador preserva nomes, hashes, integridade, formatos e evita cópias duplicadas.
4. Menu opção 4: ouça as gravações, associe corretamente os IDs G08–G14, escreva referências literais, classifique ruído, registre revisores e exporte/importe JSON.
5. Confirme o escopo de autorização de envio à OpenAI para cada novo áudio. O menu 5 mostra número de chamadas e custo estimado e exige digitar AUTORIZO STT. **Não executar sem consentimento e autorização de custo.**
6. Menu 6: recalcula resultados válidos; os 13 arquivos anteriores e suas transcrições são preservados.
7. Use preparar_whisper.ps1 e opção 8 para comparar, com mesma referência e áudio, qualidade por WER e latências documentadas. Faça decisão em TXT fundamentada nos dados.

## 8. Avaliações humanas de TTS: três pessoas × dez áudios

O enunciado exige **mínimo de três avaliadores por cada uma das dez amostras**. O kit já contém dez WAVs e formulário offline.

- Entregue o ZIP de kit de TTS aos três integrantes por canal privado.
- Cada participante extrai tudo em uma pasta e abre avaliar_tts.html sem precisar de Python.
- IDs: Thiago P01, Rafael P02, Gustavo P03.
- Cada pessoa **ouve os dez WAVs** e atribui clareza e naturalidade independentemente, duas notas inteiras de 1 a 5 por áudio.
- O formulário exporta avaliacao_tts_P01.csv (ou P02/P03), vinculando o hash ao áudio.
- Coloque os três arquivos CSV em uma pasta de notas e use **opção 7** no menu. O importador rejeita notas fora de faixa, hashes divergentes e duplicatas conflitantes.
- O sistema calcula médias e gráficos de clareza e naturalidade, sem inventar notas ausentes.

Se Gustavo ainda não avaliou, importem P01 e P02 e deixem os dez registros P03 pendentes.

## 9. Dez conversas humanas de três turnos

O enunciado exige **dez conversas completas**, não apenas o replay de três arquivos já gravados. Distribuição C01–C04 Thiago, C05–C07 Rafael, C08–C10 Gustavo.

- Abra uma sessão NOVA no navegador para cada C01 a C10.
- A pessoa grava uma pergunta, a ferramenta responde por voz, e **a pessoa realmente ouve** a resposta.
- Somente depois disso ela formula uma pergunta de continuação que usa o contexto da resposta anterior. Continue ao menos até o turno 3.
- Preserve áudio da resposta, transcrição, resposta textual, JSON da interface e tempos reais por etapa.
- Só registre heard_previous_response e interactive_confirmed se isso aconteceu.
- Eventual falha deve ter uma linha de tentativa e não ser ocultada.
- Menu 9 importa o JSON de cada turno. Consulte evaluation/coleta_e2e_upload.md e evaluation/e2e_capture_template.json.
- O evento playing do navegador é um proxy do início da reprodução, não a hora física de emissão sonora. O tempo de troca de mensagens pelo WhatsApp não é tempo do pipeline.

Para C01–C07 vocês já podem realizar as sessões sem Gustavo. C08–C10 dependem de Gustavo. O vídeo anterior e o teste técnico com upload não contam para as dez.

## 10. LLM: o que está pronto

As 30 perguntas possuem respostas reais. O avaliador IA foi registrado explicitamente como IA. A análise preliminar marcou 28 respostas adequadas e cinco recusas adequadas. Q19 e Q23 merecem conferência por uma pessoa. Não reexecutar chamadas nem declarar que os três integrantes avaliaram se não avaliaram.

As fichas de revisão humana estão em evaluation/results/llm_revisao_para_preencher.csv e o importador preserva a versão original. A comparação A/B exigida pelo enunciado será atendida com STT, quando houver WER verificado.

## 11. Recalcular métricas e relatório

Acompanhe os portões automáticos:

    .\.venv\Scripts\python.exe -m scripts.gs_preflight --dry-run

Para atualizar tabelas:

    .\.venv\Scripts\python.exe -m evaluation.academic_metrics --saida evaluation/results/metricas_nova_rodada

Para ver como ficaria a entrega sem alterar arquivos:

    .\.venv\Scripts\python.exe -m scripts.finalizar_gs --dry-run

É possível gerar outro PDF identificado como preliminar pelo menu 10 antes de finalizar.

A finalização exige:
- 20 STT reais, três vozes, cinco ruídos reais, referências revisadas e WER com jiwer;
- 30 respostas LLM avaliadas com identificação de fonte do julgamento;
- dez WAVs TTS e 30 pares de notas humanas;
- dez sessões E2E interativas com ao menos três turnos e medição real;
- comparação de dois STT baseada em qualidade e latência;
- consentimentos e escopo permitido para o professor;
- vídeo, nomes/RMs, PDF, edição e justificativa da escolha.

Com tudo verificado:

    .\.venv\Scripts\python.exe -m scripts.finalizar_gs --saida entrega_gs_final --edicao 'EDICAO_CONFIRMADA_PELO_PROFESSOR' --escopo escopo_professor.json --decisao escolha-stt.txt

ATENÇÃO: não preencher o nome da edição com texto-placeholder na versão definitiva. O escopo é um JSON privado de autorizações e o TXT descreve escolha com dados A/B. O finalizador **bloqueia** a entrega incompleta.

## 12. Privacidade, riscos e operação segura

- O ZIP contém gravações humanas e dados pessoais: permitir somente acesso restrito. **ZIP + SHA-256 não oferece criptografia**.
- Não publicar a base de áudios ou formulários no GitHub público, nem entregar autorização assinada em repositório.
- O professor precisará de material de teste; confirme antes a autorização dos titulares para compartilhar o conjunto correspondente com o avaliador.
- Armazenar comprovantes de consentimento fora do pacote de entrega; manter prova de escopo internamente.
- Ao publicar, usar link único e acesso apropriado; o projeto não publica sozinho.
- Não clonar vozes humanas. TTS utiliza voz sintética pronta.
- Não presumir que armazenamento no OneDrive esteja privado só porque o Git ignora os arquivos.
- Para evitar conflito entre computadores, eleger um responsável por integrar as alterações mais recentes e NÃO sobrescrever arquivos de avaliação divergentes.
- Não declarar 100% concluído ou prever a nota do professor apenas por passar nos testes de software.

## 13. Documentos complementares

- ENUNCIADO_OFICIAL_GS_2TIAPY.pdf — PDF original do professor.
- ORIENTACOES_DO_PROFESSOR.md — exigências por página.
- ESTADO_ATUAL_E_PENDENCIAS.md — o que foi feito e as lacunas verificadas.
- CHECKLIST_ENTREGA_FINAL.md — rubrica e responsáveis.
- GUIA_GUSTAVO.md — guia operacional anterior.
- docs/academic/metodologia.md, resultados.md, AUDITORIA_LLM.md — fundamentos e resultados.
- README.md — instruções técnicas gerais.
- evaluation/README.md, coleta_e2e_upload.md — coleta e formatos.

**Conclusão:** com esses procedimentos, Gustavo só executa as etapas pendentes de forma reprodutível e consolidará os resultados válidos. A parte humana continua obrigatória e não pode ser preenchida automaticamente.
