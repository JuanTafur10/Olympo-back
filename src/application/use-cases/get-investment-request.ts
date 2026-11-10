import { HttpError } from "../../errors/http-error.js";
import type { InvestmentRequestRepository } from "../../domain/repository/investment-request.repository.js";

export class GetInvestmentRequest {
  constructor(private readonly requests: InvestmentRequestRepository) {}

  async execute(id: string, userId: string, role: string) {
    const request = await this.requests.findById(id);
    if (!request || request.status === "DELETED") {
      throw new HttpError(404, "No se encontró la solicitud.");
    }
    const canSee = role === "ADMIN"
      || request.investorId === userId
      || request.projectOwnerId === userId;
    if (!canSee) throw new HttpError(403, "No tienes permiso para ver esta solicitud.");
    return request.data;
  }
}