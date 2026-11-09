import { Router } from "express";
import {
  createProject,
  deleteProject,
  getProject,
  listProjects,
  uploadProjectImage,
  updateProject,
} from "../controllers/project.controller.js";
import { allowRoles, authenticate, optionalAuthenticate } from "../middleware/authentication.js";
import { imageUpload } from "../middleware/image-upload.js";

export const projectRoutes = Router();

projectRoutes.get("/", optionalAuthenticate, listProjects);
projectRoutes.get("/:id", optionalAuthenticate, getProject);
projectRoutes.post("/", authenticate, allowRoles("OWNER", "ADMIN"), createProject);
projectRoutes.post("/:id/image", authenticate, allowRoles("OWNER", "ADMIN"), imageUpload, uploadProjectImage);
projectRoutes.patch("/:id", authenticate, allowRoles("OWNER", "ADMIN"), updateProject);
projectRoutes.delete("/:id", authenticate, allowRoles("OWNER", "ADMIN"), deleteProject);
