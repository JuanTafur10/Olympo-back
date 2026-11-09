import { randomUUID } from "node:crypto";
import type { RequestHandler } from "express";
import { getRouteParam } from "../utils/route-param.js";
import type { Prisma } from "../generated/prisma/client.js";
import { prisma } from "../config/database.js";
import { HttpError } from "../errors/http-error.js";
import { uploadProjectImageFile } from "../services/storage.service.js";
import { paginationFromQuery } from "../utils/pagination.js";
import { projectCreateSchema, projectListSchema, projectUpdateSchema } from "../validation/domain.schemas.js";

const slugFor = (title: string) =>
  title.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") + "-" + randomUUID().slice(0, 8);

const requireActiveCategory = async (categoryId: string) => {
  const category = await prisma.category.findFirst({
    where: { id: categoryId, status: "ACTIVE" },
    select: { id: true },
  });
  if (!category) throw new HttpError(400, "Selecciona una categoría activa.");
};

export const listProjects: RequestHandler = async (request, response) => {
  const filters = projectListSchema.parse(request.query);
  const pagination = paginationFromQuery(request.query);
  const search = filters.q
    ? { OR: [{ title: { contains: filters.q, mode: "insensitive" as const } }, { description: { contains: filters.q, mode: "insensitive" as const } }] }
    : {};
  const visibility = request.user?.role === "ADMIN"
    ? {}
    : request.user?.role === "OWNER"
      ? { OR: [{ status: "PUBLISHED" as const }, { ownerId: request.user.id }] }
      : { status: "PUBLISHED" as const };
  const where: Prisma.ProjectWhereInput = {
    AND: [
      { status: { not: "DELETED" } },
      visibility,
      search,
      ...(filters.categoryId ? [{ categoryId: filters.categoryId }] : []),
      ...(filters.status ? [{ status: filters.status }] : []),
    ],
  };

  const [total, data] = await Promise.all([
    prisma.project.count({ where }),
    prisma.project.findMany({
      where,
      include: {
        category: true,
        owner: { select: { id: true, name: true } },
      },
      orderBy: { createdAt: "desc" },
      skip: (pagination.currentPage - 1) * pagination.limit,
      take: pagination.limit,
    }),
  ]);

  response.json({
    data,
    pagination: { ...pagination, total, totalPages: Math.ceil(total / pagination.limit) },
  });
};

export const getProject: RequestHandler = async (request, response) => {
  const project = await prisma.project.findUnique({
    where: { id: getRouteParam(request, "id") },
    include: { category: true, owner: { select: { id: true, name: true } } },
  });
  if (!project || project.status === "DELETED") throw new HttpError(404, "No se encontró el proyecto.");
  const canSeeDraft = request.user?.role === "ADMIN"
    || (request.user?.role === "OWNER" && request.user.id === project.ownerId);
  if (project.status !== "PUBLISHED" && !canSeeDraft) {
    throw new HttpError(404, "No se encontró el proyecto.");
  }
  response.json({ data: project });
};

export const createProject: RequestHandler = async (request, response) => {
  const input = projectCreateSchema.parse(request.body);
  await requireActiveCategory(input.categoryId);
  const project = await prisma.project.create({
    data: {
      ...input,
      targetAmount: input.targetAmount,
      ownerId: request.user!.id,
      slug: slugFor(input.title),
    },
    include: { category: true },
  });
  response.status(201).json({ data: project });
};

const getEditableProject = async (projectId: string, userId: string, role: string) => {
  const project = await prisma.project.findUnique({ where: { id: projectId } });
  if (!project) throw new HttpError(404, "No se encontró el proyecto.");
  if (project.status === "DELETED") throw new HttpError(404, "No se encontró el proyecto.");
  if (role !== "ADMIN" && project.ownerId !== userId) {
    throw new HttpError(403, "Solo puedes gestionar los proyectos que creaste.");
  }
  return project;
};

export const updateProject: RequestHandler = async (request, response) => {
  const input = projectUpdateSchema.parse(request.body);
  await getEditableProject(getRouteParam(request, "id"), request.user!.id, request.user!.role);
  if (input.categoryId) await requireActiveCategory(input.categoryId);
  const project = await prisma.project.update({
    where: { id: getRouteParam(request, "id") },
    data: {
      ...input,
      ...(input.title ? { slug: slugFor(input.title) } : {}),
    },
    include: { category: true },
  });
  response.json({ data: project });
};

export const deleteProject: RequestHandler = async (request, response) => {
  await getEditableProject(getRouteParam(request, "id"), request.user!.id, request.user!.role);
  await prisma.$transaction(async (transaction) => {
    await transaction.investmentRequest.updateMany({
      where: { projectId: getRouteParam(request, "id"), status: { not: "DELETED" } },
      data: { status: "DELETED" },
    });
    await transaction.project.update({
      where: { id: getRouteParam(request, "id") },
      data: { status: "DELETED" },
    });
  });
  response.status(204).send();
};

export const uploadProjectImage: RequestHandler = async (request, response) => {
  if (!request.file) throw new HttpError(400, "Adjunta el archivo en el campo image.");
  await getEditableProject(getRouteParam(request, "id"), request.user!.id, request.user!.role);
  const imageUrl = await uploadProjectImageFile(getRouteParam(request, "id"), request.file);
  const project = await prisma.project.update({
    where: { id: getRouteParam(request, "id") },
    data: { imageUrl },
    include: { category: true },
  });
  response.json({ data: project });
};

export const requireProjectOwner = getEditableProject;
