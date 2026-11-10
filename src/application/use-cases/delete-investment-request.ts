import { HttpError } from "../../errors/http-error.js";
import type { InvestmentRequestRepository } from "../../domain/repository/investment-request.repository.js";

export class DeleteInvestmentRequest {
  constructor(private readonly requests: InvestmentRequestRepository) {}

  async execute(id: string, userId: string, role: string): Promise<void> {
    const current = await this.requests.findForUpdate(id);
    if (!current || current.status === "DELETED") {
      throw new HttpError(404, "No se encontró la solicitud.");
    }
    const canDelete = role === "ADMIN"
      || current.projectOwnerId === userId
      || (current.investorId === userId && current.status === "PENDING");
    if (!canDelete) throw new HttpError(403, "No tienes permiso para eliminar esta solicitud.");
    await this.requests.deleteSoft(id);
  }
}