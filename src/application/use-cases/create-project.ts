import { randomUUID } from "node:crypto";
import { HttpError } from "../../errors/http-error.js";
import type { ProjectCreateData, ProjectRepository } from "../../domain/repository/project.repository.js";

const slugFor = (title: string) =>
  title.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") + "-" + randomUUID().slice(0, 8);

export class CreateProject {
  constructor(private readonly projects: ProjectRepository) {}

  async execute(input: ProjectCreateData, ownerId: string) {
    const categoryExists = await this.projects.hasActiveCategory(input.categoryId);
    if (!categoryExists) throw new HttpError(400, "Selecciona una categoría activa.");
    return this.projects.create(input, ownerId, slugFor(input.title));
  }
}