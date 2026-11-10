import type { Prisma } from "../../generated/prisma/client.js";
import { prisma } from "../../config/database.js";
import type {
  InvestmentRequestListQuery,
  InvestmentRequestRepository,
} from "../../domain/repository/investment-request.repository.js";

export class PrismaInvestmentRequestRepository implements InvestmentRequestRepository {
  async list(query: InvestmentRequestListQuery) {
    const visibility: Prisma.InvestmentRequestWhereInput = query.viewer.role === "ADMIN"
      ? {}
      : query.viewer.role === "OWNER"
        ? { project: { ownerId: query.viewer.id } }
        : { investorId: query.viewer.id };
    const where: Prisma.InvestmentRequestWhereInput = {
      AND: [visibility, { status: { not: "DELETED" } }],
    };
    const [total, data] = await Promise.all([
      prisma.investmentRequest.count({ where }),
      prisma.investmentRequest.findMany({
        where,
        include: {
          project: {
            select: {
              id: true, title: true, imageUrl: true, ownerId: true, targetAmount: true,
              owner: { select: { id: true, name: true, email: true } },
            },
          },
          investor: { select: { id: true, name: true, email: true } },
        },
        orderBy: { createdAt: "desc" },
        skip: query.skip,
        take: query.take,
      }),
    ]);
    return { data, total };
  }
}

export const prismaInvestmentRequestRepository = new PrismaInvestmentRequestRepository();