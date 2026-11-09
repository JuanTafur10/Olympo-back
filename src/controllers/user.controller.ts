import type { RequestHandler } from "express";
import { getRouteParam } from "../utils/route-param.js";
import { prisma } from "../config/database.js";
import { HttpError } from "../errors/http-error.js";
import { updateUserSchema } from "../validation/auth.schemas.js";
import { paginationFromQuery } from "../utils/pagination.js";

export const listUsers: RequestHandler = async (request, response) => {
  const pagination = paginationFromQuery(request.query);
  const [total, users] = await Promise.all([
    prisma.user.count(),
    prisma.user.findMany({
      select: { id: true, name: true, email: true, role: true, status: true, createdAt: true },
      orderBy: { createdAt: "desc" },
      skip: (pagination.currentPage - 1) * pagination.limit,
      take: pagination.limit,
    }),
  ]);
  response.json({
    data: users,
    pagination: { ...pagination, total, totalPages: Math.ceil(total / pagination.limit) },
  });
};

export const getMe: RequestHandler = async (request, response) => {
  const user = await prisma.user.findUnique({
    where: { id: request.user!.id },
    select: { id: true, name: true, email: true, role: true, status: true, createdAt: true },
  });
  if (!user) throw new HttpError(404, "No se encontró el usuario.");
  response.json({ data: user });
};

export const getUser: RequestHandler = async (request, response) => {
  const user = await prisma.user.findUnique({
    where: { id: getRouteParam(request, "id") },
    select: { id: true, name: true, email: true, role: true, status: true, createdAt: true },
  });
  if (!user) throw new HttpError(404, "No se encontró el usuario.");
  response.json({ data: user });
};

export const updateUser: RequestHandler = async (request, response) => {
  const input = updateUserSchema.parse(request.body);
  const isAdmin = request.user!.role === "ADMIN";
  const isSelf = request.user!.id === getRouteParam(request, "id");
  if (!isAdmin && !isSelf) throw new HttpError(403, "Solo puedes editar tu propio perfil.");
  if (!isAdmin && input.role) throw new HttpError(403, "Solo administración puede cambiar roles.");

  const user = await prisma.user.update({
    where: { id: getRouteParam(request, "id") },
    data: isAdmin ? input : { name: input.name, email: input.email },
    select: { id: true, name: true, email: true, role: true, createdAt: true },
  });
  response.json({ data: user });
};

export const deleteUser: RequestHandler = async (request, response) => {
  if (request.user!.id === getRouteParam(request, "id")) throw new HttpError(400, "No puedes eliminar tu propia cuenta de administración.");
  await prisma.$transaction(async (transaction) => {
    const ownedProjects = await transaction.project.findMany({
      where: { ownerId: getRouteParam(request, "id"), status: { not: "DELETED" } },
      select: { id: true },
    });
    const projectIds = ownedProjects.map((project) => project.id);
    await transaction.investmentRequest.updateMany({
      where: {
        OR: [
          { investorId: getRouteParam(request, "id") },
          ...(projectIds.length > 0 ? [{ projectId: { in: projectIds } }] : []),
        ],
        status: { not: "DELETED" },
      },
      data: { status: "DELETED" },
    });
    await transaction.project.updateMany({
      where: { ownerId: getRouteParam(request, "id"), status: { not: "DELETED" } },
      data: { status: "DELETED" },
    });
    await transaction.user.update({
      where: { id: getRouteParam(request, "id") },
      data: { status: "INACTIVE" },
    });
  });
  response.status(204).send();
};
