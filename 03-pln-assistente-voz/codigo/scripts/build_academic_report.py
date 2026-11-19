"""Gera o relatório da Global Solution a partir de um snapshot de métricas local."""

import argparse
import csv
from html import escape
import json
from pathlib import Path
from statistics import mean

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
GREEN = colors.HexColor("#104B3D")
DARK = colors.HexColor("#15312A")
MUTED = colors.HexColor("#4B6059")
PALE = colors.HexColor("#E5F0E9")
PAPER = colors.HexColor("#F8FAF8")
LINE = colors.HexColor("#CADAD0")
BODY, BOLD = "Helvetica", "Helvetica-Bold"


def configure_fonts():
    global BODY, BOLD
    fonts = Path("C:/Windows/Fonts")
    if (fonts / "segoeui.ttf").exists():
        BODY, BOLD = "Segoe", "Segoe-Bold"
        pdfmetrics.registerFont(TTFont(BODY, str(fonts / "segoeui.ttf")))
        pdfmetrics.registerFont(TTFont(BOLD, str(fonts / "segoeuib.ttf")))
    pdfmetrics.registerFontFamily(BODY, normal=BODY, bold=BOLD, italic=BODY, boldItalic=BOLD)


def graph(rows):
    height = 38 + 21 * len(rows)
    drawing = Drawing(475, height)
    drawing.add(Rect(0, 0, 475, height, fillColor=PAPER, strokeColor=LINE, rx=6, ry=6))
    peak = max(float(row["stt_seconds"]) for row in rows) or 1
    for i, row in enumerate(rows):
        y = height - 27 - 21 * i
        value = float(row["stt_seconds"])
        drawing.add(String(13, y + 1, row["sample_id"], fontName=BOLD, fontSize=9, fillColor=DARK))
        drawing.add(Rect(68, y, value / peak * 310, 11, fillColor=GREEN, strokeColor=None))
        drawing.add(String(395, y + 1, f"{value:.3f}".replace(".", ",") + " s", fontName=BODY, fontSize=9, fillColor=DARK))
    return drawing


def architecture():
    drawing = Drawing(475, 130)
    groups = [["Microfone / upload", "FastAPI + PyAV", "OpenAI STT", "Histórico e base"],
              ["Player + texto", "OpenAI Realtime", "Adaptação pt-BR", "OpenAI LLM"]]
    for line, labels in enumerate(groups):
        y = 78 - 59 * line
        for column, label in enumerate(labels):
            x = 119 * column
            drawing.add(Rect(x, y, 107, 36, fillColor=PALE, strokeColor=LINE, rx=5, ry=5))
            drawing.add(String(x + 53.5, y + 14, label, textAnchor="middle", fontName=BOLD, fontSize=8.4, fillColor=DARK))
            if column < len(labels) - 1:
                start, end = x + 108, x + 118
                drawing.add(Line(start, y + 18, end, y + 18, strokeColor=GREEN))
                tip, back = (end, start + 4) if line == 0 else (start, end - 4)
                drawing.add(Polygon([tip, y + 18, back, y + 21, back, y + 15], fillColor=GREEN, strokeColor=None))
    drawing.add(Line(410.5, 78, 410.5, 55, strokeColor=GREEN))
    drawing.add(Polygon([410.5, 55, 407.5, 61, 413.5, 61], fillColor=GREEN, strokeColor=None))
    return drawing


def build(output, metrics_path, edition, final, decision=""):
    configure_fonts()
    if metrics_path:
        data = json.loads(metrics_path.read_text(encoding="utf-8"))
    else:
        from evaluation.academic_metrics import run
        data = run(ROOT / "evaluation")
    stt, llm, tts, e2e, comp = (data[name] or {} for name in ("stt", "llm", "tts", "e2e", "comparison"))
    if final and not (edition and stt.get("quantity_gate_met") and all(r.get("complete") for r in (llm, tts, e2e, comp))):
        raise SystemExit("A versão final exige confirmação da edição e todas as séries completas no snapshot.")
    manifest = ROOT / "evaluation/stt_manifest.csv"
    recorded = []
    if manifest.exists():
        with manifest.open(encoding="utf-8-sig", newline="") as stream:
            recorded = list(csv.DictReader(stream))
    latencies = [row for row in recorded if row["transcription_completed"] == "true" and row["stt_seconds"]]
    if len(latencies) != stt.get("transcribed", 0):
        raise SystemExit("CSV de STT diverge do snapshot acadêmico informado.")
    revision = "RELATÓRIO FINAL" if final else "RELATÓRIO PRELIMINAR"
    num = lambda value: f"{value:.3f}".replace(".", ",")
    pct = lambda value: f"{value:.2f}%".replace(".", ",")
    latency_summary = (f"Média {num(mean(float(r['stt_seconds']) for r in latencies))} s em {len(latencies)} chamadas."
                       if latencies else "Aguardando chamadas válidas.")
    ref_count = stt.get("human_references", 0)
    comparison_count = comp.get("pairs", 0)
    wer_value = stt.get("wer_corpus")
    wer_summary = f"{wer_value:.2%}".replace(".", ",") if wer_value is not None else "Pendente de referências revisadas"
    mean_ratings = tts.get("overall") or {}
    paired_config = comp.get("groups", [])
    pooled = comp.get("corpus_wer") or (paired_config[0] if len(paired_config) == 1 else {})
    judges = llm.get("judgment_sources", {})
    judge_label = "Avaliação por IA" if judges.get("ia") else "Revisão humana" if judges.get("humano") else "Avaliador registrado"
    llm_summary = (f"{judge_label}. Acerto {pct(llm['accuracy_all_percent'])} · recusas {pct(llm['refusal_percent'])}"
                   if llm.get("accuracy_all_percent") is not None and llm.get("refusal_percent") is not None else "Pendente")
    tts_summary = (f"Clareza {num(mean_ratings['clarity'])} · naturalidade {num(mean_ratings['naturalness'])}"
                   if mean_ratings.get("clarity") is not None else "Pendente")
    upload_latency = (e2e.get("by_source_seconds") or {}).get("upload")
    e2e_summary = f"Upload até playing: {num(upload_latency['mean'])} s" if upload_latency else "Pendente"
    comparison_summary = ("WER A " + pct(100 * pooled["A"]["wer_corpus"]) +
                          " e B " + pct(100 * pooled["B"]["wer_corpus"]) if pooled else
                          "Por configuração" if paired_config else "Pendente")
    s = []

    def paragraph(text, size=11, leading=16, bold=False, ink=DARK, after=8):
        return Paragraph(text, ParagraphStyle("report", fontName=BOLD if bold else BODY, fontSize=size,
                                              leading=leading, textColor=ink, spaceAfter=after))

    def section(name, title, intro=None):
        s.extend([paragraph(name.upper(), 9, 13, True, GREEN, 7), paragraph(title, 27, 32, True, DARK, 14)])
        if intro:
            s.append(paragraph(intro))

    def h(text):
        s.append(paragraph(text, 14, 19, True, GREEN, 5))

    def p(text):
        s.append(paragraph(text))

    def table(rows, widths):
        cells = [[paragraph(escape(str(col)), 9.1, 12.2, i == 0, colors.white if i == 0 else DARK, 0)
                  for col in row] for i, row in enumerate(rows)]
        t = Table(cells, colWidths=widths, hAlign="LEFT", repeatRows=1)
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), GREEN),
                               ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PAPER, PALE]),
                               ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 8),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("LEFTPADDING", (0, 0), (-1, -1), 10),
                               ("RIGHTPADDING", (0, 0), (-1, -1), 10)]))
        s.extend([t, Spacer(1, 13)])

    s.extend([Spacer(1, 77), paragraph("FIAP  /  GLOBAL SOLUTION  /  PLN", 11, 14, True, GREEN, 22),
              paragraph("VivaBairro<br/>Voz", 54, 55, True, DARK, 22),
              paragraph("Assistente de voz para relatos urbanos acessíveis", 17, 23, False, MUTED, 35),
              paragraph(revision, 10, 15, True, GREEN, 10)])
    table([("Integrante", "RM"), ("Thiago Santana Danyluk", "562286"), ("Rafael de Paiva Ramos", "563978"),
           ("Gustavo Civita Gonçalves", "561932")], [355, 120])
    p(escape(edition) if edition else "O enunciado está intitulado GS 2027. A documentação interna usa 2026.2. Edição e calendário aguardam confirmação do docente.")
    stamp = data.get("preflight", {}).get("generated", "")[:10]
    p((f"Snapshot de {escape(stamp)}. " if stamp else "") + "O enunciado prevê um único link para a entrega.")
    s.append(PageBreak())

    section("Problema e proposta", "Um relato urbano pela voz")
    h("Persona e problema")
    p("Uma moradora com mobilidade reduzida ou dificuldade para digitar precisa explicar que uma calçada quebrada bloqueia a passagem. A aplicação também atende relatos sobre buracos, iluminação pública, lixo irregular e alagamentos.")
    h("Objetivos e ODS")
    p("Receber fala em português, preservar o contexto entre turnos e ajudar o cidadão a redigir um relato verificável. A orientação apoia o ODS 11, cidades inclusivas e acessíveis, e se relaciona ao ODS 16 pela participação e pelo acesso a informações sobre serviços. O cidadão revisa a orientação e decide o encaminhamento. O sistema não abre chamados oficiais.")
    h("Arquitetura")
    s.append(architecture())
    p("FastAPI recebe upload ou áudio do MediaRecorder, valida tamanho e duração e usa PyAV para preparar WAV. STT, LLM, adaptação e TTS têm contratos separados. O navegador exibe a transcrição e o texto original, reproduz a versão adaptada e mede eventos do player.")
    h("Contexto e base de conhecimento")
    p("O prompt v1 regula o escopo e a memória da sessão guarda até seis pares. A base 1.0.0 injeta contexto curado de cinco temas, com fontes e escopo geográfico. As orientações de organização de relatos são editoriais. Para alagamentos, a base usa orientação oficial de autoproteção. Informação municipal exige fonte própria.")
    s.append(PageBreak())

    section("Ambiente e governança", "Tecnologias, licenças e dados")
    table([("Camada", "Componente e versão", "Licença ou modalidade"),
           ("Aplicação", "Python 3.14.7 · FastAPI 0.162.5 · Uvicorn 0.54.0", "PSF · MIT · BSD-3-Clause"),
           ("Áudio e métricas", "PyAV 19.0.2 · jiwer 4.0.0", "BSD-3-Clause · Apache-2.0"),
           ("Integração", "OpenAI Python SDK 3.49.0", "Apache-2.0 para o SDK"),
           ("STT em nuvem", "gpt-transcribe · português · revisão de pesos indisponível", "Serviço proprietário"),
           ("LLM e TTS", "gpt-6-luna · gpt-realtime-2.1-mini, voz marin", "Serviços proprietários"),
           ("Comparação offline", "whisper.cpp 1.8.6 · Whisper base multilíngue Q5_1", "MIT para motor e pesos originais")],
          [102, 226, 147])
    h("Nuvem e execução local")
    local = comp.get("local_environment", {})
    p("Os serviços remotos evitam dependência de GPU no computador do grupo, com custo variável e dependência de rede. O STT local reduz transferência de voz e funciona offline, com carga de pesos e CPU no cliente. "
      + (f"Ambiente local verificado: {escape(local.get('cpu', 'CPU'))}, {local.get('logical_cpus', '—')} processadores lógicos, {local.get('threads', 6)} threads usadas."
         if local else "O ambiente de B será identificado na apuração comparativa."))
    h("Privacidade e limites")
    p("A interface pede aceites separados antes do envio de áudio e texto. O backend mantém a chave fora do projeto. Entradas operacionais são transitórias e a sessão expira. O envio remoto tem política própria de tratamento e retenção. store=False não implica retenção zero. O corpus acadêmico exige finalidade, acesso e retenção documentados, com avaliação de compartilhamento separada.")
    p("O OneDrive pode sincronizar originais e derivados independentemente do Git. A equipe deve conferir acessos, versões e prazo de exclusão. Os controles técnicos reduzem exposição, mas carecem de revisão do ciclo de dados. O projeto usa voz sintética pronta e prevê recusa e encaminhamento em situações fora de escopo.")
    s.append(PageBreak())

    section("Desenho experimental", "Métodos e critérios de aceite")
    h("STT e comparação pareada")
    p("Vinte gravações, três vozes e pelo menos cinco com ruído real confirmado por escuta. Revisores ouvem os originais às cegas e confirmam ID, referência literal e condição acústica. As hipóteses históricas foram registradas antes da revisão e ficam em arquivo separado. WER = (substituições + exclusões + inserções) / palavras da referência, agregando contagens pelo jiwer. A normalização pt_v1 preserva acentos e números.")
    p("A usa gpt-transcribe via API e B usa Whisper local. Os pares compartilham hashes do original e do WAV, referência e normalização. A latência remota inclui rede. B informa tempo do processo, carga dos pesos e duração interna sem carga. Cada áudio de B inicia um processo. A não expõe inferência ou preparação do servidor. Sem base para escolher um vencedor antes da coleta.")
    h("LLM")
    p("Avaliar 20 perguntas urbanas, cinco continuações com o histórico real do antecedente e cinco fora do escopo. Registrar resposta literal, versões, latência e falhas. Julgar com os critérios previamente registrados, usando acerto e recusas adequadas com denominadores explícitos.")
    h("TTS")
    p("Gerar dez WAV numerados com marin e o adaptador pt-BR. Os três avaliadores ouvem os mesmos arquivos e atribuem, independentemente, notas inteiras de 1 a 5 para clareza e naturalidade. Exigir pelo menos 30 pares de notas.")
    h("Ponta a ponta por upload")
    p("Dez conversas de pelo menos três turnos com consentimento. O participante ouve cada resposta antes de gravar a continuação. Guardar transcrição, resposta, WAV, métricas e falhas antes do próximo envio. O navegador mede da seleção do arquivo ao evento playing e também do envio até playing. O evento é proxy da reprodução, alheio ao instante físico de emissão e à hora original no WhatsApp.")
    s.append(PageBreak())

    section("Evidências disponíveis", "Resultados da coleta")
    table([("Série", "Evidência", "Indicador"),
           ("STT", f"{stt.get('received', 0)}/20 originais, {stt.get('transcribed', 0)} transcrições e {ref_count} referências revisadas", f"WER: {wer_summary}"),
           ("LLM", f"{llm.get('count_attempted', 0)}/30 casos executados, {llm.get('accuracy_denominator', 0)} revisados", llm_summary),
           ("TTS", f"{tts.get('synthesized', 0)}/10 sínteses e {tts.get('ratings', 0)}/30 avaliações", tts_summary),
           ("Ponta a ponta", f"{e2e.get('successful_sessions', 0)}/10 conversas completas", e2e_summary),
           ("Comparação", f"{comparison_count}/20 pares com referência e saídas A e B", comparison_summary)],
          [100, 237, 138])
    h("Latência STT por gravação")
    p(latency_summary + " A medida usa o adaptador em português depois da preparação do WAV.")
    if latencies and len(latencies) <= 10:
        s.append(graph(latencies))
        s.append(Spacer(1, 10))
    elif latencies:
        p("Os tempos individuais constam no CSV acadêmico e no gráfico complementar de STT.")
    noise = stt.get("coverage", {}).get("noisy_samples", 0)
    p(f"O snapshot contém {ref_count} referências verificadas e {noise} amostras analisáveis com ruído confirmado. A identificação de R01/R02, T17/T18 e R07 foi corrigida por conteúdo e hash. Os IDs no histórico original foram preservados.")
    if judges.get("ia"):
        p("O julgamento dos casos indicados como IA foi realizado por GPT-6. A revisão técnica manteve Q19 e Q23 como falhas de critério. O ensaio técnico de três uploads usou perguntas pré-gravadas e permanece fora da coleta contextual humana.")
    p("Os arquivos experimentais com acesso restrito estão no material de teste. O CSV de STT e o JSON de métricas registram os denominadores e a origem dos dados. A demonstração em vídeo tem 199,9 segundos.")
    s.append(PageBreak())

    if len(latencies) > 10:
        section("Apêndice de resultados", "Latência STT por amostra",
                latency_summary + " Os tempos representam a chamada ao serviço a partir do cliente. O relógio inclui rede e envio.")
        s.append(graph(latencies))
        p("O manifesto associa cada medida a um ID, hash original, hash do WAV e ambiente. Use as medianas e os intervalos por participante e ambiente no JSON de métricas.")
        s.append(PageBreak())

    if any((stt.get("wer_corpus") is not None, e2e, paired_config, tts.get("ratings"))):
        section("Apuração", "Indicadores por série")
        if stt.get("word_errors"):
            h("STT por estrato")
            bins = {"Corpus": stt, **stt["by_speaker"], **{("Com ruído" if k == "true" else "Limpo"): v for k, v in stt["by_noise"].items()}}
            table([("Estrato", "WER", "S / D / I", "Palavras de referência"),
                   *[(name, pct(100 * item["wer_corpus"]), " / ".join(str(item["word_errors"][k]) for k in ("substitutions", "deletions", "insertions")),
                      item["word_errors"]["reference_words"]) for name, item in bins.items()]], [155, 75, 110, 135])
        if e2e.get("per_stage_seconds"):
            h("Latência observada por etapa")
            selected = {"stt": "STT", "llm": "LLM", "speech_text": "Adaptação", "tts": "TTS", "processing_total": "Total de processamento"}
            table([("Etapa", "Média em segundos", "Turnos medidos"), *[(selected[key], num(value["mean"]), value["n"])
                    for key, value in e2e["per_stage_seconds"].items() if key in selected and value]], [185, 160, 130])
        if paired_config:
            h("Fronteiras de latência na comparação")
            for group in paired_config:
                p(f"Cliente remoto {escape(group['environment_id_A'])}, n = {len(group['pairs'])}. Chamada A {num(group['remote']['mean'])} s. "
                  f"Processo local B {num(group['local_wall']['mean'])} s, carga {num(group['local_load']['mean'])} s e inferência sem carga {num(group['local_inference']['mean'])} s.")
        if decision.strip():
            h("Justificativa da configuração selecionada")
            p(escape(decision.strip()).replace("\n", "<br/>"))
        s.append(PageBreak())

    section("Encerramento", "Limitações e próximos passos")
    h("Limitações")
    p("Três vozes permitem uma comparação descritiva dentro do grupo. Não sustentam inferência ampla sobre sotaques, acessibilidade ou ausência de viés. Registre dispositivo e condições acústicas. R06 preserva códigos e ambiguidades e mantém frases sem ponto de corte seguro. A pronúncia depende da escuta do TTS real.")
    h("Melhorias e conclusão")
    p("Completar a coleta, preservar concordância entre referência e áudio e publicar apenas o material autorizado para a correção. Depois, testar em dispositivos variados, revisar fontes municipais e monitorar erros por condição acústica. A demonstração e as verificações comprovam integração técnica. O estado da avaliação depende do quadro de resultados e dos limiares de coleta.")
    h("Referências")
    refs = [("FIAP. GS 2027 - PLN: Assistente de Voz CitizenTech. Enunciado oficial, 3 p.", None),
            ("Nações Unidas. Objetivo 11 e Objetivo 16.", "https://sdgs.un.org/goals/goal11"),
            ("Governo Federal. Medidas de autoproteção em casos de alagamento.", "https://www.gov.br/pt-br/noticias/transito-e-transportes/2022/07/conheca-medidas-de-autoprotecao-que-a-populacao-deve-tomar-em-casos-de-alagamento"),
            ("OpenAI. Documentação dos modelos e preços da API.", "https://developers.openai.com/api/docs/pricing"),
            ("OpenAI. Controles de dados da plataforma.", "https://developers.openai.com/api/docs/guides/your-data"),
            ("Jitsi. jiwer 4.0.0, métricas de reconhecimento de fala.", "https://github.com/jitsi/jiwer"),
            ("ggml-org. whisper.cpp v1.8.6 e licença MIT.", "https://github.com/ggml-org/whisper.cpp/blob/v1.8.6/LICENSE"),
            ("OpenAI. Whisper e licença dos pesos originais.", "https://github.com/openai/whisper#license"),
            ("Microsoft. Opções para interromper sincronização no OneDrive.", "https://support.microsoft.com/en-us/onedrive/how-to-cancel-or-stop-sync-in-onedrive")]
    for label, url in refs:
        line = escape(label) if not url else f'<link href="{escape(url, quote=True)}" color="#104B3D">{escape(label)}</link>'
        if url and url.endswith("goal11"):
            line += ' <link href="https://sdgs.un.org/goals/goal16" color="#104B3D">ODS 16</link>'
        s.append(paragraph(line, 9.2, 13, False, MUTED, 4))

    def footer(canvas, doc):
        canvas.setFillColor(GREEN)
        canvas.rect(0, A4[1] - 6, A4[0], 6, fill=1, stroke=0)
        canvas.setStrokeColor(LINE)
        canvas.line(60, 45, A4[0] - 60, 45)
        canvas.setFont(BODY, 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(60, 30, "VivaBairro Voz  /  " + revision.title())
        canvas.drawRightString(A4[0] - 60, 30, str(doc.page))

    if output.exists():
        raise SystemExit("A saída já existe. Use outro nome para preservar a versão anterior.")
    doc = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=60, rightMargin=60, topMargin=63, bottomMargin=60,
                            title="VivaBairro Voz - " + revision.title(), author="Equipe VivaBairro Voz - FIAP")
    doc.build(s, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metricas", type=Path)
    parser.add_argument("--saida", type=Path, default=ROOT / "docs/academic/relatorio_global_solution.pdf")
    parser.add_argument("--edicao", help="Edição confirmada pelo docente")
    args = parser.parse_args()
    build(args.saida, args.metricas, args.edicao, False)
