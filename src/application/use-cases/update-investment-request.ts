import { HttpError } from "../../errors/http-error.js";
import type { InvestmentRequestRepository, InvestmentRequestUpdateData } from "../../domain/repository/investment-request.repository.js";
import type { InvestmentRequestNotifier } from "../../domain/services/investment-request-notifier.js";

export class UpdateInvestmentRequest {
  constructor(
    private readonly requests: InvestmentRequestRepository,
    private readonly notifier: InvestmentRequestNotifier,
  ) {}

  async execute(id: string, input: Omit<InvestmentRequestUpdateData, "reviewerId">, actor: { id: string; role: string }) {
    const current = await this.requests.findForUpdate(id);
    if (!current || current.status === "DELETED") {
      throw new HttpError(404, "No se encontró la solicitud.");
    }

    const isAdmin = actor.role === "ADMIN";
    const isInvestor = current.investorId === actor.id;
    const isProjectOwner = current.projectOwnerId === actor.id;
    if (!isAdmin && !isInvestor && !isProjectOwner) {
      throw new HttpError(403, "No tienes permiso para cambiar esta solicitud.");
    }

    let data: InvestmentRequestUpdateData;
    if (isAdmin) {
      data = { ...input, ...(input.status ? { reviewerId: actor.id } : {}) };
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
      data = { status: input.status, reviewerId: actor.id };
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

    const updated = await this.requests.update(id, data);
    if (input.status && input.status !== current.status && (input.status === "APPROVED" || input.status === "REJECTED")) {
      await this.notifier.notifyStatusUpdate({
        investorId: current.investorId,
        projectTitle: updated.projectTitle,
        requestId: updated.id,
        status: input.status,
      });
    }
    return updated.data;
  }
}