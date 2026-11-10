import type { Prisma } from "../../generated/prisma/client.js";
import { prisma } from "../../config/database.js";
import type { ProjectListQuery, ProjectRepository } from "../../domain/repository/project.repository.js";

export class PrismaProjectRepository implements ProjectRepository {
  async list(query: ProjectListQuery) {
    const search = query.q
      ? { OR: [
          { title: { contains: query.q, mode: "insensitive" as const } },
          { description: { contains: query.q, mode: "insensitive" as const } },
        ] }
      : {};
    const visibility: Prisma.ProjectWhereInput = query.viewer.role === "ADMIN"
      ? {}
      : query.viewer.role === "OWNER"
        ? { OR: [
            { status: "PUBLISHED" },
            ...(query.viewer.id ? [{ ownerId: query.viewer.id }] : []),
          ] }
        : { status: "PUBLISHED" };
    const where: Prisma.ProjectWhereInput = {
      AND: [
        { status: { not: "DELETED" } },
        visibility,
        search,
        ...(query.categoryId ? [{ categoryId: query.categoryId }] : []),
        ...(query.status ? [{ status: query.status }] : []),
      ],
    };
    const [total, data] = await Promise.all([
      prisma.project.count({ where }),
      prisma.project.findMany({
        where,
        include: {
          category: true,
          owner: { select: { id: true, name: true } },
        },
        orderBy: { createdAt: "desc" },
        skip: query.skip,
        take: query.take,
      }),
    ]);
    return { data, total };
  }
  async hasActiveCategory(categoryId: string): Promise<boolean> {
    const category = await prisma.category.findFirst({
      where: { id: categoryId, status: "ACTIVE" },
      select: { id: true },
    });
    return Boolean(category);
  }

  create(input: import("../../domain/repository/project.repository.js").ProjectCreateData, ownerId: string, slug: string) {
    return prisma.project.create({
      data: { ...input, ownerId, slug },
      include: { category: true },
    });
  }
}

export const prismaProjectRepository = new PrismaProjectRepository();