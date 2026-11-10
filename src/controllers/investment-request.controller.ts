import type { RequestHandler } from "express";
import { getRouteParam } from "../utils/route-param.js";
import type { Prisma } from "../generated/prisma/client.js";
import { ListInvestmentRequests } from "../application/use-cases/list-investment-requests.js";
import { GetInvestmentRequest } from "../application/use-cases/get-investment-request.js";
import { CreateInvestmentRequest } from "../application/use-cases/create-investment-request.js";
import { UpdateInvestmentRequest } from "../application/use-cases/update-investment-request.js";
import { prismaInvestmentRequestNotifier } from "../infrastructure/services/prisma-investment-request-notifier.js";
import { prismaInvestmentRequestRepository } from "../infrastructure/repository/prisma-investment-request.repository.js";
import { prisma } from "../config/database.js";
import { HttpError } from "../errors/http-error.js";
import { paginationFromQuery } from "../utils/pagination.js";
import {
  investmentRequestCreateSchema,
  investmentRequestUpdateSchema,
} from "../validation/domain.schemas.js";

const listInvestmentRequestsUseCase = new ListInvestmentRequests(prismaInvestmentRequestRepository);
const getInvestmentRequestUseCase = new GetInvestmentRequest(prismaInvestmentRequestRepository);
const createInvestmentRequestUseCase = new CreateInvestmentRequest(
  prismaInvestmentRequestRepository,
  prismaInvestmentRequestNotifier,
);
const updateInvestmentRequestUseCase = new UpdateInvestmentRequest(
  prismaInvestmentRequestRepository,
  prismaInvestmentRequestNotifier,
);

export const listInvestmentRequests: RequestHandler = async (request, response) => {
  const pagination = paginationFromQuery(request.query);
  const result = await listInvestmentRequestsUseCase.execute({
    pagination,
    viewer: { id: request.user!.id, role: request.user!.role },
  });
  response.json(result);
};

export const getInvestmentRequest: RequestHandler = async (request, response) => {
  const item = await getInvestmentRequestUseCase.execute(
    getRouteParam(request, "id"),
    request.user!.id,
    request.user!.role,
  );
  response.json({ data: item });
};

export const createInvestmentRequest: RequestHandler = async (request, response) => {
  const input = investmentRequestCreateSchema.parse(request.body);
  const item = await createInvestmentRequestUseCase.execute(input, request.user!.id);
  response.status(201).json({ data: item });
};

export const updateInvestmentRequest: RequestHandler = async (request, response) => {
  const input = investmentRequestUpdateSchema.parse(request.body);
  const item = await updateInvestmentRequestUseCase.execute(
    getRouteParam(request, "id"),
    input,
    { id: request.user!.id, role: request.user!.role },
  );
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
