import type { RequestHandler } from "express";
import { getRouteParam } from "../utils/route-param.js";
import type { Prisma } from "../generated/prisma/client.js";
import { ListInvestmentRequests } from "../application/use-cases/list-investment-requests.js";
import { prismaInvestmentRequestRepository } from "../infrastructure/repository/prisma-investment-request.repository.js";
import { prisma } from "../config/database.js";
import { HttpError } from "../errors/http-error.js";
import { paginationFromQuery } from "../utils/pagination.js";
import {
  investmentRequestCreateSchema,
  investmentRequestUpdateSchema,
} from "../validation/domain.schemas.js";

const listInvestmentRequestsUseCase = new ListInvestmentRequests(prismaInvestmentRequestRepository);

export const listInvestmentRequests: RequestHandler = async (request, response) => {
  const pagination = paginationFromQuery(request.query);
  const result = await listInvestmentRequestsUseCase.execute({
    pagination,
    viewer: { id: request.user!.id, role: request.user!.role },
  });
  response.json(result);
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
  await prisma.notification.create({
    data: {
      userId: project.ownerId,
      title: "Nueva solicitud de inversión",
      message: `Recibiste una solicitud para el proyecto ${project.title}.`,
      type: "investment_request",
      routeDestination: "/solicitudes",
      metadata: { investmentRequestId: item.id, projectId: project.id },
    },
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
    if (
      current.status !== "PENDING"
      || !input.status
      || input.status === "WITHDRAWN"
      || input.amount !== undefined
      || input.message !== undefined
    ) {
      throw new HttpError(400, "Como propietario solo puedes aprobar o rechazar solicitudes pendientes.");
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
  if (input.status && input.status !== current.status && (input.status === "APPROVED" || input.status === "REJECTED")) {
    await prisma.notification.create({
      data: {
        userId: current.investorId,
        title: input.status === "APPROVED" ? "Solicitud aprobada" : "Solicitud rechazada",
        message: `El propietario actualizó tu solicitud para ${item.project.title}.`,
        type: "investment_request",
        routeDestination: "/solicitudes",
        metadata: { investmentRequestId: item.id },
      },
    });
  }
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
