import { Router } from "express";

export const apiRouter = Router();

apiRouter.get("/health", (_request, response) => {
  response.json({ data: { status: "ok", service: "olympo-backend" } });
});
