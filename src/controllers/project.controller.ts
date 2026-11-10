import type { RequestHandler } from "express";
import { getRouteParam } from "../utils/route-param.js";
import { prisma } from "../config/database.js";
import { ListProjects } from "../application/use-cases/list-projects.js";
import { CreateProject } from "../application/use-cases/create-project.js";
import { UpdateProject } from "../application/use-cases/update-project.js";
import { DeleteProject } from "../application/use-cases/delete-project.js";
import { UploadProjectImage } from "../application/use-cases/upload-project-image.js";
import { prismaProjectRepository } from "../infrastructure/repository/prisma-project.repository.js";
import { HttpError } from "../errors/http-error.js";
import { uploadProjectImageFile } from "../services/storage.service.js";
import { paginationFromQuery } from "../utils/pagination.js";
import { projectCreateSchema, projectListSchema, projectUpdateSchema } from "../validation/domain.schemas.js";

const createProjectUseCase = new CreateProject(prismaProjectRepository);
const updateProjectUseCase = new UpdateProject(prismaProjectRepository);
const deleteProjectUseCase = new DeleteProject(prismaProjectRepository);
const uploadProjectImageUseCase = new UploadProjectImage(prismaProjectRepository, {
  upload: uploadProjectImageFile,
});

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
  await deleteProjectUseCase.execute(
    getRouteParam(request, "id"),
    request.user!.id,
    request.user!.role,
  );
  response.status(204).send();
};

export const uploadProjectImage: RequestHandler = async (request, response) => {
  if (!request.file) throw new HttpError(400, "Adjunta el archivo en el campo image.");
  const project = await uploadProjectImageUseCase.execute(
    getRouteParam(request, "id"),
    request.file,
    request.user!.id,
    request.user!.role,
  );
  response.json({ data: project });
};
