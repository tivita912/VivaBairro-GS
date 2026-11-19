# streamlit run app/app.py
from __future__ import annotations

import json
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from detector import CrackDetector  # noqa: E402

OUT = ROOT / "outputs"
DEMO = ROOT / "data" / "demo"
FILA_CSV = OUT / "fila_inspecao.csv"
MAX_MB = 50

st.set_page_config(page_title="CitizenTech | Manutenção Urbana", page_icon="🏙️", layout="wide")

st.markdown("""
<style>
.card {border-radius: 10px; padding: 16px 20px; margin-bottom: 12px; border: 1px solid #0002;}
.alerta {background: #fdecea; border-left: 6px solid #c62828; color: #5f1111;}
.ok {background: #e8f5e9; border-left: 6px solid #2e7d32; color: #12401a;}
.card h3 {margin: 0 0 4px 0;}
</style>
""", unsafe_allow_html=True)


@st.cache_resource(show_spinner="Carregando modelo de visão computacional...")
def carregar_detector() -> CrackDetector:
    return CrackDetector(ROOT / "models")


def ler_imagem(arquivo) -> np.ndarray | None:
    if arquivo.size > MAX_MB * 1024 * 1024:
        st.error(f"Arquivo maior que {MAX_MB} MB.")
        return None
    try:
        return np.asarray(Image.open(arquivo).convert("RGB"))
    except Exception:
        st.error("Não consegui abrir esse arquivo como imagem. Use JPG ou PNG.")
        return None


def salvar_na_fila(registro: dict):
    OUT.mkdir(exist_ok=True)
    df = pd.DataFrame([registro])
    df.to_csv(FILA_CSV, mode="a", header=not FILA_CSV.exists(), index=False, encoding="utf-8")


def card_resultado(inspecionar: bool, conf: float, lat_ms: float, extra: str = ""):
    if inspecionar:
        st.markdown(f"""<div class="card alerta"><h3>Possível fissura: encaminhar para inspeção</h3>
        Confiança do modelo: <b>{conf:.1%}</b> · tempo de análise: {lat_ms:.0f} ms {extra}</div>""",
                    unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class="card ok"><h3>Sem fissura aparente</h3>
        Confiança do modelo: <b>{conf:.1%}</b> · tempo de análise: {lat_ms:.0f} ms {extra}</div>""",
                    unsafe_allow_html=True)


def to_web_video(src: Path) -> Path:
    # o navegador nao toca mp4v, entao converte para WebM
    dst = src.with_suffix(".webm")
    cap = cv2.VideoCapture(str(src))
    fps = cap.get(cv2.CAP_PROP_FPS) or 15
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    vw = cv2.VideoWriter(str(dst), cv2.VideoWriter_fourcc(*"VP80"), fps, (w, h))
    while True:
        ok, f = cap.read()
        if not ok:
            break
        vw.write(f)
    cap.release()
    vw.release()
    return dst


st.sidebar.title("CitizenTech")
st.sidebar.caption("Da cidade ao campo, tecnologia para a vida cotidiana.")
pagina = st.sidebar.radio("Módulos", ["Manutenção Urbana", "Fila de inspeção", "Sobre o modelo"])
det = carregar_detector()
st.sidebar.divider()
st.sidebar.markdown(f"**Modelo:** {det.arch}  \n**Dispositivo:** {det.device}  \n"
                    f"**Limiar de alerta:** {det.threshold:.2f}")

if pagina == "Manutenção Urbana":
    st.title("Manutenção Urbana: detecção de fissuras em concreto")
    st.write("Envie uma foto de parede, viaduto, muro ou calçada de concreto. O sistema indica se há "
             "sinais de fissura e, se houver, sugere encaminhar o local para inspeção técnica.")
    st.caption("Dica: fotografe de perto (cerca de 1 metro) só a superfície de concreto, sem carros, "
               "pessoas ou plantas no quadro. Objetos e vegetação geram alarmes falsos.")
    st.info("O resultado é uma triagem. A presença de fissura, sozinha, não indica a gravidade do dano "
            "nem a segurança da estrutura. Quem decide é um engenheiro.", icon="ℹ️")

    aba_foto, aba_video, aba_seq = st.tabs(["Analisar foto", "Vídeo", "Sequência de imagens"])

    with aba_foto:
        c1, c2 = st.columns([1, 1])
        with c1:
            arq = st.file_uploader("Foto (JPG/PNG)", type=["jpg", "jpeg", "png"], key="foto")
            exemplos = sorted((DEMO / "sequencia").glob("*.jpg"))
            usar_ex = st.selectbox("...ou use uma imagem de exemplo",
                                   ["(nenhuma)"] + [e.name for e in exemplos])
            local = st.text_input("Endereço / referência do local", placeholder="Ex.: Viaduto da Av. X, pilar 3")
        img = None
        if arq is not None:
            img = ler_imagem(arq)
        elif usar_ex != "(nenhuma)":
            img = np.asarray(Image.open(DEMO / "sequencia" / usar_ex).convert("RGB"))

        if img is not None:
            grande = max(img.shape[:2]) > 400
            modo = c1.radio("Modo de análise",
                            ["Varredura em blocos (fotos grandes)", "Imagem inteira"],
                            index=0 if grande else 1, horizontal=True,
                            help="Fotos grandes são divididas em blocos de 227 px; cada bloco é classificado.")
            t0 = time.perf_counter()
            if modo.startswith("Varredura"):
                boxes, probs = det.scan_grid(img)
                lat = (time.perf_counter() - t0) * 1000
                n_alerta = int((probs >= det.threshold).sum())
                pmax = float(probs.max())
                inspecionar = n_alerta > 0
                conf = pmax if inspecionar else 1 - pmax
                vis = det.annotate(img, boxes, probs)
                extra = f"({n_alerta} de {len(boxes)} blocos com fissura)"
            else:
                r = det.predict_image(img)
                lat, inspecionar, conf, pmax = r["latencia_ms"], r["inspecionar"], r["confianca"], r["prob_fissura"]
                vis, extra, n_alerta = img, "", int(inspecionar)
            with c2:
                st.image(vis, caption="Resultado (blocos em vermelho = possível fissura)", width="stretch")
            with c1:
                card_resultado(inspecionar, conf, lat, extra)
                st.progress(pmax, text=f"Probabilidade de fissura: {pmax:.1%}")
                st.caption("Revisão humana: confirme ou corrija antes de registrar.")
                b1, b2 = st.columns(2)
                registro = {"data_hora": datetime.now().isoformat(timespec="seconds"),
                            "local": local or "(não informado)",
                            "arquivo": getattr(arq, "name", usar_ex),
                            "prob_fissura": round(pmax, 4), "blocos_com_fissura": n_alerta,
                            "sugestao_modelo": "inspecionar" if inspecionar else "sem fissura"}
                if b1.button("Confirmar e registrar", width="stretch"):
                    salvar_na_fila({**registro, "decisao_humana": registro["sugestao_modelo"]})
                    st.success("Registrado na fila de inspeção.")
                if b2.button("Modelo errou", width="stretch"):
                    corr = "sem fissura" if inspecionar else "inspecionar"
                    salvar_na_fila({**registro, "decisao_humana": corr})
                    st.warning("Correção registrada. Ela serve para retreinar o modelo depois.")

    with aba_video:
        st.write("Simula o monitoramento: cada quadro é varrido em blocos e os trechos com fissura são marcados.")
        vid = st.file_uploader("Vídeo curto (MP4/AVI/MOV)", type=["mp4", "avi", "mov"], key="vid")
        usar_demo = st.checkbox("Usar o vídeo de demonstração (muro com recortes do conjunto de teste)",
                                value=vid is None)
        if st.button("Processar vídeo", type="primary"):
            tmp = Path(tempfile.mkdtemp())
            if vid is not None and not usar_demo:
                src = tmp / f"entrada{Path(vid.name).suffix}"
                src.write_bytes(vid.getbuffer())
            else:
                src = DEMO / "inspecao_demo.mp4"
            barra = st.progress(0.0, text="Processando quadros...")
            try:
                stats = det.process_video(src, tmp / "saida.mp4",
                                          progress=lambda f: barra.progress(f, text=f"Processando... {f:.0%}"))
            except RuntimeError as e:
                st.error(str(e))
                st.stop()
            barra.empty()
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Quadros", stats["quadros"])
            m2.metric("FPS", f"{stats['fps']:.1f}")
            m3.metric("Latência / quadro", f"{stats['latencia_media_ms']:.0f} ms")
            m4.metric("Quadros com alerta", stats["quadros_com_alerta"])
            st.caption(f"Resolução {stats['resolucao']}, dispositivo {det.device}")
            st.video(str(to_web_video(tmp / "saida.mp4")))
            tl = pd.DataFrame(stats["timeline"]).set_index("quadro")
            st.line_chart(tl["blocos_com_fissura"], height=180)

    with aba_seq:
        st.write("Envie várias fotos de um mesmo trajeto (por exemplo, fotos tiradas a cada poste).")
        fotos = st.file_uploader("Imagens", type=["jpg", "jpeg", "png"], accept_multiple_files=True, key="seq")
        if not fotos:
            fotos_paths = sorted((DEMO / "sequencia").glob("*.jpg"))
            st.caption(f"Sem envio: usando a sequência de demonstração ({len(fotos_paths)} imagens).")
            itens = [(p.name, np.asarray(Image.open(p).convert("RGB"))) for p in fotos_paths]
        else:
            itens = [(f.name, ler_imagem(f)) for f in fotos]
            itens = [(n, i) for n, i in itens if i is not None]
        if itens and st.button("Analisar sequência", type="primary"):
            linhas, cols = [], st.columns(3)
            t_ini = time.perf_counter()
            for k, (nome, im) in enumerate(itens):
                t0 = time.perf_counter()
                boxes, probs = det.scan_grid(im)
                lat = (time.perf_counter() - t0) * 1000
                n = int((probs >= det.threshold).sum())
                linhas.append({"imagem": nome, "blocos_com_fissura": n, "prob_max": round(float(probs.max()), 3),
                               "latencia_ms": round(lat, 1), "sugestao": "inspecionar" if n else "ok"})
                cols[k % 3].image(det.annotate(im, boxes, probs), caption=f"{nome}: {n} bloco(s)",
                                  width="stretch")
            total = time.perf_counter() - t_ini
            st.metric("Taxa de processamento", f"{len(itens) / total:.1f} imagens/s")
            st.dataframe(pd.DataFrame(linhas), width="stretch", hide_index=True)

elif pagina == "Fila de inspeção":
    st.title("Fila de inspeção")
    st.write("Locais registrados pelos fiscais após a revisão do resultado do modelo.")
    if FILA_CSV.exists():
        fila = pd.read_csv(FILA_CSV)
        st.dataframe(fila.sort_values("data_hora", ascending=False), width="stretch", hide_index=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Registros", len(fila))
        c2.metric("A inspecionar", int((fila.decisao_humana == "inspecionar").sum()))
        disc = (fila.decisao_humana != fila.sugestao_modelo).mean()
        c3.metric("Correções humanas", f"{disc:.0%}")
        st.download_button("Baixar CSV", fila.to_csv(index=False).encode("utf-8"), "fila_inspecao.csv")
    else:
        st.info("Nenhum registro ainda. Analise uma foto e clique em Confirmar.")

else:
    st.title("Sobre o modelo")
    meta = det.meta
    st.write(f"**Arquitetura:** MobileNetV2 pré-treinada na ImageNet com ajuste fino.  \n"
             f"**Base:** {meta['base']}.  \n**Treinado em:** {meta['treinado_em']} ({meta['data']})")
    mt = meta["metricas_teste"]
    c = st.columns(5)
    for col, (k, nome) in zip(c, [("acuracia", "Acurácia"), ("precisao", "Precisão"), ("recall", "Recall"),
                                  ("f1", "F1"), ("auc_roc", "AUC-ROC")]):
        col.metric(nome, f"{mt[k]:.4f}")
    figs = [("matriz_confusao.png", "Matriz de confusão (teste)"),
            ("robustez_f1.png", "F1 sob interferências"),
            ("curvas_treino.png", "Curvas de treino")]
    for f, cap in figs:
        if (OUT / f).exists():
            st.image(str(OUT / f), caption=cap)
    if (OUT / "desempenho.csv").exists():
        st.subheader("Latência e vazão")
        st.dataframe(pd.read_csv(OUT / "desempenho.csv").round(2), hide_index=True, width="stretch")
    st.subheader("Uso responsável")
    st.markdown("- Fotos são processadas localmente e não são guardadas; só o resultado entra na fila.\n"
                "- Evite fotografar pessoas e placas de veículos (LGPD).\n"
                "- O modelo foi treinado com fotos de um único campus: a confiança cai com sombra forte e "
                "pouca luz, por isso todo alerta passa por revisão humana.")
