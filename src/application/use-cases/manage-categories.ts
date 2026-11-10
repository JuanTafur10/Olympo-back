import { randomUUID } from "node:crypto";
import { HttpError } from "../../errors/http-error.js";
import type { CategoryRepository } from "../../domain/repository/category.repository.js";

const slugFor = (name: string) =>
  name.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") + "-" + randomUUID().slice(0, 6);

export class ManageCategories {
  constructor(private readonly categories: CategoryRepository) {}

  async get(id: string) {
    const category = await this.categories.findActiveById(id);
    if (!category) throw new HttpError(404, "No se encontró la categoría.");
    return category;
  }

  create(input: { name: string; description?: string }) {
    return this.categories.create(input, slugFor(input.name));
  }

  async update(id: string, input: { name?: string; description?: string }) {
    await this.get(id);
    return this.categories.update(id, {
      ...input,
      ...(input.name ? { slug: slugFor(input.name) } : {}),
    });
  }

  async deactivate(id: string) {
    await this.get(id);
    const projectCount = await this.categories.countProjectsNotDeleted(id);
    if (projectCount > 0) {
      throw new HttpError(409, "La categoría tiene proyectos activos y no se puede desactivar.");
    }
    await this.categories.deactivate(id);
  }
}