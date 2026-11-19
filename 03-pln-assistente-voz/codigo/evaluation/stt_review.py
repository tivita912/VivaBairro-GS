"""Página local de escuta, com exportação de alterações e sem hipóteses de STT."""

from html import escape
import json
from urllib.parse import quote

from src.errors import ValidationError
from src.metrics import normalize_reference

FIELDS = dict(sample_id="ID após conferência", identification_note="Evidência do vínculo",
              reference_text="Referência literal", reference_reviewed_by="ID de quem revisou",
              noise_present="Ruído de fundo", noise_observation="Observação acústica", consent_id="ID do consentimento",
              consent_document="Caminho privado do comprovante", external_audio_authorized="Aceite para envio à OpenAI",
              review_completed="Revisão literal concluída")


def import_review(path, reviews):
    from evaluation.run_stt import PLAN

    try:
        changes = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(changes, dict):
            raise ValueError
        updates = {}
        for sha, fields in changes.items():
            updated = reviews[sha].copy()
            for field, (before, after) in fields.items():
                if field not in FIELDS or not isinstance(after, str) or len(after) > 8000:
                    raise ValueError
                if updated.get(field, "") not in {before, after}:
                    raise ValidationError("A revisão atual contém alterações posteriores. Reabra a página local.")
                updated[field] = after
            if updated.get("sample_id") and (updated["sample_id"] not in PLAN or not updated.get("identification_note", "").strip()):
                raise ValueError
            if updated.get("noise_present", "") not in {"", "true", "false"} or (
                    updated.get("noise_present") and not updated.get("noise_observation", "").strip()):
                raise ValueError
            if updated.get("review_completed") == "true" and not (updated.get("sample_id") and
                    updated.get("reference_reviewed_by", "").strip() and normalize_reference(updated.get("reference_text", ""))):
                raise ValueError
            updates[sha] = updated
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        raise ValidationError("JSON de revisão inválido. Confira ID, referência, revisor e observação de ruído.") from error
    reviews.update(updates)


def export_review(output, inventory, reviews, plan):
    from evaluation.run_stt import atomic_write

    def control(field, value):
        if field in {"sample_id", "noise_present", "external_audio_authorized", "review_completed"}:
            choices = ([(key, key) for key in plan] if field == "sample_id" else [("true", "Sim"), ("false", "Não")])
            options = "".join(f'<option value="{key}"{" selected" if key == value else ""}>{label}</option>'
                              for key, label in [("", "Pendente"), *choices])
            return f'<select name="{field}">{options}</select>'
        return f'<textarea name="{field}" rows="{4 if field == "reference_text" else 2}">{escape(value)}</textarea>'

    cards = []
    seen = set()
    for audio in inventory:
        sha = audio.get("sha256")
        if sha in seen or sha not in reviews or audio["app_compatible"] != "true":
            continue
        seen.add(sha)
        row = reviews[sha]
        path = audio["audio_path"]
        fields = "".join(f'<label>{label}{control(key, row.get(key, ""))}</label>' for key, label in FIELDS.items())
        cards.append(f'<article data-sha="{sha}"><h2>{escape(row.get("sample_id") or "ID pendente")}</h2>'
                     f'<p>{escape(path)}</p><audio controls preload="none" src="../{quote(path)}"></audio>'
                     f'<a href="../{quote(path)}">Abrir o original no player local</a><div>{fields}</div></article>')

    page = """<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Revisão humana STT · VivaBairro Voz</title><style>
*{box-sizing:border-box}body{margin:auto;padding:32px;max-width:980px;background:#f3f6f3;color:#142b23;font:16px/1.55 system-ui,sans-serif}h1,h2{line-height:1.2}article{background:white;border:1px solid #bccdc4;border-radius:10px;padding:22px;margin:20px 0}article p{overflow-wrap:anywhere}article div{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:14px;margin-top:14px}label{display:grid;gap:4px}select,textarea{width:100%;font:inherit;border:1px solid #667d70;border-radius:5px;padding:7px}audio{display:block;width:min(100%,450px)}a{color:#14553d}button{font:inherit;background:#14553d;color:white;border:0;border-radius:6px;padding:9px 16px;cursor:pointer}textarea{resize:vertical}.toolbar{position:sticky;top:0;background:#f3f6f3;padding:8px 0}code{overflow-wrap:anywhere}
</style><h1>Revisão humana de STT</h1><p>Ouça o original e transcreva literalmente as palavras, pausas preenchidas e autocorreções audíveis. Confira o ID com o roteiro enviado. Registre quem revisou e descreva o ruído observado. Faça a revisão sem abrir rascunhos ou hipóteses.</p>
<p>Exporte antes de fechar a página. Importe no projeto com <code>python -m evaluation.run_stt --importar-revisao caminho.json</code>. Guarde o JSON em local restrito.</p>
<div class="toolbar"><button id="export" type="button">Exportar alterações (JSON)</button> <span id="status" role="status"></span></div>
""" + "\n".join(cards) + """
<script>
const inputs = [...document.querySelectorAll('article select, article textarea')];
const original = new Map(inputs.map(input => [input, input.value]));
document.querySelector('#export').onclick = () => {
  const changes = {};
  for (const input of inputs) {
    if (original.get(input) === input.value) continue;
    const key = input.closest('article').dataset.sha;
    (changes[key] ??= {})[input.name] = [original.get(input), input.value];
  }
  const count = Object.keys(changes).length;
  if (!count) { document.querySelector('#status').textContent = 'Nenhuma alteração.'; return; }
  const href = URL.createObjectURL(new Blob([JSON.stringify(changes, null, 2)], {type:'application/json'}));
  const link = document.createElement('a'); link.href = href; link.download = 'stt_revisoes.json'; link.click();
  setTimeout(() => URL.revokeObjectURL(href), 1000);
  document.querySelector('#status').textContent = `${count} revisões exportadas.`;
};
</script></html>
"""
    atomic_write(output / "stt_revisao.html", lambda stream: stream.write(page))
