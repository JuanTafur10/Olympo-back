export interface CategoryListItem {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  status: "ACTIVE" | "INACTIVE";
  createdAt: Date;
  updatedAt: Date;
  _count: { projects: number };
}

export interface CategoryRepository {
  countActive(): Promise<number>;
  findActivePage(skip: number, take: number): Promise<CategoryListItem[]>;
}