import { Router } from "express";
import { authRoutes } from "./auth.routes.js";
import { categoryRoutes } from "./category.routes.js";
import { investmentRequestRoutes } from "./investment-request.routes.js";
import { projectRoutes } from "./project.routes.js";
import { userRoutes } from "./user.routes.js";

export const apiRouter = Router();

apiRouter.get("/health", (_request, response) => {
  response.json({ data: { status: "ok", service: "olympo-backend" } });
});
apiRouter.use("/auth", authRoutes);
apiRouter.use("/users", userRoutes);
apiRouter.use("/categories", categoryRoutes);
apiRouter.use("/projects", projectRoutes);
apiRouter.use("/investment-requests", investmentRequestRoutes);
