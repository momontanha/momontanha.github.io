/**
 * Gera o PDF de cada croqui próprio a partir da página web já construída (dist/).
 *
 * Roda depois do `astro build`: serve a pasta dist/, abre cada croqui no Chromium
 * e imprime em A4. Os arquivos saem em dist/pdf/<slug>-v<versao>.pdf
 * (com o sufixo -rascunho quando o croqui ainda é rascunho).
 *
 * Uso: npm run pdfs   (ou já incluso em npm run build)
 */
import { mkdirSync } from 'node:fs';
import { chromium } from 'playwright';
import { servir } from './servidor-estatico.mjs';

const PORTA = 4329;
const base = (process.env.BASE_PATH ?? '/').replace(/\/$/, '');
const raiz = `http://127.0.0.1:${PORTA}${base}`;

const servidor = await servir({ pasta: 'dist', base, porta: PORTA });

try {
  const croquis = await (await fetch(`${raiz}/croquis/manifesto.json`)).json();
  mkdirSync('dist/pdf', { recursive: true });
  const navegador = await chromium.launch();
  // PDF no formato celular: mesma página do site, aberta a 390 px (layout mobile), tema claro
  const pagina = await navegador.newPage({ viewport: { width: 390, height: 844 } });
  await pagina.emulateMedia({ media: 'screen', colorScheme: 'light' });
  for (const c of croquis) {
    await pagina.goto(`${raiz}/croquis/${c.slug}/`, { waitUntil: 'networkidle' });
    // imagens com loading=lazy não carregam sozinhas na impressão
    await pagina.evaluate(async () => {
      document.querySelectorAll('img[loading="lazy"]').forEach((img) => (img.loading = 'eager'));
      await Promise.all([...document.images].map((img) => (img.complete ? null : new Promise((ok) => { img.onload = img.onerror = ok; }))));
    });
    const arquivo = `dist/pdf/${c.slug}-v${c.versao}${c.rascunho ? '-rascunho' : ''}.pdf`;
    // modo PDF (páginas 390×844 do @page "movel"), tema claro e texto do rodapé
    await pagina.evaluate((t) => {
      const raiz = document.documentElement;
      raiz.classList.add('modo-pdf');
      raiz.dataset.tema = 'claro';
      raiz.style.setProperty('--rodape-esq', JSON.stringify(t));
    }, `${c.setor ?? c.titulo} · versão ${c.versao}${c.rascunho ? ' (rascunho)' : ''} · croqui pessoal`);
    await pagina.evaluate(() => document.fonts.ready);
    await pagina.pdf({ path: arquivo, printBackground: true, preferCSSPageSize: true });
    console.log('PDF gerado:', arquivo);
  }
  await navegador.close();
} finally {
  servidor.close();
}
