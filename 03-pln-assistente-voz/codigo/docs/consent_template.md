# Modelo de aviso e autorização — preencher antes da coleta

Este é um instrumento acadêmico **não preenchido**. A equipe deve definir o
responsável, os contatos, o ambiente e o prazo de retenção antes de utilizá-lo.
Não há consentimentos de participantes coletados nesta etapa.

## A. Uso operacional do assistente

**Projeto:** VivaBairro Voz, assistente acadêmico sobre infraestrutura urbana.
**Responsável e contato:** [preencher]. **Versão do aviso operacional:** 2.0-openai; registrar versão final do termo.
**Ambiente de processamento:** aplicativo local Windows com APIs OpenAI externas.

Sua fala será captada apenas quando você iniciar a gravação. Ela será processada
para transcrever o relato e gerar uma resposta em texto e voz sintética. Não diga
nome completo, documento, telefone ou endereço residencial completo. O sistema
não abre solicitações nem gera protocolos oficiais.

A cópia operacional do áudio será descartada após a transcrição, também em falhas.
O arquivo original que você escolher para upload permanecerá no seu dispositivo.
**Cache de upload, histórico, áudio sintetizado e expiração:** por padrão, a sessão
expira após 600 segundos de inatividade, com varredura de até 10 segundos. Limpar
apaga o histórico e as cópias operacionais associadas; iniciar novo turno remove a
saída anterior. Uploads interrompidos são descartados no fim da requisição. A raiz fica no
temporário local, fora da pasta do projeto. Encerramento normal limpa essa raiz;
queda abrupta, cópias do navegador e backups não têm garantia de exclusão. Confirmar
os limites efetivos se a configuração mudar.

**Serviços externos e dados enviados:** OpenAI recebe áudio para transcrição,
transcrição e histórico para resposta, e texto da resposta para síntese de voz.
Há consumo de API paga. A localização exata e as condições da conta devem ser
confirmadas pela equipe antes da coleta. A retenção do provedor é independente
da limpeza local; store=False não significa retenção zero. Consultar a fonte
oficial vinculada em docs/dependencies.md e informar as condições aplicáveis.
Colab é processamento na nuvem, não no dispositivo do cidadão. Se houver TTS remoto,
o texto da resposta pode ser enviado ao provedor; isso não equivale a envio de voz,
mas pode conter informações pessoais derivadas do relato.

- [ ] Li/ouvi o aviso e autorizo a captação e o processamento descritos.
- [ ] Autorizo o envio do meu áudio à OpenAI para transcrição.
- [ ] Autorizo o envio de transcrição, histórico e resposta à OpenAI para gerar texto e voz.

As três opções devem iniciar desmarcadas. Recusa deve impedir as operações
correspondentes. Mudança de provedor/finalidade exige novo aviso. Oferecer forma
acessível de ouvir o aviso e aceitar/recusar antes da captura; não exigir que a
pessoa grave a própria voz para poder conhecer o aviso.

## B. Corpus de avaliação — autorização independente

Gravações de teste são uma exceção à retenção operacional. Definir:

| Campo | Informação a preencher |
| --- | --- |
| consent_id e participant_id | IDs pseudônimos, sem documento pessoal |
| Responsável e contato para dúvidas/retirada | Pendente |
| Finalidade | Avaliação acadêmica de STT e demonstração, conforme opções abaixo |
| Data da gravação e versão do termo | Pendente |
| Pasta privada e pessoas com acesso | Pendente |
| Retenção até data definida | Pendente; não aceitar prazo indefinido |
| Procedimento de exclusão e retirada | Pendente; explicar limites de cópias já compartilhadas |
| Sincronização e backups | Informar OneDrive/Colab/outros, se presentes |

- [ ] Autorizo a gravação para avaliação interna do grupo.
- [ ] Autorizo o envio destas gravações à OpenAI para transcrição e avaliação de STT do corpus, conforme o aviso de processamento e retenção apresentado.
- [ ] Autorizo acesso restrito pelo professor para correção.
- [ ] Autorizo uso da voz no vídeo acadêmico indicado: [identificar destino].
- [ ] Autorizo publicação pública dos áudios nos locais indicados: [identificar].

Não vincular autorização de uso interno à publicação pública. A ausência de uma
opção não autoriza a finalidade correspondente. Pseudonimização não torna a voz
anônima. Não coletar dados pessoais desnecessários nos roteiros. Guardar autorizações
separadas das planilhas de métricas, com acesso restrito. Não clonar vozes.

**Registro de aceite:** [método acessível, data, versão do termo e responsável].
**Revisão humana do instrumento antes do uso:** [nome e data a preencher].
