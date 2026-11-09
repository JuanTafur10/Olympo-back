import { randomUUID } from "node:crypto";
import type { RequestHandler } from "express";
import { prisma } from "../config/database.js";
import { HttpError } from "../errors/http-error.js";
import { paginationFromQuery } from "../utils/pagination.js";
import { categoryCreateSchema, categoryUpdateSchema } from "../validation/domain.schemas.js";

const slugFor = (name: string) =>
  name.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") + "-" + randomUUID().slice(0, 6);

export const listCategories: RequestHandler = async (request, response) => {
  const pagination = paginationFromQuery(request.query);
  const where = { status: "ACTIVE" as const };
  const [total, data] = await Promise.all([
    prisma.category.count({ where }),
    prisma.category.findMany({
      where,
      include: { _count: { select: { projects: true } } },
      orderBy: { name: "asc" },
      skip: (pagination.currentPage - 1) * pagination.limit,
      take: pagination.limit,
    }),
  ]);
  response.json({
    data,
    pagination: { ...pagination, total, totalPages: Math.ceil(total / pagination.limit) },
  });
};

export const getCategory: RequestHandler = async (request, response) => {
  const category = await prisma.category.findFirst({
    where: { id: request.params.id, status: "ACTIVE" },
  });
  if (!category) throw new HttpError(404, "No se encontró la categoría.");
  response.json({ data: category });
};

export const createCategory: RequestHandler = async (request, response) => {
  const input = categoryCreateSchema.parse(request.body);
  const category = await prisma.category.create({
    data: { ...input, slug: slugFor(input.name) },
  });
  response.status(201).json({ data: category });
};

export const updateCategory: RequestHandler = async (request, response) => {
  const input = categoryUpdateSchema.parse(request.body);
  const current = await prisma.category.findFirst({
    where: { id: request.params.id, status: "ACTIVE" },
  });
  if (!current) throw new HttpError(404, "No se encontró la categoría.");
  const category = await prisma.category.update({
    where: { id: request.params.id },
    data: {
      ...input,
      ...(input.name ? { slug: slugFor(input.name) } : {}),
    },
  });
  response.json({ data: category });
};

export const deleteCategory: RequestHandler = async (request, response) => {
  const category = await prisma.category.findFirst({
    where: { id: request.params.id, status: "ACTIVE" },
  });
  if (!category) throw new HttpError(404, "No se encontró la categoría.");
  const projectCount = await prisma.project.count({
    where: { categoryId: category.id, status: { not: "DELETED" } },
  });
  if (projectCount > 0) {
    throw new HttpError(409, "La categoría tiene proyectos activos y no se puede desactivar.");
  }
  await prisma.category.update({
    where: { id: category.id },
    data: { status: "INACTIVE" },
  });
  response.status(204).send();
};
