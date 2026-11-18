#!/usr/bin/env python3
"""Importa um topo antigo (página de croqui com foto + linhas coloridas desenhadas por cima).

Recorta a foto da página, extrai o traço de cada linha pela cor (do pé ao topo),
apaga as linhas antigas da foto (inpainting) e salva a foto limpa. O site redesenha as
linhas por cima, no padrão do Momontanha.

Uso:
  python3 scripts/importar_topo_antigo.py pagina.png --cores vermelho,amarelo,verde --saida src/assets/croquis/x/bloco.jpg

Saída (stdout): JSON {"vermelho": "x,y x,y ...", ...} com os traços em % da foto recortada.
Opções: --sem-recorte (a imagem já é só a foto) · --sem-limpar (não apaga as linhas antigas)
"""
import argparse, json
import cv2
import numpy as np

# Cores fortes de linha desenhada (critério de saturação, para não pegar folhagem).
def mascara_cor(img, cor):
    b, g, r = [img[:, :, i].astype(int) for i in range(3)]
    if cor == 'vermelho':
        m = (r > 140) & (r - g > 80) & (r - b > 80)
    elif cor == 'amarelo':
        m = (r > 170) & (g > 150) & (r - b > 90) & (g - b > 80) & (np.abs(r - g) < 80)
    elif cor == 'verde':
        m = (g > 100) & (g - r > 50) & (g - b > 45)
    elif cor in ('azul', 'ciano'):
        m = (b > 140) & (b - r > 90) & (b - g > 15)
    else:
        raise SystemExit(f'cor desconhecida: {cor}')
    return m.astype(np.uint8)


def recortar_foto(img):
    """Acha o retângulo da foto dentro da página (ignora faixa de título, margens e legenda)."""
    h, w = img.shape[:2]
    cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(int)
    # fundo da página é branco puro; céu claro da foto não é
    nao_branco = (img.min(axis=2) < 246)
    # faixa de título: linha de cor chapada e saturada (verde); céu é chapado mas sem cor
    media = img.mean(axis=1)
    saturacao = media.max(axis=1) - media.min(axis=1)
    titulo = (cinza.std(axis=1) < 20) & (saturacao > 40)
    linhas_ok = (nao_branco.mean(axis=1) > 0.5) & ~titulo
    y0, y1 = maior_sequencia(linhas_ok)
    cols_ok = nao_branco[y0:y1].mean(axis=0) > 0.6
    x0, x1 = maior_sequencia(cols_ok)
    return x0, y0, x1, y1


def maior_sequencia(v):
    melhor, ini, atual = (0, 0), None, None
    for i, ok in enumerate(list(v) + [False]):
        if ok and ini is None:
            ini = i
        if not ok and ini is not None:
            if i - ini > melhor[1] - melhor[0]:
                melhor = (ini, i)
            ini = None
    return melhor


def componentes_longos(m, diag):
    """Mantém só os pedaços compridos (traços), descartando pontinhos de folhagem."""
    m2 = cv2.dilate(m, np.ones((5, 5), np.uint8))
    n, rot, stats, _ = cv2.connectedComponentsWithStats(m2, 8)
    manter = np.zeros_like(m)
    for i in range(1, n):
        x, y, ww, hh, area = stats[i]
        if np.hypot(ww, hh) > diag * 0.06:
            manter[(rot == i) & (m > 0)] = 1
    return manter


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    ab = b - a
    n = np.hypot(*ab) or 1e-9
    v = pts - a
    d = np.abs(ab[0] * v[:, 1] - ab[1] * v[:, 0]) / n
    i = int(np.argmax(d))
    if d[i] > eps:
        return np.vstack([rdp(pts[: i + 1], eps)[:-1], rdp(pts[i:], eps)])
    return np.array([a, b])


def ordenar_traco(m, diag):
    ys, xs = np.nonzero(m)
    if len(xs) < 20:
        return None
    celula = max(4, int(diag / 160))
    chave = (ys // celula) * 100000 + (xs // celula)
    pts = []
    for k in np.unique(chave):
        sel = chave == k
        pts.append((xs[sel].mean(), ys[sel].mean()))
    pts = np.array(pts)
    # começa no ponto mais baixo e segue sempre para o vizinho mais próximo
    ordem = [int(np.argmax(pts[:, 1]))]
    livres = set(range(len(pts))) - set(ordem)
    while livres:
        ult = pts[ordem[-1]]
        cand = np.array(sorted(livres))
        dist = np.hypot(*(pts[cand] - ult).T)
        j = int(np.argmin(dist))
        if dist[j] > celula * 12:  # pedaço solto longe: termina
            break
        ordem.append(int(cand[j]))
        livres.discard(int(cand[j]))
    cadeia = pts[ordem]
    return rdp(cadeia, diag * 0.006)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('pagina')
    ap.add_argument('--cores', required=True)
    ap.add_argument('--saida', required=True)
    ap.add_argument('--sem-recorte', action='store_true')
    ap.add_argument('--sem-limpar', action='store_true')
    a = ap.parse_args()
    img = cv2.imread(a.pagina)
    if not a.sem_recorte:
        x0, y0, x1, y1 = recortar_foto(img)
        img = img[y0:y1, x0:x1].copy()
    h, w = img.shape[:2]
    diag = float(np.hypot(w, h))
    tracos, apagar = {}, np.zeros((h, w), np.uint8)
    for cor in a.cores.split(','):
        m = componentes_longos(mascara_cor(img, cor), diag)
        apagar |= m
        pts = ordenar_traco(m, diag)
        tracos[cor] = None if pts is None else ' '.join(f'{x / w * 100:.1f},{y / h * 100:.1f}' for x, y in pts)
    if not a.sem_limpar:
        apagar = cv2.dilate(apagar, np.ones((7, 7), np.uint8))
        img = cv2.inpaint(img, apagar * 255, 5, cv2.INPAINT_TELEA)
    if max(h, w) > 1600:
        f = 1600 / max(h, w)
        img = cv2.resize(img, (int(w * f), int(h * f)), interpolation=cv2.INTER_AREA)
    cv2.imwrite(a.saida, img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(json.dumps(tracos, ensure_ascii=False))


if __name__ == '__main__':
    main()
