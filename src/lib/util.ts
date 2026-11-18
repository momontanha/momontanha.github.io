/** Monta um caminho interno respeitando o base do site (ex.: /momontanha/). */
export function url(caminho = '/'): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  const p = caminho.startsWith('/') ? caminho : `/${caminho}`;
  return `${base}${p}`;
}

export function dataBR(d: Date): string {
  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric', timeZone: 'UTC' });
}

export function slugify(s: string): string {
  return s
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '');
}

/** Faixa de dificuldade de um grau V, usada para colorir as linhas. */
export function faixaGrau(grau: string): 'facil' | 'medio' | 'dificil' | 'muito-dificil' | 'projeto' {
  const g = grau.toLowerCase();
  if (g.includes('proj')) return 'projeto';
  const m = g.match(/v(\d+)/);
  if (!m) return 'medio';
  const v = Number(m[1]);
  if (v <= 2) return 'facil';
  if (v <= 5) return 'medio';
  if (v <= 8) return 'dificil';
  return 'muito-dificil';
}

export const CORES_FAIXA: Record<string, string> = {
  facil: '#2e9e4f',
  medio: '#1f6fd1',
  dificil: '#d6312b',
  'muito-dificil': '#111111',
  projeto: '#8a8a8a',
};

export const ROTULO_LINK: Record<string, string> = {
  drive: 'Google Drive',
  pdf: 'PDF',
  guia: 'Guia (comprar)',
  wikiloc: 'Acesso no Wikiloc',
  mapa: 'Mapa',
  fotos: 'Álbum de fotos',
  instagram: 'Instagram',
  formulario: 'Formulário',
  '8a': 'Cadenas no 8a.nu',
  externo: 'Link',
};
