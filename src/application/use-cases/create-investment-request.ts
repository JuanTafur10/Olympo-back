import { HttpError } from "../../errors/http-error.js";
import type { InvestmentRequestRepository } from "../../domain/repository/investment-request.repository.js";
import type { InvestmentRequestNotifier } from "../../domain/services/investment-request-notifier.js";
import type { InvestmentRequestCreateData } from "../../domain/repository/investment-request.repository.js";

export class CreateInvestmentRequest {
  constructor(
    private readonly requests: InvestmentRequestRepository,
    private readonly notifier: InvestmentRequestNotifier,
  ) {}

  async execute(input: InvestmentRequestCreateData, investorId: string) {
    const project = await this.requests.findPublishedProject(input.projectId);
    if (!project) throw new HttpError(404, "No se encontró un proyecto publicado.");
    if (project.ownerId === investorId) {
      throw new HttpError(400, "No puedes enviar una solicitud a tu propio proyecto.");
    }

    const created = await this.requests.create(input, investorId);
    await this.notifier.notifyNewRequest({
      ownerId: project.ownerId,
      projectTitle: project.title,
      projectId: project.id,
      requestId: created.id,
    });
    return created.data;
  }
}