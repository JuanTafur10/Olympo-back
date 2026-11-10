import type { CategoryRepository } from "../../domain/repository/category.repository.js";

interface PaginationInput {
  currentPage: number;
  limit: number;
}

export class ListCategories {
  constructor(private readonly categories: CategoryRepository) {}

  async execute(pagination: PaginationInput) {
    const skip = (pagination.currentPage - 1) * pagination.limit;
    const [total, data] = await Promise.all([
      this.categories.countActive(),
      this.categories.findActivePage(skip, pagination.limit),
    ]);

    return {
      data,
      pagination: {
        ...pagination,
        total,
        totalPages: Math.ceil(total / pagination.limit),
      },
    };
  }
}