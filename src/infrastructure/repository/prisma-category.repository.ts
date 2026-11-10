import { prisma } from "../../config/database.js";
import type { CategoryListItem, CategoryRepository } from "../../domain/repository/category.repository.js";

export class PrismaCategoryRepository implements CategoryRepository {
  countActive() {
    return prisma.category.count({ where: { status: "ACTIVE" } });
  }

  async findActivePage(skip: number, take: number): Promise<CategoryListItem[]> {
    const categories = await prisma.category.findMany({
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
    return categories;
  }
}

export const prismaCategoryRepository = new PrismaCategoryRepository();