/*
 * Service worker do Momontanha: deixa o site instalável e usável offline.
 * - Páginas: rede primeiro; sem internet, usa a cópia salva; sem cópia, mostra /offline/.
 * - Arquivos (CSS, JS, fotos, fontes, PDFs): cópia salva primeiro; senão rede (e guarda).
 * - Croquis salvos pelo botão "Salvar no celular" ficam em caches próprios (momontanha-croqui-<slug>),
 *   gravados pela página (src/lib/offline.ts); aqui só são lidos.
 * Ao mudar este arquivo, suba VERSAO para renovar a casca do app.
 */
const VERSAO = 'v1';
const BASE = new URL(self.registration.scope).pathname;
const CACHE_APP = `momontanha-app-${VERSAO}`;
const CACHE_RUNTIME = 'momontanha-runtime';
const LIMITE_RUNTIME = 200;
const PAGINAS_CASCA = [BASE, `${BASE}offline/`];
const EXTRAS = ['manifest.webmanifest', 'favicon.svg', 'icones/icone-192.png', 'icones/icone-512.png'].map((f) => BASE + f);

async function precache() {
  const cache = await caches.open(CACHE_APP);
  const arquivos = new Set(EXTRAS);
  for (const pagina of PAGINAS_CASCA) {
    const resposta = await fetch(pagina, { cache: 'no-cache' });
    if (!resposta.ok) continue;
    await cache.put(pagina, resposta.clone());
    const html = await resposta.text();
    for (const m of html.matchAll(/(?:src|href)="([^"#]+\.(?:css|js|png|jpe?g|webp|svg))"/g)) {
      const u = new URL(m[1].replace(/&amp;/g, '&'), self.location.origin + pagina);
      if (u.origin === self.location.origin) arquivos.add(u.href);
    }
  }
  for (const css of [...arquivos].filter((u) => u.endsWith('.css'))) {
    try {
      const texto = await (await fetch(css)).text();
      for (const m of texto.matchAll(/url\(["']?([^"')]+\.woff2)["']?\)/g)) {
        const u = new URL(m[1], css);
        if (/latin/.test(u.pathname)) arquivos.add(u.href);
      }
    } catch {}
  }
  await Promise.all([...arquivos].map((u) => cache.add(u).catch(() => {})));
}

self.addEventListener('install', (e) => e.waitUntil(precache().then(() => self.skipWaiting())));

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((nomes) => Promise.all(nomes.filter((n) => n.startsWith('momontanha-app-') && n !== CACHE_APP).map((n) => caches.delete(n))))
      .then(() => self.clients.claim()),
  );
});

async function guardar(req, resposta) {
  const cache = await caches.open(CACHE_RUNTIME);
  await cache.put(req, resposta);
  const chaves = await cache.keys();
  if (chaves.length > LIMITE_RUNTIME) await Promise.all(chaves.slice(0, chaves.length - LIMITE_RUNTIME).map((k) => cache.delete(k)));
}

async function paginaRedePrimeiro(e) {
  const req = e.request;
  try {
    const resposta = await fetch(req);
    if (resposta.ok) e.waitUntil(guardar(req, resposta.clone()));
    return resposta;
  } catch {
    return (await caches.match(req, { ignoreSearch: true }))
      || (await caches.match(`${BASE}offline/`))
      || new Response('<h1>Sem conexão</h1>', { status: 503, headers: { 'content-type': 'text/html; charset=utf-8' } });
  }
}

async function arquivoCachePrimeiro(e) {
  const req = e.request;
  const salvo = await caches.match(req, { ignoreSearch: true });
  if (salvo) return salvo;
  try {
    const resposta = await fetch(req);
    if (resposta.ok && resposta.type === 'basic' && resposta.status === 200) e.waitUntil(guardar(req, resposta.clone()));
    return resposta;
  } catch {
    return new Response('', { status: 504 });
  }
}

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const u = new URL(req.url);
  if (u.origin !== self.location.origin) return;
  if (req.mode === 'navigate') e.respondWith(paginaRedePrimeiro(e));
  else e.respondWith(arquivoCachePrimeiro(e));
});
