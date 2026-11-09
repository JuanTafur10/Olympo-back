import "dotenv/config";
import cors from "cors";
import express from "express";
import helmet from "helmet";
import { env } from "./config/env.js";
import { errorHandler } from "./middleware/error-handler.js";
import { apiRouter } from "./routes/api.routes.js";

export const app = express();

app.disable("x-powered-by");
app.use(helmet());
app.use(cors({ origin: env.CORS_ORIGIN.split(",").map((origin) => origin.trim()) }));
app.use(express.json({ limit: "1mb" }));
app.use("/api", apiRouter);
app.use("/api/v1", apiRouter);
app.use((_request, response) => {
  response.status(404).json({ error: { message: "La ruta solicitada no existe." } });
});
app.use(errorHandler);
