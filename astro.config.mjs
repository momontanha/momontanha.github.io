// @ts-check
import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';
import { readdirSync, readFileSync } from 'node:fs';

// Endereço do site. Enquanto não tiver domínio próprio, fica no GitHub Pages:
//   https://momontanha.github.io/  (repositório momontanha/momontanha.github.io)
// Com domínio (ex.: momontanha.com), basta definir SITE_URL=https://momontanha.com e BASE_PATH=/
const site = process.env.SITE_URL ?? 'https://momontanha.github.io';
const base = process.env.BASE_PATH ?? '/';

// Croquis marcados como rascunho ficam fora do sitemap (e a página leva noindex).
const rascunhos = readdirSync('./src/content/croquis')
  .filter((f) => f.endsWith('.md') && /^rascunho:\s*true/m.test(readFileSync(`./src/content/croquis/${f}`, 'utf8')))
  .map((f) => `/croquis/${f.replace(/\.md$/, '')}/`);

export default defineConfig({
  site,
  base,
  trailingSlash: 'always',
  integrations: [
    sitemap({
      // rascunhos de croqui não entram no sitemap
      filter: (page) => !rascunhos.some((r) => page.endsWith(r)),
    }),
  ],
});
