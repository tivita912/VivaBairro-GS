"""Gera o notebook acadêmico a partir da estrutura de entrega."""
from pathlib import Path

import nbformat as nbf

root = Path(__file__).resolve().parents[1]
book = nbf.v4.new_notebook()
book.metadata.kernelspec = {'display_name':'Python 3','language':'python','name':'python3'}
book.cells = [
    nbf.v4.new_markdown_cell("""# VivaBairro · CitizenTech FIAP 2026.2

Turma 2TIAPY · Generative AI & Advanced Nets

- Gustavo Civita Gonçalves · RM 561932
- Rafael de Paiva Ramos · RM 563978
- Thiago Santana Danyluk · RM 562286

Extraia toda a entrega e instale requirements-docs.txt a partir da pasta codigo. Selecione o kernel do ambiente virtual."""),
    nbf.v4.new_code_cell("""from pathlib import Path
import json
import os
import sys

ancestors = (Path.cwd(), *Path.cwd().parents)
root = next(p for p in ancestors if (p/'codigo'/'citizentech'/'vivabairro.py').is_file())
sys.path.insert(0,str(root/'codigo'))
from citizentech.vivabairro import VivaBairro
system = VivaBairro(provider='baseline')
print('Documentos:',len(system.docs),'Trechos:',len(system.chunks))
print('Primeiro trecho:',system.chunks[0]['id'])"""),
    nbf.v4.new_markdown_cell("## Recuperação e resposta no baseline"),
    nbf.v4.new_code_cell("""question = 'Tem um buraco grande na rua onde moro.'
for doc in system.retriever.retrieve(question,domain='vias'):
    print(doc['id'],doc['score'],doc['text'])
response = system.ask(question,municipality='sao_paulo')
print(response['answer'])
print(response['draft'])
assert not response['submitted']"""),
    nbf.v4.new_markdown_cell("## Trilhas da avaliação final e reprodução opcional com Qwen"),
    nbf.v4.new_code_cell("""for mode in ('baseline','qwen-final'):
    data = json.loads((root/'evidencias'/mode/'metricas.json').read_text(encoding='utf8'))
    print(mode,data)
if os.getenv('VIVABAIRRO_NOTEBOOK_LLM')=='1':
    llm = VivaBairro(provider='llamacpp')
    current = llm.ask(question,municipality='sao_paulo',debug=True)
    assert current['trace']['generator_called']
    print('Inferência desta célula:',current['answer'])
else:
    print('Defina VIVABAIRRO_NOTEBOOK_LLM=1 e inicie o llama.cpp para executar a consulta real.')"""),
]
nbf.validate(book)
nbf.write(book,root/'notebook/VivaBairro_GS_2026_2.ipynb')

