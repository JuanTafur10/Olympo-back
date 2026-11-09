import type { Request } from "express";
import { HttpError } from "../errors/http-error.js";

export const getRouteParam = (request: Request, name: string): string => {
  const value = request.params[name];
  if (typeof value !== "string") throw new HttpError(400, "El identificador de la ruta no es válido.");
  return value;
};
