import { Router } from "express";
import { allowRoles, authenticate } from "../middleware/authentication.js";
import { deleteUser, getMe, getUser, listUsers, updateUser } from "../controllers/user.controller.js";

export const userRoutes = Router();

userRoutes.use(authenticate);
userRoutes.get("/me", getMe);
userRoutes.get("/", allowRoles("ADMIN"), listUsers);
userRoutes.get("/:id", allowRoles("ADMIN"), getUser);
userRoutes.patch("/:id", updateUser);
userRoutes.delete("/:id", allowRoles("ADMIN"), deleteUser);
