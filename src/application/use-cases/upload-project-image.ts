import { HttpError } from "../../errors/http-error.js";
import type { ProjectRepository } from "../../domain/repository/project.repository.js";
import type { ProjectImageFile, ProjectImageStorage } from "../../domain/services/project-image-storage.js";

export class UploadProjectImage {
  constructor(
    private readonly projects: ProjectRepository,
    private readonly storage: ProjectImageStorage,
  ) {}

  async execute(id: string, file: ProjectImageFile, userId: string, role: string) {
    const project = await this.projects.findForManagement(id);
    if (!project || project.status === "DELETED") throw new HttpError(404, "No se encontró el proyecto.");
    if (role !== "ADMIN" && project.ownerId !== userId) {
      throw new HttpError(403, "Solo puedes gestionar los proyectos que creaste.");
    }
    const imageUrl = await this.storage.upload(id, file);
    return this.projects.updateImage(id, imageUrl);
  }
}