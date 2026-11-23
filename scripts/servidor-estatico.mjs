/** Servidor HTTP mínimo que serve dist/ sob o base do site (usado para gerar PDFs e testar). */
import { createServer } from 'node:http';
import { createReadStream, existsSync, statSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';

const TIPOS = {
  '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json',
  '.svg': 'image/svg+xml', '.webp': 'image/webp', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
  '.xml': 'application/xml', '.txt': 'text/plain', '.pdf': 'application/pdf',
  '.webmanifest': 'application/manifest+json', '.woff2': 'font/woff2',
};

export function servir({ pasta = 'dist', base = '/', porta = 4329 } = {}) {
  const prefixo = base.replace(/\/$/, '');
  const servidor = createServer((req, res) => {
    let caminho = decodeURIComponent(new URL(req.url, 'http://x').pathname);
    if (prefixo && caminho.startsWith(prefixo)) caminho = caminho.slice(prefixo.length) || '/';
    let arquivo = normalize(join(pasta, caminho));
    if (existsSync(arquivo) && statSync(arquivo).isDirectory()) arquivo = join(arquivo, 'index.html');
    if (!arquivo.startsWith(normalize(pasta)) || !existsSync(arquivo)) {
      res.writeHead(404).end('404');
      return;
    }
    res.writeHead(200, { 'content-type': TIPOS[extname(arquivo)] ?? 'application/octet-stream' });
    createReadStream(arquivo).pipe(res);
  });
  return new Promise((ok) => servidor.listen(porta, '127.0.0.1', () => ok(servidor)));
}
