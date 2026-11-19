"""Adaptadores locais de geração para a seleção de trechos."""
from __future__ import annotations

import json
import os
from urllib.parse import urlsplit

import requests

TEMPERATURE = 0.1
SEED = 42
DEFAULT_MODELS = {'ollama':'qwen2.5:3b','llamacpp':'qwen2.5-3b-instruct-q4_k_m'}


def local_chat(url: str, payload: dict) -> dict:
    endpoint = urlsplit(url)
    if (endpoint.scheme != 'http' or endpoint.hostname not in {'127.0.0.1','localhost','::1'}
            or endpoint.username is not None or endpoint.password is not None):
        raise ValueError('O endpoint local deve usar HTTP em loopback.')
    with requests.Session() as session:
        session.trust_env = False
        response = session.post(url,json=payload,timeout=(5,90),allow_redirects=False)
        if response.is_redirect:
            raise ValueError('O servidor local respondeu com redirecionamento.')
        response.raise_for_status()
        return response.json()


def llm_answer(query, evidence, provider, model, *, system_prompt, max_tokens, schema):
    context = [
        {'trecho_id':row['id'],'titulo':row['title'],'secao':row['heading'],'texto':row['text']}
        for row in evidence
    ]
    payload = {'model':model,'stream':False,'messages':[
        {'role':'system','content':system_prompt},
        {'role':'user','content':json.dumps({'pergunta':query,'fontes':context},ensure_ascii=False)},
    ]}
    if provider == 'ollama':
        url = os.getenv('OLLAMA_URL','http://127.0.0.1:11434/api/chat')
        result = local_chat(url,{**payload,'format':schema,
            'options':{'temperature':TEMPERATURE,'seed':SEED,'num_predict':max_tokens}})
        return result['message']['content']
    url = os.getenv('LLAMACPP_URL','http://127.0.0.1:18081/v1/chat/completions')
    result = local_chat(url,{**payload,'temperature':TEMPERATURE,'seed':SEED,'max_tokens':max_tokens,
        'response_format':{'type':'json_schema','schema':schema}})
    return result['choices'][0]['message']['content']

