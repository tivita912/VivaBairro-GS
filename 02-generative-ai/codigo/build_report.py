"""Gera o relatório a partir das trilhas da entrega VivaBairro."""
from pathlib import Path
from html import escape
import json

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
NAVY = colors.HexColor('#11263b')
TEAL = colors.HexColor('#206b63')
TEXT = colors.HexColor('#24394d')
SOFT = colors.HexColor('#edf3f6')
LINE = colors.HexColor('#d7e0e8')


def read(path):
    return json.loads((ROOT/path).read_text(encoding='utf8'))


def flow():
    diagram=Drawing(490,86)
    lanes=[('PREPARAÇÃO',('Páginas oficiais','Curadoria JSON','Chunks por seção','Índice BM25 + LSA'),49),
           ('CONSULTA',('Relato e município','Triagem e busca','Seleção Qwen','Relato e fontes'),3)]
    for name,labels,y in lanes:
        diagram.add(String(0,y+28,name,fontName='Helvetica-Bold',fontSize=8,fillColor=TEAL))
        for i,label in enumerate(labels):
            x=i*122
            diagram.add(Rect(x,y,108,23,rx=4,ry=4,fillColor=SOFT,strokeColor=LINE))
            diagram.add(String(x+54,y+8,label,textAnchor='middle',fontSize=9,fillColor=TEXT))
            if i<3:
                diagram.add(Line(x+109,y+12,x+120,y+12,strokeColor=TEAL))
                diagram.add(Polygon([x+120,y+12,x+116,y+15,x+116,y+9],fillColor=TEAL,strokeColor=None))
    return diagram


def build():
    q=read('evidencias/qwen-final/metricas.json')
    previous=read('evidencias/qwen/metricas.json')
    b=read('evidencias/baseline/metricas.json')
    compare=read('evidencias/baseline/comparativo.json')
    docs=read('codigo/corpus/fontes.json')
    styles={
        'section':ParagraphStyle('section',fontName='Helvetica-Bold',fontSize=25,leading=29,textColor=NAVY,spaceAfter=14),
        'title':ParagraphStyle('title',fontName='Helvetica-Bold',fontSize=36,leading=40,textColor=NAVY,spaceAfter=14),
        'eyebrow':ParagraphStyle('eyebrow',fontName='Helvetica-Bold',fontSize=10,leading=14,textColor=TEAL,spaceAfter=9),
        'body':ParagraphStyle('body',fontName='Helvetica',fontSize=10.7,leading=15.5,textColor=TEXT,spaceAfter=9),
        'small':ParagraphStyle('small',fontName='Helvetica',fontSize=9,leading=13,textColor=TEXT,spaceAfter=6),
        'head':ParagraphStyle('head',fontName='Helvetica-Bold',fontSize=13,leading=17,textColor=NAVY,spaceAfter=6,spaceBefore=9),
        'cell':ParagraphStyle('cell',fontName='Helvetica',fontSize=8.7,leading=12.4,textColor=TEXT),
        'header':ParagraphStyle('header',fontName='Helvetica-Bold',fontSize=8.6,leading=12,textColor=colors.white),
    }
    story=[]
    def p(value,style='body'):
        story.append(Paragraph(value,styles[style]))
    def page(number,title):
        story.append(PageBreak())
        p(f'GLOBAL SOLUTION 2026.2  /  {number}','eyebrow')
        p(title,'section')
    def table(header,rows,widths):
        cells=[[Paragraph(escape(str(x)),styles['header']) for x in header]]
        cells.extend([Paragraph(escape(str(x)),styles['cell']) for x in row] for row in rows)
        block=Table(cells,colWidths=[w*mm for w in widths],hAlign='LEFT',repeatRows=1)
        block.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),NAVY),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,SOFT]),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),
            ('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
            ('LINEBELOW',(0,-1),(-1,-1),.6,LINE)]))
        story.extend((block,Spacer(1,4*mm)))
    def dec(value):
        return f'{value:.3f}'.replace('.',',')

    story.append(Spacer(1,18*mm))
    p('FIAP  /  GENERATIVE AI &amp; ADVANCED NETS  /  2TIAPY','eyebrow')
    p('VivaBairro<br/>Sua Voz na Cidade','title')
    p('Assistente CitizenTech para orientação sobre problemas urbanos e preparação de relatos revisáveis.')
    table(['Corpus','Fluxo completo','Geração Qwen'],[(f'{len(docs)} fontes municipais',f'{q["cases"]} cenários',f'{q["llm_calls"]} chamadas de inferência')],[58,58,58])
    p('Integrantes','head')
    p('Gustavo Civita Gonçalves · RM 561932','small')
    p('Rafael de Paiva Ramos · RM 563978','small')
    p('Thiago Santana Danyluk · RM 562286','small')
    p('Rodada de 11/11/2026 · Município de São Paulo como recorte demonstrativo','head')
    p('O pacote entrega um protótipo acadêmico funcional. O registro de aprovação e a integração a um protótipo separado do grupo aguardam confirmação.')

    page('01','Problema e arquitetura')
    p('Moradores podem ter dificuldade para identificar o serviço responsável por buracos, calçadas, iluminação, resíduos ou alagamentos. O VivaBairro ajuda a organizar a descrição e a localizar a carta aplicável. O público previsto inclui pessoas idosas, pessoas com deficiência e cidadãos com pouca familiaridade tecnológica.')
    p('O projeto se relaciona com os ODS 11 e 16 ao apoiar a participação cidadã e o acesso a informações municipais. O cidadão pode corrigir categoria, prioridade e relato antes de encaminhar. O protocolo é responsabilidade do canal oficial.')
    story.append(flow())
    p('Figura 1. A curadoria produz o índice usado na consulta. Categoria, prioridade e rascunho seguem regras da aplicação. O Qwen seleciona evidências.','small')
    table(['Etapa','Decisão técnica'],[
        ('Ingestão','Paráfrases municipais com ID, origem, data, domínio, município e limites. Validação de host HTTPS e unicidade.'),
        ('Segmentação','Seções de até 65 palavras e overlap configurado em 10. A ordem e o deslocamento em palavras ficam no chunk.'),
        ('Recuperação','Híbrido com BM25 e LSA. Até quatro resultados e dois por documento. Pesos 0,78 lexical e 0,22 denso.'),
        ('Geração','Qwen2.5 3B Instruct Q4_K_M em llama.cpp b12255, temperatura 0,1, seed 42 e até 64 tokens. JSON Schema limita a saída a um ID disponível ou null.'),
        ('Interface e API','FastAPI valida os dados. O navegador permite revisar e copiar o relato. A resposta exibe o trecho curado escolhido e a referência oficial.'),
    ],[35,139])

    page('02','Recuperação de evidências')
    p('O experimento comparou cinco configurações em 11 descrições anotadas. A busca dessa tabela é global, sem categoria inferida nem título acrescentado. O fluxo em produção confirma a jurisdição, escolhe o domínio e complementa a busca com o título do documento desse domínio.')
    table(['Configuração','Chunks','Overlap¹','Hit²','MRR²','Recall²','nDCG²','nDCG³'],[
        (item['name'].replace('_',' '),item['chunks'],item['overlap_transitions'],
         *[dec(item['document'][key]) for key in ('hit','mrr','recall','ndcg')],
         dec(item['section']['ndcg']) if item['section'] else '—') for item in compare
    ],[46,17,18,18,17,19,19,20])
    p('¹ Transições com overlap real. ² Métricas por fonte, @4. ³ nDCG por seção, @4. Janelas fixas cruzam seções.','small')
    p('Representação e filtros','head')
    p('BM25 utiliza k1=1,5, b=0,75 e expansão lexical por termos urbanos. LSA é uma projeção local de TF-IDF por n-gramas de caracteres com SVD e cosseno. O híbrido normaliza o BM25 pelo maior candidato e aplica o limiar lexical bruto de 1,6.')
    p('Leitura dos resultados','head')
    p('As seções curadas cabem no padrão 65/10, que teve zero sobreposições. O estrutural curto teve 12 sobreposições e menor recall por fonte. O híbrido e o BM25 global empataram nas métricas desta amostra. As descrições genéricas sem tipo de calçada, natureza do terreno ou indício de obstrução explicam perdas do documento geral na busca global.')
    p('A avaliação ponta a ponta usa o roteamento completo. Resultados da busca global e resultados da aplicação medem etapas diferentes e têm denominadores próprios.')

    page('03','Geração e fluxo completo')
    p(f'A configuração final fez {q["llm_calls"]} chamadas reais sem erro de execução. A avaliação controlada entregou contexto fixo ao Qwen. A avaliação do fluxo completo incluiu confirmação de município, ambiguidade, esclarecimentos, risco imediato, escopo, dois turnos e cenários defensivos.')
    table(['Cenários','Extrator','Qwen sem esquema','Qwen final'],[
        ('Ponta a ponta',f'{b["passed"]}/{b["cases"]}',f'{previous["passed"]}/{previous["cases"]}',f'{q["passed"]}/{q["cases"]}'),
        ('Contexto controlado','—',f'{previous["controlled_passed"]}/{previous["controlled_cases"]}',f'{q["controlled_passed"]}/{q["controlled_cases"]}'),
        ('Defesas do conjunto','2/2','2/2','2/2'),
        ('Acompanhamento V01 e V22','Passou','Passou','Passou'),
    ],[54,39,42,39])
    p('Geração controlada','head')
    p('O Qwen selecionou as evidências esperadas para buraco, iluminação, resíduos públicos e obstáculo na calçada. Em G03 e G05, recusou selecionar uma fonte para passaporte ou prazo garantido. O julgamento verifica IDs e contexto. A adequação de cada orientação também foi revisada com as fontes.')
    p('O que mudou com o esquema JSON','head')
    p('Em V11, a rodada inicial devolveu o texto em lugar do identificador e a aplicação se absteve. A rodada final selecionou F03 e publicou a paráfrase curada. Em V05, o Qwen se absteve nas duas rodadas ao receber apenas orientação geral para alagamento recorrente. A interface preservou o rascunho e pediu esclarecimento.')
    p('A abstenção de V05 perdeu a expectativa de informar o canal geral. Evitou atribuir ao alagamento uma causa não descrita. O próximo dado necessário é a frequência ou um indício de obstrução observado em segurança.')

    page('04','Proteções e aplicação')
    table(['Validação','Evidência observada'],[
        ('V21 · instruções internas','Entrada sintética bloqueada antes da inferência.'),
        ('S02 · trecho inserido','Trecho sintético recuperado e removido. A resposta selecionou evidência restante sem repetir o marcador.'),
        ('Risco imediato','V17 orientou procurar um lugar seguro e acionar os serviços de emergência locais. Nenhum rascunho ou canal municipal de rotina foi exibido.'),
        ('Município e privacidade','Sem município confirmado ou fora da capital, o sistema não encaminha ao SP156. O filtro retém padrões de dados pessoais e instruções indevidas.'),
        ('Verificação da saída','A referência precisa pertencer ao contexto. O sistema exibe texto do corpus. A relevância semântica continua dependendo da classificação e do ranking.'),
        ('Falha do provedor','A instância sem runtime respondeu HTTP 503. O navegador mostrou indisponibilidade.'),
    ],[45,129])
    p('Acessibilidade e autonomia','head')
    p('A interface usa texto direto, rótulos para município e campos, navegação por teclado, histórico com anúncio e foco visível. O cidadão pode editar o rascunho e ajustar a prioridade. A prioridade elevada representa uma menção a bloqueio de passagem. É uma proposta de organização do relato.')
    p('Limites e próximos passos','head')
    p('A detecção textual de risco é conservadora e pode falhar em descrições indiretas ou em negações. O corpus abrange a capital e uma amostra pequena de serviços. O conjunto foi usado no desenvolvimento. A leitura qualitativa assistida por IA precisa da revisão do grupo e de testes com o público previsto.')
    p('A demonstração integra o RAG à interface VivaBairro do pacote. A integração a outro protótipo do grupo depende de acesso ao código, confirmação da jornada e validação nesse ambiente.')

    page('05','Fontes e reprodução')
    p('Dez páginas municipais consultadas em 11/11/2026. Cada entrada em codigo/corpus/fontes.json identifica o conteúdo como paráfrase curada.')
    for doc in docs:
        p(f'<b>{doc["id"]}</b> · <a href="{escape(doc["url"],quote=True)}" color="#206b63">{escape(doc["title"])}</a> · {escape(doc["origin"])}','small')
    p('Reprodução e conclusão','head')
    p('O README descreve a instalação no Windows, a execução de FastAPI e Qwen e os comandos de avaliação. O notebook usa o mesmo corpus e código. O pacote contém o roteiro, a demonstração gravada, os testes e a matriz dos oito critérios do barema.')
    p('O VivaBairro organiza relatos urbanos e oferece referências verificáveis para o recorte proposto. A avaliação identifica pontos de cobertura e segurança que precisam ser retestados quando o grupo confirmar o protótipo e o município de aplicação.')
    p('Referências técnicas','head')
    p('Enunciado oficial FIAP, Global Solution 2026.2, §§ 1–7. <a href="https://github.com/ggml-org/llama.cpp/releases/tag/b12255" color="#206b63">llama.cpp b12255</a> · <a href="https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF" color="#206b63">Qwen2.5 3B Instruct GGUF</a>.','small')

    def frame(canvas,doc):
        w,h=A4
        canvas.setFillColor(NAVY)
        canvas.rect(0,h-4*mm,w,4*mm,fill=1,stroke=0)
        canvas.setStrokeColor(LINE)
        canvas.line(18*mm,16*mm,w-18*mm,16*mm)
        canvas.setFont('Helvetica',8)
        canvas.setFillColor(TEXT)
        canvas.drawString(18*mm,11*mm,'FIAP · Global Solution 2026.2 · VivaBairro')
        canvas.drawRightString(w-18*mm,11*mm,f'{doc.page:02}')
    output=ROOT/'relatorio/Relatorio_Final_VivaBairro.pdf'
    document=SimpleDocTemplate(str(output),pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,
                               topMargin=19*mm,bottomMargin=22*mm,title='VivaBairro · Sua Voz na Cidade',
                               author='Equipe VivaBairro · FIAP 2TIAPY')
    document.build(story,onFirstPage=frame,onLaterPages=frame)


if __name__=='__main__':
    build()

