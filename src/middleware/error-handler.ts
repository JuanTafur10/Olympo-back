import type { ErrorRequestHandler } from "express";
import { Prisma } from "../generated/prisma/client.js";
import { ZodError } from "zod";
import { HttpError } from "../errors/http-error.js";

export const errorHandler: ErrorRequestHandler = (error, _request, response, _next) => {
  if (error instanceof HttpError) {
    response.status(error.statusCode).json({
      error: { message: error.message, details: error.details },
    });
    return;
  }

  if (error instanceof ZodError) {
    response.status(400).json({
      error: {
        message: "Hay datos que necesitan corrección.",
        details: error.issues.map((issue) => ({
          field: issue.path.join("."),
          message: issue.message,
        })),
      },
    });
    return;
  }

  if (error instanceof Prisma.PrismaClientKnownRequestError) {
    if (error.code === "P2002") {
      response.status(409).json({ error: { message: "Ese dato ya está registrado." } });
      return;
    }
    if (error.code === "P2025") {
      response.status(404).json({ error: { message: "No se encontró el registro." } });
      return;
    }
    if (error.code === "P2003") {
      response.status(409).json({ error: { message: "El registro está relacionado con otros datos." } });
      return;
    }
  }

  const message = error instanceof Error ? error.message : "Error interno del servidor.";
  console.error(error);
  response.status(500).json({ error: { message: "Ocurrió un error interno." } });
};
