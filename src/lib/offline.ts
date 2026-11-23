/**
 * Croquis salvos no celular (uso offline). Cada croqui salvo fica num cache próprio
 * (momontanha-croqui-<slug>) com a página, fotos, CSS, JS, fontes e o PDF; o service worker
 * (public/sw.js) serve esses arquivos quando não há internet. A lista fica no localStorage.
 */
const CHAVE = 'momontanha-offline';
export interface InfoCroqui { slug: string; titulo: string; versao: string; pagina: string; pdf?: string }
export interface Salvo extends InfoCroqui { salvoEm: string; bytes: number }

const nomeCache = (slug: string) => `momontanha-croqui-${slug}`;
export const suportaOffline = () => typeof window !== 'undefined' && 'caches' in window && 'serviceWorker' in navigator;

export function lerSalvos(): Record<string, Salvo> {
  try { return JSON.parse(localStorage.getItem(CHAVE) || '{}'); } catch { return {}; }
}
function gravarSalvos(s: Record<string, Salvo>) { localStorage.setItem(CHAVE, JSON.stringify(s)); }

/** Dados do croqui salvo, se o cache dele ainda existir. */
export async function salvo(slug: string): Promise<Salvo | null> {
  const s = lerSalvos()[slug];
  if (!s || !suportaOffline()) return null;
  if (await caches.has(nomeCache(slug))) return s;
  const todos = lerSalvos(); delete todos[slug]; gravarSalvos(todos);
  return null;
}

/** Endereços de tudo o que a página usa: ela mesma, CSS, JS, imagens, ícones e fontes (latin). */
async function coletar(pagina: string): Promise<string[]> {
  const base = new URL(pagina, location.href);
  const html = await (await fetch(base, { cache: 'no-cache' })).text();
  const urls = new Set<string>([base.href]);
  const mesmaOrigem = (bruto: string, rel: URL | string) => {
    const u = new URL(bruto.replace(/&amp;/g, '&'), rel);
    return u.origin === location.origin ? u.href : null;
  };
  for (const m of html.matchAll(/(?:src|href)="([^"#]+)"/g)) {
    const u = mesmaOrigem(m[1], base);
    if (u && /\.(css|js|mjs|png|jpe?g|webp|avif|svg|gif|ico|webmanifest)(\?|$)/i.test(u)) urls.add(u);
  }
  for (const m of html.matchAll(/srcset="([^"]+)"/g)) {
    for (const parte of m[1].split(',')) { const u = mesmaOrigem(parte.trim().split(/\s+/)[0], base); if (u) urls.add(u); }
  }
  const fontes = (texto: string, rel: string) => {
    for (const m of texto.matchAll(/url\(["']?([^"')]+\.woff2)["']?\)/g)) {
      const u = mesmaOrigem(m[1], rel);
      if (u && /latin/.test(u)) urls.add(u);
    }
  };
  fontes(html, base.href);
  for (const css of [...urls].filter((u) => /\.css(\?|$)/.test(u))) {
    try { fontes(await (await fetch(css)).text(), css); } catch {}
  }
  return [...urls];
}

/** Salva (ou atualiza) um croqui para uso offline. `aoProgredir` recebe de 0 a 1. */
export async function salvarCroqui(info: InfoCroqui, aoProgredir?: (p: number) => void): Promise<Salvo> {
  if (!suportaOffline()) throw new Error('Este navegador não consegue salvar páginas para uso offline.');
  try { await navigator.storage?.persist?.(); } catch {}
  const urls = await coletar(info.pagina);
  if (info.pdf) urls.push(new URL(info.pdf, location.href).href);
  for (const extra of ['/offline/', '/manifest.webmanifest', '/icones/icone-192.png']) urls.push(new URL(extra, location.origin + import.meta.env.BASE_URL).href);
  const fila = [...new Set(urls)];
  const total = fila.length;
  const temporario = await caches.open(`${nomeCache(info.slug)}-novo`);
  let feitos = 0, bytes = 0;
  async function trabalhador() {
    while (fila.length) {
      const u = fila.shift()!;
      const r = await fetch(u, { cache: 'no-cache' });
      if (!r.ok) throw new Error(`Não consegui baixar ${new URL(u).pathname} (${r.status}).`);
      bytes += (await r.clone().blob()).size;
      await temporario.put(u, r);
      aoProgredir?.(++feitos / total);
    }
  }
  try {
    await Promise.all(Array.from({ length: 4 }, trabalhador));
  } catch (erro) {
    await caches.delete(`${nomeCache(info.slug)}-novo`);
    throw erro;
  }
  // troca a cópia antiga pela nova só depois que tudo baixou
  const definitivo = nomeCache(info.slug);
  await caches.delete(definitivo);
  const cache = await caches.open(definitivo);
  for (const req of await temporario.keys()) await cache.put(req, (await temporario.match(req))!);
  await caches.delete(`${nomeCache(info.slug)}-novo`);
  const dados: Salvo = { ...info, salvoEm: new Date().toISOString(), bytes };
  const todos = lerSalvos(); todos[info.slug] = dados; gravarSalvos(todos);
  return dados;
}

export async function removerCroqui(slug: string) {
  await caches.delete(nomeCache(slug));
  const todos = lerSalvos(); delete todos[slug]; gravarSalvos(todos);
}

export const tamanho = (b: number) => (b > 1e6 ? `${(b / 1e6).toFixed(1).replace('.', ',')} MB` : `${Math.round(b / 1e3)} KB`);

/** Liga os botões [data-offline] (página do croqui e lista offline). */
export function ligarBotoesOffline(raiz: ParentNode = document) {
  raiz.querySelectorAll<HTMLButtonElement>('button[data-offline]').forEach(async (botao) => {
    const info: InfoCroqui = {
      slug: botao.dataset.slug!, titulo: botao.dataset.titulo!, versao: botao.dataset.versao!,
      pagina: botao.dataset.pagina!, pdf: botao.dataset.pdf,
    };
    const titulo = botao.querySelector('.rotulo') as HTMLElement;
    const sub = botao.querySelector('small') as HTMLElement;
    const mostrar = (t: string, s: string, estado: string) => { titulo.textContent = t; sub.textContent = s; botao.dataset.estado = estado; };
    if (!suportaOffline()) { mostrar('Offline indisponível', 'navegador sem suporte', 'erro'); botao.disabled = true; return; }
    const atualizar = async () => {
      const s = await salvo(info.slug);
      if (!s) mostrar('Salvar no celular', 'para usar offline', 'livre');
      else if (s.versao !== info.versao) mostrar('Atualizar offline', `salvo v${s.versao} → v${info.versao}`, 'velho');
      else mostrar('Salvo no celular ✓', `v${s.versao} · ${tamanho(s.bytes)}`, 'salvo');
      botao.dispatchEvent(new CustomEvent('offline-mudou', { bubbles: true }));
    };
    await atualizar();
    botao.addEventListener('click', async () => {
      if (botao.dataset.estado === 'salvo') {
        if (botao.dataset.aoSalvo === 'lista') location.href = new URL('offline/', location.origin + import.meta.env.BASE_URL).href;
        return;
      }
      if (!navigator.onLine) { mostrar('Sem internet', 'conecte para salvar', 'erro'); return; }
      botao.disabled = true;
      try {
        await salvarCroqui(info, (p) => mostrar('Salvando…', `${Math.round(p * 100)}%`, 'salvando'));
      } catch (erro) {
        mostrar('Não deu para salvar', (erro as Error).message.slice(0, 60), 'erro');
        botao.disabled = false;
        return;
      }
      botao.disabled = false;
      await atualizar();
    });
  });
}
