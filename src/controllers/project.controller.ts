import type { RequestHandler } from "express";
import { getRouteParam } from "../utils/route-param.js";
import { prisma } from "../config/database.js";
import { ListProjects } from "../application/use-cases/list-projects.js";
import { CreateProject } from "../application/use-cases/create-project.js";
import { UpdateProject } from "../application/use-cases/update-project.js";
import { prismaProjectRepository } from "../infrastructure/repository/prisma-project.repository.js";
import { HttpError } from "../errors/http-error.js";
import { uploadProjectImageFile } from "../services/storage.service.js";
import { paginationFromQuery } from "../utils/pagination.js";
import { projectCreateSchema, projectListSchema, projectUpdateSchema } from "../validation/domain.schemas.js";

const createProjectUseCase = new CreateProject(prismaProjectRepository);
const updateProjectUseCase = new UpdateProject(prismaProjectRepository);

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
  const viewer = request.user
    ? { id: request.user.id, role: request.user.role }
    : { role: "USER" as const };
  const result = await new ListProjects(prismaProjectRepository).execute({
    pagination,
    viewer,
    q: filters.q,
    categoryId: filters.categoryId,
    status: filters.status,
  });
  response.json(result);
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
  const project = await createProjectUseCase.execute(input, request.user!.id);
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
  const project = await updateProjectUseCase.execute(
    getRouteParam(request, "id"),
    input,
    request.user!.id,
    request.user!.role,
  );
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
