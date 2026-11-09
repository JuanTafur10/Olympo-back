import { Router } from "express";
import {
  createCategory,
  deleteCategory,
  getCategory,
  listCategories,
  updateCategory,
} from "../controllers/category.controller.js";
import { allowRoles, authenticate } from "../middleware/authentication.js";

export const categoryRoutes = Router();

categoryRoutes.get("/", listCategories);
categoryRoutes.get("/:id", getCategory);
categoryRoutes.post("/", authenticate, allowRoles("ADMIN"), createCategory);
categoryRoutes.patch("/:id", authenticate, allowRoles("ADMIN"), updateCategory);
categoryRoutes.delete("/:id", authenticate, allowRoles("ADMIN"), deleteCategory);
