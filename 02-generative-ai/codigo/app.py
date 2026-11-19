"""Demo web de CitizenTech, executavel com `uvicorn app:app --reload`."""
from __future__ import annotations
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from citizentech.vivabairro import Category, Municipality, VivaBairro

load_dotenv(Path(__file__).resolve().parent/'.env')
app = FastAPI(title='VivaBairro | CitizenTech FIAP', version='2.0.0', description='Demonstração acadêmica de orientação urbana.')
rag = VivaBairro()

class Query(BaseModel):
    municipality: Municipality | None = None
    location: str | None = Field(default=None, max_length=180)
    category: Category | None = None
    question: str=Field(min_length=4,max_length=2000)
    context_doc_id: str|None=Field(default=None,pattern=r"^F\d{2}$")

@app.exception_handler(RequestValidationError)
async def invalid_query(_request, _error):
    return JSONResponse(status_code=422, content={
        'detail': 'Pergunta ou referência inválida. Revise o tamanho e o formato da entrada.',
    })


@app.get('/')
def home():
    return FileResponse(Path(__file__).resolve().parent/'static/index.html')

@app.get('/health')
def health():
    return {'ok':True,'generator':rag.provider,'model':rag.model,'corpus_docs':len(rag.docs),'chunks':len(rag.chunks),
            'warning':'Demo academica - nenhum banco de dados do cidadao e acessado'}

@app.post('/api/ask')
def ask(request: Query):
    try:
        result = rag.ask(**request.model_dump())
    except Exception:
        # Nao devolver detalhes internos, chaves, prompt ou payload do provedor.
        raise HTTPException(status_code=503,detail='Gerador indisponivel. Verifique a configuracao local do provedor.') from None
    return {k:v for k,v in result.items() if k not in {'evidence', 'trace'}}
