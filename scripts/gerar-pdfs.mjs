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
  const pagina = await navegador.newPage();
  for (const c of croquis) {
    await pagina.goto(`${raiz}/croquis/${c.slug}/`, { waitUntil: 'networkidle' });
    // imagens com loading=lazy não carregam sozinhas na impressão
    await pagina.evaluate(async () => {
      document.querySelectorAll('img[loading="lazy"]').forEach((img) => (img.loading = 'eager'));
      await Promise.all([...document.images].map((img) => (img.complete ? null : new Promise((ok) => { img.onload = img.onerror = ok; }))));
    });
    const arquivo = `dist/pdf/${c.slug}-v${c.versao}${c.rascunho ? '-rascunho' : ''}.pdf`;
    // texto do rodapé vem do título do croqui (as margens e a numeração estão no @page da página)
    await pagina.evaluate((t) => document.documentElement.style.setProperty('--rodape-esq', JSON.stringify(t)), `${c.titulo} — versão ${c.versao}${c.rascunho ? ' (rascunho)' : ''} · croqui pessoal, não oficial`);
    await pagina.pdf({
      path: arquivo,
      format: 'A4',
      printBackground: true,
      preferCSSPageSize: true, // margens vêm do @page da página (a capa sai sem margem)
    });
    console.log('PDF gerado:', arquivo);
  }
  await navegador.close();
} finally {
  servidor.close();
}
