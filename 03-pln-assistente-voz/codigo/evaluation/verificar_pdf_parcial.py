from pathlib import Path
import json
import pymupdf
from PIL import Image,ImageDraw
from src.config import PROJECT_ROOT
source=PROJECT_ROOT/"docs/academic/relatorio_global_solution_parcial_ia_avaliada_20261117.pdf"
if not source.exists():raise SystemExit("Arquivo PDF não encontrado")
folder=PROJECT_ROOT/".runtime/pdf_preview_atualizado"
folder.mkdir(parents=True,exist_ok=True)
document=pymupdf.open(source)
meta=[]
thumbs=[]
for index,page in enumerate(document):
    content=page.get_text()
    meta.append(dict(page=index+1,characters=len(content),start=content[:150]))
    pix=page.get_pixmap(matrix=pymupdf.Matrix(1.5,1.5),alpha=False)
    output=folder/f"page_{index+1:02d}.png"
    pix.save(str(output))
    image=Image.open(output).convert("RGB")
    w=355
    image.thumbnail((w,505))
    thumbs.append(image.copy())
ncol=3;nrow=(len(thumbs)+ncol-1)//ncol
sheet=Image.new("RGB",(ncol*380,nrow*545),(237,240,238))
canvas=ImageDraw.Draw(sheet)
for i,im in enumerate(thumbs):
    x=(i%ncol)*380+12;y=(i//ncol)*545+15
    sheet.paste(im,(x,y))
    canvas.text((x,y+510),f"Página {i+1}",fill=(20,39,29))
sheet.save(folder/"contato.jpg",quality=86)
(folder/"verificacao.json").write_text(json.dumps({"pages":len(document),"page_details":meta,
"checks":{"all_have_text":all(m["characters"]>150 for m in meta),
"covers_12_stt":"12 transcrições" in "".join(p.get_text() for p in document),
"covers_30_llm":"30 casos" in "".join(p.get_text() for p in document),
"covers_10_tts":"10 sínteses" in "".join(p.get_text() for p in document)}},ensure_ascii=False,indent=2),encoding="utf-8")
print(len(document),"páginas renderizadas; contato em",folder/"contato.jpg")
