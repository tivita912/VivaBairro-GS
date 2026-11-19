from __future__ import annotations

import json
import time
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
from torchvision import models, transforms

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models"
IMG_SIZE = 224
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]
CLASSES = ["sem_fissura", "com_fissura"]


def build_model(arch: str = "mobilenet_v2", pretrained: bool = True) -> nn.Module:
    if arch == "mobilenet_v2":
        w = models.MobileNet_V2_Weights.IMAGENET1K_V1 if pretrained else None
        m = models.mobilenet_v2(weights=w)
        m.classifier[1] = nn.Linear(m.last_channel, 2)
    elif arch == "resnet18":
        w = models.ResNet18_Weights.IMAGENET1K_V1 if pretrained else None
        m = models.resnet18(weights=w)
        m.fc = nn.Linear(m.fc.in_features, 2)
    else:
        raise ValueError(arch)
    return m


def eval_transform(size: int = IMG_SIZE):
    return transforms.Compose([
        transforms.Resize((size, size)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])


def _to_tensor_batch(rgb_list: list[np.ndarray], size: int = IMG_SIZE) -> torch.Tensor:
    arr = np.stack([cv2.resize(x, (size, size), interpolation=cv2.INTER_AREA) for x in rgb_list])
    t = torch.from_numpy(arr).permute(0, 3, 1, 2).float().div_(255.0)
    mean = torch.tensor(MEAN).view(1, 3, 1, 1)
    std = torch.tensor(STD).view(1, 3, 1, 1)
    return (t - mean) / std


class CrackDetector:
    def __init__(self, model_dir: Path | str = MODEL_DIR, device: str | None = None):
        model_dir = Path(model_dir)
        meta = json.loads((model_dir / "model_meta.json").read_text(encoding="utf-8"))
        self.meta = meta
        self.arch = meta["arch"]
        self.threshold = float(meta["threshold"])
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model = build_model(self.arch, pretrained=False)
        state = torch.load(model_dir / meta["weights"], map_location="cpu", weights_only=True)
        self.model.load_state_dict(state)
        self.model.eval().to(self.device)
        with torch.inference_mode():
            self.model(torch.zeros(1, 3, IMG_SIZE, IMG_SIZE, device=self.device))

    @torch.inference_mode()
    def prob_crack(self, rgb_list: list[np.ndarray]) -> np.ndarray:
        x = _to_tensor_batch(rgb_list).to(self.device)
        p = torch.softmax(self.model(x), dim=1)[:, 1]
        return p.cpu().numpy()

    def predict_image(self, rgb: np.ndarray) -> dict:
        t0 = time.perf_counter()
        p = float(self.prob_crack([rgb])[0])
        if self.device.type == "cuda":
            torch.cuda.synchronize()
        ms = (time.perf_counter() - t0) * 1000
        crack = p >= self.threshold
        return {
            "classe": CLASSES[int(crack)],
            "prob_fissura": p,
            "confianca": p if crack else 1 - p,
            "inspecionar": crack,
            "latencia_ms": ms,
        }

    def scan_grid(self, rgb: np.ndarray, tile: int = 227, stride: int | None = None):
        # fotos grandes: classifica blocos do mesmo tamanho dos recortes de treino
        stride = stride or tile
        h, w = rgb.shape[:2]
        if h < tile or w < tile:
            return [(0, 0, w, h)], self.prob_crack([rgb])
        ys = list(range(0, h - tile + 1, stride))
        xs = list(range(0, w - tile + 1, stride))
        if ys[-1] + tile < h:
            ys.append(h - tile)
        if xs[-1] + tile < w:
            xs.append(w - tile)
        boxes, crops = [], []
        for y in ys:
            for x in xs:
                boxes.append((x, y, x + tile, y + tile))
                crops.append(rgb[y:y + tile, x:x + tile])
        return boxes, self.prob_crack(crops)

    def annotate(self, rgb: np.ndarray, boxes, probs, info: str | None = None) -> np.ndarray:
        out = rgb.copy()
        overlay = out.copy()
        for (x1, y1, x2, y2), p in zip(boxes, probs):
            if p >= self.threshold:
                cv2.rectangle(overlay, (x1, y1), (x2, y2), (220, 40, 40), -1)
        out = cv2.addWeighted(overlay, 0.25, out, 0.75, 0)
        for (x1, y1, x2, y2), p in zip(boxes, probs):
            if p >= self.threshold:
                cv2.rectangle(out, (x1, y1), (x2, y2), (220, 40, 40), 2)
                txt = f"fissura {p:.0%}"
                (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
                cv2.rectangle(out, (x1 + 2, y1 + 2), (x1 + 10 + tw, y1 + 10 + th), (180, 20, 20), -1)
                cv2.putText(out, txt, (x1 + 6, y1 + 6 + th), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                            (255, 255, 255), 1, cv2.LINE_AA)
        if info:
            cv2.rectangle(out, (0, 0), (out.shape[1], 26), (20, 20, 20), -1)
            cv2.putText(out, info, (8, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                        (255, 255, 255), 1, cv2.LINE_AA)
        return out

    def process_video(self, src: str | Path, dst: str | Path, tile: int = 227,
                      max_frames: int | None = None, progress=None) -> dict:
        cap = cv2.VideoCapture(str(src))
        if not cap.isOpened():
            raise RuntimeError(f"Nao foi possivel abrir o video: {src}")
        fps_in = cap.get(cv2.CAP_PROP_FPS) or 10
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        writer = cv2.VideoWriter(str(dst), cv2.VideoWriter_fourcc(*"mp4v"), fps_in, (w, h))
        times, alerts, n = [], 0, 0
        timeline = []
        while True:
            ok, bgr = cap.read()
            if not ok or (max_frames and n >= max_frames):
                break
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            t0 = time.perf_counter()
            boxes, probs = self.scan_grid(rgb, tile=tile)
            times.append(time.perf_counter() - t0)
            n_crack = int((probs >= self.threshold).sum())
            alerts += n_crack > 0
            timeline.append({"quadro": n, "blocos_com_fissura": n_crack,
                             "prob_max": float(probs.max())})
            fps_now = 1 / np.mean(times[-15:])
            info = f"CitizenTech | quadro {n} | blocos c/ fissura: {n_crack} | {fps_now:.1f} FPS"
            out = self.annotate(rgb, boxes, probs, info)
            writer.write(cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
            n += 1
            if progress and total:
                progress(min(n / total, 1.0))
        cap.release()
        writer.release()
        # o primeiro quadro inclui o aquecimento da GPU, entao fica fora da media
        times = np.array(times[1:] if len(times) > 1 else times)
        return {
            "quadros": n,
            "resolucao": f"{w}x{h}",
            "latencia_media_ms": float(times.mean() * 1000),
            "fps": float(1 / times.mean()),
            "quadros_com_alerta": int(alerts),
            "timeline": timeline,
        }
