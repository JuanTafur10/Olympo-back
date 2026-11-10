import { HttpError } from "../../errors/http-error.js";
import type { ProjectRepository } from "../../domain/repository/project.repository.js";

export class DeleteProject {
  constructor(private readonly projects: ProjectRepository) {}

  async execute(id: string, userId: string, role: string): Promise<void> {
    const project = await this.projects.findForManagement(id);
    if (!project || project.status === "DELETED") throw new HttpError(404, "No se encontró el proyecto.");
    if (role !== "ADMIN" && project.ownerId !== userId) {
      throw new HttpError(403, "Solo puedes gestionar los proyectos que creaste.");
    }
    await this.projects.deleteSoft(id);
  }
}