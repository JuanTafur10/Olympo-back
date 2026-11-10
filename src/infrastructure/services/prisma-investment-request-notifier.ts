import { prisma } from "../../config/database.js";
import type {
  InvestmentRequestNotifier,
  NewInvestmentRequestNotice,
} from "../../domain/services/investment-request-notifier.js";

export class PrismaInvestmentRequestNotifier implements InvestmentRequestNotifier {
  async notifyNewRequest(notice: NewInvestmentRequestNotice): Promise<void> {
    await prisma.notification.create({
      data: {
        userId: notice.ownerId,
        title: "Nueva solicitud de inversión",
        message: `Recibiste una solicitud para el proyecto ${notice.projectTitle}.`,
        type: "investment_request",
        routeDestination: "/solicitudes",
        metadata: { investmentRequestId: notice.requestId, projectId: notice.projectId },
      },
    });
  }
}

export const prismaInvestmentRequestNotifier = new PrismaInvestmentRequestNotifier();