import type { ProjectRepository, ProjectViewerRole } from "../../domain/repository/project.repository.js";

interface ListProjectsInput {
  pagination: { currentPage: number; limit: number };
  viewer: { id?: string; role: ProjectViewerRole };
  q?: string;
  categoryId?: string;
  status?: "DRAFT" | "PUBLISHED" | "CLOSED";
}

export class ListProjects {
  constructor(private readonly projects: ProjectRepository) {}

  async execute(input: ListProjectsInput) {
    const { pagination, ...filters } = input;
    const { data, total } = await this.projects.list({
      ...filters,
      skip: (pagination.currentPage - 1) * pagination.limit,
      take: pagination.limit,
    });

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