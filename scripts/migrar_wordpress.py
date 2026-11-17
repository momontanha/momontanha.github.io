#!/usr/bin/env python3
"""Migração única do momontanha.wordpress.com para o site em Astro.

Lê a API pública do WordPress.com, converte cada post em Markdown e baixa as
imagens (redimensionadas para no máximo 1600 px) para src/assets/wp/.

Uso:  python3 scripts/migrar_wordpress.py  [--sem-imagens]

Gera:
  src/content/relatos/<slug>.md      (posts que não são da categoria Croqui)
  src/content/croquiteca/<slug>.md   (posts da categoria Croqui)
  src/content/paginas/sobre.md
Arquivos que já existem NÃO são sobrescritos (para não perder edições feitas depois).
"""
import html, json, os, re, sys, time, urllib.request
from pathlib import Path
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from markdownify import markdownify

RAIZ = Path(__file__).resolve().parent.parent
API = "https://public-api.wordpress.com/rest/v1.1/sites/momontanha.wordpress.com"
ASSETS = RAIZ / "src/assets/wp"
BAIXAR = "--sem-imagens" not in sys.argv

# Região e tipo de cada entrada da croquiteca (slug do WordPress -> dados).
CROQUITECA = {
    "morro-do-sete": ("Serra do Marumbi", "montanha"),
    "marumbi": ("Serra do Marumbi", "montanha"),
    "pico-caratuva": ("Serra do Ibitiraquire", "montanha"),
    "ferraria": ("Serra do Ibitiraquire", "montanha"),
    "mar-de-caratuvas": ("Serra do Ibitiraquire", "montanha"),
    "pico-itapiroca": ("Serra do Ibitiraquire", "montanha"),
    "pico-tucum": ("Serra do Ibitiraquire", "montanha"),
    "morro-do-anhangava-croqui": ("Anhangava", "tradicional e esportiva"),
    "castelinhos-do-anhangava": ("Anhangava", "boulder"),
    "jardim-secreto-anhangava": ("Anhangava", "boulder"),
    "setor-1-sao-luiz-do-puruna": ("São Luiz do Purunã", "esportiva"),
    "setor-2": ("São Luiz do Purunã", "esportiva"),
    "setor-3-sao-luiz-do-puruna": ("São Luiz do Purunã", "esportiva"),
    "setor-caicara": ("A confirmar", "esportiva"),
    "morro-pao-de-lo": ("A confirmar", "esportiva"),
    "perau-vermelho": ("A confirmar", "esportiva"),
    "setor-spider-lapa": ("Lapa", "esportiva"),
    "setor-macarrao-buraco-do-padre": ("Campos Gerais", "esportiva"),
    "pirai-do-sul": ("Campos Gerais", "esportiva"),
    "aracatuba-boulder": ("Serra do Quiriri", "boulder"),
    "cabaraquara": ("Litoral", "esportiva"),
    "morro-escalvado": ("Litoral", "esportiva"),
    "caioba": ("Litoral", "boulder"),
    "ilha-do-mel": ("Litoral", "boulder"),
}
# Slugs novos (mais legíveis) para algumas entradas.
SLUG_NOVO = {"setor-2": "setor-1-75-sao-luiz-do-puruna", "mar-de-caratuvas": "ibitirati",
             "morro-do-anhangava-croqui": "morro-do-anhangava", "pico-caratuva": "pico-caratuva-agulha-rs"}


def get_json(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def baixar(url_original):
    """Baixa a imagem (máx. 1600 px) e devolve o caminho local relativo a src/assets/wp."""
    p = urlparse(url_original)
    caminho = p.path.split("/wp-content/uploads/")[-1]
    destino = ASSETS / caminho
    if BAIXAR and not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://momontanha.wordpress.com/wp-content/uploads/{caminho}?w=1600"
        for tentativa in range(4):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "momontanha-migracao"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    destino.write_bytes(r.read())
                break
            except Exception as e:  # noqa: BLE001
                print("  falha", url, e)
                time.sleep(2 ** tentativa)
    return caminho


def link_tipo(href, texto):
    h = href.lower()
    if "drive.google" in h:
        return "drive"
    if "photos.app.goo.gl" in h:
        return "fotos"
    if "wikiloc" in h:
        return "wikiloc"
    if "maps.app.goo.gl" in h or "goo.gl/maps" in h:
        return "mapa"
    if "instagram.com" in h:
        return "instagram"
    if "forms.gle" in h:
        return "formulario"
    if "extremeoutdoor" in h or "lojaam" in h:
        return "guia"
    return "externo"


def limpar_html(conteudo, rel_assets):
    """Normaliza o HTML do WordPress antes de virar Markdown."""
    soup = BeautifulSoup(conteudo, "html.parser")
    # Vídeos do YouTube: vira um marcador que é trocado por HTML puro no fim.
    videos = []
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src", "")
        m = re.search(r"youtube\.com/embed/([\w-]+)", src)
        alvo = iframe.find_parent("figure") or iframe
        if m:
            videos.append(m.group(1))
            alvo.replace_with(soup.new_string(f"\n\nVIDEO{len(videos) - 1}FIM\n\n"))
        else:
            alvo.decompose()
    # Galerias em mosaico: viram uma sequência de imagens num parágrafo só.
    for gal in soup.select("div.tiled-gallery, div.gallery, figure.wp-block-gallery"):
        imgs = gal.find_all("img")
        p = soup.new_tag("p")
        for img in imgs:
            novo = soup.new_tag("img", src=img.get("data-orig-file") or img.get("src", ""),
                                alt=html.unescape(img.get("data-image-title") or img.get("alt") or ""))
            p.append(novo)
            p.append(" ")
        gal.replace_with(p)
    # Imagens: aponta para o arquivo local.
    for img in soup.find_all("img"):
        src = img.get("data-orig-file") or img.get("src", "")
        src = re.sub(r"^https://i\d\.wp\.com/", "https://", src).split("?")[0]
        if "/wp-content/uploads/" not in src:
            img.decompose()
            continue
        if "momontanha" not in urlparse(src).netloc:
            # imagem de outro site (ex.: altamontanha.com): mantém o link original
            img.replace_with(soup.new_tag("img", src=src, alt=html.unescape(img.get("alt") or "")))
            continue
        caminho = baixar(src)
        alt = html.unescape(img.get("alt") or "")
        if re.fullmatch(r"[\w\- .()]*\d{4,}[\w\- .()]*|img.*|dsc.*|dji.*|lce.*", alt.lower() or "x"):
            alt = ""
        a = img.find_parent("a")
        novo = soup.new_tag("img", src=f"{rel_assets}/{caminho}", alt=alt)
        (a if a else img).replace_with(novo)
    # Legendas de imagem do editor de blocos.
    for fc in soup.find_all("figcaption"):
        fc.name = "em"
    for tag in soup.find_all(["figure", "div", "span"]):
        tag.unwrap()
    md = markdownify(str(soup), heading_style="ATX", bullets="-", strip=["script", "style"])
    md = re.sub(r"^#+\s*$", "", md, flags=re.M)  # títulos vazios
    # listas que só têm imagens (galerias do editor novo) viram um parágrafo de imagens
    md = re.sub(r"(?:^- (!\[[^\]]*\]\([^)]+\))\s*\n?)+",
                lambda m: " ".join(re.findall(r"!\[[^\]]*\]\([^)]+\)", m.group(0))) + "\n\n", md, flags=re.M)
    md = re.sub(r"\n{3,}", "\n\n", md).replace("\xa0", " ").strip()
    for i, vid in enumerate(videos):
        md = md.replace(f"VIDEO{i}FIM", f'<div class="video"><iframe src="https://www.youtube-nocookie.com/embed/{vid}" title="Vídeo" loading="lazy" allowfullscreen></iframe></div>')
    return md


def yaml_str(s):
    return json.dumps(s, ensure_ascii=False)


def escrever(destino, frontmatter, corpo):
    if destino.exists():
        print("  já existe, mantido:", destino.relative_to(RAIZ))
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    linhas = ["---"]
    for k, v in frontmatter.items():
        if v is None or v == [] or v == "":
            continue
        if isinstance(v, list) and v and isinstance(v[0], dict):
            linhas.append(f"{k}:")
            for item in v:
                primeiro = True
                for kk, vv in item.items():
                    linhas.append(f"  {'- ' if primeiro else '  '}{kk}: {yaml_str(vv)}")
                    primeiro = False
        elif isinstance(v, list):
            linhas.append(f"{k}: [{', '.join(yaml_str(x) for x in v)}]")
        else:
            linhas.append(f"{k}: {yaml_str(v)}")
    linhas.append("---")
    destino.write_text("\n".join(linhas) + "\n\n" + corpo.strip() + "\n", encoding="utf-8")
    print("  ok", destino.relative_to(RAIZ))


def capa(post):
    url = post.get("featured_image") or ""
    if "/wp-content/uploads/" not in url:
        return None
    return baixar(url.split("?")[0])


def main():
    posts = get_json(f"{API}/posts/?number=100&status=publish")["posts"]
    paginas = get_json(f"{API}/posts/?number=100&type=page")["posts"]
    for post in posts:
        titulo = html.unescape(post["title"]).replace("–", "—")
        slug_wp = post["slug"]
        cats = list(post.get("categories", {}).keys())
        tags = sorted({t.lower() for t in post.get("tags", {}).keys()} - {"croqui", "croquis", "momontanha"})
        if "Croqui" in cats:
            slug = SLUG_NOVO.get(slug_wp, slug_wp)
            regiao, tipo = CROQUITECA.get(slug_wp, ("A confirmar", "esportiva"))
            soup = BeautifulSoup(post["content"], "html.parser")
            links = []
            for a in soup.find_all("a"):
                href = a.get("href", "")
                txt = a.get_text(" ", strip=True)
                if not href or "momontanha.wordpress.com/about" in href or txt == href:
                    continue
                rotulo = "Croqui (download)" if txt.lower() == "download" else txt
                links.append({"rotulo": rotulo, "url": href, "tipo": link_tipo(href, txt)})
            # O texto do post sem os botões de link (eles viram a lista "links").
            for a in soup.find_all("a"):
                if a.get("href") and a.get_text(strip=True) != a.get("href"):
                    a.decompose()
            corpo = limpar_html(str(soup), "../../assets/wp")
            c = capa(post)
            escrever(RAIZ / f"src/content/croquiteca/{slug}.md", {
                "nome": titulo, "regiao": regiao, "tipo": tipo,
                "capa": f"../../assets/wp/{c}" if c else None,
                "links": links, "tags": tags, "wp_url": post["URL"],
            }, corpo)
        else:
            corpo = limpar_html(post["content"], "../../assets/wp")
            c = capa(post)
            resumo = html.unescape(BeautifulSoup(post.get("excerpt", ""), "html.parser").get_text(" ", strip=True))
            resumo = re.sub(r"\s*(\[…\]|\[\.\.\.\]|…)\s*$", "…", resumo)[:220]
            escrever(RAIZ / f"src/content/relatos/{slug_wp}.md", {
                "titulo": titulo, "data": post["date"][:10], "resumo": resumo,
                "capa": f"../../assets/wp/{c}" if c else None,
                "tags": tags, "wp_url": post["URL"],
            }, corpo)
    for pag in paginas:
        if pag["slug"] == "about":
            corpo = limpar_html(pag["content"], "../../assets/wp")
            escrever(RAIZ / "src/content/paginas/sobre.md", {"titulo": "Sobre", "wp_url": pag["URL"]}, corpo)


if __name__ == "__main__":
    main()
