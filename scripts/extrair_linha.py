#!/usr/bin/env python3
"""Extrai o traço de uma linha riscada à mão numa foto e devolve o campo `traco` do croqui.

Fluxo: no celular, risque a linha por cima da foto com o dedo, numa cor forte
(vermelho puro ou amarelo), do pé até o topo. Mande a foto riscada e a original.

Uso:
  python3 scripts/extrair_linha.py foto-riscada.jpg [--original foto.jpg] [--cor vermelho|amarelo|verde|azul] [--pontos 8] [--inverter]

Com --original, só conta o que mudou entre as duas fotos (evita confundir a linha com
uma jaqueta ou um crashpad da mesma cor).

Saída: algo como  "41.2,71.8 44.0,55.3 50.1,40.2 56.0,28.4"  (x,y em % da largura e da altura),
começando pelo ponto mais baixo da foto (o início do boulder). Use --inverter se a linha
começar por cima (ex.: descida ou travessia da direita para a esquerda).
Cole o resultado no campo `traco` da linha, no arquivo do croqui.
"""
import argparse
import numpy as np
from PIL import Image, ImageOps

CORES = {
    "vermelho": lambda r, g, b: (r > 170) & (g < 90) & (b < 90) & (r - np.maximum(g, b) > 100),
    "amarelo": lambda r, g, b: (r > 190) & (g > 170) & (b < 90),
    "verde": lambda r, g, b: (g > 160) & (r < 110) & (b < 110),
    "azul": lambda r, g, b: (b > 170) & (r < 90) & (g < 140),
}


def extrair(caminho, cor="vermelho", pontos=8, inverter=False, original=None):
    im = ImageOps.exif_transpose(Image.open(caminho)).convert("RGB")
    a = np.asarray(im).astype(int)
    h, w, _ = a.shape
    mascara = CORES[cor](a[:, :, 0], a[:, :, 1], a[:, :, 2])
    if original:
        o = ImageOps.exif_transpose(Image.open(original)).convert("RGB").resize((w, h))
        mudou = np.abs(np.asarray(o).astype(int) - a).sum(axis=2) > 120
        mascara &= mudou
    ys, xs = np.nonzero(mascara)
    if len(xs) < 50:
        raise SystemExit(f"Não achei a linha {cor} na foto ({len(xs)} pixels). Tente outra --cor.")
    p = np.column_stack([xs, ys]).astype(float)
    centro = p.mean(axis=0)
    # eixo principal da linha (funciona para linhas verticais, diagonais e travessias)
    _, _, v = np.linalg.svd(p - centro, full_matrices=False)
    eixo = v[0]
    t = (p - centro) @ eixo
    nbins = max(pontos * 6, 20)
    bordas = np.linspace(t.min(), t.max(), nbins + 1)
    medios = []
    for i in range(nbins):
        sel = (t >= bordas[i]) & (t <= bordas[i + 1])
        if sel.sum() > 3:
            medios.append(p[sel].mean(axis=0))
    medios = np.array(medios)
    # começa pelo ponto mais baixo da foto (maior y)
    if medios[0][1] < medios[-1][1]:
        medios = medios[::-1]
    if inverter:
        medios = medios[::-1]
    idx = np.linspace(0, len(medios) - 1, pontos).round().astype(int)
    sel = medios[idx]
    return " ".join(f"{x / w * 100:.1f},{y / h * 100:.1f}" for x, y in sel)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("foto")
    ap.add_argument("--cor", default="vermelho", choices=CORES)
    ap.add_argument("--pontos", type=int, default=8)
    ap.add_argument("--inverter", action="store_true")
    ap.add_argument("--original", help="a mesma foto sem o risco")
    a = ap.parse_args()
    print(extrair(a.foto, a.cor, a.pontos, a.inverter, a.original))
