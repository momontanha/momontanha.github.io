#!/usr/bin/env python3
"""Compara a lista de boulders do 8a.nu com um croqui próprio e gera o backlog.

O 8a.nu bloqueia acesso automatizado, então a lista entra por arquivo, exportado à mão:
  - TSV/CSV com colunas: nome, grau, cadenas, url (opcional), setor (opcional); ou
  - texto colado da página do 8a.nu (uma linha por boulder, com o grau Font e as cadenas).

Uso:
  python3 scripts/comparar_8a.py lista-8a.tsv [--croqui castelinhos-anhangava] [--aplicar]

Saída: tabela em Markdown (stdout) com, para cada boulder do 8a.nu:
  - situação: no croqui · variante de linha do croqui · NOVO (backlog) · possível duplicata no 8a.nu
  - grau no 8a.nu (Font ≈ V) x grau no croqui, marcando divergência de 2+ graus V
Com --aplicar, grava a URL do 8a.nu (campo `oitoa`) nas linhas do croqui com casamento seguro.
"""
import argparse, csv, difflib, re, sys, unicodedata
from pathlib import Path
import yaml

RAIZ = Path(__file__).resolve().parent.parent
FONT_V = {'3': 'VB', '4': 0, '4+': 0, '5': 1, '5+': 2, '6A': 3, '6A+': 3, '6B': 4, '6B+': 4, '6C': 5, '6C+': 5,
          '7A': 6, '7A+': 7, '7B': 8, '7B+': 8, '7C': 9, '7C+': 10, '8A': 11, '8A+': 12, '8B': 13, '8B+': 14, '8C': 15, '8C+': 16}
# palavras que indicam variante da mesma linha (não linha nova)
VARIANTE = r'\b(sds|sit|sit start|saida sentado|sentado|em pe|standing|stand|low|baixo|extension|ext|direct|direta|esquerda|direita|variante|var)\b'
VAZIAS = r'\b(do|da|de|dos|das|o|a|os|as|e|the|of|bloco|boulder|lance)\b'


def normalizar(nome):
    s = unicodedata.normalize('NFD', nome.lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^a-z0-9 ]+', ' ', s)
    s = s.replace('orelhinha', 'orelinha').replace('quebrada', 'quebrou')
    return re.sub(r'\s+', ' ', s).strip()


def base(nome):
    """Nome sem as marcas de variante e sem palavras vazias (para casar 'Satã SDS' com 'Satã')."""
    s = re.sub(VARIANTE, ' ', normalizar(nome))
    s = re.sub(VAZIAS, ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def eh_variante(nome):
    return re.search(VARIANTE, normalizar(nome)) is not None


def font_para_v(g):
    g = g.strip().upper().replace(' ', '')
    m = re.fullmatch(r'([3-8])([ABC]?)(\+?)(/.*)?', g)
    if not m:
        return None
    chave = m.group(1) + m.group(2) + m.group(3)
    return FONT_V.get(chave, FONT_V.get(m.group(1) + m.group(2)))


def v_do_croqui(g):
    m = re.search(r'v(\d+)(?:/(\d+))?', g.lower())
    if not m:
        return None
    a = int(m.group(1)); b = int(m.group(2) or a)
    return (a + b) / 2


def ler_lista(arq):
    texto = Path(arq).read_text(encoding='utf-8')
    linhas = [l for l in texto.splitlines() if l.strip()]
    if '\t' in linhas[0] or ',' in linhas[0] and 'nome' in linhas[0].lower():
        dial = 'excel-tab' if '\t' in linhas[0] else 'excel'
        return [{k.strip().lower(): (v or '').strip() for k, v in r.items()} for r in csv.DictReader(linhas, dialect=dial)]
    # texto colado: procura o grau Font e um número de cadenas em cada linha
    itens = []
    for l in linhas:
        m = re.search(r'\b([3-8][ABCabc]?\+?)\b', l)
        if not m:
            continue
        resto = (l[:m.start()] + ' ' + l[m.end():]).strip()
        cad = re.search(r'(\d+)\s*(cadenas?|ascents?|subidas?)?\s*$', resto)
        n = cad.group(1) if cad else ''
        nome = resto[:cad.start()].strip(' -|·•') if cad else resto
        url = re.search(r'https?://\S+', l)
        itens.append({'nome': nome, 'grau': m.group(1).upper(), 'cadenas': n, 'url': url.group(0) if url else ''})
    return itens


def linhas_do_croqui(slug):
    texto = (RAIZ / f'src/content/croquis/{slug}.md').read_text(encoding='utf-8')
    d = yaml.safe_load(texto.split('---')[1])
    out = []
    for s in d['subsetores']:
        for b in s['blocos']:
            for l in b['linhas']:
                out.append({'nome': l['nome'], 'grau': str(l['grau']), 'bloco': b['nome'], 'subsetor': s['nome'], 'saida': l.get('saida')})
    return out


def casar(item, croqui):
    alvo = normalizar(item['nome']); alvo_b = base(item['nome'])
    melhor, nota = None, 0.0
    for c in croqui:
        r = max(difflib.SequenceMatcher(None, alvo, normalizar(c['nome'])).ratio(),
                difflib.SequenceMatcher(None, alvo_b, base(c['nome'])).ratio() if alvo_b and base(c['nome']) else 0)
        if r > nota:
            melhor, nota = c, r
    return melhor, nota


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('lista')
    ap.add_argument('--croqui', default='castelinhos-anhangava')
    ap.add_argument('--aplicar', action='store_true')
    a = ap.parse_args()
    lista = ler_lista(a.lista)
    croqui = linhas_do_croqui(a.croqui)

    # duplicatas dentro do próprio 8a.nu: mesmo nome-base
    grupos = {}
    for i, it in enumerate(lista):
        grupos.setdefault(base(it['nome']), []).append(i)
    for i, it in enumerate(lista):
        it['irmaos'] = [lista[j]['nome'] for j in grupos[base(it['nome'])] if j != i]
        if not it['irmaos']:  # nomes quase iguais (erro de digitação)
            it['irmaos'] = [o['nome'] for j, o in enumerate(lista) if j != i and
                            difflib.SequenceMatcher(None, base(it['nome']), base(o['nome'])).ratio() >= 0.82]

    print('| 8a.nu | Grau 8a (≈V) | Cadenas | Situação | No croqui | Observação |')
    print('|---|---|---|---|---|---|')
    gravar = {}
    for it in sorted(lista, key=lambda x: -int(x.get('cadenas') or 0)):
        c, nota = casar(it, croqui)
        v8 = font_para_v(it['grau']) if it.get('grau') else None
        obs = []
        if nota >= 0.86 and eh_variante(it['nome']) == eh_variante(c['nome'] + (' sds' if c.get('saida') == 'sentado' else '')):
            situacao = 'no croqui'
            if it.get('url'):
                gravar.setdefault(c['nome'] + '|' + c['bloco'], it['url'])
        elif nota >= 0.7 and eh_variante(it['nome']):
            situacao = 'variante (backlog)'
        elif nota >= 0.7:
            situacao = 'confirmar: mesmo boulder?'
        else:
            situacao = '**NOVO (backlog)**'
            c = None
        vc = v_do_croqui(c['grau']) if c else None
        if c and v8 is not None and isinstance(v8, int) and vc is not None and abs(v8 - vc) >= 2:
            obs.append(f"grau diverge: 8a ≈ V{v8}, croqui {c['grau']}")
        if c and 'proj' in c['grau'].lower() and v8 is not None:
            obs.append(f"**projeto no croqui, mas já tem grau no 8a.nu ({it['grau']}): encadenado?**")
        dup = [o for o in it['irmaos'] if eh_variante(o) == eh_variante(it['nome'])]
        var = [o for o in it['irmaos'] if eh_variante(o) != eh_variante(it['nome'])]
        if dup:
            obs.append('**possível duplicata no 8a.nu:** ' + ', '.join(dup))
        if var:
            obs.append('variante no 8a.nu: ' + ', '.join(var))
        no_croqui = f"{c['nome']} {c['grau']} ({c['bloco']})" if c else '—'
        vtxt = f"{it.get('grau', '')} (≈V{v8})" if isinstance(v8, int) else it.get('grau', '')
        nome = f"[{it['nome']}]({it['url']})" if it.get('url') else it['nome']
        print(f"| {nome} | {vtxt} | {it.get('cadenas', '')} | {situacao} | {no_croqui} | {'; '.join(obs)} |")

    if a.aplicar and gravar:
        p = RAIZ / f'src/content/croquis/{a.croqui}.md'
        texto = p.read_text(encoding='utf-8')
        n = 0
        for chave, url in gravar.items():
            nome = chave.split('|')[0]
            padrao = re.compile(r"(\{nome: " + re.escape(nome) + r", (?:(?!oitoa:)[^}])*?)\}")
            texto, k = padrao.subn(lambda m: m.group(1) + f", oitoa: '{url}'}}", texto, count=1)
            n += k
        p.write_text(texto, encoding='utf-8')
        print(f'\n{n} link(s) do 8a.nu gravado(s) no croqui.', file=sys.stderr)


if __name__ == '__main__':
    main()
