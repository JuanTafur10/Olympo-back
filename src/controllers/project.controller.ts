import { randomUUID } from "node:crypto";
import type { RequestHandler } from "express";
import type { Prisma } from "../generated/prisma/client.js";
import { prisma } from "../config/database.js";
import { HttpError } from "../errors/http-error.js";
import { uploadProjectImageFile } from "../services/storage.service.js";
import { paginationFromQuery } from "../utils/pagination.js";
import { projectCreateSchema, projectListSchema, projectUpdateSchema } from "../validation/domain.schemas.js";

const slugFor = (title: string) =>
  title.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") + "-" + randomUUID().slice(0, 8);

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
    where: { id: request.params.id },
    include: { category: true, owner: { select: { id: true, name: true } } },
  });
  if (!project) throw new HttpError(404, "No se encontró el proyecto.");
  const canSeeDraft = request.user?.role === "ADMIN"
    || (request.user?.role === "OWNER" && request.user.id === project.ownerId);
  if (project.status !== "PUBLISHED" && !canSeeDraft) {
    throw new HttpError(404, "No se encontró el proyecto.");
  }
  response.json({ data: project });
};

export const createProject: RequestHandler = async (request, response) => {
  const input = projectCreateSchema.parse(request.body);
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
  if (role !== "ADMIN" && project.ownerId !== userId) {
    throw new HttpError(403, "Solo puedes gestionar los proyectos que creaste.");
  }
  return project;
};

export const updateProject: RequestHandler = async (request, response) => {
  const input = projectUpdateSchema.parse(request.body);
  await getEditableProject(request.params.id, request.user!.id, request.user!.role);
  const project = await prisma.project.update({
    where: { id: request.params.id },
    data: {
      ...input,
      ...(input.title ? { slug: slugFor(input.title) } : {}),
    },
    include: { category: true },
  });
  response.json({ data: project });
};

export const deleteProject: RequestHandler = async (request, response) => {
  await getEditableProject(request.params.id, request.user!.id, request.user!.role);
  await prisma.project.delete({ where: { id: request.params.id } });
  response.status(204).send();
};

export const uploadProjectImage: RequestHandler = async (request, response) => {
  if (!request.file) throw new HttpError(400, "Adjunta el archivo en el campo image.");
  await getEditableProject(request.params.id, request.user!.id, request.user!.role);
  const imageUrl = await uploadProjectImageFile(request.params.id, request.file);
  const project = await prisma.project.update({
    where: { id: request.params.id },
    data: { imageUrl },
    include: { category: true },
  });
  response.json({ data: project });
};

export const requireProjectOwner = getEditableProject;
