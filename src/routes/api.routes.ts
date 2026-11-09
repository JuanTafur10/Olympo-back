import { Router } from "express";
import { authRoutes } from "./auth.routes.js";
import { userRoutes } from "./user.routes.js";

export const apiRouter = Router();

apiRouter.get("/health", (_request, response) => {
  response.json({ data: { status: "ok", service: "olympo-backend" } });
});
apiRouter.use("/auth", authRoutes);
apiRouter.use("/users", userRoutes);
