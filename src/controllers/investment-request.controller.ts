import type { RequestHandler } from "express";
import { getRouteParam } from "../utils/route-param.js";
import type { Prisma } from "../generated/prisma/client.js";
import { prisma } from "../config/database.js";
import { HttpError } from "../errors/http-error.js";
import { paginationFromQuery } from "../utils/pagination.js";
import {
  investmentRequestCreateSchema,
  investmentRequestUpdateSchema,
} from "../validation/domain.schemas.js";

export const listInvestmentRequests: RequestHandler = async (request, response) => {
  const pagination = paginationFromQuery(request.query);
  const where: Prisma.InvestmentRequestWhereInput = request.user!.role === "ADMIN"
    ? {}
    : request.user!.role === "OWNER"
      ? { project: { ownerId: request.user!.id } }
      : { investorId: request.user!.id };
  const activeWhere: Prisma.InvestmentRequestWhereInput = {
    AND: [where, { status: { not: "DELETED" } }],
  };
  const [total, data] = await Promise.all([
    prisma.investmentRequest.count({ where: activeWhere }),
    prisma.investmentRequest.findMany({
      where: activeWhere,
      include: {
        project: { select: { id: true, title: true, imageUrl: true, ownerId: true } },
        investor: { select: { id: true, name: true } },
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

export const getInvestmentRequest: RequestHandler = async (request, response) => {
  const item = await prisma.investmentRequest.findUnique({
    where: { id: getRouteParam(request, "id") },
    include: {
      project: { select: { id: true, title: true, imageUrl: true, ownerId: true } },
      investor: { select: { id: true, name: true } },
    },
  });
  if (!item || item.status === "DELETED") throw new HttpError(404, "No se encontró la solicitud.");
  const canSee = request.user!.role === "ADMIN"
    || item.investorId === request.user!.id
    || item.project.ownerId === request.user!.id;
  if (!canSee) throw new HttpError(403, "No tienes permiso para ver esta solicitud.");
  response.json({ data: item });
};

export const createInvestmentRequest: RequestHandler = async (request, response) => {
  const input = investmentRequestCreateSchema.parse(request.body);
  const project = await prisma.project.findUnique({ where: { id: input.projectId } });
  if (!project || project.status !== "PUBLISHED") throw new HttpError(404, "No se encontró un proyecto publicado.");
  if (project.ownerId === request.user!.id) throw new HttpError(400, "No puedes enviar una solicitud a tu propio proyecto.");

  const item = await prisma.investmentRequest.create({
    data: { ...input, investorId: request.user!.id },
    include: { project: { select: { id: true, title: true } } },
  });
  response.status(201).json({ data: item });
};

export const updateInvestmentRequest: RequestHandler = async (request, response) => {
  const input = investmentRequestUpdateSchema.parse(request.body);
  const current = await prisma.investmentRequest.findUnique({
    where: { id: getRouteParam(request, "id") },
    include: { project: { select: { ownerId: true } } },
  });
  if (!current || current.status === "DELETED") throw new HttpError(404, "No se encontró la solicitud.");

  const isAdmin = request.user!.role === "ADMIN";
  const isInvestor = current.investorId === request.user!.id;
  const isProjectOwner = current.project.ownerId === request.user!.id;
  if (!isAdmin && !isInvestor && !isProjectOwner) throw new HttpError(403, "No tienes permiso para cambiar esta solicitud.");

  let data: Prisma.InvestmentRequestUncheckedUpdateInput;
  if (isAdmin) {
    data = { ...input, ...(input.status ? { reviewerId: request.user!.id } : {}) };
  } else if (isProjectOwner) {
    if (!input.status || input.status === "WITHDRAWN" || input.amount !== undefined || input.message !== undefined) {
      throw new HttpError(400, "Como propietario solo puedes aprobar o rechazar la solicitud.");
    }
    data = { status: input.status, reviewerId: request.user!.id };
  } else {
    if (
      current.status !== "PENDING"
      || (input.status && input.status !== "WITHDRAWN")
      || (input.status === "WITHDRAWN" && (input.amount !== undefined || input.message !== undefined))
      || (!input.status && input.amount === undefined && input.message === undefined)
    ) {
      throw new HttpError(400, "Solo puedes editar una solicitud pendiente o retirarla.");
    }
    data = { amount: input.amount, message: input.message, status: input.status };
  }

  const item = await prisma.investmentRequest.update({
    where: { id: getRouteParam(request, "id") },
    data,
    include: { project: { select: { id: true, title: true } } },
  });
  response.json({ data: item });
};

export const deleteInvestmentRequest: RequestHandler = async (request, response) => {
  const current = await prisma.investmentRequest.findUnique({
    where: { id: getRouteParam(request, "id") },
    include: { project: { select: { ownerId: true } } },
  });
  if (!current || current.status === "DELETED") throw new HttpError(404, "No se encontró la solicitud.");
  const canDelete = request.user!.role === "ADMIN"
    || current.project.ownerId === request.user!.id
    || (current.investorId === request.user!.id && current.status === "PENDING");
  if (!canDelete) throw new HttpError(403, "No tienes permiso para eliminar esta solicitud.");
  await prisma.investmentRequest.update({
    where: { id: getRouteParam(request, "id") },
    data: { status: "DELETED" },
  });
  response.status(204).send();
};
