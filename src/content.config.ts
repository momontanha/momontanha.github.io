import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

/** Relatos do blog: trilhas, travessias e escaladas. */
const relatos = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/relatos' }),
  schema: ({ image }) =>
    z.object({
      titulo: z.string(),
      data: z.coerce.date(),
      resumo: z.string().optional(),
      capa: image().optional(),
      tags: z.array(z.string()).default([]),
      wp_url: z.string().url().optional(),
      rascunho: z.boolean().default(false),
    }),
});

const tipoLink = z.enum(['drive', 'pdf', 'guia', 'wikiloc', 'mapa', 'fotos', 'instagram', 'formulario', 'externo']);

/** Croquiteca: um verbete por setor/montanha, com links para croquis, guias e acesso. */
const croquiteca = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/croquiteca' }),
  schema: ({ image }) =>
    z.object({
      nome: z.string(),
      regiao: z.string(),
      tipo: z.string(),
      capa: image().optional(),
      coordenadas: z.tuple([z.number(), z.number()]).optional(),
      /** slug de um croqui próprio em src/content/croquis/ */
      croqui: z.string().optional(),
      links: z
        .array(z.object({ rotulo: z.string(), url: z.string().url(), tipo: tipoLink }))
        .default([]),
      tags: z.array(z.string()).default([]),
      atualizado: z.coerce.date().optional(),
      wp_url: z.string().url().optional(),
    }),
});

const linha = z.object({
  /** número da linha no croqui (aparece na foto e na tabela) */
  n: z.number().int().optional(),
  nome: z.string(),
  /** grau como escrito no croqui: "V4", "V6/7", "projeto", "7a" */
  grau: z.string(),
  saida: z.enum(['em pé', 'sentado']).optional(),
  conquista: z.string().optional(),
  ano: z.union([z.number(), z.string()]).optional(),
  descricao: z.string().optional(),
  /** pontos da linha sobre a foto, em % da largura e da altura: "12,95 18,70 25,40" */
  traco: z.string().optional(),
  /** de onde veio a informação, quando não é do autor */
  fonte: z.string().optional(),
});

/** Croquis próprios: dados estruturados que viram página web e PDF versionado. */
const croquis = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/croquis' }),
  schema: ({ image }) =>
    z.object({
      titulo: z.string(),
      setor: z.string(),
      regiao: z.string(),
      municipio: z.string(),
      tipo: z.string(),
      versao: z.string(),
      atualizado: z.coerce.date(),
      rascunho: z.boolean().default(false),
      capa: image().optional(),
      capa_credito: z.string().optional(),
      coordenadas: z.tuple([z.number(), z.number()]).optional(),
      escala: z.string().default('V (Hueco)'),
      creditos: z.array(z.string()).default([]),
      subsetores: z.array(
        z.object({
          nome: z.string(),
          descricao: z.string().optional(),
          blocos: z.array(
            z.object({
              nome: z.string(),
              descricao: z.string().optional(),
              foto: image().optional(),
              foto_credito: z.string().optional(),
              linhas: z.array(linha).default([]),
            }),
          ),
        }),
      ),
      historico: z.array(z.object({ versao: z.string(), data: z.coerce.date(), mudancas: z.string() })),
    }),
});

const paginas = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/paginas' }),
  schema: ({ image }) =>
    z.object({
      titulo: z.string(),
      foto: image().optional(),
      foto_legenda: z.string().optional(),
      wp_url: z.string().url().optional(),
    }),
});

export const collections = { relatos, croquiteca, croquis, paginas };
