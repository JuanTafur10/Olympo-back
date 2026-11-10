export type ProjectViewerRole = "ADMIN" | "OWNER" | "USER";

export interface ProjectListQuery {
  skip: number;
  take: number;
  viewer: { id?: string; role: ProjectViewerRole };
  q?: string;
  categoryId?: string;
  status?: "DRAFT" | "PUBLISHED" | "CLOSED";
}

export interface ProjectRepository {
  list(query: ProjectListQuery): Promise<{ data: unknown[]; total: number }>;
}