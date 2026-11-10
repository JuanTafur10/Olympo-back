import { HttpError } from "../../errors/http-error.js";
import type { ProjectViewerRole, ProjectRepository } from "../../domain/repository/project.repository.js";

export class GetProject {
  constructor(private readonly projects: ProjectRepository) {}

  async execute(id: string, viewer: { id?: string; role: ProjectViewerRole }) {
    const project = await this.projects.findByIdWithAccess(id);
    if (!project || project.status === "DELETED") {
      throw new HttpError(404, "No se encontró el proyecto.");
    }
    const canSeeDraft = viewer.role === "ADMIN"
      || (viewer.role === "OWNER" && viewer.id === project.ownerId);
    if (project.status !== "PUBLISHED" && !canSeeDraft) {
      throw new HttpError(404, "No se encontró el proyecto.");
    }
    return project.data;
  }
}