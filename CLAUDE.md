# Momontanha — contexto para o Claude

Site do Leandro Cechinel: **relatos** de trilhas, travessias e escaladas, a **croquiteca** do Paraná
e **croquis próprios** (web + PDF versionado). Substitui o antigo `momontanha.wordpress.com`.
Idioma: **português**. Na escalada o Leandro é chamado de **Cechinel**: nos textos de croqui e créditos
de conquista use "Cechinel" (o nome completo, Leandro Cechinel, só em créditos formais como autoria e fotos). O Leandro não mexe em código: ele manda texto, áudio, fotos e linhas
riscadas, e o Claude transforma em arquivos aqui.

## Stack
- **Astro 7** (site estático) · conteúdo em Markdown em `src/content/` · esquemas em `src/content.config.ts`.
- **GitHub Pages** via `.github/workflows/publicar.yml`: todo push na `main` monta o site, gera os PDFs
  (Chromium/Playwright) e publica. PDFs de versões novas (não rascunho) viram **Release** com o nome do arquivo.
- Endereço: `SITE_URL` + `BASE_PATH` (padrão `https://momontanha.github.io` + `/`; repositório `momontanha/momontanha.github.io`, na organização gratuita `momontanha`).
  Com domínio próprio: variáveis do repositório `SITE_URL=https://dominio` e `BASE_PATH=/`, mais o arquivo `public/CNAME`.
- Links internos nas páginas `.astro` sempre com `url('/caminho/')` de `src/lib/util.ts` (respeita o base).
- **Cores e modo escuro:** variáveis em `src/styles/global.css` com `light-dark(claro, escuro)` (`--fundo`, `--superficie`,
  `--tinta`, `--titulo`, `--link`, `--marca`…). O tema segue o sistema; o botão do topo grava `data-tema` (claro/escuro)
  no `localStorage`. Não usar cor fixa (`#fff`) em fundo/texto: usar as variáveis. Impressão/PDF é sempre claro.

## Comandos
- `npm run build` — site + PDFs em `dist/` (PDFs em `dist/pdf/`).
- `npm run build:site` / `npm run pdfs` — cada etapa separada.
- `npm run dev` — servidor local.

## Coleções
| Pasta | O que é |
|---|---|
| `src/content/relatos/` | Posts do blog. Frontmatter: `titulo`, `data`, `resumo`, `capa`, `tags`, `rascunho`. |
| `src/content/croquiteca/` | Um verbete por setor/montanha: `nome`, `regiao`, `tipo`, `capa`, `links` (`rotulo`, `url`, `tipo`: drive, pdf, guia, wikiloc, mapa, fotos, instagram, formulario, externo), `coordenadas`, `croqui` (slug de um croqui próprio). |
| `src/content/croquis/` | Croquis próprios, dados estruturados (subsetores → blocos → linhas). Viram `/croquis/<slug>/` e `/pdf/<slug>-v<versao>.pdf`. |
| `src/content/paginas/` | Páginas soltas (Sobre). |

Imagens ficam em `src/assets/` (as migradas em `src/assets/wp/`); o Astro converte para WebP no build.
Antes de adicionar foto nova, reduzir para no máximo 1600 px e JPEG qualidade ~80.

## Fluxos

### Relato novo
1. Criar `src/content/relatos/<slug>.md` com o frontmatter acima; fotos em `src/assets/relatos/<slug>/`.
2. Texto do Leandro com revisão leve (manter a voz dele, primeira pessoa). Vídeo do YouTube:
   `<div class="video"><iframe src="https://www.youtube-nocookie.com/embed/ID" title="Vídeo" loading="lazy" allowfullscreen></iframe></div>`.
3. Várias imagens seguidas no mesmo parágrafo viram galeria automaticamente.

### Croqui próprio: linha nova ou correção
1. Editar `src/content/croquis/<slug>.md` (adicionar a linha no bloco certo; criar o bloco se precisar).
2. **Sempre** subir a `versao` e adicionar uma entrada em `historico` dizendo o que mudou.
   - Correção pequena ou linha nova: `0.1 → 0.2`. A série 0.x é o croqui em construção (o Castelinhos foi publicado
     na v0.2, em 18/11/2026). `1.0` só quando o setor estiver completo, com fotos próprias de todos os blocos.
3. Fotos do bloco: `src/assets/croquis/<slug>/<bloco>.jpg` na lista `fotos` do bloco (`imagem`, `credito`).
   Cada linha diz em qual foto está o traço (`foto: 2`; padrão 1). As linhas são numeradas dentro de cada bloco
   (1, 2, 3… na ordem do arquivo; `n` fixa outro número) e o número aparece no início e no topo do traço. Mapas do subsetor vão em `mapas`
   (`imagem`, `legenda`, `credito`). Vídeos/posts do bloco: `links` (`rotulo`, `url`), só na versão web. Nos croquis as imagens saem em JPEG (`format="jpg"`): o Chromium põe
   WebP sem compressão no PDF (68 MB em vez de 9 MB).
4. Linha na foto (`traco`): pontos `x,y` em % da foto, do pé ao topo. Se o Leandro mandar a foto
   riscada (cor forte) + a original: `python3 scripts/extrair_linha.py riscada.jpg --original original.jpg`.
   Conferir o resultado olhando a página gerada.
   **Topo antigo** (página de PDF com foto + linhas coloridas desenhadas por cima, como os croquis de 2013/2015):
   `python3 scripts/importar_topo_antigo.py pagina.png --cores vermelho,amarelo,verde --saida src/assets/croquis/<slug>/<bloco>.jpg`
   recorta a foto, tira o traço de cada cor (início = ponta mais baixa) e apaga as linhas antigas. Precisa de
   `pip install opencv-python-headless`. Conferir lado a lado com o original; em travessia o início pode sair invertido.
5. Créditos: quem conquistou (`conquista`, `ano`) e de onde veio a informação. Nunca copiar texto
   ou fotos de croqui de outra pessoa sem crédito e autorização; guias vendidos só entram como link (`tipo: guia`).
   **Fotos de terceiros** (croquis de 2013/2015, posts de outros escaladores): o Leandro decidiu (18/11/2026)
   mantê-las, com crédito em cada foto, até tirar fotos novas no setor. Ao receber foto nova de um bloco,
   trocar a foto antiga e redesenhar as linhas (pedir o risco quando o ângulo mudar muito).
6. `rascunho: true` mantém a página fora do sitemap, com `noindex`, e sem botão na croquiteca.
   Tirar o rascunho só quando o Leandro aprovar.

### Croquiteca
- Verbete novo: arquivo em `src/content/croquiteca/` com `regiao` de uma das regiões existentes
  (Anhangava, Serra do Ibitiraquire, Serra do Marumbi, São Luiz do Purunã, Campos Gerais, Lapa, Serra do Quiriri, Litoral).
- Escrever um parágrafo com acesso e o que tem no setor: é esse texto que faz a página aparecer no Google.
- Croquis livres podem ir como PDF em `public/croquis/` (`tipo: pdf`); pagos, só link de compra.

## Git
Trabalhar em branch, abrir PR para `main` e fazer squash merge. O merge na `main` publica o site.

## Origem
`scripts/migrar_wordpress.py` fez a migração única do WordPress (API pública) em 17/11/2026.
Não roda de novo sem necessidade: ele não sobrescreve arquivos que já existem.
