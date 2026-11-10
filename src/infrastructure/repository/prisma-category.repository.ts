import { prisma } from "../../config/database.js";
import type { CategoryListItem, CategoryRecord, CategoryRepository } from "../../domain/repository/category.repository.js";

export class PrismaCategoryRepository implements CategoryRepository {
  countActive() {
    return prisma.category.count({ where: { status: "ACTIVE" } });
  }

  async findActivePage(skip: number, take: number): Promise<CategoryListItem[]> {
    return prisma.category.findMany({
      where: { status: "ACTIVE" },
      include: {
        _count: {
          select: { projects: { where: { status: { not: "DELETED" } } } },
        },
      },
      orderBy: { name: "asc" },
      skip,
      take,
    });
  }

  findActiveById(id: string): Promise<CategoryRecord | null> {
    return prisma.category.findFirst({ where: { id, status: "ACTIVE" } });
  }

  create(input: { name: string; description?: string }, slug: string): Promise<CategoryRecord> {
    return prisma.category.create({ data: { ...input, slug } });
  }

  update(id: string, input: { name?: string; description?: string; slug?: string }): Promise<CategoryRecord> {
    return prisma.category.update({ where: { id }, data: input });
  }

  countProjectsNotDeleted(categoryId: string) {
    return prisma.project.count({
      where: { categoryId, status: { not: "DELETED" } },
    });
  }

  async deactivate(id: string): Promise<void> {
    await prisma.category.update({ where: { id }, data: { status: "INACTIVE" } });
  }
}

export const prismaCategoryRepository = new PrismaCategoryRepository();