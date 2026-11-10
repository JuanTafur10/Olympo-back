export interface CategoryRecord {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  status: "ACTIVE" | "INACTIVE";
  createdAt: Date;
  updatedAt: Date;
}

export interface CategoryListItem extends CategoryRecord {
  _count: { projects: number };
}

export interface CategoryRepository {
  countActive(): Promise<number>;
  findActivePage(skip: number, take: number): Promise<CategoryListItem[]>;
  findActiveById(id: string): Promise<CategoryRecord | null>;
  create(input: { name: string; description?: string }, slug: string): Promise<CategoryRecord>;
  update(id: string, input: { name?: string; description?: string; slug?: string }): Promise<CategoryRecord>;
  countProjectsNotDeleted(categoryId: string): Promise<number>;
  deactivate(id: string): Promise<void>;
}