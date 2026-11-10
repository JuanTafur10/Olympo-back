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
  async findById(id: string) {
    const item = await prisma.investmentRequest.findUnique({
      where: { id },
      include: {
        project: { select: { id: true, title: true, imageUrl: true, ownerId: true } },
        investor: { select: { id: true, name: true } },
      },
    });
    if (!item) return null;
    return {
      id: item.id,
      investorId: item.investorId,
      projectOwnerId: item.project.ownerId,
      status: item.status,
      data: item,
    };
  }
  findPublishedProject(projectId: string) {
    return prisma.project.findFirst({
      where: { id: projectId, status: "PUBLISHED" },
      select: { id: true, title: true, ownerId: true },
    });
  }

  async create(input: import("../../domain/repository/investment-request.repository.js").InvestmentRequestCreateData, investorId: string) {
    const item = await prisma.investmentRequest.create({
      data: { ...input, investorId },
      include: { project: { select: { id: true, title: true } } },
    });
    return { id: item.id, data: item };
  }
}

export const prismaInvestmentRequestRepository = new PrismaInvestmentRequestRepository();