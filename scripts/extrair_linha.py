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


def simplificar(pts, eps):
    """Ramer-Douglas-Peucker: tira pontos que não mudam o desenho."""
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    ab = b - a
    v = pts - a
    d = np.abs(ab[0] * v[:, 1] - ab[1] * v[:, 0]) / (np.hypot(*ab) or 1e-9)
    i = int(np.argmax(d))
    if d[i] > eps:
        return np.vstack([simplificar(pts[: i + 1], eps)[:-1], simplificar(pts[i:], eps)])
    return np.array([a, b])


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
    # segue o risco ponto a ponto (mantém curvas e cantos): agrupa em células, começa
    # no ponto mais baixo e vai sempre para o vizinho mais próximo; depois simplifica.
    diag = float(np.hypot(w, h))
    # espessura do risco ≈ área / comprimento; a célula precisa ser mais larga que o risco,
    # senão o caminho zigue-zagueia de um lado para o outro do traço
    # (largura medida pela extensão do risco em cada linha/coluna da imagem: o marca-texto
    # costuma ter falhas no meio, então contar pixels subestima a espessura)
    def extensao_mediana(a, b):
        ordem = np.argsort(a)
        a, b = a[ordem], b[ordem]
        cortes = np.flatnonzero(np.diff(a)) + 1
        ext = [g.max() - g.min() + 1 for g in np.split(b, cortes)]
        return float(np.median(ext))
    espessura = min(extensao_mediana(ys, xs), extensao_mediana(xs, ys))
    celula = int(max(4, diag / 160, espessura * 1.3))
    chave = (ys // celula) * 100000 + (xs // celula)
    pts = np.array([(xs[chave == k].mean(), ys[chave == k].mean()) for k in np.unique(chave)])
    ordem = [int(np.argmax(pts[:, 1]))]
    livres = set(range(len(pts))) - set(ordem)
    while livres:
        cand = np.array(sorted(livres))
        dist = np.hypot(*(pts[cand] - pts[ordem[-1]]).T)
        j = int(np.argmin(dist))
        if dist[j] > celula * 4:  # resto solto longe do caminho: termina
            break
        ordem.append(int(cand[j]))
        livres.discard(int(cand[j]))
    cadeia = pts[ordem]
    if inverter:
        cadeia = cadeia[::-1]
    # tolerância proporcional à espessura: o tremido da borda do risco não vira curva
    sel = simplificar(cadeia, max(diag * 0.006, espessura * 0.8))
    # tira "vai e volta" (ponto onde o caminho dá meia-volta), comum no canto de risco grosso
    mudou = True
    while mudou and len(sel) > 2:
        mudou = False
        for i in range(1, len(sel) - 1):
            a, b = sel[i] - sel[i - 1], sel[i + 1] - sel[i]
            cos = (a @ b) / ((np.hypot(*a) * np.hypot(*b)) or 1e-9)
            if cos < -0.5:
                sel = np.delete(sel, i, axis=0)
                mudou = True
                break
    if len(sel) > pontos:  # ainda muitos pontos: amostra mantendo as pontas
        sel = sel[np.linspace(0, len(sel) - 1, pontos).round().astype(int)]
    return " ".join(f"{x / w * 100:.1f},{y / h * 100:.1f}" for x, y in sel)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("foto")
    ap.add_argument("--cor", default="vermelho", choices=CORES)
    ap.add_argument("--pontos", type=int, default=14, help="máximo de pontos")
    ap.add_argument("--inverter", action="store_true")
    ap.add_argument("--original", help="a mesma foto sem o risco")
    a = ap.parse_args()
    print(extrair(a.foto, a.cor, a.pontos, a.inverter, a.original))
