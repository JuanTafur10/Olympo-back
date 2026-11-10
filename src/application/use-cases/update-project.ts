import { randomUUID } from "node:crypto";
import { HttpError } from "../../errors/http-error.js";
import type { ProjectRepository, ProjectUpdateData } from "../../domain/repository/project.repository.js";

const slugFor = (title: string) =>
  title.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
    .replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") + "-" + randomUUID().slice(0, 8);

export class UpdateProject {
  constructor(private readonly projects: ProjectRepository) {}

  async execute(id: string, input: ProjectUpdateData, userId: string, role: string) {
    const project = await this.projects.findForManagement(id);
    if (!project || project.status === "DELETED") throw new HttpError(404, "No se encontró el proyecto.");
    if (role !== "ADMIN" && project.ownerId !== userId) {
      throw new HttpError(403, "Solo puedes gestionar los proyectos que creaste.");
    }
    if (input.categoryId && !(await this.projects.hasActiveCategory(input.categoryId))) {
      throw new HttpError(400, "Selecciona una categoría activa.");
    }
    return this.projects.update(id, input, input.title ? slugFor(input.title) : undefined);
  }
}