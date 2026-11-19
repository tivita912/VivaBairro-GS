from __future__ import annotations

import cv2
import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset


class CrackDataset(Dataset):
    def __init__(self, paths, labels, transform, perturb=None, seed: int = 0):
        self.paths = list(paths)
        self.labels = list(labels)
        self.transform = transform
        self.perturb = perturb
        self.seed = seed

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, i):
        img = Image.open(self.paths[i]).convert("RGB")
        if self.perturb is not None:
            # seed=None sorteia de novo a cada epoca (treino); com seed o teste fica reprodutivel
            rng = np.random.default_rng() if self.seed is None else np.random.default_rng(self.seed * 100003 + i)
            img = Image.fromarray(self.perturb(np.asarray(img), rng))
        return self.transform(img), torch.tensor(self.labels[i], dtype=torch.long)


# Interferencias que imitam fotos tiradas na rua

def sombra(img: np.ndarray, rng, forca: float = 0.6) -> np.ndarray:
    h, w = img.shape[:2]
    pts = rng.integers(0, [w, h], size=(4, 2)).astype(np.int32)
    pts[:2, 0] = rng.integers(0, w // 2, size=2)
    mask = np.zeros((h, w), np.uint8)
    cv2.fillPoly(mask, [cv2.convexHull(pts)], 255)
    mask = cv2.GaussianBlur(mask, (15, 15), 0).astype(np.float32)[..., None] / 255
    out = img.astype(np.float32) * (1 - forca * mask)
    return out.clip(0, 255).astype(np.uint8)


def pouca_luz(img, rng):
    g = 2.2
    return (255 * (img / 255.0) ** g).clip(0, 255).astype(np.uint8)


def superexposicao(img, rng):
    return cv2.convertScaleAbs(img, alpha=1.3, beta=70)


def desfoque(img, rng):
    k = np.zeros((9, 9), np.float32)
    k[4, :] = 1 / 9
    return cv2.filter2D(img, -1, k)


def ruido(img, rng):
    n = rng.normal(0, 18, img.shape)
    return (img.astype(np.float32) + n).clip(0, 255).astype(np.uint8)


def textura(img, rng):
    h, w = img.shape[:2]
    out = img.copy()
    for _ in range(3):
        x1, y1 = rng.integers(0, w), rng.integers(0, h)
        x2, y2 = rng.integers(0, w), rng.integers(0, h)
        cor = int(rng.integers(30, 90))
        cv2.line(out, (int(x1), int(y1)), (int(x2), int(y2)), (cor, cor, cor),
                 int(rng.integers(1, 3)), cv2.LINE_AA)
    return out


def obstaculo(img, rng):
    # objeto na frente da parede (poste, placa, folhagem) cobrindo 15% a 35% da imagem
    h, w = img.shape[:2]
    out = img.copy()
    area = rng.uniform(0.15, 0.35) * h * w
    ow = int(np.clip(np.sqrt(area * rng.uniform(0.3, 3.0)), 20, w))
    oh = int(np.clip(area / ow, 20, h))
    x, y = int(rng.integers(0, w - ow + 1)), int(rng.integers(0, h - oh + 1))
    cor = tuple(int(c) for c in rng.integers(20, 200, size=3))
    if rng.random() < 0.5:
        cv2.rectangle(out, (x, y), (x + ow, y + oh), cor, -1)
    else:
        cv2.ellipse(out, (x + ow // 2, y + oh // 2), (ow // 2, oh // 2), 0, 0, 360, cor, -1)
    return out


def aumento_campo(img, rng):
    # metade das imagens recebe ruido, sombra ou luz variada; riscos e obstaculos ficam
    # de fora para continuarem sendo um teste que o modelo nunca viu
    if rng.random() < 0.5:
        return img
    op = rng.integers(0, 3)
    if op == 0:
        n = rng.normal(0, rng.uniform(5, 25), img.shape)
        return (img.astype(np.float32) + n).clip(0, 255).astype(np.uint8)
    if op == 1:
        return sombra(img, rng, forca=rng.uniform(0.3, 0.7))
    g = rng.uniform(0.6, 2.4)
    return (255 * (img / 255.0) ** g).clip(0, 255).astype(np.uint8)


PERTURBACOES = {
    "original": None,
    "sombra": sombra,
    "pouca_luz": pouca_luz,
    "superexposicao": superexposicao,
    "desfoque": desfoque,
    "ruido": ruido,
    "riscos_textura": textura,
    "obstaculo": obstaculo,
}
