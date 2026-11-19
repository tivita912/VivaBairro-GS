"""Ensaio técnico de 3 turnos via upload com áudios reais do próprio usuário.
NÃO é uma conversa humana interativa e não integra as 10 conversas formais.
"""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from fastapi.testclient import TestClient
from src.config import PROJECT_ROOT, Settings
from src.web import create_app

inputs=[
    PROJECT_ROOT/"evaluation/audio/Thiago/Gravando (16).m4a",
    PROJECT_ROOT/"evaluation/audio/Thiago/Gravando (21).m4a",
    PROJECT_ROOT/"evaluation/audio/Thiago/Gravando (20).m4a",
]
for path in inputs:
    if not path.exists(): raise SystemExit("Arquivo ausente: "+str(path))
output=PROJECT_ROOT/"evaluation/results/ensaio_tecnico_upload_3_turnos_tentativa_2"
output.mkdir(parents=True,exist_ok=True)
record={
 "label":"ENSAIO TÉCNICO REAL DE API - replay de áudios humanos pré-gravados",
 "formal_e2e_conversation":False,
 "limitations":"Não são perguntas formuladas após ouvir respostas; não substitui conversas humanas nem mede início de reprodução no navegador.",
 "origin":"user_recordings", "created_at":datetime.now(timezone.utc).isoformat(),"turns":[]
}
try:
    with TestClient(create_app(Settings.load())) as client:
        info=client.get("/api/info")
        info.raise_for_status()
        version=info.json()["notice_version"]
        authorized=client.post("/api/consent",json=dict(accepted=True,external_audio=True,external_text=True,notice_version=version))
        authorized.raise_for_status()
        headers={"x-vivabairro-session":authorized.json()["session"],"Content-Type":"application/octet-stream"}
        try:
            for index,path in enumerate(inputs,1):
                raw=path.read_bytes()
                response=client.post("/api/turn?format=m4a&source=upload",content=raw,headers=headers)
                row=dict(turn=index,input=path.relative_to(PROJECT_ROOT).as_posix(),input_sha256=sha256(raw).hexdigest(),
                         status=response.status_code)
                if response.status_code==200:
                    payload=response.json()
                    row.update(transcription=payload["transcription"],response=payload["response"],
                               speech_text=payload["speech_text"],metrics=payload.get("metrics"),
                               history_length=len(payload.get("history",[])))
                    audio_response=client.get(payload["audio_url"],headers={"x-vivabairro-session":headers["x-vivabairro-session"]})
                    row["audio_http_status"]=audio_response.status_code
                    if audio_response.status_code==200:
                        voice=output/f"turno_{index:02d}.wav"
                        voice.write_bytes(audio_response.content)
                        row["generated_audio_sha256"]=sha256(audio_response.content).hexdigest()
                        row["generated_audio_path"]=voice.relative_to(PROJECT_ROOT).as_posix()
                else:
                    row["error"]=response.text[:600]
                record["turns"].append(row)
                print(f"Turno {index}: HTTP {row['status']}, reprodução WAV {row.get('audio_http_status','—')}")
                if response.status_code!=200: break
        finally:
            client.post("/api/clear",headers={"x-vivabairro-session":headers["x-vivabairro-session"]})
finally:
    (output/"resultado.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
print("Evidência técnica:",output/"resultado.json")
