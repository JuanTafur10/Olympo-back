export type ProjectViewerRole = "ADMIN" | "OWNER" | "USER";

export interface ProjectListQuery {
  skip: number;
  take: number;
  viewer: { id?: string; role: ProjectViewerRole };
  q?: string;
  categoryId?: string;
  status?: "DRAFT" | "PUBLISHED" | "CLOSED";
}

export interface ProjectCreateData {
  title: string;
  description: string;
  categoryId: string;
  targetAmount: number;
  status: "DRAFT" | "PUBLISHED";
}

export interface ProjectRecord {
  id: string;
  ownerId: string;
  status: "DRAFT" | "PUBLISHED" | "CLOSED" | "DELETED";
}

export interface ProjectUpdateData {
  title?: string;
  description?: string;
  categoryId?: string;
  targetAmount?: number;
  status?: "DRAFT" | "PUBLISHED" | "CLOSED";
}
export interface ProjectRepository {
  list(query: ProjectListQuery): Promise<{ data: unknown[]; total: number }>;
  hasActiveCategory(categoryId: string): Promise<boolean>;
  create(input: ProjectCreateData, ownerId: string, slug: string): Promise<unknown>;
  findForManagement(id: string): Promise<ProjectRecord | null>;
  update(id: string, input: ProjectUpdateData, slug?: string): Promise<unknown>;
  deleteSoft(id: string): Promise<void>;
  updateImage(id: string, imageUrl: string): Promise<unknown>;
}