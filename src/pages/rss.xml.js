import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';

export async function GET(context) {
  const relatos = (await getCollection('relatos', (r) => !r.data.rascunho)).sort(
    (a, b) => b.data.data.getTime() - a.data.data.getTime(),
  );
  const base = import.meta.env.BASE_URL.replace(/\/$/, '');
  return rss({
    title: 'Momontanha',
    description: 'Relatos de trilhas, travessias e escaladas nas serras do Paraná.',
    site: context.site,
    items: relatos.map((r) => ({
      title: r.data.titulo,
      pubDate: r.data.data,
      description: r.data.resumo,
      link: `${base}/relatos/${r.id}/`,
    })),
  });
}
