import { getCollection } from 'astro:content';

/** Lista dos croquis próprios, usada pelo script que gera os PDFs. */
export async function GET() {
  const croquis = await getCollection('croquis');
  return Response.json(
    croquis.map((c) => ({ slug: c.id, titulo: c.data.titulo, versao: c.data.versao, rascunho: c.data.rascunho })),
  );
}
